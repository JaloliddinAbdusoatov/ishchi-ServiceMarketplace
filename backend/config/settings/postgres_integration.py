"""Pre-provisioned, explicitly approved disposable target only; no CREATE DATABASE."""
from .testing import *  # noqa: F403
from .database import postgres_database

POSTGRES_INTEGRATION = True
LOCAL_DEVELOPMENT = False
DATABASE_ROUTERS = []
DATABASES = {"default": postgres_database(os.environ, production=False)}
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["OPTIONS"]["options"] = "-c statement_timeout=15000 -c lock_timeout=10000 -c idle_in_transaction_session_timeout=20000 -c search_path=public"
DATABASES["default"]["TEST"] = {"NAME": DATABASES["default"]["NAME"]}
if not DATABASES["default"]["NAME"].startswith("ishchi_marketplace_sprint1_"):
    raise ImproperlyConfigured("Integration requires a dedicated ishchi_marketplace_sprint1_* database.")
