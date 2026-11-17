from django.db import transaction
from django.core.cache import cache
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import AccountStatus, User, UserRole
from apps.common.validators import UZ_PHONE_REGEX
from apps.profiles.models import EmployerType


class UserSummarySerializer(serializers.ModelSerializer):
    is_worker = serializers.BooleanField(read_only=True)
    is_employer = serializers.BooleanField(read_only=True)
    is_verified_worker = serializers.BooleanField(read_only=True)
    worker_profile_id = serializers.SerializerMethodField()
    employer_profile_id = serializers.SerializerMethodField()
    worker_verification_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "email",
            "full_name",
            "role",
            "has_worker_role",
            "has_employer_role",
            "is_worker",
            "is_employer",
            "is_verified_worker",
            "worker_profile_id",
            "employer_profile_id",
            "worker_verification_status",
            "is_phone_verified",
            "account_status",
            "created_at",
        ]
        read_only_fields = fields

    def get_worker_profile_id(self, obj):
        wp = getattr(obj, "worker_profile", None)
        return str(wp.id) if wp else None

    def get_employer_profile_id(self, obj):
        ep = getattr(obj, "employer_profile", None)
        return str(ep.id) if ep else None

    def get_worker_verification_status(self, obj):
        wp = getattr(obj, "worker_profile", None)
        return wp.verification_status if wp else None


class UserAccountUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "email"]

    def validate_email(self, value):
        if value is None or value.strip() == "":
            return None
        email = value.strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This email address is already in use.")
        return email


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(regex=UZ_PHONE_REGEX, max_length=20)
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    full_name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=[UserRole.WORKER, UserRole.EMPLOYER], default=UserRole.WORKER)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    enable_worker = serializers.BooleanField(required=False, default=False)
    enable_employer = serializers.BooleanField(required=False, default=False)
    employer_type = serializers.ChoiceField(choices=EmployerType.choices, required=False, default=EmployerType.INDIVIDUAL)
    company_name = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    location = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    district = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs.get("role") == UserRole.EMPLOYER or attrs.get("enable_employer"):
            if attrs.get("employer_type") == EmployerType.COMPANY and not attrs.get("company_name", "").strip():
                raise serializers.ValidationError({"company_name": "Company name is required for COMPANY employers."})
        return attrs


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(regex=UZ_PHONE_REGEX, max_length=20)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=False)


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(regex=UZ_PHONE_REGEX, max_length=20)
    purpose = serializers.ChoiceField(choices=["VERIFY_PHONE", "PASSWORD_RESET"], default="VERIFY_PHONE")


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(regex=UZ_PHONE_REGEX, max_length=20)
    otp = serializers.RegexField(regex=r"^[0-9]{6}$", max_length=6)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(regex=UZ_PHONE_REGEX, max_length=20)


class PasswordResetConfirmSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(regex=UZ_PHONE_REGEX, max_length=20)
    otp = serializers.RegexField(regex=r"^[0-9]{6}$", max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)


class EnableRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[UserRole.WORKER, UserRole.EMPLOYER])
    employer_type = serializers.ChoiceField(choices=EmployerType.choices, required=False, default=EmployerType.INDIVIDUAL)
    company_name = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("You must explicitly confirm account deletion (confirm=true).")
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["has_worker_role"] = user.is_worker
        token["has_employer_role"] = user.is_employer
        token["token_version"] = user.token_version
        token["phone_number"] = user.phone_number
        return token


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    @transaction.atomic
    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        user_id = refresh.get("user_id")
        token_version = refresh.get("token_version")

        user = User.objects.select_for_update().filter(id=user_id).first()
        if refresh.get("session_id") and cache.get(f"revoked_session:{refresh['session_id']}"):
            raise InvalidToken("Session has been revoked.")
        if not user or not user.is_active or user.is_anonymized or user.account_status != AccountStatus.ACTIVE:
            raise InvalidToken("User account is inactive, suspended, or deleted.")
        if token_version != user.token_version:
            raise InvalidToken("Refresh token has been invalidated due to password change or logout-all.")

        data = super().validate(attrs)
        # Ensure rotated access token includes current user claims
        new_access = RefreshToken(data["refresh"]).access_token if "refresh" in data else None
        if new_access:
            new_access["role"] = user.role
            new_access["has_worker_role"] = user.is_worker
            new_access["has_employer_role"] = user.is_employer
            new_access["token_version"] = user.token_version
            new_access["phone_number"] = user.phone_number
            data["access"] = str(new_access)
        return data
