<#
.SYNOPSIS
    Stops and completely removes the VUES Windows service.

.NOTES
    Does NOT delete any app files, logs, or database records.
    Safe to re-run. Safe to run when service is already stopped.
#>

#Requires -RunAsAdministrator

# Dynamically resolve paths from script location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path

$ServiceName = 'VUES'
$WinSW       = Join-Path $AppRoot 'VUES.exe'

Write-Host ''
Write-Host '  Uninstalling VUES service...' -ForegroundColor Yellow

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "  Service '$ServiceName' is not installed. Nothing to do." -ForegroundColor Green
    exit 0
}

if ($svc.Status -eq 'Running') {
    Write-Host '  Stopping service...' -ForegroundColor Yellow
    & $WinSW stop
    Start-Sleep -Seconds 5
}

& $WinSW uninstall
Write-Host "  Service '$ServiceName' removed." -ForegroundColor Green
Write-Host '  Logs preserved at:' (Join-Path $AppRoot 'logs')
Write-Host ''