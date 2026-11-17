"""Disposable localhost PostgreSQL only. SQLite security cache, separate Redis suite."""
from .testing import *  # noqa: F403
from apps.common.local_targets import local_database

LOCAL_TARGET_KIND = "test"
POSTGRES_INTEGRATION = True
LOCAL_DEVELOPMENT = False
DATABASE_ROUTERS = []
DATABASES = {"default": local_database(os.environ, "test")}
DATABASES["default"]["TEST"] = {"NAME": DATABASES["default"]["NAME"]}
