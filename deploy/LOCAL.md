# Local ISHCHI — running on the owner's computer

Status: `LOCAL_MVP_RUNNING_VERIFIED` (2026-11-16).

Owner explicitly approved the exact new test and working targets/operations in
chat, through **2026-11-17 23:59 Asia/Tashkent** (18:59 UTC). New dedicated clusters
were provisioned, current migrations applied and runtime checks passed.
`ishchi_test` and existing unrelated databases/Redis were not accessed. No backup,
restore, working-data reset or real-user deletion ran. Production remains blocked.
Open **http://127.0.0.1:8080**; no public domain/TLS is needed.

**Current safety status:** the synthetic administrator credential is treated as
exposed. Owner-approved password/JWT rotation completed with PASS on November 16;
new login and old-token/session rejection passed. Old-password login rejection
was NOT RUN because the previous password was unknown. File-backed administrator
login/bootstrap in the live verifier
is retired. See [daily data safety procedures and actual checks](LOCAL_SAFETY.md).

Daily working PG/Redis use was explicitly renewed through **2026-11-24 23:59
Asia/Tashkent**; mounted interlocks and readiness passed. Test/migration scopes
retain their original expiry and are not renewed. Role/audit corrections and a
real isolated encrypted-backup restore have now passed under separate one-time
approval through November 17, 23:59. Overall security status is
`LOCAL_SECURITY_PARTIAL`; see the remaining owner actions in LOCAL_SAFETY.md.

## Approved exact targets

- Working PostgreSQL: `127.0.0.1:55432`, DB `ishchi_marketplace_local`, non-superuser
  `ishchi_local_app`; new `ishchi-local_pg-work` volume.
- Disposable PostgreSQL: `127.0.0.1:55433`, DB `ishchi_marketplace_sprint1_local`,
  non-superuser `ishchi_local_test`; separate `ishchi-local_pg-test` volume.
- Working Redis: `127.0.0.1:56379`, DB 0, ACL user `ishchi_local_app`, keys
  `ishchi:local:work:*`; separate persistent AOF volume `ishchi-local_redis-work`.
- Test Redis: `127.0.0.1:56380`, DB 0, ACL user `ishchi_local_test`, keys
  `ishchi-sprint2-*`; separate `ishchi-local_redis-test` volume and network.
- App: `http://127.0.0.1:8080`; nginx serves React/static/public profile images and
  proxies API/admin to private loopback Gunicorn. Order/chat media remains private.

The recorded owner approval specifies these targets, roles, operations and expiry. Provisioning
includes initializing **new dedicated clusters**, creating their bootstrap
superuser `ishchi_bootstrap`, databases/non-superuser roles, and restricting default
postgres/template1 CONNECT privileges inside those new clusters only. Test approval
must also cover migrations, reverse/reapply, synthetic writes/fixture flushing and
temporary test-media deletion. Working approval covers persistent app reads/writes
and separately controlled migrations. Redis approval covers security operations
and test namespace SCAN/DEL cleanup, never FLUSHDB/FLUSHALL. Runtime keys/volumes
are never shared with tests. No legacy DB, role or SQL proposal is imported.

JSON interlocks, generated passwords, names and environment variables are not
approval. These commands were executed only after the explicit owner consent;
future use must stay within its targets/scopes/expiry. Existing project data now
belongs to this approved local app: do not reset/adopt other volumes or targets.
PostgreSQL initialization
scripts run only on empty volumes; they never rotate/reset an existing cluster.

## Initial configuration preparation (already completed; do not regenerate secrets)

From `D:\Project\ishchi`:

```powershell
.\backend\.venv\Scripts\python.exe deploy/local.py check
.\backend\.venv\Scripts\python.exe deploy/local.py init-secrets --directory C:/Users/user/.codex/ishchi-local-private
Copy-Item deploy/.env.local.example deploy/.env.local
```

Set `LOCAL_SECRETS_DIR` in `.env.local` to that absolute directory. Secret generation
refuses overwrites, generates different work/test/bootstrap credentials and a
`local.pgpass`, and writes **blank expired** interlock templates. It does not grant
authority or create databases. Keep the directory private with host ACLs; Windows
chmod is not an ACL guarantee. Mounts must be readable by their container processes
(backend UID 10001); never solve this by publishing secrets. Do not print Compose
configuration/env/credentials or commit `.env.local`/the private directory.

