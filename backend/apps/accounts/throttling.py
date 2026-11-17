"""Rate-limit identities must use only operator-trusted forwarding headers."""
import ipaddress
from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle


class TrustedClientIP:
    def get_ident(self, request):
        remote = request.META.get("REMOTE_ADDR", "")
        if remote in settings.TRUSTED_PROXY_IPS:
            try:
                return str(ipaddress.ip_address(request.META.get("HTTP_X_REAL_IP", "")))
            except ValueError:
                pass
        return remote


class AnonymousThrottle(TrustedClientIP, AnonRateThrottle):
    pass


class AccountThrottle(TrustedClientIP, UserRateThrottle):
    pass


class SecurityScopedThrottle(TrustedClientIP, ScopedRateThrottle):
    pass
