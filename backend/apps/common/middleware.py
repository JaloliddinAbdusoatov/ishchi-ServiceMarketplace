"""Correlate requests without recording URLs, query strings, bodies or tokens."""
from contextvars import ContextVar
import logging
import re
import time
import uuid
from django.conf import settings

request_id = ContextVar("request_id", default="-")
logger = logging.getLogger("ishchi.request")


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id.get()
        return True


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.META.get("HTTP_X_REQUEST_ID", "")
        trusted = request.META.get("REMOTE_ADDR") in settings.TRUSTED_PROXY_IPS
        value = supplied if trusted and re.fullmatch(r"[a-f0-9]{32}", supplied) else uuid.uuid4().hex
        token = request_id.set(value)
        started = time.monotonic()
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = value
            route = getattr(request.resolver_match, "view_name", "unmatched")
            logger.info("request method=%s route=%s status=%s duration_ms=%d",
                request.method, route, response.status_code, (time.monotonic() - started) * 1000)
            return response
        finally:
            request_id.reset(token)
