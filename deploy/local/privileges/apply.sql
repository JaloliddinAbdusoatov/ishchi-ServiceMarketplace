-- NOT AUTHORIZATION. Existing local database only; no data/reset/drop statements.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $guard$
BEGIN
  IF current_database() <> 'ishchi_marketplace_local' OR session_user <> 'ishchi_bootstrap' THEN
    RAISE EXCEPTION 'Wrong database or privileged operator';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('ishchi_local_owner','ishchi_local_migrator')) THEN RAISE EXCEPTION 'New role already exists; independent review required'; END IF;
  IF (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()) <> 'ishchi_local_app'
     OR (SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='public') <> 'ishchi_local_app' THEN
    RAISE EXCEPTION 'Database/schema owner drift; independent review required';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname='ishchi_local_app') THEN
    RAISE EXCEPTION 'Runtime role has unexpected memberships';
  END IF;
  IF (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public') <> 4 THEN
    RAISE EXCEPTION 'Function inventory drift; review before ownership transfer';
  END IF;
  IF to_regprocedure('public.fn_enforce_worker_category_limit()') IS NULL OR to_regprocedure('public.fn_purge_deactivated_worker_categories()') IS NULL OR to_regprocedure('public.ishchi_check_hiring(uuid)') IS NULL OR to_regprocedure('public.ishchi_hiring_integrity_event()') IS NULL THEN
    RAISE EXCEPTION 'Function signature drift; independent review required';
  END IF;
  IF (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='S') <> 11 THEN
    RAISE EXCEPTION 'Sequence inventory drift; independent review required';
  END IF;
  IF (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND c.relkind IN ('r','p')) <> 31
     OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND c.relkind IN ('r','p') AND c.relname NOT IN ('accounts_deletion_audit','accounts_user','accounts_user_groups','accounts_user_user_permissions','applications_order_application','auth_group','auth_group_permissions','auth_permission','categories_category','categories_worker_category','chat_conversation','chat_message','common_mediadeletiontask','django_admin_log','django_content_type','django_migrations','django_session','favorites_order','favorites_worker','invitations_order_invitation','notifications_notification','orders_order_image','orders_service_order','orders_service_order_assigned_workers','profiles_employer','profiles_worker','profiles_worker_portfolio','reports_report','reviews_review','token_blacklist_blacklistedtoken','token_blacklist_outstandingtoken')) THEN
    RAISE EXCEPTION 'Table inventory drift; do not apply this plan';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND c.relkind IN ('r','p','S') AND pg_get_userbyid(c.relowner) <> 'ishchi_local_app')
     OR EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE n.nspname='public' AND (p.prosecdef OR pg_get_userbyid(p.proowner) <> 'ishchi_local_app')) THEN
    RAISE EXCEPTION 'Ownership/security-definer drift; manual review required';
  END IF;
END;
$guard$;

CREATE ROLE ishchi_local_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE ishchi_local_migrator LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD NULL;
GRANT ishchi_local_owner TO ishchi_local_migrator WITH ADMIN FALSE, INHERIT FALSE, SET TRUE;

ALTER DATABASE ishchi_marketplace_local OWNER TO ishchi_local_owner;
ALTER SCHEMA public OWNER TO ishchi_local_owner;
DO $owners$
DECLARE obj record;
BEGIN
  FOR obj IN SELECT c.relname,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relkind IN ('r','p','S') ORDER BY CASE WHEN c.relkind='S' THEN 1 ELSE 0 END,c.relname LOOP
    IF obj.relkind='S' THEN
      EXECUTE format('ALTER SEQUENCE public.%I OWNER TO ishchi_local_owner',obj.relname);
    ELSE
      EXECUTE format('ALTER TABLE public.%I OWNER TO ishchi_local_owner',obj.relname);
    END IF;
  END LOOP;
  FOR obj IN SELECT p.proname,pg_get_function_identity_arguments(p.oid) AS args FROM pg_proc p
    JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' LOOP
    EXECUTE format('ALTER FUNCTION public.%I(%s) OWNER TO ishchi_local_owner',obj.proname,obj.args);
  END LOOP;
