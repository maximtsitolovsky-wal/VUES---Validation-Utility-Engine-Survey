# Register Scout Completion Sync Task in Windows Task Scheduler
# Run as Administrator (required for Task Scheduler)
# Schedule: Monday-Friday at 10:00 AM and 3:00 PM

$ErrorActionPreference = "Stop"

Write-Host "=== Scout Completion Sync Task Scheduler Registration ===" -ForegroundColor Cyan

# Paths
$scriptDir = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$scriptPath = Join-Path $projectRoot "scripts\scout_completion_sync.py"
$pythonExe = (Get-Command python).Path
$taskName = "ScoutCompletionSync"

# Validate script exists
if (-not (Test-Path $scriptPath)) {
    Write-Host "[ERROR] Script not found: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "[*] Script: $scriptPath" -ForegroundColor Yellow
Write-Host "[*] Python: $pythonExe" -ForegroundColor Yellow

# Remove existing task if present
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Write-Host "[*] Removing existing task '$taskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create action
$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument "`"$scriptPath`"" `
    -WorkingDirectory (Split-Path $scriptPath)

# Create triggers for 10 AM and 3 PM Monday-Friday
$trigger10AM = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 10:00AM
$trigger3PM = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 3:00PM

# Settings
$settings = New-ScheduledTaskSettings `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew

# Principal (run as current user)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited

# Register task
Write-Host "[*] Registering scheduled task..." -ForegroundColor Yellow
Register-ScheduledTask `
    -TaskName $taskName `
    -Description "Syncs Scout Airtable completion status to Excel tracker (10 AM & 3 PM, Mon-Fri)" `
    -Action $action `
    -Trigger $trigger10AM,$trigger3PM `
    -Settings $settings `
    -Principal $principal | Out-Null

Write-Host "[OK] Task '$taskName' registered successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Schedule: Monday-Friday at 10:00 AM and 3:00 PM" -ForegroundColor Cyan
Write-Host "To view:  Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
Write-Host "To test:  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
Write-Host "To remove: Unregister-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
Write-Host ""

# Test run (optional)
$response = Read-Host "Run a test now? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "[*] Starting test run..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $taskName
    Start-Sleep -Seconds 2
    Write-Host "[OK] Task started. Check logs for results." -ForegroundColor Green
}

Write-Host "[DONE]" -ForegroundColor Green
