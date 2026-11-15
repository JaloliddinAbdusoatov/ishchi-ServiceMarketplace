"""Serialize OTP mutation in Redis; local fallback is explicitly single process."""
from contextlib import contextmanager
from functools import wraps
import hashlib
import threading
from django.conf import settings
from django.core.cache import cache
from .sms_service import SMSUnavailable

_local_lock = threading.RLock()


@contextmanager
def otp_lock(phone_number):
    key = "otp_lock:" + hashlib.sha256(str(phone_number).encode()).hexdigest()
    if hasattr(cache, "lock"):
        lock = cache.lock(key, timeout=20, blocking_timeout=2)
        if not lock.acquire(blocking=True):
            raise SMSUnavailable()
        try:
            yield
        finally:
            lock.release()
    elif getattr(settings, "LOCAL_DEVELOPMENT", False) and not getattr(settings, "IS_PRODUCTION", False):
        with _local_lock:
            yield
    else:
        raise SMSUnavailable()


def serialize_otp(method):
    @wraps(method)
    def wrapped(cls, phone_number, *args, **kwargs):
        with otp_lock(phone_number):
            return method(cls, phone_number, *args, **kwargs)
    return wrapped


def increment_bucket(key, timeout):
    # add/incr are atomic on Redis and local cache, unlike get/set counters.
    if cache.add(key, 1, timeout=timeout):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        return 1 if cache.add(key, 1, timeout=timeout) else cache.incr(key)
