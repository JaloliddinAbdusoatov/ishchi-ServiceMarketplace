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

  IF (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()) <> 'ishchi_local_owner'
     OR (SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='public') <> 'ishchi_local_owner' THEN
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
      WHERE n.nspname='public' AND c.relkind IN ('r','p','S') AND pg_get_userbyid(c.relowner) <> 'ishchi_local_owner')
     OR EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE n.nspname='public' AND (p.prosecdef OR pg_get_userbyid(p.proowner) <> 'ishchi_local_owner')) THEN
    RAISE EXCEPTION 'Ownership/security-definer drift; manual review required';
  END IF;
END;
$guard$;

ALTER DATABASE ishchi_marketplace_local OWNER TO ishchi_local_app;
ALTER SCHEMA public OWNER TO ishchi_local_app;
DO $owners$
DECLARE obj record;
BEGIN
  FOR obj IN SELECT c.relname,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relkind IN ('r','p','S') ORDER BY CASE WHEN c.relkind='S' THEN 1 ELSE 0 END,c.relname LOOP
    IF obj.relkind='S' THEN
      EXECUTE format('ALTER SEQUENCE public.%I OWNER TO ishchi_local_app',obj.relname);
    ELSE
      EXECUTE format('ALTER TABLE public.%I OWNER TO ishchi_local_app',obj.relname);
    END IF;
  END LOOP;
  FOR obj IN SELECT p.proname,pg_get_function_identity_arguments(p.oid) AS args FROM pg_proc p
    JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' LOOP
    EXECUTE format('ALTER FUNCTION public.%I(%s) OWNER TO ishchi_local_app',obj.proname,obj.args);
  END LOOP;
END;
$owners$;

REVOKE ishchi_local_owner FROM ishchi_local_migrator;
ALTER ROLE ishchi_local_migrator NOLOGIN;
GRANT USAGE, CREATE ON SCHEMA public TO ishchi_local_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO PUBLIC;
COMMIT;
-- No roles or data are dropped. This rollback restores the prior insecure ownership model.
