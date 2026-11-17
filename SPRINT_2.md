# Sprint 2 — integration preparation and defect fixes

`SPRINT_2_COMPLETE_OFFLINE_RUNTIME_BLOCKED` — 2026-11-16.

No owner approval identifying an exact host, database/Redis index, role, operations
and expiration was supplied. No PostgreSQL/Redis connection, provisioning, schema
change or PostgreSQL migration ran. `ishchi_test` and legacy SQL remained untouched.

## Fixed

- **Self-issued authority:** Sprint 1 accepted a locally writable attestation as
  a production connection gate. Production PostgreSQL and Redis access now always
  fail closed, including with a valid-looking self-generated JSON file. No env
  switch or attestation enables production access. A reviewed owner-controlled
  deployment authorization mechanism remains a **release blocker**; no invented
  signatures, keys or approvals were added. Integration JSON files are target
  interlocks only and never prove owner consent. Arbitrary Python/process access
  is outside this interlock's trust boundary.
- **Redis target mismatch:** approval checks now use redis-py's decoded endpoint
  identity. TLS URLs require explicit ACL username/password, numeric DB index and
  no query overrides. Multiple endpoints/replicas are rejected because checking
  only the first allowed unapproved fallback connections. Base settings now also
  use the guarded backend. Optional `REDIS_SSLROOTCERT` supports a private CA.
- **Unavailable workers:** both hiring paths re-read the locked worker profile;
  `is_available=False` rejects hiring and rolls back request/assignment changes.
  Existing hires remain historical when availability changes afterwards.
- **Cache outage:** connection/time-out failures return sanitized HTTP 503 for
  authentication, login and OTP requests; no insecure cache fallback is used.
- **Audit deletion:** Django admin no longer allows adding, changing or deleting
  deletion audit entries, including bulk deletion. Raw DB append-only permissions
  still require a separately reviewed runtime role and remain unverified.
- **Harness safety:** Django automatic PostgreSQL create/clone/drop APIs are
  blocked before connection. The dedicated harness rejects reuse/create/xdist,
  verifies the connected identity, denies elevated/assumable privileged roles,
  checks disposable DB/public-schema ownership and empty objects/user schemas,
  pins search_path, and bounds statement/lock/idle-transaction timeouts.
  Setup failures close connections. Shared test cache clearing now operates on
  a captured LocMemCache only; exceptions are not silently swallowed. PostgreSQL,
  Redis and ordinary unit suites have separate runtime settings/fixtures.
- **Migration hardening:** the still-unapplied `orders/0004` functions now pin
  search_path to prevent temp/user-schema object shadowing. Added real PostgreSQL
  tests for reverse/reapply, repeat-migrate no-op, deferred ORM sequencing and
  integrity failure at the actual outer commit with notification rollback.

## Actual results and coverage

- PASS: **159 local backend tests**, including 27 new Sprint 2 offline regressions.
  DB-backed cases ran on ephemeral SQLite; metadata preflight tests use mocks.
- PASS: Django system check, migration consistency/drift, Python dependency check.
- PASS: **16 frontend tests** and production build. Build emitted existing Zod
  annotation warnings; the SQLite suite emitted one DATABASES-override warning.
- PASS: collection/import of **32 PostgreSQL cases and 8 Redis cases** only.
- BLOCKED / NOT RUN: every PostgreSQL/Redis runtime integration case below.

For each requested marketplace scenario, execution status is:

1. Registration/login — SQLite PASS; PostgreSQL NOT RUN.
2. Worker/employer eligibility — SQLite PASS; PostgreSQL NOT RUN.
3. Maximum 10 categories — SQLite PASS; PostgreSQL NOT RUN.
4. Job creation/publication — SQLite PASS; PostgreSQL NOT RUN.
5. Application submission — SQLite PASS; PostgreSQL NOT RUN.
6. Invitation creation/acceptance — SQLite PASS; PostgreSQL NOT RUN.
7. Multi-worker hiring — SQLite PASS; PostgreSQL NOT RUN.
8. Duplicate hire rejection — SQLite PASS; PostgreSQL NOT RUN.
9. Capacity enforcement — SQLite PASS for API/model checks; PG trigger NOT RUN.
10. Accepted request/team consistency — service workflows SQLite PASS; PG deferred checks NOT RUN.
11. Invitation ownership/origin — service authorization SQLite PASS; PG cross-table checks NOT RUN.
12. Job completion — SQLite PASS; PostgreSQL NOT RUN.
13. Review uniqueness — SQLite PASS; PostgreSQL NOT RUN.
14. Chat permissions — SQLite PASS; PostgreSQL NOT RUN.
15. Admin authorization — SQLite PASS; PostgreSQL NOT RUN.
16. Induced hire rollback — new PostgreSQL write/notification rollback test NOT RUN;
    commit-time deferred rollback is PostgreSQL-only and NOT RUN.

