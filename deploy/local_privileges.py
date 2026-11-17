"""Offline privilege plan generator. NEVER connects or executes SQL.

Apply and rollback both require separate exact-target owner approval. Grant lists
are explicit; unknown/new tables fail closed until their required DML is reviewed.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = {
    "accounts_deletion_audit": "SELECT, INSERT",
    "django_admin_log": "SELECT, INSERT",
    "django_migrations": "SELECT",
    "django_content_type": "SELECT",
    "auth_permission": "SELECT",
    "auth_group": "SELECT",
    "auth_group_permissions": "SELECT",
    "accounts_user_groups": "SELECT",
    "accounts_user_user_permissions": "SELECT",
    "accounts_user": "SELECT, INSERT, UPDATE",
    "applications_order_application": "SELECT, INSERT, UPDATE",
    "categories_category": "SELECT, INSERT, UPDATE",
    "categories_worker_category": "SELECT, INSERT, UPDATE, DELETE",
    "chat_conversation": "SELECT, INSERT, UPDATE",
    "chat_message": "SELECT, INSERT, UPDATE",
    "common_mediadeletiontask": "SELECT, INSERT, UPDATE",
    "django_session": "SELECT, INSERT, UPDATE, DELETE",
    "favorites_order": "SELECT, INSERT, DELETE",
    "favorites_worker": "SELECT, INSERT, DELETE",
    "invitations_order_invitation": "SELECT, INSERT, UPDATE",
    "notifications_notification": "SELECT, INSERT, UPDATE",
    "orders_order_image": "SELECT, INSERT, UPDATE, DELETE",
    "orders_service_order": "SELECT, INSERT, UPDATE, DELETE",
    "orders_service_order_assigned_workers": "SELECT, INSERT, DELETE",
    "profiles_employer": "SELECT, INSERT, UPDATE",
    "profiles_worker": "SELECT, INSERT, UPDATE",
    "profiles_worker_portfolio": "SELECT, INSERT, UPDATE, DELETE",
    "reports_report": "SELECT, INSERT, UPDATE",
    "reviews_review": "SELECT, INSERT",
    "token_blacklist_blacklistedtoken": "SELECT, INSERT",
    "token_blacklist_outstandingtoken": "SELECT, INSERT",
}
SEQUENCES = ("django_admin_log_id_seq", "orders_service_order_assigned_workers_id_seq",
             "token_blacklist_blacklistedtoken_id_seq", "token_blacklist_outstandingtoken_id_seq")
FUNCTIONS = ("fn_enforce_worker_category_limit()", "fn_purge_deactivated_worker_categories()",
             "ishchi_check_hiring(uuid)", "ishchi_hiring_integrity_event()")


def guard(owner, *, applying):
    names = ",".join("'" + name + "'" for name in sorted(POLICY))
    missing_functions = " OR ".join("to_regprocedure('public." + signature + "') IS NULL" for signature in FUNCTIONS)
    roles = "  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('ishchi_local_owner','ishchi_local_migrator')) THEN RAISE EXCEPTION 'New role already exists; independent review required'; END IF;\n" if applying else "\n"
    return f"""-- NOT AUTHORIZATION. Existing local database only; no data/reset/drop statements.
\\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $guard$
BEGIN
  IF current_database() <> 'ishchi_marketplace_local' OR session_user <> 'ishchi_bootstrap' THEN
    RAISE EXCEPTION 'Wrong database or privileged operator';
  END IF;
{roles}  IF (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()) <> '{owner}'
     OR (SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='public') <> '{owner}' THEN
    RAISE EXCEPTION 'Database/schema owner drift; independent review required';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname='ishchi_local_app') THEN
    RAISE EXCEPTION 'Runtime role has unexpected memberships';
  END IF;
  IF (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public') <> 4 THEN
    RAISE EXCEPTION 'Function inventory drift; review before ownership transfer';
  END IF;
  IF {missing_functions} THEN
    RAISE EXCEPTION 'Function signature drift; independent review required';
  END IF;
  IF (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='S') <> 11 THEN
    RAISE EXCEPTION 'Sequence inventory drift; independent review required';
  END IF;
  IF (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND c.relkind IN ('r','p')) <> {len(POLICY)}
     OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND c.relkind IN ('r','p') AND c.relname NOT IN ({names})) THEN
    RAISE EXCEPTION 'Table inventory drift; do not apply this plan';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND c.relkind IN ('r','p','S') AND pg_get_userbyid(c.relowner) <> '{owner}')
     OR EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE n.nspname='public' AND (p.prosecdef OR pg_get_userbyid(p.proowner) <> '{owner}')) THEN
    RAISE EXCEPTION 'Ownership/security-definer drift; manual review required';
  END IF;