END;
$owners$;

REVOKE ALL ON DATABASE ishchi_marketplace_local FROM PUBLIC, ishchi_local_app, ishchi_local_migrator;
GRANT CONNECT ON DATABASE ishchi_marketplace_local TO ishchi_local_app, ishchi_local_migrator;
REVOKE ALL ON SCHEMA public FROM PUBLIC, ishchi_local_app, ishchi_local_migrator;
GRANT USAGE ON SCHEMA public TO ishchi_local_app;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC, ishchi_local_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, ishchi_local_app;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC, ishchi_local_app;
-- Future objects require explicit reviewed grants. No default runtime DML.
ALTER DEFAULT PRIVILEGES FOR ROLE ishchi_local_owner REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
GRANT SELECT, INSERT ON TABLE public.accounts_deletion_audit TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.accounts_user TO ishchi_local_app;
GRANT SELECT ON TABLE public.accounts_user_groups TO ishchi_local_app;
GRANT SELECT ON TABLE public.accounts_user_user_permissions TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.applications_order_application TO ishchi_local_app;
GRANT SELECT ON TABLE public.auth_group TO ishchi_local_app;
GRANT SELECT ON TABLE public.auth_group_permissions TO ishchi_local_app;
GRANT SELECT ON TABLE public.auth_permission TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.categories_category TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.categories_worker_category TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.chat_conversation TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.chat_message TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.common_mediadeletiontask TO ishchi_local_app;
GRANT SELECT, INSERT ON TABLE public.django_admin_log TO ishchi_local_app;
GRANT SELECT ON TABLE public.django_content_type TO ishchi_local_app;
GRANT SELECT ON TABLE public.django_migrations TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.django_session TO ishchi_local_app;
GRANT SELECT, INSERT, DELETE ON TABLE public.favorites_order TO ishchi_local_app;
GRANT SELECT, INSERT, DELETE ON TABLE public.favorites_worker TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.invitations_order_invitation TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.notifications_notification TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.orders_order_image TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.orders_service_order TO ishchi_local_app;
GRANT SELECT, INSERT, DELETE ON TABLE public.orders_service_order_assigned_workers TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.profiles_employer TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.profiles_worker TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.profiles_worker_portfolio TO ishchi_local_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.reports_report TO ishchi_local_app;
GRANT SELECT, INSERT ON TABLE public.reviews_review TO ishchi_local_app;
GRANT SELECT, INSERT ON TABLE public.token_blacklist_blacklistedtoken TO ishchi_local_app;
GRANT SELECT, INSERT ON TABLE public.token_blacklist_outstandingtoken TO ishchi_local_app;
GRANT USAGE, SELECT ON SEQUENCE public.django_admin_log_id_seq TO ishchi_local_app;
GRANT USAGE, SELECT ON SEQUENCE public.orders_service_order_assigned_workers_id_seq TO ishchi_local_app;
GRANT USAGE, SELECT ON SEQUENCE public.token_blacklist_blacklistedtoken_id_seq TO ishchi_local_app;
GRANT USAGE, SELECT ON SEQUENCE public.token_blacklist_outstandingtoken_id_seq TO ishchi_local_app;
GRANT EXECUTE ON FUNCTION public.fn_enforce_worker_category_limit() TO ishchi_local_app;
GRANT EXECUTE ON FUNCTION public.fn_purge_deactivated_worker_categories() TO ishchi_local_app;
GRANT EXECUTE ON FUNCTION public.ishchi_check_hiring(uuid) TO ishchi_local_app;
GRANT EXECUTE ON FUNCTION public.ishchi_hiring_integrity_event() TO ishchi_local_app;
COMMIT;
-- Migrator remains password-disabled until separately approved private credential installation.
