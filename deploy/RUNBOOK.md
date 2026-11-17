# ISHCHI release preparation

`SPRINT_5_COMPLETE_OFFLINE_RUNTIME_BLOCKED` — 2026-11-16 (Asia/Tashkent).
Sprint 5 results and the current operator handoff are at the end of this runbook;
the Sprint 4 results below are historical.

**Production access remains BLOCKED.** Container configuration does not grant
permission to connect. The Sprint 2 PostgreSQL/Redis gates intentionally reject
production operations even if credentials or locally written JSON files exist.
A separately reviewed owner-controlled authorization mechanism is still required.
No Compose stack, database, Redis, cloud host or public deployment was started.

## Architecture and local validation

nginx serves the React production build, Django static assets and explicitly
public profile/category images. Private order images/chat attachments pass through
the authorized Django API. nginx and Gunicorn share a loopback network namespace;
Gunicorn binds only 127.0.0.1:8000. Two threaded WSGI workers serve polling chat;
no WebSockets, queue system or Kubernetes are needed. PostgreSQL and TLS Redis
are separately provisioned approved dependencies, not Compose services.

The Compose example publishes only host loopback ports 8080/8443. An authorized
host release must explicitly choose public binding/80-to-8080/443-to-8443 mapping
and firewall policy. Both application processes are non-root with read-only roots,
bounded temporary storage/logs, dropped capabilities and graceful stop periods.

Safe commands from the repository root (builds download public package/image data):

```powershell
.\backend\.venv\Scripts\python.exe deploy/check_config.py
.\backend\.venv\Scripts\python.exe deploy/scan_secrets.py
.\backend\.venv\Scripts\python.exe deploy/smoke_local.py
docker --context desktop-linux build -t ishchi-backend:sprint4 backend
docker --context desktop-linux build -t ishchi-frontend:sprint4 frontend
.\backend\.venv\Scripts\python.exe deploy/validate_containers.py --context desktop-linux
```

On a Linux CI runner omit `--context desktop-linux` and use the default local
Docker context. The validator rejects remote Docker endpoints. It never starts
Compose or service databases; temporary `--network none` containers test nginx
syntax and production WSGI liveness using synthetic settings/certificates.
The HTTP smoke script uses only loopback and an in-memory SQLite database.

Images exclude .env, local data, media, virtual environments and test fixtures.
Base image digests and the hashed Python runtime lock are pinned. Frontend uses
`npm ci` and same-origin `/api/v1`; no build-time secrets or default admin exist.
Static collection runs with dummy DB/cache build settings, which refuse production
mode. Startup performs no migrations, seeding, database creation or readiness loops.

## Authorized host release checklist — NOT EXECUTED

1. Record actual owner approval outside this repository: exact host/port/database
   or Redis service/index, operator/role, allowed operations, expiry and any
   destructive scopes. A local JSON file or GitHub environment is not proof of
   this approval. Review and implement the still-missing production authority gate
   without weakening the existing protections.
2. Provision a new dedicated marketplace PostgreSQL database and TLS Redis service;
   do not clone or reuse protected/legacy databases. Review the migration graph,
   including `orders/0004` and new `common/0001` erasure outbox. Neither is approved
   for production execution by this sprint. Do not point integration tests at a
   production database; use the separate disposable harness and explicit scope.
3. Use a NOLOGIN schema-owner role, a separately authenticated migration operator
   that may SET ROLE only to that owner, and a runtime LOGIN role that cannot
   assume either role. Runtime must have no superuser/CREATEDB/CREATEROLE/
   replication/BYPASSRLS or schema CREATE privileges. Owner controls the dedicated
   application schema; remove PUBLIC CREATE and unneeded function EXECUTE grants.
4. Review individual table/sequence/function grants. Runtime ordinarily needs DML
   for marketplace/session data, but deletion audit and django_admin_log need only
   SELECT/INSERT, never UPDATE/DELETE/TRUNCATE. Runtime must not own those tables
   or inherit an owner role. Review foreign-key cascades and default privileges;
   audit retention/deletion belongs to a separate authorized retention role.
   These database-level guarantees are NOT VERIFIED.
5. Require PostgreSQL `verify-full`, the correct CA and hostname, SCRAM credentials,
   connection/statement/lock limits, and private routing. Initial Gunicorn capacity
   is 2 workers x 2 threads; budget DB connections accordingly. Introduce an
   external pooler only after session/transaction semantics and locks are tested.
6. Review `redis/redis.conf.example` and `users.acl.example`: port 0, TLS, verified
   CA, ACL authentication, private bind, environment-prefixed keys, no public ports,
   AOF persistence and noeviction. Runtime ACL stays OFF until the operator installs
   a secret. Test the exact allowed commands, Lua locks/counters and outage behavior.
   Redis DB indexes do not enforce ACL isolation; prefer separate environment
   services. Missing/stale Redis state can lose revocation/lockout history: after
   loss or stale restore, keep traffic closed and invalidate JWT versions and
   outstanding sessions before recovery. Never fall back to process-local cache.
