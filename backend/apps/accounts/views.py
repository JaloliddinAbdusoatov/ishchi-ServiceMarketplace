import ipaddress
from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.permissions import IsActiveAccount
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    CustomTokenRefreshSerializer,
    DeleteAccountSerializer,
    EnableRoleSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SendOTPSerializer,
    UserAccountUpdateSerializer,
    UserSummarySerializer,
    VerifyOTPSerializer,
)
from apps.accounts.services.auth_service import AuthService, generate_jwt_pair
from apps.accounts.services.otp_service import OTPPurpose, OTPService
from apps.common.responses import error_response, success_response


def _get_client_ip(request) -> str | None:
    remote = request.META.get("REMOTE_ADDR")
    if remote in getattr(settings, "TRUSTED_PROXY_IPS", []):
        try:
            return str(ipaddress.ip_address(request.META.get("HTTP_X_REAL_IP", "")))
        except ValueError:
            pass
    return remote


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        summary="Register User Account",
        description="Creates a WORKER or EMPLOYER user (optionally dual-role) with a hashed password and activates the account immediately. No SMS is sent.",
        request=RegisterSerializer,
        responses={201: UserSummarySerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, tokens = AuthService.register_user(
            ip_address=_get_client_ip(request),
            **serializer.validated_data,
        )
        return success_response(
            data={
                "user": UserSummarySerializer(user).data,
                "tokens": tokens,
            },
            message="Registration successful. Your account is active.",
            status_code=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        summary="Login with Phone & Password",
        description="Authenticates user and returns JWT access & refresh tokens with brute-force lockout protection.",
        request=LoginSerializer,
        responses={200: UserSummarySerializer, 401: OpenApiResponse(description="Invalid credentials")},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, tokens = AuthService.login_user(
            phone_number=serializer.validated_data["phone_number"],
            password=serializer.validated_data["password"],
        )
        return success_response(
            data={
                "user": UserSummarySerializer(user).data,
                "tokens": tokens,
            },
            message="Login successful.",
        )


class LogoutView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="Logout Current Session",
        description="Blacklists submitted refresh token and revokes current access token JTI in Redis.",
        request=LogoutSerializer,
        responses={200: OpenApiResponse(description="Logged out")},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        access_str = auth_header.split()[1] if len(auth_header.split()) == 2 else None
        AuthService.logout_session(
            refresh_token_str=serializer.validated_data.get("refresh"),
            access_token_str=access_str,
            user=request.user,
        )
        return success_response(message="Logged out successfully.")


class LogoutAllView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="Logout All Sessions",
        description="Increments token_version and blacklists all outstanding refresh tokens for the user.",
        responses={200: OpenApiResponse(description="All sessions invalidated")},
        tags=["Authentication"],
    )
    def post(self, request):
        AuthService.logout_all_sessions(request.user)
        return success_response(message="All active sessions have been invalidated.")


class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = CustomTokenRefreshSerializer

    @extend_schema(
        summary="Rotate JWT Refresh Token",
        description="Exchanges a valid refresh token for a rotated refresh + access token pair.",
        tags=["Authentication"],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            return error_response(
                code="invalid_refresh_token",
                message=str(exc),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        return success_response(data=serializer.validated_data, message="Token refreshed.")


class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    @extend_schema(
        summary="Send or Resend OTP",
        description="Dispatches a 6-digit OTP to the phone number with Redis cooldown and rate limiting.",
        request=SendOTPSerializer,
        responses={200: OpenApiResponse(description="OTP dispatched"), 429: OpenApiResponse(description="Rate limit or cooldown")},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = OTPService.send_otp(
            phone_number=serializer.validated_data["phone_number"],
            purpose=serializer.validated_data["purpose"],
            ip_address=_get_client_ip(request),
        )
        if not result["success"]:
            return error_response(
                code=result["error_code"],
                message=result["message"],
                details={"remaining_cooldown": result.get("remaining_cooldown")},
                status_code=result["status_code"],
            )
        return success_response(
            data={
                "cooldown_seconds": result["cooldown_seconds"],
                "expires_in_seconds": result["expires_in_seconds"],
            },
            message=result["message"],
        )


class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        summary="Verify Phone OTP",
        description="Verifies 6-digit OTP and marks the user's phone number as verified.",
        request=VerifyOTPSerializer,
        responses={200: UserSummarySerializer, 400: OpenApiResponse(description="Invalid or expired OTP")},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.verify_phone_otp(
            phone_number=serializer.validated_data["phone_number"],
            otp=serializer.validated_data["otp"],
        )
        return success_response(
            data={"user": UserSummarySerializer(user).data, "tokens": generate_jwt_pair(user)},
            message="Phone number verified successfully.",
        )


class ChangePasswordView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="Change Password",
        description="Changes authenticated user's password and invalidates all existing sessions.",
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description="Password changed")},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.change_password(
            user=request.user,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"],
        )
        return success_response(message="Password changed successfully. Existing tokens have been invalidated.")


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    @extend_schema(
        summary="Request Password Reset OTP",
        description="Dispatches a password reset OTP to the phone number if an active account exists.",
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="Reset OTP dispatched if account exists")},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthService.request_password_reset(
            phone_number=serializer.validated_data["phone_number"],
            ip_address=_get_client_ip(request),
        )
        if not result["success"]:
            return error_response(
                code=result["error_code"],
                message=result["message"],
                details={"remaining_cooldown": result.get("remaining_cooldown")},
                status_code=result["status_code"],
            )
        return success_response(
            data={
                "cooldown_seconds": result["cooldown_seconds"],
                "expires_in_seconds": result["expires_in_seconds"],
            },
            message=result["message"],
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Confirm Password Reset",
        description="Verifies password reset OTP, updates password, and invalidates all existing sessions.",
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description="Password reset successful")},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.confirm_password_reset(
            phone_number=serializer.validated_data["phone_number"],
            otp=serializer.validated_data["otp"],
            new_password=serializer.validated_data["new_password"],
        )
        return success_response(message="Password has been reset successfully.")


