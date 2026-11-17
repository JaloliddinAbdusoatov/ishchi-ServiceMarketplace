# Production Sprint 1 — offline implementation

Historical Sprint 1 report. [Sprint 2](SPRINT_2.md) supersedes authorization,
operator execution and validation guidance below. Local JSON attestations are
not owner approval; production PostgreSQL/Redis access is now explicitly blocked
pending a separately reviewed deployment authorization mechanism.

Status: `SPRINT_1_COMPLETE_OFFLINE` (2026-11-16).
Reference HEAD: `462bf166f13b85897e5b293125f0416f73b058a1`.

## Implemented

- `backend/config/settings/database.py`: explicit PostgreSQL credentials/target,
  validated port, connection lifetime and timeout, health checks, and mandatory
  `verify-full` with a readable, parseable CA file in production. Production has
  no SQLite fallback. Development/testing retain isolated SQLite settings.
- Custom PostgreSQL backend: rejects protected/system targets, DSNs, target
  overrides and libpq `PG*` environment overrides before the driver connects.
  A matching, unexpired operator attestation is required before every connection.
  Naming patterns and credentials alone grant no permission.
- Normal production migration command/router/schema-editor blocks remain.
  A separate integration setting permits schema work only with `test_schema`
  approval on an explicitly disposable `ishchi_marketplace_sprint1_*` target.
  The runner uses a pre-provisioned empty database; it never creates/clones a
  database or connects to Django's maintenance database.
- Both hiring paths lock active employer/worker User rows in UUID order before
  order/profile/request rows. Account anonymization already locks User first;
  hiring now serializes with it and account deactivation updates. Eligibility is
  re-read from the database, including suspended employer accounts.
- Current Django category migration passes literal PL/pgSQL `%` placeholders
  with `params=None`; the earlier call could incorrectly interpolate them.
- Proposed `orders/0004_postgres_hiring_integrity.py` adds deferred PostgreSQL
  constraint triggers: capacity, primary-worker/team consistency, accepted
  application/invitation membership, hire provenance, and invitation ownership.
  Parent order locking serializes checks. Existing partial unique constraints
  protect active applications/invitations; team pairs and reviews have unique
  constraints; existing category triggers enforce the maximum of ten.
  New PostgreSQL trigger behavior is **NOT VERIFIED** until authorized execution.

## Migration readiness and boundaries

The migration graph builds without a database, has no conflicts, missing nodes
or cycles, and produces model state matching the current models. All model
tables belong to this MVP; no legacy baseline/schema/data import is required.
The only data migration copies existing primary hires into the team relation;
it does nothing on an empty database. Cross-app FK/dependency order is resolved
by Django. PostgreSQL indexes, checks, partial uniqueness and vendor-specific
category triggers are present in the graph.

This establishes **static readiness**, not successful PostgreSQL migration.
SQL execution, collation, locking, permissions and clean migration compatibility
are **NOT VERIFIED**. The new hiring migration is intended for a fresh database;
populated deployments require a separate consistency/backfill plan. SQLite tests
apply migrations only to ephemeral in-memory fixtures; PostgreSQL-only operations
are no-ops there. No persistent or PostgreSQL migration was applied in this sprint.

Deletion audits remain created atomically with anonymization and retain UUID/hash
references without restoring deleted PII. Their existing model does not enforce
append-only access at the database privilege level; release-role privileges need
review before deployment.

## Executable integration coverage

`backend/pgtests` reuses real API/ORM scenarios for registration/login, profiles,
categories, job creation, applications, invitations, multi-worker hiring,
duplicate/capacity rejection, chat permissions, completion/reviews and admin
authorization. Its initial setup checks an empty public schema and runs the full
current migration graph. Additional transaction tests use independent PostgreSQL
connections and thread barriers, including mixed application/invitation races.
Account deactivation/anonymization tests observe actual PostgreSQL blocking via
`pg_blocking_pids`; induced failure verifies rollback of hires and notifications.
Direct writes test deferred integrity constraints. Exceptions/deadlocks/timeouts
fail tests; no dictionary simulation supplies these results.

