# Local security closure — 2026-11-17

Status: `LOCAL_SECURITY_PARTIAL`. Confirmed database privilege defects are fixed.
Old-password login rejection was NOT RUN because the old password was unknown;
the owner still needs an independent offline recovery-identity copy. No public
service/payment/SMS deployment, reset, reseed or unrelated database access occurred.

## Applied and actually verified

- **PASS administrator rotation:** exact account
  `489124fe-ae1b-4551-8495-9f148c46490b`, hidden owner-entered password, token
  version 1 → 2. Old access/refresh JWTs and admin session rejected; new API/admin
  authentication and dashboard worked. Other account security state and working
  global key unchanged. Do not rotate again just to repeat this check.
- **NOT RUN old-password login:** previous password unknown. The explicit
  `--previous-password-unknown` skips only that input/test, still checks new
  password policy/difference from the stored old hash, JWT/session revocation,
  new login and other accounts. Failed preceding attempts did not commit rotation.
- **OWNER RETAINED:** old `local-verification-admin.json` remains at the owner's
  explicit request. It was not read/deleted/reused. Plaintext-file authentication
  and automatic administrator bootstrap remain retired; no new plaintext copy.
- **PASS daily-use renewal:** working PG/Redis scopes only, through **2026-11-24
  23:59 Asia/Tashkent / 18:59 UTC**, exact original targets and credentials.
  Both mounted expiry values and readiness were verified. Test scope was not
  renewed; migration/backup/restore scopes are separate.
- **PASS role separation:** existing work DB/public schema, 31 tables, 11
  sequences and four SECURITY INVOKER functions now belong to NOLOGIN
  `ishchi_local_owner`. Runtime `ishchi_local_app` is non-owner/non-superuser,
  without schema/database CREATE or privileged membership. Only dedicated
  `ishchi_local_migrator` may SET ROLE to owner, without ADMIN or automatic
  inheritance. It has no SUPERUSER/CREATEDB/CREATEROLE/BYPASSRLS grants.
- **PASS audit enforcement:** runtime SELECT/INSERT on `accounts_deletion_audit`
  and `django_admin_log`; actual INSERTs succeeded, six UPDATE/DELETE/TRUNCATE
  statements returned SQLSTATE 42501. Runtime CREATE TABLE and SET ROLE owner
  were also denied. Existing audit records stayed unchanged. Preflight refuses
  rejection probes while dangerous grants remain. No actual table was truncated.
- **PASS atomic business audit:** real admin suspension produced an audit row;
  a real PostgreSQL NOT NULL failure during audit insertion returned the existing
  API integrity-conflict response (409), and the business update rolled back.
  All probe rows rolled back; sequence gaps can remain, as PostgreSQL sequences
  are not transactional. No existing account was a mutation test subject.

Actual one-time owner approval ends **2026-11-17 23:59 Asia/Tashkent**. Dedicated
migrator password validity also ends then. Separate operator/probe interlocks do
not extend runtime or test scope. Future operator/recovery work needs genuine
renewal; do not edit expiry files without it.

The guarded offline `local_privileges.py` creates apply/rollback SQL.
`apply_local_roles.py --apply` checks real recorded owner approval and exact target,
compares data in memory, installs only the new migrator credential and checks the
operator. A first validation attempt restored prior privileges safely after a
409-vs-500 test expectation failed; the corrected guarded retry passed. No role
or data was dropped. Rollback restores the old insecure ownership model, not a
successful security closure. Do not rerun apply on the already-corrected DB.

## Daily operation and migrations

Continue ordinary work-only start/stop from `LOCAL.md`; never remove volumes,
seed/reset or migrate on startup. Runtime migrate/schema-editor guards reject
before connection. For a separately approved migration, use the existing private
migrator secret and `compose.local-roles.yml` operator overlay:

```powershell
$dc = @('--context','desktop-linux','compose','--env-file','deploy/.env.local','-f','deploy/compose.local.yml','-f','deploy/compose.local-roles.yml','--profile','operator')
docker @dc run --rm --no-deps migrate python manage.py migrate --check --noinput
```

Operator `migrate --check` passed (49 applied migrations, no pending changes).
No artificial migration was added to the working DB. Subsequent new objects need
explicit reviewed runtime grants; there is no broad future-table default DML.
Future owner-function EXECUTE defaults are revoked globally, as required by
[PostgreSQL default-privilege semantics](https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html).

## Real encrypted backup and isolated restore — PASS

Owner separately approved new age identity, encrypted PG+media backup in
`D:/Ishchi-backups/`, 30-day retention without automatic deletion, and new
`127.0.0.1:55434 / ishchi_marketplace_restore_local / ishchi_local_restore` with
new isolated volume/media under `D:/Ishchi-restore-sandbox/`. Working restore was
never attempted. Recovery/provisioning scopes end November 17 at 23:59 Tashkent.