class MeView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="Get Current User",
        responses={200: UserSummarySerializer},
        tags=["Authentication"],
    )
    def get(self, request):
        return success_response(data=UserSummarySerializer(request.user).data)

    @extend_schema(
        summary="Update Current User Basic Account Info",
        request=UserAccountUpdateSerializer,
        responses={200: UserSummarySerializer},
        tags=["Authentication"],
    )
    def patch(self, request):
        serializer = UserAccountUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=UserSummarySerializer(request.user).data, message="Account updated.")


class EnableComplementaryRoleView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="Enable Dual Role (Worker <-> Employer)",
        description="Allows an existing WORKER or EMPLOYER to add the complementary marketplace role without duplicate accounts.",
        request=EnableRoleSerializer,
        responses={200: UserSummarySerializer},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = EnableRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.enable_complementary_role(
            user=request.user,
            target_role=serializer.validated_data["role"],
            employer_type=serializer.validated_data["employer_type"],
            company_name=serializer.validated_data["company_name"],
        )
        return success_response(
            data=UserSummarySerializer(user).data,
            message=f"{serializer.validated_data['role']} capability enabled.",
        )


class DeleteAccountView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="Delete & Anonymize Account",
        description=(
            "Permanently anonymizes personal information, revokes all JWT tokens, "
            "records an immutable deletion audit entry, and preserves transaction history."
        ),
        request=DeleteAccountSerializer,
        responses={200: OpenApiResponse(description="Account deleted and anonymized")},
        tags=["Authentication", "Privacy"],
    )
    def post(self, request):
        serializer = DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        audit = AuthService.anonymize_and_delete_account(
            user=request.user,
            password=serializer.validated_data["password"],
            reason=serializer.validated_data.get("reason", ""),
            performed_by=request.user,
            require_password=True,
        )
        return success_response(
            data={"audit_id": str(audit.id), "anonymized_at": audit.created_at},
            message="Account has been deleted and personal data anonymized.",
        )
