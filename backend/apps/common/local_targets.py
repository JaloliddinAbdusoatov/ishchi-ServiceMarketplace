"""Exact local endpoints. These are safety interlocks, never owner consent."""
from pathlib import Path
from urllib.parse import quote
from django.core.exceptions import ImproperlyConfigured

PG = {
    "work": {("postgres-work", "5432", "ishchi_marketplace_local", "ishchi_local_app"),
             ("127.0.0.1", "55432", "ishchi_marketplace_local", "ishchi_local_app")},
    "test": {("127.0.0.1", "55433", "ishchi_marketplace_sprint1_local", "ishchi_local_test")},
    "migration": {("postgres-work", "5432", "ishchi_marketplace_local", "ishchi_local_migrator"),
                  ("127.0.0.1", "55432", "ishchi_marketplace_local", "ishchi_local_migrator")},
    "restore": {("127.0.0.1", "55434", "ishchi_marketplace_restore_local", "ishchi_local_restore")},
}
REDIS = {
    "work": {("redis-work", 6379, 0, "ishchi_local_app"), ("127.0.0.1", 56379, 0, "ishchi_local_app")},
    "test": {("127.0.0.1", 56380, 0, "ishchi_local_test")},
}
REDIS["migration"] = REDIS["work"]


def validate_local_pg(params, kind):
    target = tuple(str(params.get(key, "")) for key in ("host", "port", "dbname", "user"))
    if target not in PG.get(kind, set()):
        raise ImproperlyConfigured("Local PostgreSQL target differs from the exact working/test allowlist.")


def validate_local_redis(target, kind):
    if tuple(target.get(key) for key in ("host", "port", "database", "user")) not in REDIS.get(kind, set()):
        raise ImproperlyConfigured("Local Redis target differs from the exact working/test allowlist.")


def secret_file(env, name):
    try:
        path = Path(env[name + "_FILE"])
        if not path.is_absolute():
            raise ValueError()
        value = path.read_text(encoding="utf-8").rstrip("\r\n")
        if len(value) < 24 or any(char in value for char in ("\n", "\r", "\x00")):
            raise ValueError()
        return value
    except (OSError, KeyError, ValueError):
        raise ImproperlyConfigured(f"Local configuration requires an absolute {name}_FILE containing a secret of at least 24 characters.") from None


def local_database(env, kind):
    from config.settings.database import postgres_database
    defaults = {
        "work": ("postgres-work", "5432", "ishchi_marketplace_local", "ishchi_local_app"),
        "migration": ("postgres-work", "5432", "ishchi_marketplace_local", "ishchi_local_migrator"),
        "test": ("127.0.0.1", "55433", "ishchi_marketplace_sprint1_local", "ishchi_local_test"),
        "restore": ("127.0.0.1", "55434", "ishchi_marketplace_restore_local", "ishchi_local_restore"),
    }
    if kind not in defaults:
        raise ImproperlyConfigured("Unknown local PostgreSQL purpose.")
    host, port, name, role = defaults[kind]
    values = {**env, "DB_HOST": env.get("DB_HOST", host), "DB_PORT": env.get("DB_PORT", port),
              "DB_NAME": env.get("DB_NAME", name), "DB_USER": env.get("DB_USER", role),
              "DB_PASSWORD": secret_file(env, "DB_PASSWORD"), "DB_SSLMODE": "disable", "DB_CONN_MAX_AGE": "0"}
    config = postgres_database(values, production=False)
    validate_local_pg({"host": config["HOST"], "port": config["PORT"], "dbname": config["NAME"], "user": config["USER"]}, kind)
    config["OPTIONS"]["options"] = "-c statement_timeout=15000 -c lock_timeout=10000 -c idle_in_transaction_session_timeout=20000 -c search_path=public"
    return config


def local_redis_url(env, kind):
    host, port, user = ("redis-work", 6379, "ishchi_local_app") if kind == "work" else ("127.0.0.1", 56380, "ishchi_local_test")
    host = env.get("LOCAL_REDIS_HOST", host)
    try:
        port = int(env.get("LOCAL_REDIS_PORT", port))
    except ValueError:
        raise ImproperlyConfigured("LOCAL_REDIS_PORT must be numeric.") from None
    validate_local_redis({"host": host, "port": port, "database": 0, "user": user}, kind)
    password = secret_file(env, "REDIS_PASSWORD")
    return f"redis://{user}:{quote(password, safe='')}@{host}:{port}/0"
