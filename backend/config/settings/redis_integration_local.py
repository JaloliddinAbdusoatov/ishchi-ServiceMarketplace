"""Disposable localhost Redis only; relational fixtures stay on in-memory SQLite."""
from .testing import *  # noqa: F403
from apps.common.local_targets import local_redis_url

LOCAL_TARGET_KIND = "test"
LOCAL_INTEGRATION_REDIS_URL = local_redis_url(os.environ, "test")
