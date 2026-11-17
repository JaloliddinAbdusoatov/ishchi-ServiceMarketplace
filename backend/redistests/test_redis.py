"""Explicit owner-approved TLS Redis only. PostgreSQL is never used here."""
import os
import time
import uuid
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.conf import settings
from django.core.cache import caches
from redis.connection import SSLConnection
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework.test import APIClient

from apps.common.redis_backend import authorize_redis
from apps.accounts.services.otp_service import OTPService
from apps.accounts.services.auth_service import AuthService, generate_jwt_pair
from apps.common.exceptions import BusinessRuleViolation
from tests.conftest import UserFactory


@pytest.fixture
def redis_cache():
    url = getattr(settings, "LOCAL_INTEGRATION_REDIS_URL", os.environ.get("REDIS_URL", ""))
    # Attestations are interlocks; obtain owner approval separately before running.
    authorize_redis(url, "cache_test")
    authorize_redis(url, "cache")
    prefix = "ishchi-sprint2-" + uuid.uuid4().hex
    pool_options = {"ssl_cert_reqs": "required", "ssl_check_hostname": True} if url.startswith("rediss://") else {}
    if pool_options and os.environ.get("REDIS_SSLROOTCERT"):
        pool_options["ssl_ca_certs"] = os.environ["REDIS_SSLROOTCERT"]
    config = {
        "BACKEND": "apps.common.redis_backend.RedisCache", "LOCATION": url, "KEY_PREFIX": prefix,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient", "SOCKET_CONNECT_TIMEOUT": 5,
                    "SOCKET_TIMEOUT": 5, "IGNORE_EXCEPTIONS": False, "CLOSE_CONNECTION": True,
                    "CONNECTION_POOL_KWARGS": pool_options},
    }
    with override_settings(CACHES={"default": config, "observer": config}):
        cache = caches["default"]
        try:
            yield cache
        finally:
            try:
                # Expanded by django-redis with this unique KEY_PREFIX/version.
                cache.delete_pattern("*")
            finally:
                cache.close()
                caches["observer"].close()


def test_authenticated_connection_and_configured_transport(redis_cache):
    client = redis_cache.client.get_client(write=True)
    assert client.ping() is True
    if getattr(settings, "LOCAL_TARGET_KIND", "") == "test":
        assert not issubclass(client.connection_pool.connection_class, SSLConnection)
        assert client.connection_pool.connection_kwargs["host"] == "127.0.0.1"
        assert client.connection_pool.connection_kwargs["port"] == 56380
    else:
        assert issubclass(client.connection_pool.connection_class, SSLConnection)
        assert client.connection_pool.connection_kwargs["ssl_cert_reqs"] == "required"
        assert client.connection_pool.connection_kwargs["ssl_check_hostname"] is True


def test_atomic_counters_and_key_ttl(redis_cache):
    assert redis_cache.add("counter", 1, timeout=30)
    assert not caches["observer"].add("counter", 1, timeout=30)
    assert caches["observer"].incr("counter") == 2
    assert redis_cache.get("counter") == 2
    assert 0 < redis_cache.ttl("counter") <= 30


def test_distributed_lock_contention(redis_cache):
    lock = redis_cache.lock("otp-lock", timeout=10, blocking_timeout=1)
    contender = caches["observer"].lock("otp-lock", timeout=10, blocking_timeout=1)
    assert lock.acquire(blocking=False)
    try:
        assert not contender.acquire(blocking=False)
    finally:
        lock.release()
    assert contender.acquire(blocking=False)
    contender.release()


@pytest.mark.django_db
def test_actual_session_revocation_shared_with_another_client(redis_cache):
    user = UserFactory()
    tokens = generate_jwt_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get("/api/v1/auth/me/").status_code == 200
    AuthService.logout_session(access_token_str=tokens["access"])
    from rest_framework_simplejwt.tokens import AccessToken
    session = AccessToken(tokens["access"])["session_id"]
    assert caches["observer"].get(f"revoked_session:{session}") is True
    assert client.get("/api/v1/auth/me/").status_code == 401


@pytest.mark.django_db
def test_login_lockout_persists_in_shared_cache(redis_cache):
    user = UserFactory()
    with override_settings(LOGIN_MAX_ATTEMPTS=2, LOGIN_LOCKOUT_SECONDS=30):
        for _ in range(2):
            with pytest.raises(BusinessRuleViolation) as failure:
                AuthService.login_user(user.phone_number, "WrongPassword2026!")
            assert failure.value.get_codes() == "invalid_credentials"
        assert caches["observer"].get(f"login_lockout:{user.phone_number}") is True
        with pytest.raises(BusinessRuleViolation) as failure:
            AuthService.login_user(user.phone_number, "StrongPass2026!")
        assert failure.value.get_codes() == "account_locked"
        assert 0 < caches["observer"].ttl(f"login_lockout:{user.phone_number}") <= 30


@pytest.mark.django_db
def test_otp_uses_real_redis_expiration(redis_cache):
    phone = "+998935500901"
    UserFactory(phone_number=phone)
    with override_settings(OTP_EXPIRATION_SECONDS=2), patch("apps.accounts.services.otp_service.get_sms_provider") as sms:
        assert OTPService.send_otp(phone)["success"]
        code = sms.return_value.send_otp.call_args.args[1]
        key = f"otp_session:VERIFY_PHONE:{phone}"
        session = caches["observer"].get(key)
        assert code not in str(session)
        deadline = time.monotonic() + 8
        while caches["observer"].get(key) is not None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert caches["observer"].get(key) is None
        assert OTPService.verify_otp(phone, code)[0] is False


@pytest.mark.django_db
def test_otp_rate_and_attempt_limits_use_shared_counters(redis_cache):
    phone = "+998935500902"
    UserFactory(phone_number=phone)
    with override_settings(OTP_MAX_PER_PHONE_HOURLY=1, OTP_MAX_ATTEMPTS=2), patch("apps.accounts.services.otp_service.get_sms_provider"):
        assert OTPService.send_otp(phone)["success"]
        assert caches["observer"].get(f"otp_rate:phone:{phone}") == 1
        assert OTPService.send_otp(phone)["error_code"] == "rate_limit_exceeded"
        assert OTPService.verify_otp(phone, "000000")[1] == "otp_invalid"
        assert OTPService.verify_otp(phone, "000000")[1] == "otp_max_attempts"
        assert caches["observer"].get(f"otp_session:VERIFY_PHONE:{phone}") is None


@pytest.mark.django_db
def test_redis_transport_failure_is_sanitized_and_fails_closed(redis_cache):
    # Real connection first; injection never stops/modifies the Redis server.
    assert redis_cache.client.get_client(write=True).ping()
    user = UserFactory()
    tokens = generate_jwt_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    with patch.object(redis_cache.client, "get", side_effect=RedisConnectionError("private-redis-password")):
        result = client.get("/api/v1/auth/me/")
    assert result.status_code == 503
    assert result.data["error"]["code"] == "service_unavailable"
    assert "private-redis-password" not in str(result.data)
