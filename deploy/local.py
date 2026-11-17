"""Local setup helpers. Secrets/configuration are NOT owner authorization.

No command provisions infrastructure. pg-tests/redis-tests are connection commands:
invoke them only after separate exact-target owner approval. No resets are supplied.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
SECRET_NAMES = ("django_key", "work_pg_bootstrap", "test_pg_bootstrap", "work_pg_password",
                "test_pg_password", "work_redis_password", "test_redis_password")


def initialize_secrets(directory):
    original = Path(directory)
    if not original.is_absolute() or original.is_symlink() or original.resolve() == Path(original.anchor):
        raise ValueError("Choose an absolute private directory, never a filesystem root or symlink")
    directory = original.resolve()
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Refusing to overwrite an existing secrets directory")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in SECRET_NAMES:
        with (directory / name).open("x", encoding="utf-8", newline="\n") as output:
            output.write(secrets.token_hex(48) + "\n")
        (directory / name).chmod(0o600)
    # pg_dump's password file format differs from the raw container secret.
    password = (directory / "work_pg_password").read_text(encoding="utf-8").strip()
    with (directory / "local.pgpass").open("x", encoding="utf-8", newline="\n") as output:
        output.write(f"127.0.0.1:55432:ishchi_marketplace_local:ishchi_local_app:{password}\n")
    (directory / "local.pgpass").chmod(0o600)
    work_db = {"host": "postgres-work", "port": "5432", "dbname": "ishchi_marketplace_local", "user": "ishchi_local_app"}
    test_db = {"host": "127.0.0.1", "port": "55433", "dbname": "ishchi_marketplace_sprint1_local", "user": "ishchi_local_test"}
    work_redis = {"host": "redis-work", "port": 6379, "database": 0, "user": "ishchi_local_app"}
    test_redis = {"host": "127.0.0.1", "port": 56380, "database": 0, "user": "ishchi_local_test"}
    for name, target, operations, disposable in (
        ("work-db", work_db, ["connect"], False),
        ("work-db-migration", work_db, ["connect", "local_migrate"], False),
        ("work-redis", work_redis, ["cache"], False),
        ("test-db", test_db, ["connect", "test_schema"], True),
        ("test-redis", test_redis, ["cache", "cache_test"], True),
    ):
        # Deliberately inert templates. Never manufacture an operational approval.
        value = {"approved_by": "", "expires_at": "2000-01-01T00:00:00Z", "target": target,
                 "operations": operations, "disposable": disposable}
        path = directory / (name + "-authorization.json")
        with path.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(value, output, indent=2)
            output.write("\n")
        path.chmod(0o600)
    return directory


def check(root=ROOT):
    config = yaml.safe_load((root / "deploy/compose.local.yml").read_text(encoding="utf-8"))
    services = config["services"]
    for service in services.values():
        if not service.get("profiles"):
            raise ValueError("Every local service requires an explicit profile")
        for port in service.get("ports", []):
            if not isinstance(port, str) or not port.startswith("127.0.0.1:"):
                raise ValueError("All local published ports must bind IPv4 loopback")
    if any(value and (value.get("external") or value.get("name")) for value in config["volumes"].values()):
        raise ValueError("Local data volumes cannot import external or named existing volumes")
    if services["backend"].get("command"):
        raise ValueError("Backend startup must use the image command, never migrate or seed")
    if services["postgres-work"]["environment"]["POSTGRES_DB"] != "ishchi_marketplace_local" or services["postgres-test"]["environment"]["POSTGRES_DB"] != "ishchi_marketplace_sprint1_local":
        raise ValueError("Working and disposable database names are fixed and separate")
    if services["backend"]["environment"]["DJANGO_SETTINGS_MODULE"] != "config.settings.local_postgres":
        raise ValueError("Local backend must explicitly use local settings")
    for service in ("postgres-work", "redis-work", "backend"):
        if services[service]["networks"] != ["work"]:
            raise ValueError("Working services cannot join the disposable network")
    for service in ("postgres-test", "redis-test"):
        if services[service]["networks"] != ["test"]:
            raise ValueError("Disposable services cannot join the working network")
    for first, second in (("postgres-work", "postgres-test"), ("redis-work", "redis-test")):
        first_data = {str(v).split(":")[0] for v in services[first]["volumes"] if not str(v).startswith(".")}
        second_data = {str(v).split(":")[0] for v in services[second]["volumes"] if not str(v).startswith(".")}
        if not first_data or first_data & second_data:
            raise ValueError("Working/test services must not share data volumes")
    if not all(not value.get("internal", False) and value.get("driver") == "bridge" and value.get("driver_opts", {}).get(
        "com.docker.network.bridge.host_binding_ipv4") == "127.0.0.1" for value in config["networks"].values()):
        raise ValueError("Separate local bridges must default all publication to loopback")
    return config


def test_command(kind, directory, python=None):
    directory = Path(directory).resolve()
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("DB_", "REDIS_", "PG", "LOCAL_REDIS_", "DJANGO_", "ISHCHI_"))}
    env.update(ISHCHI_ENV="local", DB_PASSWORD_FILE=str(directory / "test_pg_password"),
               DB_AUTHORIZATION_FILE=str(directory / "test-db-authorization.json"),
               REDIS_PASSWORD_FILE=str(directory / "test_redis_password"),
               REDIS_AUTHORIZATION_FILE=str(directory / "test-redis-authorization.json"))
    module = "postgres_integration_local" if kind == "pg" else "redis_integration_local"
    executable = python or str(ROOT / "backend/.venv/Scripts/python.exe" if os.name == "nt" else ROOT / "backend/.venv/bin/python")
    return [executable, "-m", "pytest", "pgtests" if kind == "pg" else "redistests", "--ds=config.settings." + module, "-q"], env


def recovery_plan(kind, directory, recipient=None, archive=None, identity_file=None):
    spec = importlib.util.spec_from_file_location("ishchi_local_ops", ROOT / "deploy/ops.py")
    ops = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ops)
    if kind == "backup":
        target = ops.database_target("127.0.0.1", 55432, "ishchi_marketplace_local", "ishchi_local_app")
        plan = ops.backup_plan(target, directory, recipient)
    else:
        target = ops.database_target("127.0.0.1", 55434, "ishchi_marketplace_restore_local", "ishchi_local_restore", restore=True)
        plan = ops.restore_plan(target, archive, identity_file)
    # Deliberate localhost-only plaintext, unlike the unchanged production planner.
    plan["environment"]["PGSSLMODE"] = "disable"
    plan["environment"].pop("PGSSLROOTCERT", None)
    plan["local_only"] = True
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    init = sub.add_parser("init-secrets")
    init.add_argument("--directory", required=True)
    for kind in ("pg", "redis"):
        child = sub.add_parser(kind + "-tests")
        child.add_argument("--secrets-dir", required=True)
    backup = sub.add_parser("backup-plan")
    backup.add_argument("--destination", required=True)
    backup.add_argument("--recipient", required=True)
    restore = sub.add_parser("restore-plan")
    restore.add_argument("--archive", required=True)
    restore.add_argument("--identity-file", required=True)
    args = parser.parse_args(argv)
    if args.command == "check":
        check()
        print("PASS: local profiles, loopback ports, exact targets and separate volumes/networks; no connection or provisioning")
    elif args.command == "init-secrets":
        initialize_secrets(args.directory)
        print("Generated private local secrets and EXPIRED BLANK interlocks; no authority granted or services started")
    elif args.command in {"pg-tests", "redis-tests"}:
        command, env = test_command(args.command.split("-")[0], args.secrets_dir)
        return subprocess.run(command, env=env, cwd=ROOT / "backend").returncode
    else:
        plan = recovery_plan("backup", args.destination, recipient=args.recipient) if args.command == "backup-plan" else recovery_plan(
            "restore", None, archive=args.archive, identity_file=args.identity_file)
        print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