`backend/redistests` verifies actual Redis counters, TTL/revocation storage and
distributed lock contention, using unique expiring keys without FLUSHDB.

## Redis assessment

Redis is required by the **current code** for shared security state:
`accounts/authentication.py` and `accounts/serializers.py` read revoked sessions;
`accounts/services/auth_service.py` writes revocations/login lockouts;
`accounts/services/otp_service.py` stores OTP/rate counters; and
`accounts/services/locks.py` uses distributed OTP locks. DRF throttling also uses
the configured cache. Process-local cache remains suitable only for local tests.
No Celery, Channels, Redis notifications or hiring distributed lock dependency
was found: notifications/chat use relational models and hiring uses DB locks.
Production Redis requires TLS certificate/hostname verification, bounded timeouts
and exact-target operator approval before cache access. No Redis connection ran.

## Actual validation

- PASS: 132 backend tests on isolated SQLite (105 original + 27 new).
- PASS: offline migration-graph consistency, Django system check,
  `makemigrations --check --dry-run`, Python `pip check`, and `git diff --check`.
- PASS: offline collection of 23 PostgreSQL cases and 1 Redis case; this checks
  imports/collection only and is not an integration execution result.
- NOT RUN: PostgreSQL migration, constraints, API and concurrency runtime tests.
- NOT RUN: Redis runtime integration; no approved target was configured.
- NOT RUN: frontend tests/build (no frontend files changed).
- BLOCKED: runtime integration and production deployment await explicit target
  authorization, isolated infrastructure, credentials and trusted certificates.

One existing SQLite test warns about overriding `DATABASES`; no failures remain.
The protected database `ishchi_test` was never connected to or inspected. Legacy
baseline v1.1.13, Batch 16.x SQL and proposed v1.1.14/v1.1.15 were not touched.

## Operator execution after explicit authorization

1. Obtain owner approval for provisioning, the exact host/port/database/role,
   destructive test fixtures/migrations/flushes, and expiration. Any maintenance
   endpoint used by the provisioning operator needs separate approval too.
2. The authorized operator provisions a **new empty** database named
   `ishchi_marketplace_sprint1_<lowercase_id>` and a dedicated non-superuser owner
   role. Give it ownership of this database/public schema, with no CREATEROLE,
   CREATEDB, replication or access to protected databases. Configure TLS and a
   hostname matching the server certificate. Do not import or clone legacy data.
3. Use `backend/postgres-integration.env.example` as a variable checklist; inject
   values into the process environment (the example is not automatically loaded).
   Remove libpq `PG*` variables. Production requires `DB_SSLMODE=verify-full`;
   `disable` is accepted only for explicitly approved isolated local integration.
4. Outside the repository, copy `backend/db-authorization.example.json`, fill the
   owner-approved exact target and future UTC expiration, and set
   `DB_AUTHORIZATION_FILE` to that path. Examples are deliberately expired and
   unsigned/blank; filling a template without owner approval is not authorization.
   Keep files/secrets accessible only to the operator/runtime identity.
5. From the project root run `backend/scripts/run_postgres_integration.ps1`.
   It checks authorization before connection, refuses an occupied public schema,
   applies the migration graph and runs the tests. Fixtures write/flush synthetic
   records. The schema remains afterwards; re-runs require another fresh approved
   database or an explicitly authorized operator reset. No automatic reset/drop
   is provided. Never use `--create-db`, `--reuse-db` or parallel xdist runs here.
6. For separate Redis verification, obtain approval for a dedicated disposable
   TLS Redis target, fill `backend/redis-authorization.example.json` outside Git,
   set `REDIS_AUTHORIZATION_FILE` and `REDIS_URL`, then from `backend` run:
   `.venv/Scripts/python.exe -m pytest redistests --ds=config.settings.testing -q`.
7. Record real results before a separate release migration/deployment approval.
   Use `backend/.env.production.example` for runtime settings; runtime attestations
   need `connect` for PostgreSQL and `cache` for Redis, not schema/test privileges.
   Production schema deployment remains blocked pending a reviewed release plan.

No full production-readiness or deployment claim is made.
