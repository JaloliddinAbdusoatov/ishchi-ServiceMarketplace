import hashlib
import hmac
import logging
import secrets
import time
from django.conf import settings
from django.core.cache import cache
from apps.accounts.services.sms_service import get_sms_provider
from apps.common.validators import UZ_PHONE_REGEX
from apps.accounts.services.locks import serialize_otp, increment_bucket

logger = logging.getLogger(__name__)


class OTPPurpose:
    VERIFY_PHONE = "VERIFY_PHONE"
    PASSWORD_RESET = "PASSWORD_RESET"
    VALID_PURPOSES = {VERIFY_PHONE, PASSWORD_RESET}


class OTPService:
    """Redis-backed OTP generation, cooldown, rate limiting, and atomic verification."""

    @staticmethod
    def _hash_otp(phone_number: str, purpose: str, code: str) -> str:
        key = settings.SECRET_KEY.encode("utf-8")
        msg = f"{purpose}:{phone_number}:{code}".encode("utf-8")
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    @classmethod
    @serialize_otp
    def send_otp(cls, phone_number: str, purpose: str = OTPPurpose.VERIFY_PHONE, ip_address: str = None) -> dict:
        if purpose not in OTPPurpose.VALID_PURPOSES:
            return {
                "success": False,
                "error_code": "invalid_purpose",
                "message": "Invalid OTP purpose.",
                "status_code": 400,
            }

        if not phone_number or not UZ_PHONE_REGEX.match(phone_number):
            return {
                "success": False,
                "error_code": "invalid_phone_format",
                "message": "Phone number must match Uzbekistan format +998XXXXXXXXX.",
                "status_code": 400,
            }

        now = time.time()
        exp_seconds = getattr(settings, "OTP_EXPIRATION_SECONDS", 300)
        cooldown_seconds = getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
        max_attempts = getattr(settings, "OTP_MAX_ATTEMPTS", 5)
        max_phone_hourly = getattr(settings, "OTP_MAX_PER_PHONE_HOURLY", 10)
        max_ip_hourly = getattr(settings, "OTP_MAX_PER_IP_HOURLY", 30)

        session_key = f"otp_session:{purpose}:{phone_number}"
        phone_rate_key = f"otp_rate:phone:{phone_number}"
        ip_rate_key = f"otp_rate:ip:{ip_address}" if ip_address else None

        if ip_rate_key:
            ip_count = cache.get(ip_rate_key, 0)
            if ip_count >= max_ip_hourly:
                return {
                    "success": False,
                    "error_code": "rate_limit_exceeded",
                    "message": "Too many OTP requests from this IP address. Please try again later.",
                    "status_code": 429,
                }
        else:
            ip_count = 0

        phone_count = cache.get(phone_rate_key, 0)
        if phone_count >= max_phone_hourly:
            return {
                "success": False,
                "error_code": "rate_limit_exceeded",
                "message": "Too many OTP requests for this phone number. Please try again later.",
                "status_code": 429,
            }

        active_session = cache.get(session_key)
        if active_session:
            resend_at = active_session.get("resend_available_at", 0)
            if now < resend_at:
                remaining = max(1, int(resend_at - now))
                return {
                    "success": False,
                    "error_code": "cooldown_active",
                    "message": f"Please wait {remaining} seconds before requesting a new code.",
                    "remaining_cooldown": remaining,
                    "status_code": 429,
                }

        code = str(secrets.randbelow(900000) + 100000)
        session_data = {
            "hashed_otp": cls._hash_otp(phone_number, purpose, code),
            "attempts": 0,
            "max_attempts": max_attempts,
            "created_at": now,
            "expires_at": now + exp_seconds,
            "resend_available_at": now + cooldown_seconds,
        }

        cache.set(session_key, session_data, timeout=exp_seconds)
        phone_count = increment_bucket(phone_rate_key, 3600)
        ip_count = increment_bucket(ip_rate_key, 3600) if ip_rate_key else 0
        if phone_count > max_phone_hourly or ip_count > max_ip_hourly:
            cache.delete(session_key)
            return {"success": False, "error_code": "rate_limit_exceeded",
                "message": "Too many OTP requests. Please try again later.", "status_code": 429}

        try:
            get_sms_provider().send_otp(phone_number, code, purpose, exp_seconds)
        except Exception:
            cache.delete(session_key)
            raise

        return {
            "success": True,
            "message": "Verification code has been dispatched if the phone number is valid.",
            "cooldown_seconds": cooldown_seconds,
            "expires_in_seconds": exp_seconds,
            "status_code": 200,
        }

    @classmethod
    @serialize_otp
    def verify_otp(cls, phone_number: str, submitted_otp: str, purpose: str = OTPPurpose.VERIFY_PHONE) -> tuple[bool, str, str]:
        if not phone_number or not submitted_otp:
            return False, "invalid_input", "Phone number and OTP code are required."

        session_key = f"otp_session:{purpose}:{phone_number}"
        session_data = cache.get(session_key)
        if not session_data:
            return False, "otp_expired_or_invalid", "Verification code has expired or was not requested."

        now = time.time()
        if now > session_data.get("expires_at", 0):
            cache.delete(session_key)
            return False, "otp_expired", "Verification code has expired. Please request a new code."

        attempts = session_data.get("attempts", 0) + 1
        max_attempts = session_data.get("max_attempts", 5)
        if attempts > max_attempts:
            cache.delete(session_key)
            return False, "otp_max_attempts", "Maximum verification attempts exceeded. Request a new code."

        expected_hash = session_data.get("hashed_otp", "")
        submitted_hash = cls._hash_otp(phone_number, purpose, submitted_otp)
        if not hmac.compare_digest(submitted_hash, expected_hash):
            session_data["attempts"] = attempts
            remaining = max_attempts - attempts
            if remaining > 0:
                ttl = max(1, int(session_data["expires_at"] - now))
                cache.set(session_key, session_data, timeout=ttl)
                return False, "otp_invalid", f"Invalid verification code. {remaining} attempt(s) remaining."
            cache.delete(session_key)
            return False, "otp_max_attempts", "Maximum verification attempts exceeded. Code invalidated."

        created_at = session_data.get("created_at", 0)
        consumed_key = f"otp_consumed:{purpose}:{phone_number}:{created_at}"
        exp_seconds = getattr(settings, "OTP_EXPIRATION_SECONDS", 300)
        if not cache.add(consumed_key, True, timeout=exp_seconds):
            return False, "otp_already_used", "Verification code has already been used."

        cache.delete(session_key)
        return True, "success", "OTP verified successfully."