After real approval, an authorized operator records the exact approved target,
scopes and future UTC expiry in the corresponding interlocks. Work DB runtime file
has only `connect`; the separate migration file also needs `local_migrate`. Test DB
requires `connect` + `test_schema` and disposable=true. Work Redis needs `cache`;
test Redis needs `cache` + `cache_test`, disposable=true. Container work targets in
the templates are `postgres-work:5432` / `redis-work:6379`; host test targets are
the loopback endpoints above. Never substitute working credentials into tests.

Local settings deliberately allow plaintext DB/Redis only on these exact loopback/
private Docker endpoints. Host ports bind only 127.0.0.1; separate bridge networks
also default publication to loopback. They allow outbound traffic (not an egress
firewall). Production still requires verified TLS and remains blocked. DEBUG=false,
no seed/demo endpoints, real phone/password/JWT auth, optional KYC and disabled
payments are preserved. SMS is disabled by default; optional verification/reset
requires a separately configured real HTTP provider, never a synthetic OTP.

## Startup/shutdown commands within the approval period

Use this command prefix in PowerShell (selects local Docker Desktop only):

```powershell
$dc = @('--context','desktop-linux','compose','--env-file','deploy/.env.local','-f','deploy/compose.local.yml')
docker @dc config --quiet
docker @dc build backend gateway
```

The following test commands already passed. They are preserved for reproducibility:

```powershell
docker @dc --profile test up -d postgres-test redis-test
.\backend\.venv\Scripts\python.exe deploy/local.py pg-tests --secrets-dir C:/Users/user/.codex/ishchi-local-private
.\backend\.venv\Scripts\python.exe deploy/local.py redis-tests --secrets-dir C:/Users/user/.codex/ishchi-local-private
```

The launcher clears inherited DB/Redis/libpq targets and selects exact local test
settings. PG tests use process-local cache; Redis tests use in-memory SQLite user
fixtures. PG leaves its schema, so reruns need a separately approved disposable
reset/new target. No automatic reset, cloning, --reuse-db or --create-db is supplied.

Working provisioning/migrations were previously completed. Ordinary startup is:

```powershell
docker @dc --profile work up -d postgres-work redis-work
docker @dc --profile work up -d backend gateway
```

Current source prohibits migrations under the runtime login before connection.
Future migrations use the approved dedicated migrator and private secret with
the `deploy/compose.local-roles.yml` overlay. The role/ownership change is applied;
operator migrate-check passed. Its one-time approval/login validity ends November
17 at 23:59 Tashkent; later migration work requires separate genuine renewal.
Do not use the old runtime migrate command or create an administrator on startup.

An explicit one-time synthetic verification administrator was created through
Django's normal manager, not application startup. Treat its original credential
as exposed: do not use the old plaintext file for operational authentication.
Use the separately approved interactive rotation procedure in LOCAL_SAFETY.md.
No administrator is automatically bootstrapped by the verifier anymore.
Open `http://127.0.0.1:8080`, admin `/django-admin/`, and verify
`/api/v1/health/ready/` returns 200. Then check real registration/login, profiles/
categories, publication, applications/invitations, capacity/hiring, authorized chat,
notifications, completion/reviews and payments-disabled behavior. Existing users
and media are retained; never reseed/reset the working target. For future static
asset updates run an explicitly approved `collectstatic` against the static volume.

Normal stop/start preserves data and never removes volumes:

```powershell
docker @dc --profile work stop
docker @dc --profile work up -d postgres-work redis-work backend gateway
```

Do not use `down -v`, volume prune, destructive reseeding or restore on working DB.
Redis AOF uses every-second fsync; keep data volumes and JWT secret stable. After
Redis state loss, keep traffic closed until sessions/revocations are reconciled.

## Backup preparation

`deploy/local.py backup-plan --destination <existing-private-directory> --recipient
<owner-age-public-recipient>` prints an **inert** encrypted pg_dump/age plan for
working localhost:55432 only. Set its PGPASSFILE to the generated private
`local.pgpass`; never put the password in command arguments. Coordinate DB/media
snapshots, stream encryption before persistent output and check both exit codes.
The existing `ops.py plan-media-backup` remains planner-only.

