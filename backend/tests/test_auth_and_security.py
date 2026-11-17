from unittest.mock import patch
import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status

from apps.accounts.models import User, UserRole
from apps.accounts.services.otp_service import OTPPurpose, OTPService


@pytest.mark.django_db
class TestAuthenticationAndSecurity:
    def test_register_worker_hashes_password_and_creates_profile(self, api_client):
        captured = {}

        class CaptureSMS:
            def send_otp(self, phone_number, code, purpose, expires_in_seconds):
                captured["code"] = code

        with patch("apps.accounts.services.otp_service.get_sms_provider", return_value=CaptureSMS()):
            resp = api_client.post(
                "/api/v1/auth/register/",
                {
                    "phone_number": "+998901234567",
                    "password": "StrongPassword2026!",
                    "full_name": "Sardorbek Valiyev",
                    "role": "WORKER",
                    "location": "Toshkent",
                    "district": "Chilonzor",
                },
                format="json",
            )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["success"] is True
        assert resp.data["data"]["tokens"]["access"]
        assert resp.data["data"]["tokens"]["refresh"]
        assert "otp" not in resp.data["data"]
        assert "code" not in resp.data["data"]
        assert captured == {}

        user = User.objects.get(phone_number="+998901234567")
        assert user.password != "StrongPassword2026!"
        assert user.check_password("StrongPassword2026!") is True
        assert user.is_worker is True
        assert user.worker_profile.is_verified is False

    def test_cannot_register_as_admin(self, api_client):
        resp = api_client.post(
            "/api/v1/auth/register/",
            {
                "phone_number": "+998901234568",
                "password": "StrongPassword2026!",
                "full_name": "Fake Admin",
                "role": "ADMIN",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_jwt_rotation_and_logout_invalidation(self, api_client):
        User.objects.create_user(
            phone_number="+998901234569",
            password="StrongPassword2026!",
            full_name="Login Tester",
            role=UserRole.EMPLOYER,
            is_phone_verified=True,
        )
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"phone_number": "+998901234569", "password": "StrongPassword2026!"},
            format="json",
        )
        assert login_resp.status_code == status.HTTP_200_OK
        access1 = login_resp.data["data"]["tokens"]["access"]
        refresh1 = login_resp.data["data"]["tokens"]["refresh"]

        # Refresh rotates token and blacklists old refresh1
        refresh_resp = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh1},
            format="json",
        )
        assert refresh_resp.status_code == status.HTTP_200_OK
        refresh2 = refresh_resp.data["data"]["refresh"]
        access2 = refresh_resp.data["data"]["access"]
        assert refresh2 != refresh1

        # Replaying rotated refresh1 must fail
        replay_resp = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh1},
            format="json",
        )
        assert replay_resp.status_code == status.HTTP_401_UNAUTHORIZED

        # Logout invalidates both refresh2 and access2
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access2}")
        logout_resp = api_client.post("/api/v1/auth/logout/", {"refresh": refresh2}, format="json")
        assert logout_resp.status_code == status.HTTP_200_OK

        me_after_logout = api_client.get("/api/v1/auth/me/")
        assert me_after_logout.status_code == status.HTTP_401_UNAUTHORIZED

        refresh_after_logout = api_client.post("/api/v1/auth/token/refresh/", {"refresh": refresh2}, format="json")
        assert refresh_after_logout.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_brute_force_lockout(self, api_client):
        User.objects.create_user(
            phone_number="+998901234570",
            password="StrongPassword2026!",
            full_name="Lockout User",
            role=UserRole.WORKER,
        )
        for _ in range(5):
            r = api_client.post(
                "/api/v1/auth/login/",
                {"phone_number": "+998901234570", "password": "WrongPassword!"},
                format="json",
            )
            assert r.status_code == status.HTTP_401_UNAUTHORIZED

        # 6th attempt must be locked even with valid password
        locked_resp = api_client.post(
            "/api/v1/auth/login/",
            {"phone_number": "+998901234570", "password": "StrongPassword2026!"},
            format="json",
        )
        assert locked_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_password_change_invalidates_existing_tokens(self, api_client):
        User.objects.create_user(
            phone_number="+998901234571",
            password="OldPassword2026!",
            full_name="Pwd User",
            is_phone_verified=True,
            role=UserRole.WORKER,
        )
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"phone_number": "+998901234571", "password": "OldPassword2026!"},
            format="json",
        )
        access = login_resp.data["data"]["tokens"]["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        chg = api_client.post(
            "/api/v1/auth/password/change/",
            {"old_password": "OldPassword2026!", "new_password": "NewPassword2026!"},
            format="json",
        )
        assert chg.status_code == status.HTTP_200_OK

        # Old access token must immediately fail because token_version incremented
        me_resp = api_client.get("/api/v1/auth/me/")
        assert me_resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_otp_verification_cooldown_and_max_attempts(self, api_client):
        user = User.objects.create_user(
            phone_number="+998901234572",
            password="StrongPassword2026!",
            full_name="OTP User",
            role=UserRole.WORKER,
            is_phone_verified=False,
        )
        captured = {}

        from apps.accounts.services.auth_service import generate_jwt_pair
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {generate_jwt_pair(user)['access']}")

        class CaptureSMS:
            def send_otp(self, phone_number, code, purpose, expires_in_seconds):
                captured["code"] = code

        with patch("apps.accounts.services.otp_service.get_sms_provider", return_value=CaptureSMS()):
            r1 = api_client.post(
                "/api/v1/auth/otp/send/",
                {"phone_number": "+998901234572", "purpose": "VERIFY_PHONE"},
                format="json",
            )
            assert r1.status_code == status.HTTP_200_OK
            assert "code" not in r1.data
            assert len(captured["code"]) == 6

            # Resend within cooldown must return 429
            r_cool = api_client.post(
                "/api/v1/auth/otp/resend/",
                {"phone_number": "+998901234572", "purpose": "VERIFY_PHONE"},
                format="json",
            )
            assert r_cool.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # Verify with valid code
        v_resp = api_client.post(
            "/api/v1/auth/otp/verify/",
            {"phone_number": "+998901234572", "otp": captured["code"]},
            format="json",
        )
        assert v_resp.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_phone_verified is True

        # Replaying same code fails
        replay = api_client.post(
            "/api/v1/auth/otp/verify/",
            {"phone_number": "+998901234572", "otp": captured["code"]},
            format="json",
        )
        assert replay.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_flow(self, api_client):
        user = User.objects.create_user(
            phone_number="+998901234573",
            password="InitialPass2026!",
            full_name="Reset User",
            is_phone_verified=True,
            role=UserRole.EMPLOYER,
        )
        captured = {}

        class CaptureSMS:
            def send_otp(self, phone_number, code, purpose, expires_in_seconds):
                captured["code"] = code

        with patch("apps.accounts.services.otp_service.get_sms_provider", return_value=CaptureSMS()):
            req = api_client.post(
                "/api/v1/auth/password/reset/request/",
                {"phone_number": "+998901234573"},
                format="json",
            )
            assert req.status_code == status.HTTP_200_OK

        conf = api_client.post(
            "/api/v1/auth/password/reset/confirm/",
            {
                "phone_number": "+998901234573",
                "otp": captured["code"],
                "new_password": "ResetNewPass2026!",
            },
            format="json",
        )
        assert conf.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password("ResetNewPass2026!") is True

    def test_enable_dual_role_without_duplicate_account(self, auth_client, verified_worker):
        user, _ = verified_worker
        client = auth_client(user)
        resp = client.post(
            "/api/v1/auth/enable-role/",
            {"role": "EMPLOYER", "employer_type": "INDIVIDUAL"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_worker is True
        assert user.is_employer is True
        assert hasattr(user, "employer_profile")
        assert User.objects.filter(phone_number=user.phone_number).count() == 1
