"""One-time approved existing-local role correction. No resets or working data DML.

Requires real independent approval recorded in role-change-authorization.json;
this file is an interlock, not a source of owner authority. Default is offline.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path(r"C:\Users\user\.codex\ishchi-local-private")
TARGET = dict(host="127.0.0.1", port="55432", dbname="ishchi_marketplace_local", user="ishchi_bootstrap")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def approval():
    doc = json.loads((PRIVATE / "role-change-authorization.json").read_text())
    if doc["target"] != TARGET or not doc["approved_by"].strip() or datetime.fromisoformat(doc["expires_at"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
        raise ValueError("Exact, unexpired owner approval is required")
    if not {"apply_local_roles", "install_local_migrator", "rollback_local_roles"} <= set(doc["operations"]):
        raise ValueError("Missing privileged operation scope")
    if any(value for key, value in os.environ.items() if key.startswith("PG")):
        raise ValueError("Clear libpq environment overrides")
    return doc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--resume-after-rollback", action="store_true")
    args = parser.parse_args(argv)
    if not args.apply:
        print("DRY RUN: no connection, secret generation, SQL or service change")
        return
    authorization = approval()
    import psycopg
    from psycopg import sql
    plan = load_module("local_privilege_plan", ROOT / "deploy/local_privileges.py")
    stability = load_module("local_stability", ROOT / "deploy/stabilize_local.py")
    dc = stability.docker_prefix("desktop-linux") + ["compose", "--env-file", "deploy/.env.local", "-f", "deploy/compose.local.yml", "--profile", "work"]
    overlay = dc + ["-f", "deploy/compose.local-roles.yml", "--profile", "operator"]
    for filename, expected in (("apply.sql", plan.apply_sql()), ("rollback.sql", plan.rollback_sql())):
        if (ROOT / "deploy/local/privileges" / filename).read_text() != expected:
            raise ValueError("SQL plan drift")
    password_file = PRIVATE / "local_migration_password"
    if args.resume_after_rollback:
        previous = json.loads((ROOT / "deploy/.local/role-change-result.json").read_text())
        if previous.get('privilege_rollback') != 'PASS - prior insecure ownership restored' or previous.get('readiness') != 'PASS':
            raise ValueError('Verified prior rollback is required for retry')
        password = password_file.read_text().strip()
        if len(password) < 24:
            raise ValueError('Invalid existing dedicated migrator secret')
    elif password_file.exists():
        raise ValueError("Refusing to replace an existing migration credential")
    else:
        password = secrets.token_urlsafe(48)
        with password_file.open("x", encoding="utf-8", newline="\n") as file:
            file.write(password + "\n")
        password_file.chmod(0o600)
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "role_change": "NOT RUN"}
    destination = ROOT / "deploy/.local/role-change-result.json"
    destination.parent.mkdir(exist_ok=True)

    def run(command, *, input=None, timeout=60):
        result = subprocess.run(command, input=input, text=True, capture_output=True, cwd=ROOT, timeout=timeout)
        if result.returncode:
            report['failed_command'] = command[-2:]
            report['safe_error'] = next((line for line in result.stderr.splitlines() if line.startswith('CommandError:')), 'No safe diagnostic line')
            # Commands never include passwords; do not emit arbitrary child output.
            raise RuntimeError("Operator command failed: " + " ".join(command[-5:]))
        return result.stdout

    payload = {"mode": "snapshot", "key": secrets.token_hex(32), "probe": "role-change-no-new-marker"}

    def snapshot():
        return json.loads(run(dc + ["run", "--rm", "-T", "--no-deps", "backend", "python", "-c", stability.SERVER_CODE], input=json.dumps(payload)))

    stopped = applied = False
    connection = None
    try:
        run(dc + ["stop", "gateway", "backend"])
        stopped = True
        before = snapshot()
        connection = psycopg.connect(**TARGET, password=(PRIVATE / "work_pg_bootstrap").read_text().strip(), sslmode="disable", connect_timeout=5, autocommit=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(),session_user,inet_server_port()")
            if cursor.fetchone() != (TARGET["dbname"], TARGET["user"], 5432):
                raise ValueError("Wrong privileged endpoint")
            verifier = connection.pgconn.encrypt_password(password.encode(), b"ishchi_local_migrator", b"scram-sha-256").decode()
            # Add the new login's SCRAM verifier inside the SAME guarded transaction.
            statement = plan.apply_sql(reuse_rolled_back_roles=args.resume_after_rollback).replace("\\set ON_ERROR_STOP on\n", "")
            credential_sql = sql.SQL("ALTER ROLE ishchi_local_migrator PASSWORD {} VALID UNTIL {};").format(sql.Literal(verifier),sql.Literal(authorization['expires_at'])).as_string(connection)
            statement = statement.replace("COMMIT;", credential_sql + "\nCOMMIT;", 1)
            cursor.execute(statement, prepare=False)
        applied = True
        report["role_change"] = "PASS"
        password = verifier = statement = credential_sql = None
        run(overlay + ["run", "--rm", "-T", "--no-deps", "migrate", "python", "manage.py", "migrate", "--check", "--noinput"])
        report["migration_operator_check"] = "PASS"
        probe = PRIVATE / "runtime-probe-authorization.json"
        run(dc + ["run", "--rm", "-T", "--no-deps", "--volume", str(probe) + ":/run/secrets/runtime_probe:ro", "-e", "DB_AUTHORIZATION_FILE=/run/secrets/runtime_probe", "backend", "python", "manage.py", "verify_local_audit_privileges", "--exercise"])
        report["audit_database_exercise"] = "PASS"
        after = snapshot()
        report.update(data_preserved=before == after, row_counts=after["row_counts"], media_files=after["media_files"])
        if before != after:
            raise RuntimeError("Before/after inventory differs; no reset or data repair attempted")
    except Exception as exc:
        report["error"] = type(exc).__name__ + (":" + exc.sqlstate if getattr(exc, "sqlstate", None) else "")
        if connection is not None:
            connection.execute("ROLLBACK")
        if applied:
            approval()
            try:
                connection.execute(plan.rollback_sql().replace("\\set ON_ERROR_STOP on\n", ""), prepare=False)
                report["privilege_rollback"] = "PASS - prior insecure ownership restored"
            except Exception:
                report["privilege_rollback"] = "FAIL - manual intervention required"
        raise RuntimeError("Role correction did not verify; see secret-free role-change-result.json. No data reset attempted.") from None
    finally:
        if connection is not None:
            connection.close()
        if stopped:
            try:
                run(dc + ["up", "-d", "--no-deps", "--force-recreate", "backend", "gateway"])
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    try:
                        with opener.open("http://127.0.0.1:8080/api/v1/health/ready/", timeout=3) as response:
                            if response.status == 200:
                                report["readiness"] = "PASS"
                                break
                    except OSError:
                        pass
                    time.sleep(.3)
                else:
                    report["readiness"] = "FAIL"
            except Exception:
                report["readiness"] = "FAIL"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        destination.write_text(json.dumps(report, indent=2) + "\n")
    if report.get("readiness") != "PASS":
        raise RuntimeError("Readiness failed; inspect local service state")
    print("PASS: roles/migrator/audit checks verified; all table/media/security fingerprints preserved; readiness 200")


if __name__ == "__main__":
    main()
