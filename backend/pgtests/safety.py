"""Checks run only inside an explicitly owner-approved disposable target."""
from django.core.exceptions import ImproperlyConfigured


def verify_database(connection):
    expected = connection.settings_dict
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user, current_schema()")
        if cursor.fetchone() != (expected["NAME"], expected["USER"], "public"):
            raise ImproperlyConfigured("Connected identity/schema differs from approved test target.")
        cursor.execute("""SELECT EXISTS (
            SELECT 1 FROM pg_roles WHERE
            (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
            AND pg_has_role(current_user, oid, 'MEMBER')
        )""")
        if cursor.fetchone()[0]:
            raise ImproperlyConfigured("Integration role must not possess or assume elevated role privileges.")
        cursor.execute("""SELECT pg_get_userbyid(datdba) = current_user
            FROM pg_database WHERE datname = current_database()""")
        if not cursor.fetchone()[0]:
            raise ImproperlyConfigured("Integration migration role must own this disposable database.")
        cursor.execute("SELECT pg_has_role(current_user, nspowner, 'USAGE') FROM pg_namespace WHERE nspname = 'public'")
        if not cursor.fetchone()[0]:
            raise ImproperlyConfigured("Integration role must own/control the disposable public schema.")
        cursor.execute("""SELECT EXISTS (
            SELECT 1 FROM pg_namespace WHERE nspname NOT IN ('public', 'pg_catalog', 'information_schema')
            AND nspname !~ '^pg_'
        )""")
        if cursor.fetchone()[0]:
            raise ImproperlyConfigured("Disposable database contains an unexpected user schema.")
        cursor.execute("""SELECT EXISTS (
            SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public'
            UNION ALL SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'public'
            UNION ALL SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace WHERE n.nspname = 'public'
        )""")
        if cursor.fetchone()[0]:
            raise ImproperlyConfigured("Integration requires an empty public schema; nothing was migrated.")