Actual checkpoint: `20261116T185338Z-fb0662b5`. Ciphertexts are
`postgres.dump.age`, `media.tar.age` and `manifest.json.age` under that backup
subdirectory. Database/media stream encryption required both producer and age
success, fsync and unique atomic publication; no plaintext dump/tar was persisted.
The encrypted manifest records ciphertext hashes/sizes. Full authenticated age
decryption succeeded before restore. Pinned age v1.3.2 came from its
[upstream release](https://github.com/FiloSottile/age/releases/tag/v1.3.2), checked
against the upstream GitHub API SHA-256; independent Sigsum verification was NOT
RUN. Recovery identity/files inherit owner/SYSTEM-only Windows ACLs.

The new empty restore DB received an atomic `pg_restore --single-transaction`
with no owner/ACL import. Its non-superuser restore operator owns only that fresh
DB. An initial credential-file CRLF error failed before any table restore; the
corrected attempt exited 0. All 31 table contents (including 49 migration records),
constraints, trigger/function definitions, sequence states and checkpoint media
matched. Two known equivalent status-array cast forms in partial-index deparsing
are narrowly normalized; other index definitions must match. Django checks,
migration inventory and restored admin authorization passed using isolated
settings, a fresh sandbox-only signing key and memory cache. No restore app or
working Redis connection was exposed. The restore PG service is now **STOPPED**;
its volume and sandbox remain, with no deletion or adoption of an old target.

An independent encrypted erasure ledger is stored in the private recovery area,
separately from backup archives. Current account tombstones/deletion audit IDs,
pending erasures and allowed media hashes were checked. Actual checkpoint had no
existing account/media erasures; additional rollback-only synthetic restore tests
proved that a nonempty tombstone blocks an active restored account, an anonymized
fixture passes, and pending erased media blocks recovery. No fixture rows remain.

After subsequent erasures and before recovery traffic, export a fresh ledger
under separately valid recovery authorization:

```powershell
.\backend\.venv\Scripts\python.exe deploy/local_recovery.py --export-ledger
```

This manually pauses app writers, uses runtime read-only SELECT, writes a NEW
independent encrypted ledger, authenticates it and updates only a metadata
pointer. It was actually run successfully. There is **no automatic export job**;
unproven ledger currentness blocks future recovery traffic. Never trust an old
backup's erasure outbox or ledger as the latest deletion record.

Keep the recovery identity private and make a separate secure offline copy;
that owner action is **NOT RUN**. Current backup/identity on one computer does
not protect against loss of that computer. No retention deletion ran. The
`local_recovery.py --execute` full-run helper refuses an existing sandbox/key/
archive/occupied port: do not rerun it against retained verification targets;
a future backup/restore run requires separately reviewed fresh-target preparation.

## Preservation and tests

- **PASS ordinary PG/Redis/app stop-start:** all table fingerprints unchanged,
  including 5 accounts, 2 jobs, 3 applications, 3 assignments, credentials/token
  versions, audit records and history. Working administrator remains active at
  token version 2. Media markers and checked Redis security values persisted;
  same Redis ACL/password/namespace and authenticated readiness were preserved.
- **Limits:** both existing jobs were COMPLETED, so a preexisting PUBLISHED-job
  restart case was NOT RUN. Both existing media files are synthetic markers;
  real-upload persistence is NOT RUN. Existing live Redis lockout/revocation keys
  were absent; persistence of those particular cases is NOT RUN. The backup
  checkpoint contained one marker; the later restart added a second harmless one.
- **PASS real work PG/Redis API flow:** normal registration/password login,
  optional phone/KYC, admin authorization/audit, job publication, applications/
  hiring, chat/notifications, completion/review and deferred constraints. Payments
  remained disabled. Django APIClient exercised actual views/DB/cache, not a
  browser UI walkthrough. All synthetic DB fixtures rolled back; existing
  database/media/security fingerprints matched before/after.
- **PASS 301 backend SQLite tests**, one existing DATABASES-override warning;
  **18 frontend tests**; Django/migration-drift/dependency checks, local/Compose
  invariants and bounded source secret scan (not a historical/full certification).
- **NOT RUN again:** original 34 PG and 8 Redis integration suites. The occupied
  test DB was not reset. Historical results remain PASS; separate actual work PG
  audit/DDL/business and isolated recovery checks above did run and pass.

Secret-free actual evidence is in `deploy/.local/security-closure.json`,
`role-change-result.json`, `runtime-marketplace.json`,
`security-final-preservation.json`, `security-final-role-audit.json`,
`rotation-success-state.json` and `recovery-result.json` (ignored by Git).