7. Copy the blank backend production environment template to an operator-controlled
   external secret file. Compose inputs go in a separate public configuration file.
   Mount actual PostgreSQL/Redis CAs and TLS certificate/key from that external
   directory. No real values belong in Git, images, command arguments or CI.
   For file-backed Compose secrets, host ACLs must make the real TLS key readable
   only by the operator and nginx UID/GID 101 (for example root:101 mode 0640 on
   a locked-down Linux directory). Compose secret uid/mode fields are not a
   substitute for host permissions. Synthetic validation keys are not deploy keys.
8. Replace example.uz consistently in nginx, Compose APP_HOST, Django host/origins
   and certificates. Trust only loopback nginx and overwrite all forwarded headers.
   Keep WSGI unreachable directly. Validate real nginx/TLS/domain/firewall behavior
   and certificate renewal before public traffic. Real TLS is NOT VERIFIED.
9. Mount persistent writable media owned by backend UID 10001, and static assets
   read-only into nginx. Refresh the static volume with an explicitly authorized
   `collectstatic` for each release; image copy-up refreshes only an empty volume.
   Shared network namespaces mean backend recreation requires gateway recreation
   too. Publish immutable release image digests only after review; CI does not push
   or deploy images. Apply only the separately approved migrations with the
   reviewed migration role; runtime credentials must never run DDL.
10. Check liveness `/api/v1/health/live/` separately from dependency readiness
    `/api/v1/health/ready/` (legacy `/health/` is also readiness). Only dependency-free
    liveness bypasses HTTPS redirect for local probing. HTTP liveness 200 does not
    authorize traffic: readiness must pass with approved dependencies. Monitor
    readiness failures, 5xx/429 rates, request latency, disk/memory, certificate
    expiry and backup/outbox age. Logs carry request IDs/route/status without
    authentication bodies, query strings or tokens; restrict log access/retention.

## Backup, restore and rollback preparation

`ops.py` is an offline planner, deliberately without an execution/approval bypass.
It prepares exact-target pg_dump/age and tar/age command arrays, isolated restore
requirements, checksum inspection and retention candidates. It does not load
credentials, connect, make a backup, restore or delete anything. An operator must
review the plans after independent authorization. No live backup executor is
enabled while the trusted production authorization facility remains absent.

Subcommands: `plan-backup`, `plan-media-backup`, `plan-restore`,
`plan-media-restore`, `plan-retention`, `verify-archive` (use `--help`). Database
restore accepts only a separately provisioned `ishchi_marketplace_restore_*`
target and never proposes --create/--clean. Clear inherited libpq overrides, use
verified TLS/PGPASSFILE from private storage, and check both stream exit codes.
Encrypt before persistent output, publish only completed encrypted artifacts with
an independently protected SHA-256/size manifest, and avoid plaintext dumps.
Checksum/header inspection is not authenticated decryption or recovery proof.

Proposed policy: daily coordinated DB/media backup, encrypted restricted local
storage plus an independently controlled offsite copy, 30-day retention, and
monthly isolated restore drill. Provisional RPO is 24h; RTO must be measured by an
authorized restore (no RTO claim here). Owners must approve policy, locations,
recipient keys, access ACLs, key recovery/rotation and destruction scopes. Never
delete the last verified recovery point. The retention planner only lists exact
expired `.age` artifacts, skips partials/symlinks and never recursively deletes.
Restore media only into an empty sandbox after validating paths, links/types,
expanded sizes and hashes; replay deletion/tombstone obligations before serving
so backups do not reintroduce erased personal data.

Erasure now uses a transactional durable outbox. Post-commit storage failure leaves
a retryable task, reports only its ID/error type, and never undoes successful
anonymization. Completed task rows discard their storage key. `retry_media_erasure` is dry-run by default; --apply requires the
exact media root and reports failures with nonzero exit status. The inert systemd
templates propose five-minute retries; do not install/enable them before target
authorization. Restrict outbox access/retention because storage keys can contain
PII; monitor failed/oldest pending tasks and deny public serving of affected files
until erasure succeeds. Already downloaded files/backups require separate policy.

Before any schema release take an authorized verified recovery point, review
reversibility/data-loss impact and keep the last known-good application image.
Prefer compatible application rollback; never blindly reverse migrations or drop
volumes. Schema/data rollback needs its own exact-target approval and restore plan.

## CI and remaining release blockers

