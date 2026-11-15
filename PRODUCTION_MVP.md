# ISHCHI MVP вЂ” local operation and release gates

Implemented locally; not deployed or declared production-ready. The standalone
project contains the React frontend in `frontend/` and Django backend in `backend/`.

Current registration policy: users register with a phone number and password,
receive an active account and JWT session immediately, and enter their dashboard.
No registration SMS is sent. `is_phone_verified` remains false until an optional
verification succeeds. This supersedes the earlier mandatory registration-OTP rule.

## Run locally (PowerShell)

From `backend/`, install `requirements.txt` in a virtual environment created at
the current location. Copy `.env.example` to `.env` if needed; never reuse another
project's `.env`. See [the setup instructions](README.md) after moving the folder.
The default development settings use `.local/ishchi.sqlite3`, not the old seeded
`.demo/` database. Existing local data is preserved. No synthetic accounts or
categories are created during setup.

```powershell
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.development
.\.venv\Scripts\python.exe manage.py createsuperuser --settings=config.settings.development
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --settings=config.settings.development
```

`createsuperuser` prompts for the operator's own phone and unique password. No
administrator exists by default. Create real categories through the admin UI.
Registration works with `SMS_BACKEND=disabled`. Optional phone verification and
SMS password recovery require the HTTPS gateway described below. `SMS_BACKEND=memory`
is available only for explicit local Python tests and never logs or exposes codes.
Development settings reject `ISHCHI_ENV=production`.

From `frontend/`, run `npm ci`, then `npm run dev`.

## Safe tests

```powershell
# From backend: all database fixtures are SQLite in memory, PostgreSQL is refused.
.\.venv\Scripts\python.exe -m pytest --ds=config.settings.testing
# From frontend:
npm test
npm run build
```

The frontend build defaults to `/api/v1` on its own origin and ignores legacy
local `.env` API/media URLs in production. A separate API host requires explicit
process environment `VITE_API_BASE_URL=https://.../api/v1` at build time and an
explicit HTTPS `VITE_MEDIA_BASE_URL`. Build variables are public, never secrets.

## Production configuration (template only)

Inject `backend/.env.production.example` values through the hosting secret manager;
production deliberately does not load local `.env`. Generate a fresh random
Django secret (at least 50 characters), list exact hosts and HTTPS CSRF/CORS origins,
and provide TLS-verified PostgreSQL and Redis endpoints. SMS defaults to disabled;
configure `SMS_BACKEND=http` only when enabling optional verification/password recovery.
Set `TRUST_HTTPS_PROXY=true` only behind a proxy that overwrites forwarding headers
and blocks direct access to the WSGI server. Set `TRUSTED_PROXY_IPS` to exact
proxy addresses so OTP IP limits use the overwritten `X-Real-IP`, not user headers. The included nginx template supplies
TLS termination, frontend/static/media serving, attachment denial, and IP limiting.
Run `nginx -t` on the actual host; this template has not been host-validated.

The gateway contract is an authenticated HTTPS JSON POST to `SMS_API_URL`:
`phone_number`, `code`, `purpose` (`VERIFY_PHONE` or `PASSWORD_RESET`), and
`expires_in_seconds`; `Authorization: Bearer <SMS_API_TOKEN>`. A 2xx response means
accepted for delivery. Redirects are rejected. Transport failures return a generic
503 and invalidate the optional OTP; registration does not call this gateway. Integrate an operator-owned
adapter for the chosen SMS vendor and test actual delivery; no vendor account or
credential is assumed. The gateway must not log OTP payloads.

After the database release gates below are approved and verified, collect Django
static files with production settings, build the frontend, and run
`config.wsgi:application` with the host's audited WSGI server behind nginx.
Never use Django `runserver` in production. Configure durable media storage,
backups/restore monitoring, log retention, Redis persistence/availability, and TLS.
After approved schema provisioning, use interactive `createsuperuser` with production
settings from the operator console. Do not seed data or supply default passwords.
Run `manage.py check --deploy --tag security --settings=config.settings.production` with real
injected settings before deployment. No deployment is performed by this task.

## Database decision and approval boundary

