# Local operations — 2026-11-17

Status: `LOCAL_OPERATIONS_VERIFIED` for approved demotion and encrypted backup
scheduling. No new restore was executed; this is not a production deployment.

## Actual results

- Owner separately approved exact-account demotion through Nov 17 23:59 Tashkent,
  first backup/daily task through Nov 24 23:59, and one additional scheduled test.
- Synthetic `489124fe-ae1b-4551-8495-9f148c46490b`: staff/superuser false, role
  WORKER, active preserved, token_version 2 -> 3. Account/password/history retained.
  No worker profile created. Memberships were empty; no unnecessary permission
  table DELETE or new GRANT was used. Initial denied DELETE rolled back fully;
  guarded retry passed. Only subject sessions/refresh tokens revoked; audit added.
- Live checks PASS: old-version access/refresh 401, subject /me 200, admin API 403,
  Django admin permission false, unblacklisted refresh tokens/sessions zero.
  Owner `319cb674-96bc-4de3-bf08-e6c4462500f7` unchanged, admin API 200 and Django
  permission true. Short-lived in-memory verification JWTs; no password login.
- No runtime/background configuration depends on the synthetic UUID. Only old
  rotation/verification operator tooling references it; that tooling is not a job.
- Backup-only runner PASS: `20261117T090147Z-0e6a0942`.
- Native Windows Task Scheduler run PASS: `20261117T090554Z-7cf616e7`,
  LastTaskResult=0; enabled/Ready; next run Nov 17 at 20:00 Asia/Tashkent.
- Existing data/media/migrations and original backup/recovery files preserved;
  expected changes only subject demotion, subject sessions, blacklist and audit.
- PASS: 345 backend tests (42 focused operations regressions), one existing
  DATABASES-override warning; native task schema/Windows ACL checks and backend
  image build also passed.
  Frontend NOT RUN: no frontend/API contract change.

## Daily operation

1. Keep the Windows operator logged in, Docker Desktop and existing local app
   running. Use the work-only start/stop commands in LOCAL.md; no migrations/seed.
2. Task `ISHCHI Encrypted Local Backup` runs at 20:00 +05:00. InteractiveToken,
   LeastPrivilege, IgnoreNew and kernel file lock prevent overlapping runs.
   Missed runs catch up when available; this is not an unattended Windows service.
3. Check Task Scheduler LastTaskResult (0 success, 1 failure, 3 renewal/approval
   needed, 4 overlap skip). Failures show a bounded desktop warning. Restricted
   fixed-metadata event logs are retained under private recovery/backup-logs;
   scheduled-backup-status.json is the latest result.
4. Authorization ends **2026-11-24 23:59 Asia/Tashkent**. Runner fails safely after
   expiry and before any new pause/dump. No existing expiry files were extended.
   New separate backup scope permits existing migrator/SET ROLE owner for read-only
   dump only; it does not extend migration/DDL/role-change authorization.
5. `python deploy/local_backup.py` is a safe offline plan. Do not manually repeat
   backup runs outside the owner-approved scope.

## Backup and recovery boundaries

Existing age v1.3.2 identity/public recipient reused; no key regeneration. Source:
127.0.0.1:55432 / ishchi_marketplace_local, existing ishchi_local_migrator with
SET ROLE ishchi_local_owner for read-only backup. Destination D:/Ishchi-backups.
New directories restrict files to operator/SYSTEM; preflight permits existing
trusted local-admin/owner ACLs and rejects broad readers. No passwords in scripts,
task arguments or logs; raw credential files are mounted read-only, never copied.

The runner reuses local_recovery encryption/fingerprinting; pauses gateway/backend
for a quiet DB/media checkpoint and checks before/after row/schema/sequence/media
fingerprints. No independent external writer may run during that checkpoint.
Existing recovery identity authenticates independent encrypted manifest/ledger
using a domain-separated HMAC. Full age authentication, ciphertext hashes, tar
member/media inventory checks and network-disabled pg_restore --list passed.
COMPLETE publishes only after validation. This checks archives, **not a restore**.
256 MiB ciphertext per archive is the local verification ceiling; larger runs fail
closed pending sizing review. No plaintext archives are written to disk.

No existing backups are automatically deleted. Review retention after 30 days;
actual deletion needs separate approval. Only the current run's known incomplete
.partial files are cleaned; failed encrypted artifacts/history remain.

A nightly ledger is CURRENT ONLY AT ITS CHECKPOINT. Cross-storage deletion-to-host
synchronization is not atomic here. After anonymization/media deletion and before
ANY recovery traffic, require a separately approved quiet authoritative export
and compare current tombstones, deletion audit IDs, all outbox update/completion
IDs and live media inventory using require_fresh_ledger. Timestamp/old backup's
ledger is insufficient. If currentness cannot be proved, recovery stays offline.
Historical backups may also contain old privileges/sessions: reconcile current
admin demotion and token/session security state before exposing any restored app.
Future restore always needs a separately approved NEW empty DB/media sandbox.
No new restore PASS is claimed; previous isolated restore remains historical PASS.

Finally resumes backend/recreates gateway and checks readiness after failures.
Forced machine/task termination can prevent finally; backup-resume-required.json
blocks another backup. With valid runtime authorization, run
`python deploy/local_backup.py --resume-only`: no backup/restore, readiness first,
then removal of only that interruption marker. Do not bypass expired guards.

The private recovery identity must still receive an owner-managed secure offline
copy outside this computer/backups. Do not put it in chat/Git or beside archives.

## Reviewed demotion command / reversal

The completed action used the owner-approved private exact-target authorization
and an ephemeral backend operator container. Do not replay the command: it refuses
an already demoted subject. Templates in local/*.example.json remain unapproved;
the repository XML stays disabled as a safe installation template; the registered
task was separately enabled after owner approval.

Reinstatement requires NEW owner approval. Restore only this subject's original
role/staff/superuser and original membership IDs from deploy/.local/demotion-receipt.json,
inside an audited transaction. Prior state: ADMIN/true/true, memberships empty.
Never decrement token_version, restore old sessions or remove token blacklists.
Owner administrator must remain unchanged. No reinstatement was authorized/run.

## Source/configuration and evidence

Changed: backend/apps/accounts/services/local_demotion.py;
backend/apps/accounts/management/commands/demote_local_verification_admin.py;
backend/tests/test_local_operations.py; deploy/local_backup.py;
deploy/local_recovery.py (bounded metadata-encryption timeout);
deploy/local/{run-scheduled-backup.ps1,ishchi-backup-task.xml,
admin-demotion-authorization.example.json,scheduled-backup-authorization.example.json};
this file and DAILY_USE.md. Unrelated existing working-tree edits retained.

Evidence in deploy/.local/: demotion-receipt.json, demotion-verification.json,
local-backup-first-run.json, scheduled-backup-execution.json,
local-operations-preservation.json, local-operations-tests.log. Credentials are
not included. Private approval files were created only after explicit chat consent.