CI runs SQLite tests, HTTP smoke, Django/drift/dependency checks, secret scan,
frontend tests/build/npm audit, Python runtime vulnerability audit, Docker builds,
Compose validation and network-isolated container smoke. The manual
release-preparation workflow only collects integration tests and documents the
blocked boundary. Configure required reviewers for `release-review`; no CI job
contains production credentials or a remote deploy/migration executor.

Remaining: trusted production authorization; separately approved PostgreSQL/Redis
provisioning/migrations/concurrency/audit ACL checks; real SMS and hosted TLS/media
verification; an approved backup executor, encrypted backup/restore and retention
drill; operational monitoring/alerts and actual recovery objectives. Container OS
package vulnerability scanning and multi-architecture builds are also not claimed.

## Sprint 4 local results (historical)

- PASS: **244 backend tests** (27 added cases), **18 frontend tests**, TypeScript/
  Vite build, Django check, migration drift check, pip consistency and diff check.
- PASS: both Docker images built on local Linux amd64; non-root/clean-image checks,
  Compose validation, real Gunicorn startup/liveness/shutdown with network disabled,
  fail-closed readiness and nginx `-t` with disposable synthetic TLS fixtures.
- PASS: real loopback HTTP smoke against ephemeral in-memory SQLite, including
  login/registration, admin authorization, marketplace, private-media denial,
  disabled payments and revocation. Fixtures/server were removed/stopped.
- PASS: source secret scan, infrastructure invariant checks and **0 npm advisories**.
  Scan scope is current Git-visible text, not historical Git/full secret proof.
- PASS: isolated **pip-audit 2.10.1**, PyPI advisory service: **34 installed Python
  packages**, **25 runtime lock packages**, **0 advisories**, **0 skipped packages**.
  Raw results and inventory are in `security/`; no advisory-driven upgrades were
  needed. Existing application venv dependencies were not changed.
- COLLECTION ONLY: **32 PostgreSQL + 8 Redis cases**. Runtime results **NOT RUN**.
- NOT VERIFIED: real TLS, approved PostgreSQL/Redis/migration/ACL/concurrency work,
  SMS, real encrypted backup/restore/deletion/retention, recovery objectives,
  remote CI execution and hosted deployment. No service stack was launched and
  no source commit, push or image publication occurred.
- Non-failing output: existing SQLite DATABASES-override warning and Zod build
  annotation warnings. Final test failures: **0**.