END;
$guard$;
"""


def transfer(owner):
    return f"""
ALTER DATABASE ishchi_marketplace_local OWNER TO {owner};
ALTER SCHEMA public OWNER TO {owner};
DO $owners$
DECLARE obj record;
BEGIN
  FOR obj IN SELECT c.relname,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relkind IN ('r','p','S') ORDER BY CASE WHEN c.relkind='S' THEN 1 ELSE 0 END,c.relname LOOP
    IF obj.relkind='S' THEN
      EXECUTE format('ALTER SEQUENCE public.%I OWNER TO {owner}',obj.relname);
    ELSE
      EXECUTE format('ALTER TABLE public.%I OWNER TO {owner}',obj.relname);
    END IF;
  END LOOP;
  FOR obj IN SELECT p.proname,pg_get_function_identity_arguments(p.oid) AS args FROM pg_proc p
    JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' LOOP
    EXECUTE format('ALTER FUNCTION public.%I(%s) OWNER TO {owner}',obj.proname,obj.args);
  END LOOP;
END;
$owners$;
"""


def apply_sql(*, reuse_rolled_back_roles=False):
    sql = guard("ishchi_local_app", applying=not reuse_rolled_back_roles)
    if reuse_rolled_back_roles:
        sql += """
DO $retry_guard$
BEGIN
 IF (SELECT count(*) FROM pg_roles WHERE rolname IN ('ishchi_local_owner','ishchi_local_migrator')
     AND NOT rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
     AND NOT rolreplication AND NOT rolbypassrls AND rolconfig IS NULL) <> 2
    OR EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
        WHERE r.rolname IN ('ishchi_local_owner','ishchi_local_migrator')) THEN
   RAISE EXCEPTION 'Rolled-back role state does not match; refuse retry';
 END IF;
END;
$retry_guard$;
ALTER ROLE ishchi_local_migrator LOGIN;
"""
    else:
        sql += """
CREATE ROLE ishchi_local_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE ishchi_local_migrator LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD NULL;
"""
    sql += "GRANT ishchi_local_owner TO ishchi_local_migrator WITH ADMIN FALSE, INHERIT FALSE, SET TRUE;\n"
    sql += transfer("ishchi_local_owner")
    sql += """
REVOKE ALL ON DATABASE ishchi_marketplace_local FROM PUBLIC, ishchi_local_app, ishchi_local_migrator;
GRANT CONNECT ON DATABASE ishchi_marketplace_local TO ishchi_local_app, ishchi_local_migrator;
REVOKE ALL ON SCHEMA public FROM PUBLIC, ishchi_local_app, ishchi_local_migrator;
GRANT USAGE ON SCHEMA public TO ishchi_local_app;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC, ishchi_local_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, ishchi_local_app;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC, ishchi_local_app;
-- Future objects require explicit reviewed grants. No default runtime DML.
ALTER DEFAULT PRIVILEGES FOR ROLE ishchi_local_owner REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
"""
    for table, permissions in sorted(POLICY.items()):
        sql += f"GRANT {permissions} ON TABLE public.{table} TO ishchi_local_app;\n"
    for sequence in SEQUENCES:
        sql += f"GRANT USAGE, SELECT ON SEQUENCE public.{sequence} TO ishchi_local_app;\n"
    for function in FUNCTIONS:
        sql += f"GRANT EXECUTE ON FUNCTION public.{function} TO ishchi_local_app;\n"
    return sql + "COMMIT;\n-- Migrator remains password-disabled until separately approved private credential installation.\n"


def rollback_sql():
    sql = guard("ishchi_local_owner", applying=False)
    sql += transfer("ishchi_local_app")
    sql += """
REVOKE ishchi_local_owner FROM ishchi_local_migrator;
ALTER ROLE ishchi_local_migrator NOLOGIN;
GRANT USAGE, CREATE ON SCHEMA public TO ishchi_local_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO PUBLIC;
COMMIT;
-- No roles or data are dropped. This rollback restores the prior insecure ownership model.
"""
    return sql


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "deploy/local/privileges")
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "apply.sql").write_text(apply_sql(), encoding="utf-8", newline="\n")
    (args.output_dir / "rollback.sql").write_text(rollback_sql(), encoding="utf-8", newline="\n")
    print("Prepared apply/rollback SQL only; no connection, role/grant change or password generation occurred.")


if __name__ == "__main__":
    main()
