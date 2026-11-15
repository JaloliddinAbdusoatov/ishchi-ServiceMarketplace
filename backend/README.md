# ISHCHI backend

Run from this directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --settings=config.settings.development
```

Development uses `.local/ishchi.sqlite3`; existing accounts and marketplace data
are preserved. Registration sends no SMS. The real administration UI is at
http://127.0.0.1:8001/django-admin/.

See [configuration and release instructions](../PRODUCTION_MVP.md).
