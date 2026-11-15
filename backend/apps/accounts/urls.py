from django.urls import path
from apps.accounts.views import (
    ChangePasswordView,
    CustomTokenRefreshView,
    DeleteAccountView,
    EnableComplementaryRoleView,
    LoginView,
    LogoutAllView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    SendOTPView,
    VerifyOTPView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("logout-all/", LogoutAllView.as_view(), name="auth-logout-all"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="auth-token-refresh"),
    path("otp/send/", SendOTPView.as_view(), name="auth-otp-send"),
    path("otp/resend/", SendOTPView.as_view(), name="auth-otp-resend"),
    path("otp/verify/", VerifyOTPView.as_view(), name="auth-otp-verify"),
    path("password/change/", ChangePasswordView.as_view(), name="auth-password-change"),
    path("password/reset/request/", PasswordResetRequestView.as_view(), name="auth-password-reset-request"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("enable-role/", EnableComplementaryRoleView.as_view(), name="auth-enable-role"),
    path("delete-account/", DeleteAccountView.as_view(), name="auth-delete-account"),
]
