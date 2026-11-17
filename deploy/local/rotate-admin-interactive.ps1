# Run only after explicit approval for this exact administrator and revocation.
# No transcript, redirected password input, credential file, or global key change.
param([switch]$PreviousPasswordUnknown)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
Write-Host 'Approved single-administrator rotation. Enter passwords only in hidden prompts.'
Write-Host 'Never paste passwords into chat. Closing/cancelling before rotation leaves it pending.'
Write-Host 'Use a unique password or passphrase (12+ characters recommended). Check the keyboard layout.'
Write-Host 'A mismatch or policy rejection allows up to three attempts without changing the account.'
@{ checked_at = [DateTime]::UtcNow.ToString('o'); account = '489124fe-ae1b-4551-8495-9f148c46490b'; status = 'INTERACTIVE_INPUT_PENDING'; exit_code = $null } | ConvertTo-Json | Set-Content -LiteralPath 'deploy/.local/rotation-result.json' -Encoding utf8
$dc = @('--context','desktop-linux','compose','--env-file','deploy/.env.local','-f','deploy/compose.local.yml','--profile','work')
$rotationArgs = @('run','--rm','--no-deps','backend','python','manage.py','rotate_local_admin','--account','489124fe-ae1b-4551-8495-9f148c46490b','--apply','--verify')
if ($PreviousPasswordUnknown) {
    Write-Host 'Owner-approved reset: enter ONLY a NEW password twice. The previous password is not required.'
    Write-Host 'Old-password login test will remain NOT RUN; token/session revocation and new login will be checked.'
    $rotationArgs += '--previous-password-unknown'
}
& docker @dc @rotationArgs
$rotationExit = $LASTEXITCODE
$result = @{ checked_at = [DateTime]::UtcNow.ToString('o'); account = '489124fe-ae1b-4551-8495-9f148c46490b'; exit_code = $rotationExit; previous_password_test = $(if ($PreviousPasswordUnknown) { 'NOT RUN' } else { 'INCLUDED' }); status = $(if ($rotationExit -eq 0) { 'PASS' } else { 'FAIL_OR_CANCELLED_CHECK_ACCOUNT_STATE' }) }
$result | ConvertTo-Json | Set-Content -LiteralPath 'deploy/.local/rotation-result.json' -Encoding utf8
Write-Host "Rotation/verification command exit code: $rotationExit"
Read-Host 'Press Enter to close this window'
exit $rotationExit
