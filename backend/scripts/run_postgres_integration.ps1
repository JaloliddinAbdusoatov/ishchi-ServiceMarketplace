# Execute only after the database owner explicitly approves the exact target
# and test_schema scope. This script does not provision or create databases.
$ErrorActionPreference = 'Stop'
$PythonExe = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not $env:DB_AUTHORIZATION_FILE) {
    throw 'DB_AUTHORIZATION_FILE is required; credentials do not authorize tests.'
}
Push-Location (Join-Path $PSScriptRoot '..')
try {
    & $PythonExe -m pytest pgtests --ds=config.settings.postgres_integration -q
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