`deploy/local.py restore-plan --archive <encrypted-dump> --identity-file
<owner-private-key>` can only propose `127.0.0.1:55434`, DB
`ishchi_marketplace_restore_local`, role `ishchi_local_restore`. That separate
empty target is **not provisioned** by Compose and needs independent approval.
Never restore over working DB/media. Check archive provenance, data/ACL/application
compatibility and a current independent erasure ledger before traffic; completed
outbox tasks alone cannot identify all previously erased keys. Backup, restore,
media recovery, RPO and RTO remain **NOT VERIFIED**; no backup pipeline ran.

## Actual validation and remaining limits

- PASS: 269 backend tests, including local isolation/production-gate regressions
  and Windows smoke-process cleanup; the latter fixes an observed locked-log
  teardown failure by stopping the owned venv interpreter tree.
- PASS: 18 frontend tests/build; both local Docker images built; local nginx `-t`,
  bootstrap shell syntax checks, existing network-isolated production-guard smoke
  on those images, and SQLite-only loopback HTTP smoke.
- PASS: Compose configuration and local isolation checks; Django/drift/pip checks.
- PASS: **34/34 PostgreSQL integration cases** against the approved disposable
  PostgreSQL 18.6 target; full migrations, `orders/0004`, `common/0001`, reverse/
  reapply, hiring concurrency, commit/audit rollback and media-outbox retry.
- PASS: **8/8 Redis integration cases** against the approved isolated Redis 7.4.12
  target. This deliberate localhost profile uses authenticated plaintext; it is
  not evidence of production TLS. Outage is transport-failure injection, not a
  physical server outage. Namespace cleanup uses SCAN/DEL, never FLUSH.
- PASS: full current migrations on the separate working database; backend,
  gateway and dependencies healthy; readiness reports PostgreSQL/Redis ok.
- PASS: actual HTTP through nginx/React assets: real admin login, registration/
  login for employer and three workers, optional phone/KYC, profiles/categories,
  publication, duplicate/capacity rejection, two-worker hiring, invitations,
  authorized chat/notifications, completion/review uniqueness and revocation.
  Two completed synthetic jobs and their synthetic accounts are retained. No
  fixture flushing/reset occurred in the working database. The Uzbek React
  landing page was also verified visually in a browser with live server metrics.
- Fixed after first runtime attempt: Docker Desktop suppressed host publication
  for `internal` networks, causing initial PG/Redis connection failures. Separate
  loopback-publishing bridges corrected this; both suites then passed in full.
- NOT RUN: backup/restore/recovery and real SMS; no verified RPO/RTO. Production
  trust authority, TLS/hosting, role separation and append-only DB audit ACLs are
  still outside this local verification. No public production readiness claim.
- Approval expires **2026-11-17 23:59 Tashkent**. Existing connection interlocks fail
  closed after expiry; obtain explicit renewal before further access. Do not
  silently extend files or regenerate passwords/JWT keys. Test reruns still need
  an empty separately approved/reset disposable schema; no automatic reset exists.

The reusable live verifier is `deploy/verify_local.py --allow-synthetic-writes`.
It requires separate approval, interactive credentials and creates NEW synthetic
data. Legacy `--credentials` and `--bootstrap-admin` fail before reading files or
accessing the application. It was not rerun during stabilization. Evidence without
passwords/tokens is in `deploy/.local/live-verification.json`; PG output is in
`deploy/.local/postgres-tests.log` (both intentionally ignored by Git).

- Cleanup note: an earlier synthetic smoke directory
  `C:\Users\user\AppData\Local\Temp\ishchi-http-smoke-7u273vj0` remains because
  automatic approval review rejected its recursive deletion ("blocked by policy").
  Subsequent smoke execution passed and removed its own new fixtures.

PostgreSQL 18 volume layout and empty-volume initialization follow the
[official image](https://hub.docker.com/_/postgres). Redis role/key scoping follows
the [Redis ACL documentation](https://redis.io/docs/latest/manual/security/acl/).
