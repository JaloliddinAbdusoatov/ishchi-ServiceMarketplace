"""Pure configuration validation: never opens a socket."""
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from apps.common.db_backends.postgresql.base import validate_target


def postgres_database(env, *, production):
    def required(key):
        value = env.get(key, "").strip()
        if not value:
            raise ImproperlyConfigured(f"Database requires {key}.")
        return env[key] if key == "DB_PASSWORD" else value

    def number(key, default, minimum, maximum):
        try:
            value = int(env.get(key, str(default)))
            if not minimum <= value <= maximum:
                raise ValueError()
            return value
        except ValueError:
            raise ImproperlyConfigured(f"{key} must be between {minimum} and {maximum}.") from None

    config = {
        "ENGINE": "apps.common.db_backends.postgresql",
        "NAME": required("DB_NAME"), "HOST": required("DB_HOST"),
        "PORT": str(number("DB_PORT", 5432, 1, 65535)),
        "USER": required("DB_USER"), "PASSWORD": required("DB_PASSWORD"),
        "CONN_MAX_AGE": number("DB_CONN_MAX_AGE", 60, 0, 3600),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"connect_timeout": number("DB_CONNECT_TIMEOUT", 5, 1, 60)},
    }
    mode = env.get("DB_SSLMODE", "verify-full")
    if mode not in ({"verify-full"} if production else {"disable", "verify-ca", "verify-full"}):
        raise ImproperlyConfigured("Production requires DB_SSLMODE=verify-full.")
    config["OPTIONS"]["sslmode"] = mode
    if mode != "disable":
        cert = Path(required("DB_SSLROOTCERT"))
        if not cert.is_file():
            raise ImproperlyConfigured("DB_SSLROOTCERT must be a readable CA certificate file.")
        try:
            import ssl
            ssl.create_default_context(cafile=str(cert))
        except (OSError, ssl.SSLError):
            raise ImproperlyConfigured("DB_SSLROOTCERT is not a valid CA certificate.") from None
        config["OPTIONS"]["sslrootcert"] = str(cert.resolve())
    validate_target({"dbname": config["NAME"], "host": config["HOST"], "port": config["PORT"], "user": config["USER"]})
    return config