The root backend maps unmanaged v1.1.13 models and exposes auth/profiles/categories;
its jobs, applications, invitations, and assignments apps remain scaffolding. It
cannot replace the marketplace backend without losing working API flows. Its
production SMS configuration now also refuses the development provider.

The selected backend has managed `accounts_user`, `profiles_worker`, `orders_*`,
team membership, chat, reviews and JWT blacklist tables. These are incompatible
with the root v1.1.13 schema. Never point it at `ishchi_test`, run its migrations
there, or copy the old synthetic SQLite data into production. The connection
wrapper accepts only dedicated `ishchi_marketplace` / `ishchi_marketplace_*` names,
rejects DSNs/target overrides before connecting, and requires explicit endpoints.
Production migration commands and schema editing fail before execution until a
separately approved release changes the guards. Migration history is unchanged except an application-owned
payment display-label migration; this does not alter the authoritative schema.
No PostgreSQL connection, migration, clone, privilege change or data import was run.

REQUIRES_APPROVAL: select a new dedicated PostgreSQL database/schema ownership
plan OR approve implementation against the authoritative schema; review the full
managed migration graph and integrity triggers, runtime/migrator privileges,
backup/rollback plan, and any real-data mapping (IDs, hashes, roles, KYC trust
state, assignments/capacity, media and blacklist sessions). Old sessions should
be revoked at cutover. v1.1.14, v1.1.15 and Batch 16.x SQL remain proposal-only.

BLOCKED: approved PostgreSQL provisioning/migration plus integration and concurrent
hiring/category/account-state tests; external hosting/TLS/media/backups and
deployment security/load verification. SMS credentials/delivery are required only
for optional phone verification and SMS password recovery.

## Search classification and remaining historical references

Runtime account selector + credentials: removed entirely from React. Branding and
API health/payment strings: converted to ISHCHI in UZ/RU/EN. Fake payment preview:
removed, no form or submit API. Success notifications reviewed: marketplace ones
follow persisted backend mutations. SMS console code: replaced with provider
abstraction, retained root console no longer logs codes. Synthetic seeding:
moved to `backend/local_tools`, installed only in development, with a guard before
any transaction; unavailable in production. Tests/mocks and fictional fixtures:
retained for regression verification. Historical docs, SQL constraint identifiers,
migration history, package tooling paths and the legacy settings import are
compatibility/history references, not login shortcuts; preserved deliberately.
Old README demonstration instructions are superseded by this file.

## Verification recorded for this change

TESTED: 103 backend tests passed (unit/contracts plus real SQLite API/ORM flows),
16 frontend component/client tests passed, TypeScript/Vite production build passed,
Django system check and migration-state dry-run passed. The startup subprocess tests
block socket connections and validate production security checks with placeholder
configuration, including registration with SMS disabled and refusal of invalid
HTTP SMS credentials or development-only SMS providers in production. Compiled assets
contain no synthetic credentials, switcher flag, teacher branding, or local API URL.
Mobile browser inspection covered login and unavailable-payment UZ/RU/EN layouts;
the preview had no live API, and correctly showed a status-fetch error on payments.

NOT_TESTED: PostgreSQL/Redis integration, distributed locking/concurrent load,
real SMS delivery, hosted end-to-end registration, nginx/TLS, external hosting,
backup restore, dependency vulnerability assessment, penetration and load tests.
The root backend's PostgreSQL-dependent suite was deliberately not run. Full OpenAPI
deployment validation still reports existing serializer metadata warnings; the
security-tagged deployment checks pass. Frontend tests report an existing React
`act(...)` warning in the chat read-receipt test; all assertions pass.

IMPLEMENTED describes the offline source conversion, not production readiness.
BLOCKED and REQUIRES_APPROVAL gates above remain in force. `ishchi_test` and all
schema/privilege SQL proposals were untouched. No code was committed or published.

## Optional local random content

From `backend`, `python manage.py seed_marketplace --settings=config.settings.development`
appends 30 workers, 10 employers, 24 taxonomy entries (reused on later runs), 60 orders,
and related marketplace events. It never creates administrators or deletes existing
records, sends no SMS, and accepts only the local SQLite target. Fictional accounts
have unusable passwords and do not claim phone/KYC verification. This tool is not
installed in production. Counts can be set with `--workers`, `--employers`, `--orders`.
