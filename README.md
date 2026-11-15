# ISHCHI marketplace

The Django backend and React frontend are in `backend/` and `frontend/`.
See [current run instructions](PRODUCTION_MVP.md) for local startup and configuration.

Registration activates an account immediately without sending SMS.
The local frontend is at http://127.0.0.1:5173; the API is at http://127.0.0.1:8001.

This directory can be moved or copied as a standalone project. Its runtime and
tests do not require the parent repository. Keep `backend/`, `frontend/`, `deploy/`,
`.gitignore` and `PRODUCTION_MVP.md` together.

Local `.env`, databases, media, virtual environments and installed packages are
Git-ignored. For local data continuity, copy `backend/.local/` and any uploaded
media separately; keep those private. The Git repository root is this directory.

## Local setup (PowerShell)

Use Python 3.14 and Node.js 24 LTS. Open PowerShell in the cloned project
directory, then run:

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
Set-Location frontend
npm ci
```

After moving the project, remove the copied `backend/.venv` before running setup,
then reinstall packages at the new location. A fresh clone also
needs migrations; an existing database keeps its accounts and marketplace data.
Local development uses SQLite and an in-process cache, without PostgreSQL or Redis.

Start the API in one terminal:

```powershell
# From the cloned project directory:
Set-Location backend
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.development
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --settings=config.settings.development
```

Start the frontend in another terminal:

```powershell
# From the cloned project directory:
Set-Location frontend
npm run dev
```

Open http://127.0.0.1:5173. API and media requests use Vite's proxy to port 8001.
The admin UI is at http://127.0.0.1:8001/django-admin/; create your own administrator
with `manage.py createsuperuser` if needed.

## Checks

From the project directory, run the backend checks against an isolated in-memory
SQLite database; no PostgreSQL or Redis service is needed:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check --settings=config.settings.testing
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.testing
.\.venv\Scripts\python.exe -m pytest --ds=config.settings.testing
```

In a separate terminal, from the project directory:

```powershell
Set-Location frontend
npm ci
npm test
npm run build
npm audit
```

GitHub Actions runs these checks on pushes and pull requests. A successful local
test run covers SQLite development behavior; production integration and deployment
checks still require the release gates in `PRODUCTION_MVP.md`.

## Before publishing to GitHub

Publish this `ishchi/` directory. Review `git status --short` and `git diff --cached`
before committing. Keep `.env.example` and `.env.production.example` in Git;
keep actual `.env` files, `.local/`, media and credentials private. Frontend `VITE_`
variables are public and must never contain secrets.

Publishing source code does not deploy the application. Production variables and
the outstanding database/deployment gates are documented in
[PRODUCTION_MVP.md](PRODUCTION_MVP.md).