Concurrency tests now cover final-slot competition, duplicate attempts, mixed
application/invitation acceptance, capacities 1/2, worker deactivation/anonymization/
availability, employer suspension, and cancellation winning or following a hire.
They use independent connections, barriers or observed `pg_blocking_pids` waits,
assert specific business failures/final states, and surface unexpected DB failures
with SQLSTATE/locking scenario. Cancellation currently means whole-order cancellation;
there is no individual assignment-cancellation API. Historical team membership is
retained on cancelled orders. No concurrency result or deadlock-free claim is made.

Redis tests cover TLS/authenticated PING, counters/TTL, competing locks, actual JWT
session revocation, login lockout persistence, OTP expiry/attempt/rate limits and
transport failure injection after a real connection. Security-domain tests use local
SQLite users, two Redis cache aliases and UUID namespaces; SMS is mocked. Cleanup
SCANS/deletes only the fixture namespace, never FLUSHDB/FLUSHALL. These tests are
**NOT RUN**; injected outage handling also has passing offline HTTP regressions.

## Next authorized operator action

1. First obtain the real owner's explicit approval naming exact host/port,
   disposable DB/Redis index, role, allowed connect/introspection/migrate/reverse/
   synthetic-write/fixture-flush or namespaced-cache operations, and UTC expiration.
   Template files, credentials and database names are insufficient. No approval
   record was generated for operational use; forged/synthetic JSON exists only
   as offline regression-test input and never authorizes a connection.
2. An authorized infrastructure operator separately provisions a new empty
   `ishchi_marketplace_sprint1_<lowercase_id>` database and non-superuser migration
   owner without CREATEDB/CREATEROLE/replication/BYPASSRLS or privileged memberships.
   This role owns only the new database/public schema. Provisioning/maintenance
   connections require their own explicit approval; never clone protected data.
3. Inject the process variables listed in `backend/postgres-integration.env.example`;
   it is not auto-loaded. Match the approved target and trusted CA, clear libpq
   `PG*` overrides, and set `DB_AUTHORIZATION_FILE` to an owner-authorized operator's
   exact-target interlock outside Git. Use `verify-full` TLS. From the project root:

```powershell
& .\backend\scripts\run_postgres_integration.ps1
```

4. Independently approve a disposable TLS Redis target/ACL role. Set `REDIS_URL` to
   `rediss://<percent-encoded-user>:<percent-encoded-password>@<approved-host>:<port>/<index>`,
   optional `REDIS_SSLROOTCERT`, and `REDIS_AUTHORIZATION_FILE` matching the decoded
   host/user, integer port/index, scopes `cache`/`cache_test`, and expiry. From the
   project root run the separate Redis suite:

```powershell
Push-Location .\backend
try {
    & .\.venv\Scripts\python.exe -m pytest redistests --ds=config.settings.testing -q
} finally {
    Pop-Location
}
```

Do not combine the runtime suites or use --reuse-db/--create-db/xdist. PostgreSQL
fixtures write/flush synthetic rows and leave the schema; every rerun needs a new
empty approved database or a separately authorized operator reset. No automated
provisioning/reset/drop is supplied. Record runtime results and SQLSTATE failures.

Runtime-only migration syntax/version/trigger ordering/reverse correctness,
schema privileges, runtime-vs-migration role separation, audit DB permissions,
actual TLS/authentication and server outage behavior remain **NOT VERIFIED**.
Production access remains deliberately blocked; no deployment/readiness claim.
