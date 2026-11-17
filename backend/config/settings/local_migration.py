"""Owner-approved operator only; separate login explicitly assumes NOLOGIN owner."""
from .local_postgres import *  # noqa: F403

LOCAL_TARGET_KIND = "migration"
LOCAL_DEVELOPMENT = False
DATABASES = {"default": local_database({**os.environ, "DB_USER": "ishchi_local_migrator"}, "migration")}
DATABASES["default"]["OPTIONS"]["assume_role"] = "ishchi_local_owner"
