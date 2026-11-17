# PREPARED ONLY. Installation and enabling require separate owner approval.
# Uses the current operator's interactive Windows session; no stored task password.
$ErrorActionPreference = 'Stop'
$backupExit = 1
try {
    Set-Location -LiteralPath (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
    if ([DateTimeOffset]::Now.Offset -ne [TimeSpan]::FromHours(5)) {
        $backupExit = 3
        throw 'Asia/Tashkent UTC+05 schedule configuration required.'
    }
    & '.\backend\.venv\Scripts\python.exe' 'deploy/local_backup.py' --execute
    $backupExit = $LASTEXITCODE
} catch {
    Write-Output 'ISHCHI backup runner failed before completion; inspect operator configuration.'
}
if ($backupExit -ne 0 -and $backupExit -ne 4) {
    Write-Output "ISHCHI backup failed or requires authorization renewal. Exit: $backupExit"
    try {
        $notifier = New-Object -ComObject WScript.Shell
        $null = $notifier.Popup('ISHCHI backup failed or requires owner approval renewal. Check Task Scheduler LastTaskResult and the private scheduled-backup-status.json. Check application readiness before retrying.', 30, 'ISHCHI backup requires attention', 48)
    } catch { Write-Output 'Notification unavailable; inspect Task Scheduler LastTaskResult.' }
}
exit $backupExit
