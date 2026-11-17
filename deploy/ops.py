"""Offline operational plans. Deliberately has no live execution/approval bypass.

JSON command arrays are review material, not authorization. No subprocess, network,
backup, restore, deletion, database client or credential loading occurs here.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

BACKUP_NAME = re.compile(r"ishchi-(database|media)-(\d{8}T\d{6}Z)-[a-f0-9]{8}\.(dump|tar)\.age\Z")


def database_target(host, port, database, user, *, restore=False):
    if not re.fullmatch(r"[A-Za-z0-9.-]+", host) or not 1 <= port <= 65535:
        raise ValueError("An exact hostname/IP and valid port are required")
    pattern = r"ishchi_marketplace_restore_[a-z0-9_]+" if restore else r"ishchi_marketplace(?:_[a-z0-9_]+)?"
    if not re.fullmatch(pattern, database) or not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", user):
        raise ValueError("Only dedicated marketplace targets and explicit roles are accepted")
    return {"host": host, "port": port, "database": database, "user": user}


def base_plan(operation):
    return {"operation": operation, "execution": "BLOCKED_PENDING_OWNER_AUTHORIZATION_AND_REVIEW",
        "authorization": "NOT_GRANTED: owner must identify exact target, role, operations and expiry",
        "preconditions": ["Operator-approved clients and private output directory (0700/0600 or equivalent ACL)",
            "Credentials from an external secret manager; never command-line passwords",
            "Independent operator review; this plan is not an approval record"]}


def backup_directory(destination):
    original = Path(destination)
    directory = original.resolve()
    if not directory.is_dir() or original.is_symlink() or directory == Path(directory.anchor):
        raise ValueError("Select an explicit existing private backup directory")
    return directory


def backup_plan(target, destination, recipient, *, now=None):
    target = database_target(target["host"], target["port"], target["database"], target["user"])
    if not re.fullmatch(r"age1[0-9a-z]{58}", recipient):
        raise ValueError("An explicit age X25519 public recipient is required")
    directory = backup_directory(destination)
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    name = f"ishchi-database-{timestamp}-{uuid.uuid4().hex[:8]}.dump.age"
    output = directory / name
    connection = ["--host", target["host"], "--port", str(target["port"]), "--username", target["user"], "--dbname", target["database"]]
    plan = base_plan("database-backup")
    plan.update(target=target, output=str(output), clear_environment_prefixes=["PG"], environment={"PGSSLMODE": "verify-full",
        "PGSSLROOTCERT": "OPERATOR_CA_FILE", "PGPASSFILE": "OPERATOR_PRIVATE_PASSWORD_FILE"},
        pipeline=[["pg_dump", "--no-password", "--format=custom", "--no-owner", "--no-privileges", *connection],
                  ["age", "--recipient", recipient, "--output", str(output) + ".partial"]],
        finalize=["Require both pipeline exit codes == 0", "Fsync encrypted .partial then atomically rename to final output",
            "Write encrypted-file SHA-256/size to an operator-protected manifest",
            "Alert on failure; never publish incomplete output or leave a plaintext dump"], retention_days=30)
    return plan


def media_backup_plan(source, destination, recipient):
    if not re.fullmatch(r"age1[0-9a-z]{58}", recipient):
        raise ValueError("An explicit public age recipient is required")
    original = Path(source)
    root = original.resolve()
    if not root.is_dir() or root == Path(root.anchor) or original.is_symlink():
        raise ValueError("Select an explicit existing media directory, never a filesystem root")
    output_directory = backup_directory(destination)
    if output_directory == root or root in output_directory.parents:
        raise ValueError("Backup output must be outside the media source tree")
    # Symlinks are not followed by this proposed tar invocation. Operator must
    # quiesce uploads/anonymization and snapshot DB+media at a coordinated point.
    name = f"ishchi-media-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}.tar.age"
    plan = base_plan("media-backup")
    plan.update(source=str(root), output=str(output_directory / name),
        pipeline=[["tar", "--one-file-system", "--create", "--file=-", "--directory", str(root), "."],
            ["age", "--recipient", recipient, "--output", str(output_directory / (name + ".partial"))]],
        finalize=["Require both exit codes == 0 before atomic rename and manifest creation",
            "Coordinate a consistent DB/media snapshot; do not follow symlinks"], retention_days=30)
    return plan


def restore_plan(target, archive, identity_file):
    target = database_target(target["host"], target["port"], target["database"], target["user"], restore=True)
    path = Path(archive).resolve()
    if not BACKUP_NAME.fullmatch(path.name) or not path.name.endswith(".dump.age"):
        raise ValueError("Select an explicitly named encrypted database backup")
    plan = base_plan("isolated-restore")
    plan.update(target=target, archive=str(path),
        clear_environment_prefixes=["PG"], environment={"PGSSLMODE": "verify-full", "PGSSLROOTCERT": "OPERATOR_CA_FILE", "PGPASSFILE": "OPERATOR_PRIVATE_PASSWORD_FILE"},
        pipeline=[["age", "--decrypt", "--identity", str(Path(identity_file).resolve()), str(path)],
            ["pg_restore", "--no-password", "--exit-on-error", "--single-transaction", "--no-owner", "--no-privileges",
             "--host", target["host"], "--port", str(target["port"]), "--username", target["user"], "--dbname", target["database"]]],
        pre_restore=["Verify the independent protected manifest and backup provenance",
            "Operator provisions and verifies EMPTY isolated target; do not clone protected data",
            "Obtain a current erasure/tombstone ledger independent of this backup; completed outbox rows discard file keys and are insufficient for replay",
            "Keep traffic closed until approved post-backup erasures and session invalidation are reconciled",
            "Never use --clean or --create; restore grants/audit ownership require separate review"],
        verification=["Both pipeline exit codes zero", "Compare schema/migration inventory and row counts with the backup manifest",
            "Check relationships, representative media and anonymization retention",
            "Reapply reviewed least-privilege ACLs and test audit immutability",
            "Revoke old sessions and rebuild Redis security state before any traffic"],
        recovery_verified=False)
    return plan


def media_restore_plan(archive, destination, identity_file):
    archive = Path(archive).resolve()
    destination = Path(destination).resolve()
    if not BACKUP_NAME.fullmatch(archive.name) or not archive.name.endswith(".tar.age"):
        raise ValueError("Select an explicitly named encrypted media backup")
    if not destination.is_dir() or destination == Path(destination.anchor) or any(destination.iterdir()):
        raise ValueError("Media recovery requires an explicit empty isolated directory")
    plan = base_plan("isolated-media-restore")
    plan.update(archive=str(archive), destination=str(destination),
        decrypt_command=["age", "--decrypt", "--identity", str(Path(identity_file).resolve()), str(archive)],
        pre_restore=["Authenticate the independent manifest and encryption recipient",
            "Require a current independent erasure ledger; completed outbox rows alone cannot identify previously erased storage keys",
            "Inspect the decrypted stream in an approved restricted recovery sandbox before extraction",
            "Reject absolute/traversing paths, links, device files, duplicate names and excessive expanded sizes",
            "Extract only reviewed regular files/directories into this empty sandbox; preserve no archive ownership",
            "Compare recovered file hashes with manifest, then reconcile deletion outbox/tombstones before serving",
            "Never restore erased personal media into public storage without retention review"],
        extraction_execution="BLOCKED: operator-reviewed sandbox extractor and target approval required",
        recovery_verified=False)
    return plan


def retention_plan(directory, days=30, *, now=None):
    root = Path(directory).resolve()
    if not root.is_dir() or root == Path(root.anchor) or not 7 <= days <= 3650:
        raise ValueError("Select an existing backup directory and retention of 7..3650 days")
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    candidates = []
    for path in sorted(root.iterdir()):
        match = BACKUP_NAME.fullmatch(path.name)
        if path.is_symlink() or not path.is_file() or not match:
            continue
        dated = datetime.strptime(match[2], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        if dated < cutoff:
            candidates.append(str(path))
    return {**base_plan("expired-backup-cleanup"), "directory": str(root), "retention_days": days,
        "candidates": candidates, "deleted": 0,
        "preconditions": ["Confirm immutable/offsite copies and at least one verified restore point",
            "Obtain exact artifact deletion authorization; never recursively delete directories"]}


def verify_archive(path, expected_sha256):
    path = Path(path)
    if path.is_symlink() or not BACKUP_NAME.fullmatch(path.name) or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise ValueError("An encrypted backup and independent expected SHA-256 are required")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        if source.read(22) != b"age-encryption.org/v1\n":
            raise ValueError("Not an age encrypted archive")
        source.seek(0)
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected_sha256:
        raise ValueError("Encrypted archive checksum mismatch")
    return {"checksum_matches": True, "age_header_present": True, "recovery_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan-backup", "plan-restore"):
        child = sub.add_parser(command)
        for name in ("host", "database", "user"):
            child.add_argument("--" + name, required=True)
        child.add_argument("--port", type=int, default=5432)
        if command == "plan-backup":
            child.add_argument("--destination", required=True)
            child.add_argument("--recipient", required=True)
        else:
            child.add_argument("--archive", required=True)
            child.add_argument("--identity-file", required=True)
    media = sub.add_parser("plan-media-backup")
    for name in ("source", "destination", "recipient"):
        media.add_argument("--" + name, required=True)
    retention = sub.add_parser("plan-retention")
    retention.add_argument("--directory", required=True)
    retention.add_argument("--days", type=int, default=30)
    verify = sub.add_parser("verify-archive")
    verify.add_argument("--archive", required=True)
    verify.add_argument("--sha256", required=True)
    media_restore = sub.add_parser("plan-media-restore")
    for name in ("archive", "destination", "identity-file"):
        media_restore.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ("plan-backup", "plan-restore"):
            target = database_target(args.host, args.port, args.database, args.user, restore=args.command == "plan-restore")
            plan = backup_plan(target, args.destination, args.recipient) if args.command == "plan-backup" else restore_plan(target, args.archive, args.identity_file)
        elif args.command == "plan-media-backup":
            plan = media_backup_plan(args.source, args.destination, args.recipient)
        elif args.command == "plan-retention":
            plan = retention_plan(args.directory, args.days)
        elif args.command == "plan-media-restore":
            plan = media_restore_plan(args.archive, args.destination, args.identity_file)
        else:
            plan = verify_archive(args.archive, args.sha256)
    except (ValueError, OSError):
        parser.error("Invalid operational target or artifact; no operation performed")
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
