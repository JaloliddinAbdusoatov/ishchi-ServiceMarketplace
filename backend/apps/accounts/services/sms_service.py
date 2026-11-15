"""SMS adapter contract. Codes are never written to application logs."""
import json
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import APIException

class SMSUnavailable(APIException):
    status_code = 503
    default_code = "sms_unavailable"
    default_detail = "SMS delivery is unavailable. Please try again later or contact support."

class SMSProvider(Protocol):
    def send_otp(self, phone_number: str, code: str, purpose: str, expires_in_seconds: int) -> None: ...

class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class HTTPSMSProvider:
    """Operator gateway: HTTPS JSON POST, bearer token, 2xx acceptance.

    The operator supplies a gateway implementing this contract and verifies real
    SMS delivery before release. No vendor account or credentials are assumed.
    """
    def send_otp(self, phone_number, code, purpose, expires_in_seconds):
        payload = json.dumps({"phone_number": phone_number, "code": code,
            "purpose": purpose, "expires_in_seconds": expires_in_seconds}).encode("utf-8")
        request = Request(settings.SMS_API_URL, data=payload, method="POST", headers={
            "Authorization": f"Bearer {settings.SMS_API_TOKEN}", "Content-Type": "application/json"})
        try:
            # Redirects must never forward a credential or OTP to another host.
            with build_opener(NoRedirects()).open(request, timeout=10) as response:
                if not 200 <= response.status < 300:
                    raise SMSUnavailable()
        except (HTTPError, URLError, OSError, TimeoutError, ValueError):
            # Provider response bodies may contain credentials/PII.
            raise SMSUnavailable() from None

class LocalMemorySMSProvider:
    """Explicit local development only; inspect outbox in a Python session."""
    outbox = []
    def send_otp(self, phone_number, code, purpose, expires_in_seconds):
        self.outbox[:] = [{"phone_number": phone_number, "code": code, "purpose": purpose}]

def validate_sms_configuration():
    backend = getattr(settings, "SMS_BACKEND", "disabled")
    if backend == "memory" and not getattr(settings, "IS_PRODUCTION", False) and settings.DEBUG and getattr(settings, "LOCAL_DEVELOPMENT", False):
        return
    if backend == "http":
        url = urlsplit(getattr(settings, "SMS_API_URL", ""))
        if url.scheme == "https" and url.hostname and not url.username and not url.password and not url.fragment and getattr(settings, "SMS_API_TOKEN", ""):
            return
    raise ImproperlyConfigured("Configure SMS_BACKEND=http, SMS_API_URL (HTTPS), and SMS_API_TOKEN. Local OTP is prohibited in production.")

def get_sms_provider() -> SMSProvider:
    try:
        validate_sms_configuration()
    except ImproperlyConfigured:
        raise SMSUnavailable() from None
    return HTTPSMSProvider() if settings.SMS_BACKEND == "http" else LocalMemorySMSProvider()
