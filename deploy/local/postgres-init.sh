#!/bin/sh
# Runs ONLY at the first initialization of an explicitly approved NEW cluster.
set -eu
case "$ISHCHI_DB_ROLE:$POSTGRES_DB" in
  ishchi_local_app:ishchi_marketplace_local|ishchi_local_test:ishchi_marketplace_sprint1_local) ;;
  *) echo 'Unexpected local database identity' >&2; exit 1 ;;
esac
export ISHCHI_APP_PASSWORD="$(tr -d '\r\n' < /run/secrets/app_password)"
test "${#ISHCHI_APP_PASSWORD}" -ge 24
psql -X --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set app_role="$ISHCHI_DB_ROLE" --set app_db="$POSTGRES_DB" <<'SQL'
\getenv app_password ISHCHI_APP_PASSWORD
CREATE ROLE :"app_role" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'app_password';
ALTER DATABASE :"app_db" OWNER TO :"app_role";
REVOKE ALL ON DATABASE :"app_db" FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE :"app_db" TO :"app_role";
ALTER SCHEMA public OWNER TO :"app_role";
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
REVOKE CONNECT ON DATABASE template1 FROM PUBLIC;
SQL
unset ISHCHI_APP_PASSWORD
