"""Django operator UI uses the same account boundary as administrator APIs."""
import hashlib
from django.contrib.admin import AdminSite
from django.http import HttpResponse
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
from apps.accounts.services.locks import increment_bucket
from apps.accounts.throttling import TrustedClientIP


class MarketplaceAdminSite(AdminSite):
    def has_permission(self, request):
        user = request.user
        return bool(super().has_permission(request) and user.is_admin_user
            and user.account_status == "ACTIVE" and not user.is_anonymized)

    def login(self, request, extra_context=None):
        if request.method == "POST":
            identity = TrustedClientIP().get_ident(request)
            key = "admin_login:" + hashlib.sha256(identity.encode()).hexdigest()
            try:
                if increment_bucket(key, 900) > 10:
                    return HttpResponse("Too many login attempts. Try again later.", status=429)
            except (RedisConnectionError, RedisTimeoutError):
                return HttpResponse("Service temporarily unavailable.", status=503)
        return super().login(request, extra_context)