Gunicorn configuration follows its [settings reference](https://gunicorn.org/reference/settings/).
Dependency auditing uses [PyPA pip-audit](https://github.com/pypa/pip-audit) against
the complete pinned package inventories; a zero-advisory result is not a full
security certification.

## Sprint 5 release candidate — actual results

Owner confirmed that runtime authorization/trust-service configuration is **not
available** and directed offline completion. No existing PostgreSQL/Redis, cloud
host or deployment target was accessed. Protected `ishchi_test` was not connected
to or inspected; no PostgreSQL migration, backup, restore, reset or retention
command was executed. Only ephemeral SQLite/test media and network-isolated local
containers were used. No public service, DNS change, image push or deployment.

- PASS: **245 backend tests** (244 baseline plus a Redis teardown regression),
  **18 frontend tests**, TypeScript/Vite build, Django check, migration drift and
  pip consistency. Existing non-failing SQLite and Zod warnings remain.
- PASS: source secret scan (0 findings), infrastructure invariant checks and
  loopback HTTP smoke for registration/login, optional KYC, admin/marketplace,
  private-media denial, disabled payments and token revocation.
- PASS: current source built as `ishchi-backend:sprint5` and
  `ishchi-frontend:sprint5`; network-isolated Compose/nginx syntax and Gunicorn
  startup/liveness/graceful shutdown checks passed on those images. Readiness
  correctly stayed 503 with unauthorized dependencies. Initial builds with
  build-network disabled could not install dependencies; normal cached builds
  passed. This does not affect the network-disabled runtime smoke result.
- PASS: fresh npm audit, **0 advisories**; fresh pip-audit 2.10.1, **34 installed**
  and **25 locked runtime** packages, **0 advisories / 0 skipped**. Installed
  inventory was compared with the current venv. Inventory hashes/raw results are
  in `security/sprint5-audit-summary.json` and its two referenced JSON artifacts.
- COLLECTION ONLY: **34 PostgreSQL + 8 Redis** cases; all runtime cases **NOT RUN**.
  The two added PG cases close the new durable-outbox coverage gap: audit failure
  rolls back account/tokens/outbox; committed anonymization survives storage
  failure and retries sandbox media deletion. Existing reverse/reapply now also
  covers `common/0001` and its pending-key unique index. These claims describe test
  code, not executed PostgreSQL behavior.
- FIXED: Redis test fixture `.close()` previously left its pool open because
  django-redis defaults CLOSE_CONNECTION to false. It now requests connection
  closure. A no-socket regression executes the actual fixture teardown, verifies
  namespace cleanup and pool-disconnect delegation, and confirms idempotent close.

### Release candidate checklist and exact blockers

- [x] Safe local regressions, build, dependency checks, private media and offline
  container/proxy checks passed; no demo login/payment simulation reintroduced.
- [x] Existing integration suites extended without a duplicate suite; guarded
  disposable targets, timeouts, cleanup and executable commands retained.
- [ ] **BLOCKED:** owner-approved disposable PG/Redis endpoints, roles, CAs,
  action/destructive scopes and expiry. No operational approval was fabricated.
- [ ] **NOT VERIFIED:** migration SQL/trigger execution, reverse/reapply, real
  concurrent hiring/outbox/audit rollback, runtime/migration role separation and
  append-only audit DB permissions. SQLite/collection do not establish these.
- [ ] **BLOCKED:** externally controlled production authority described below.
- [ ] **NOT VERIFIED:** real TLS/domain/proxy/secret/media configuration, SMS,
  monitoring, container OS vulnerability scan and hosted deployment.
- [ ] **BLOCKED / NOT RUN:** encrypted backup, decryption/archive integrity,
  separate-target restore and recovery drill. No verified RPO or RTO exists.
  Completed erasure tasks discard storage keys: restoring an older snapshot needs
  an independent current deletion/tombstone ledger, not just the restored outbox.
  No such ledger or reconciliation executor is supplied; keep restored data and
  media closed to traffic until this obligation is demonstrably satisfied.

### Production authority handoff — no enable switch supplied

Production PostgreSQL/Redis guards remain unconditional denials. A URL, JSON,
callable plugin, environment flag or application-held signing key would not meet
the requested independent authority boundary, so none was added to open access.
The owner/platform team must supply these concrete integration inputs:

1. The actual owner-operated trust service and workload-identity registration,
   issuer/trust domain, authenticated transport, policy administrator and revocation
   endpoint/semantics. No endpoint, issuer or deployment secret is invented here.
2. Canonical PG host/port/database/role and Redis host/port/index/ACL user plus
   namespace. Map each identity to read/write/connect scopes; schema, backup,
   restore, reset and erasure operations need distinct operator identities/scopes.
3. Enforce policy outside the app: independently controlled egress/credential
   broker or service proxy, PostgreSQL role grants and Redis ACLs. App-configurable
   allow decisions are not authoritative. The app must not obtain broader direct
   credentials or a network route that bypasses the broker.
4. Define expiry and revocation for existing sessions as well as new connections:
   broker/service terminates or revalidates live DB/Redis sessions, uses bounded
   leases and fails closed on service errors. Checking only connection creation
   cannot revoke a pooled session. Authority denial must stop readiness/traffic;
   dependency-free liveness may remain available. Audit policy decisions without
   payloads, passwords, tokens or private storage keys.
5. With that real facility supplied, implement/review the narrow client adapter
   and verify wrong identity/target/action, expiry, revocation during an open
   session and authority outage on approved disposable infrastructure. Until
   then there is no production connection, migration or deployment command.

### Minimal next operator steps (after separate authorization)

Record exact owner-approved targets, identities, actions, expiry and any synthetic
writes/migrations/reverse/fixture-flush/sandbox-media-delete scopes outside Git.
An authorized operator provisions empty disposable targets; the application does
not create/clone them. Set process variables from
`backend/postgres-integration.env.example` and the separately approved integration
interlock files. Those files merely prevent target mistakes; they are not consent.

From the repository root, **only after that approval**:

```powershell
& .\backend\scripts\run_postgres_integration.ps1
Push-Location .\backend
try {
    & .\.venv\Scripts\python.exe -m pytest redistests --ds=config.settings.testing -q
} finally {
    Pop-Location
}
```

Run the suites separately. PG requires a new empty approved
`ishchi_marketplace_sprint1_<lowercase_id>` target; it leaves the schema afterwards.
Redis requires an isolated authenticated TLS service, exact approved ACL user/index
and the fixture's `ishchi-sprint2-*` key namespace; cleanup needs namespaced
SCAN/DEL in addition to the security operations under test. Never use production
targets, --reuse-db/--create-db/xdist, FLUSHDB or FLUSHALL. Role-separation/audit ACL
verification needs separately approved runtime credentials and a dedicated drill;
the owner-role test harness alone does not prove runtime least privilege.

Backup/restore steps remain **planner-only** in `ops.py --help`; do not execute
generated pipelines without distinct source/destination/crypto/media permissions,
owner-provided encryption/recovery identities, an independent manifest and current
erasure ledger. Measure real recovery duration and validate data/ACL/session/media
compatibility before opening restored traffic. These are remaining blockers,
not successful release-candidate verification.
