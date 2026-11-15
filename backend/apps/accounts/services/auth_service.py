import hashlib
import time
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import AccountDeletionAudit, AccountStatus, User, UserRole
from apps.accounts.services.otp_service import OTPPurpose, OTPService
from apps.accounts.services.locks import increment_bucket
from apps.common.exceptions import BusinessRuleViolation, ConflictError
from apps.profiles.models import EmployerProfile, EmployerType, VerificationStatus, WorkerProfile


def generate_jwt_pair(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["session_id"] = refresh["jti"]
    refresh["role"] = user.role
    refresh["has_worker_role"] = user.is_worker
    refresh["has_employer_role"] = user.is_employer
    refresh["token_version"] = user.token_version
    refresh["phone_number"] = user.phone_number

    access = refresh.access_token
    access["role"] = user.role
    access["has_worker_role"] = user.is_worker
    access["has_employer_role"] = user.is_employer
    access["token_version"] = user.token_version
    access["phone_number"] = user.phone_number

    return {
        "access": str(access),
        "refresh": str(refresh),
        "token_type": "Bearer",
    }


def _blacklist_all_user_tokens(user: User) -> None:
    tokens = OutstandingToken.objects.filter(user=user)
    for outstanding in tokens:
        BlacklistedToken.objects.get_or_create(token=outstanding)


class AuthService:
    """Handles registration, login, brute-force protection, password lifecycle, dual roles, and anonymization."""

    @classmethod
    @transaction.atomic
    def register_user(
        cls,
        phone_number: str,
        password: str,
        full_name: str,
        role: str,
        email: str = None,
        enable_worker: bool = False,
        enable_employer: bool = False,
        employer_type: str = EmployerType.INDIVIDUAL,
        company_name: str = "",
        location: str = "",
        district: str = "",
        ip_address: str = None,
    ) -> tuple[User, dict]:
        if role not in (UserRole.WORKER, UserRole.EMPLOYER):
            raise BusinessRuleViolation(
                "Registration role must be WORKER or EMPLOYER.",
                code="invalid_role",
            )

        if User.objects.filter(phone_number=phone_number, is_anonymized=False).exists():
            raise ConflictError("An account with this phone number already exists.", code="phone_already_exists")

        normalized_email = email.strip().lower() if email and email.strip() else None
        if normalized_email and User.objects.filter(email__iexact=normalized_email).exists():
            raise ConflictError("An account with this email already exists.", code="email_already_exists")

        has_worker = role == UserRole.WORKER or bool(enable_worker)
        has_employer = role == UserRole.EMPLOYER or bool(enable_employer)

        temp_user = User(phone_number=phone_number, full_name=full_name, email=normalized_email, role=role)
        validate_password(password, user=temp_user)

        user = User.objects.create_user(
            phone_number=phone_number,
            password=password,
            role=role,
            email=normalized_email,
            full_name=full_name,
            has_worker_role=has_worker,
            has_employer_role=has_employer,
            is_phone_verified=False,
            is_active=True,
            account_status=AccountStatus.ACTIVE,
        )

        if has_worker:
            WorkerProfile.objects.create(
                user=user,
                full_name=full_name,
                phone_number=phone_number,
                location=location,
                district=district,
                verification_status=VerificationStatus.UNSUBMITTED,
                is_verified=False,
            )

        if has_employer:
            EmployerProfile.objects.create(
                user=user,
                employer_type=employer_type,
                full_name=full_name,
                company_name=company_name if employer_type == EmployerType.COMPANY else "",
                phone_number=phone_number,
                email=normalized_email or "",
                location=location,
                district=district,
            )

        # Product policy: registration activates immediately without sending SMS.
        # Phone ownership remains unverified until an optional OTP check succeeds.
        return user, generate_jwt_pair(user)

    @classmethod
    def login_user(cls, phone_number: str, password: str) -> tuple[User, dict]:
        lock_key = f"login_lockout:{phone_number}"
        fail_key = f"login_fail:{phone_number}"

        if cache.get(lock_key):
            raise BusinessRuleViolation(
                "Account temporarily locked due to too many failed login attempts. Try again later.",
                code="account_locked",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = User.objects.filter(phone_number=phone_number, is_anonymized=False).first()
        if not user or not user.check_password(password):
            fails = increment_bucket(fail_key, getattr(settings, "LOGIN_LOCKOUT_SECONDS", 900))
            max_attempts = getattr(settings, "LOGIN_MAX_ATTEMPTS", 5)
            lockout_seconds = getattr(settings, "LOGIN_LOCKOUT_SECONDS", 900)
            if fails >= max_attempts:
                cache.set(lock_key, True, timeout=lockout_seconds)
            raise BusinessRuleViolation(
                "Invalid phone number or password.",
                code="invalid_credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active or user.account_status != AccountStatus.ACTIVE:
            raise BusinessRuleViolation(
                "This account has been suspended by an administrator.",
                code="account_suspended",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        cache.delete(fail_key)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        tokens = generate_jwt_pair(user)
        return user, tokens

    @classmethod
    def logout_session(cls, refresh_token_str: str = None, access_token_str: str = None, user: User = None) -> None:
        if refresh_token_str:
            try:
                token = RefreshToken(refresh_token_str)
                if user is not None and str(token.get("user_id")) != str(user.pk):
                    raise BusinessRuleViolation("Refresh token belongs to another account.", code="invalid_token")
                token.blacklist()
            except TokenError as exc:
                raise BusinessRuleViolation("Invalid or already blacklisted refresh token.", code="invalid_token") from exc

        if access_token_str:
            try:
                access = AccessToken(access_token_str)
                jti = access.get("jti")
                exp = access.get("exp")
                session_id = access.get("session_id")
                if session_id:
                    ttl = max(1, int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()))
                    cache.set(f"revoked_session:{session_id}", True, timeout=ttl)
                if jti and exp:
                    ttl = max(1, int(exp - time.time()))
                    cache.set(f"revoked_access_jti:{jti}", True, timeout=ttl)
            except TokenError:
                pass

    @classmethod
    @transaction.atomic
    def logout_all_sessions(cls, user: User) -> None:
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        locked_user.token_version += 1
        locked_user.save(update_fields=["token_version", "updated_at"])
        _blacklist_all_user_tokens(locked_user)

    @classmethod
    @transaction.atomic
    def change_password(cls, user: User, old_password: str, new_password: str) -> None:
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if not locked_user.check_password(old_password):
            raise BusinessRuleViolation("Current password is incorrect.", code="invalid_current_password")

        validate_password(new_password, user=locked_user)
        locked_user.set_password(new_password)
        locked_user.token_version += 1
        locked_user.save(update_fields=["password", "token_version", "updated_at"])
        _blacklist_all_user_tokens(locked_user)

    @classmethod
    def request_password_reset(cls, phone_number: str, ip_address: str = None) -> dict:
        # Always dispatch rate-limit check cleanly without leaking account existence
        user_exists = User.objects.filter(
            phone_number=phone_number,
            is_anonymized=False,
            is_active=True,
            account_status=AccountStatus.ACTIVE,
        ).exists()
        if user_exists:
            return OTPService.send_otp(phone_number, purpose=OTPPurpose.PASSWORD_RESET, ip_address=ip_address)
        return {
            "success": True,
            "message": "If an active account exists for this phone number, a reset code has been dispatched.",
            "cooldown_seconds": getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60),
            "expires_in_seconds": getattr(settings, "OTP_EXPIRATION_SECONDS", 300),
            "status_code": 200,
        }

    @classmethod
    @transaction.atomic
    def confirm_password_reset(cls, phone_number: str, otp: str, new_password: str) -> None:
        ok, err_code, err_msg = OTPService.verify_otp(phone_number, otp, purpose=OTPPurpose.PASSWORD_RESET)
        if not ok:
            raise BusinessRuleViolation(err_msg, code=err_code)

        user = User.objects.select_for_update().filter(
            phone_number=phone_number,
            is_anonymized=False,
            is_active=True,
            account_status=AccountStatus.ACTIVE,
        ).first()
        if not user:
            raise BusinessRuleViolation("Account not found or inactive.", code="account_not_found")

        validate_password(new_password, user=user)
        user.set_password(new_password)
        user.token_version += 1
        user.save(update_fields=["password", "token_version", "updated_at"])
        _blacklist_all_user_tokens(user)

    @classmethod
    @transaction.atomic
    def verify_phone_otp(cls, phone_number: str, otp: str) -> User:
        ok, err_code, err_msg = OTPService.verify_otp(phone_number, otp, purpose=OTPPurpose.VERIFY_PHONE)
        if not ok:
            raise BusinessRuleViolation(err_msg, code=err_code)

        user = User.objects.select_for_update().filter(
            phone_number=phone_number,
            is_anonymized=False,
        ).first()
        if not user:
            raise BusinessRuleViolation("User not found.", code="user_not_found")

        if not user.is_active or user.account_status != AccountStatus.ACTIVE:
            raise BusinessRuleViolation("Account is inactive.", code="account_inactive", status_code=403)
        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified", "updated_at"])
        return user

    @classmethod
    @transaction.atomic
    def enable_complementary_role(
        cls,
        user: User,
        target_role: str,
        company_name: str = "",
        employer_type: str = EmployerType.INDIVIDUAL,
    ) -> User:
        if target_role not in (UserRole.WORKER, UserRole.EMPLOYER):
            raise BusinessRuleViolation("Only WORKER or EMPLOYER capability can be enabled.", code="invalid_role")

        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if locked_user.role == UserRole.ADMIN:
            raise BusinessRuleViolation("Administrators cannot add marketplace roles.", code="forbidden_role_switch")

        if target_role == UserRole.WORKER:
            locked_user.has_worker_role = True
            locked_user.save(update_fields=["has_worker_role", "updated_at"])
            WorkerProfile.objects.get_or_create(
                user=locked_user,
                defaults={
                    "full_name": locked_user.full_name or "Worker",
                    "phone_number": locked_user.phone_number or "",
                    "verification_status": VerificationStatus.UNSUBMITTED,
                    "is_verified": False,
                },
            )
        else:
            locked_user.has_employer_role = True
            locked_user.save(update_fields=["has_employer_role", "updated_at"])
            EmployerProfile.objects.get_or_create(
                user=locked_user,
                defaults={
                    "employer_type": employer_type,
                    "full_name": locked_user.full_name or "Employer",
                    "company_name": company_name if employer_type == EmployerType.COMPANY else "",
                    "phone_number": locked_user.phone_number or "",
                    "email": locked_user.email or "",
                },
            )

        return locked_user

    @classmethod
    @transaction.atomic
    def anonymize_and_delete_account(
        cls,
        user: User,
        password: str = None,
        reason: str = "",
        performed_by: User = None,
        require_password: bool = True,
    ) -> AccountDeletionAudit:
        from apps.applications.models import ApplicationStatus, OrderApplication
        from apps.favorites.models import FavoriteOrder, FavoriteWorker
        from apps.invitations.models import InvitationStatus, OrderInvitation
        from apps.orders.models import OrderStatus, ServiceOrder

        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if locked_user.is_anonymized or locked_user.account_status == AccountStatus.DELETED:
            raise BusinessRuleViolation("Account is already deleted and anonymized.", code="already_deleted")

        if require_password:
            if not password or not locked_user.check_password(password):
                raise BusinessRuleViolation("Invalid password confirmation.", code="invalid_password")

        # Partially staffed teams are active even while remaining slots are advertised.
        has_in_progress = ServiceOrder.objects.filter(
            Q(employer__user=locked_user, status=OrderStatus.IN_PROGRESS)
            | (Q(assigned_worker__user=locked_user) | Q(assigned_workers__user=locked_user))
            & Q(status__in=[OrderStatus.PUBLISHED, OrderStatus.PAUSED, OrderStatus.IN_PROGRESS]),
        ).exists()
        if has_in_progress:
            raise BusinessRuleViolation(
                "Cannot delete account while hired on an active order. Complete or cancel active orders first.",
                code="active_orders_in_progress",
            )

        now = timezone.now()
        old_phone = locked_user.phone_number or str(locked_user.id)
        phone_hash = hashlib.sha256(old_phone.encode("utf-8")).hexdigest()
        short_id = str(locked_user.id)[:8]

        # Cancel open employer orders while preserving COMPLETED / historical orders
        if hasattr(locked_user, "employer_profile"):
            ep = locked_user.employer_profile
            ServiceOrder.objects.filter(
                employer=ep,
                status__in=[OrderStatus.DRAFT, OrderStatus.PUBLISHED, OrderStatus.PAUSED],
            ).update(status=OrderStatus.CANCELLED, updated_at=now)
            OrderInvitation.objects.filter(
                employer=ep,
                status=InvitationStatus.PENDING,
            ).update(status=InvitationStatus.CANCELLED, responded_at=now, updated_at=now)

            ep.full_name = f"Deleted Employer {short_id}"
            ep.company_name = ""
            ep.bio = ""
            ep.phone_number = ""
            ep.email = None
            ep.photo = None
            ep.location = ""
            ep.district = ""
            ep.address = ""
            ep.save()

        # Withdraw pending worker applications, cancel pending invitations, scrub worker PII
        if hasattr(locked_user, "worker_profile"):
            wp = locked_user.worker_profile
            OrderApplication.objects.filter(
                worker=wp,
                status=ApplicationStatus.PENDING,
            ).update(status=ApplicationStatus.WITHDRAWN, responded_at=now, updated_at=now)
            OrderInvitation.objects.filter(
                worker=wp,
                status=InvitationStatus.PENDING,
            ).update(status=InvitationStatus.CANCELLED, responded_at=now, updated_at=now)
            wp.worker_categories.all().delete()
            wp.portfolio_items.all().delete()

            wp.full_name = f"Deleted Worker {short_id}"
            wp.bio = ""
            wp.phone_number = ""
            wp.photo = None
            wp.location = ""
            wp.district = ""
            wp.skills = []
            wp.experience_description = ""
            wp.is_available = False
            wp.verification_status = VerificationStatus.UNSUBMITTED
            wp.is_verified = False
            wp.verification_notes = ""
            wp.save()

        # Remove user's favorites bookmarks
        FavoriteWorker.objects.filter(user=locked_user).delete()
        FavoriteOrder.objects.filter(user=locked_user).delete()

        # Scrub User PII & invalidate all credentials/tokens
        locked_user.phone_number = None
        locked_user.email = None
        locked_user.full_name = f"Deleted User {short_id}"
        locked_user.set_unusable_password()
        locked_user.is_active = False
        locked_user.is_phone_verified = False
        locked_user.account_status = AccountStatus.DELETED
        locked_user.is_anonymized = True
        locked_user.anonymized_at = now
        locked_user.token_version += 1
        locked_user.save()

        _blacklist_all_user_tokens(locked_user)

        audit = AccountDeletionAudit.objects.create(
            user_id=locked_user.id,
            phone_hash=phone_hash,
            role=locked_user.role,
            reason=reason,
            performed_by_id=(performed_by.id if performed_by else locked_user.id),
        )
        return audit
