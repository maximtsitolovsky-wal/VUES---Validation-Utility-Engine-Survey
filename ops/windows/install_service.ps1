<#
.SYNOPSIS
    Installs SiteOwlQA as a Windows service using WinSW.

.DESCRIPTION
    - Must be run as Administrator (script self-elevates if needed).
    - Installs the service to run as the CURRENT logged-in user so that
      Windows NTLM proxy credentials are available for PowerShell attachment
      downloads from the Airtable CDN.
    - Sets startup type to Automatic (Delayed) so it survives reboots.
    - Configures 3-tier crash recovery (10s / 1min / 5min restart).

.NOTES
    WinSW binary : C:\SiteOwlQA_App\SiteOwlQA.exe
    Config XML   : C:\SiteOwlQA_App\SiteOwlQA.xml
    Python       : C:\Python314\python.exe
    App root     : C:\SiteOwlQA_App
    Log output   : C:\SiteOwlQA_App\logs\SiteOwlQA.out.log
#>

#Requires -RunAsAdministrator

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ServiceName  = 'SiteOwlQA'
$AppRoot      = 'C:\SiteOwlQA_App'
$WinSW        = Join-Path $AppRoot 'SiteOwlQA.exe'
$LogDir       = Join-Path $AppRoot 'logs'

Write-Host ''
Write-Host '=========================================' -ForegroundColor Cyan
Write-Host '  SiteOwlQA Service Installer            ' -ForegroundColor Cyan
Write-Host '=========================================' -ForegroundColor Cyan
Write-Host ''

# ---------------------------------------------------------------------------
# 1. Pre-flight checks
# ---------------------------------------------------------------------------
if (-not (Test-Path $WinSW)) {
    Write-Error "WinSW binary not found at: $WinSW`nRun this script from C:\SiteOwlQA_App."
    exit 1
}

if (-not (Test-Path (Join-Path $AppRoot 'main.py'))) {
    Write-Error "main.py not found in $AppRoot. Wrong directory?"
    exit 1
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Write-Host "  Created log directory: $LogDir" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 2. Remove existing service if present
# ---------------------------------------------------------------------------
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  Existing service found (status: $($existing.Status)). Removing..." -ForegroundColor Yellow
    if ($existing.Status -eq 'Running') {
        Write-Host '  Stopping service...' -ForegroundColor Yellow
        & $WinSW stop 2>&1 | Out-Null
        Start-Sleep -Seconds 3
    }
    & $WinSW uninstall 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    Write-Host '  Old service removed.' -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 3. Get current logged-in user for service account
#    The service must run as this user so that Windows NTLM credentials
#    are available for PowerShell Invoke-WebRequest through the corporate
#    proxy (sysproxy.wal-mart.com:8080) when downloading Airtable attachments.
# ---------------------------------------------------------------------------
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Host ''
Write-Host "  Service will log on as: $currentUser" -ForegroundColor Cyan
Write-Host '  (Required for corporate NTLM proxy auth on attachment downloads)'
Write-Host ''

$credential = Get-Credential -UserName $currentUser -Message (
    "Enter your Windows password for '$currentUser'.`n" +
    "This is stored securely in the Windows Service Control Manager.`n" +
    "It is never written to disk by this script."
)

if (-not $credential) {
    Write-Error 'No credentials provided. Aborting.'
    exit 1
}

# ---------------------------------------------------------------------------
# 4. Install via WinSW
# ---------------------------------------------------------------------------
Write-Host '  Installing service via WinSW...' -ForegroundColor Cyan
Set-Location $AppRoot
& $WinSW install
if ($LASTEXITCODE -ne 0) {
    Write-Error "WinSW install failed (exit $LASTEXITCODE)."
    exit 1
}
Write-Host '  WinSW install OK.' -ForegroundColor Green

# ---------------------------------------------------------------------------
# 5. Set logon account via sc.exe
#    WinSW installs as LocalSystem by default. We override to the current
#    user so NTLM proxy credentials are available in the service context.
# ---------------------------------------------------------------------------
Write-Host '  Configuring service logon account...' -ForegroundColor Cyan
$plainPass = $credential.GetNetworkCredential().Password
$scResult = sc.exe config $ServiceName obj= "$currentUser" password= "$plainPass"
$plainPass = $null  # clear from memory immediately

if ($LASTEXITCODE -ne 0) {
    Write-Warning "sc.exe config failed (exit $LASTEXITCODE): $scResult"
    Write-Warning "Service will run as LocalSystem. NTLM proxy downloads may fail."
    Write-Warning "Fix manually: Services.msc -> SiteOwlQA -> Log On tab."
} else {
    Write-Host "  Logon account set to: $currentUser" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 6. Configure failure recovery via sc.exe
#    WinSW XML handles this but sc.exe gives us GUI-visible failure actions.
# ---------------------------------------------------------------------------
sc.exe failure $ServiceName reset= 3600 actions= restart/10000/restart/60000/restart/300000 | Out-Null
Write-Host '  Failure recovery configured (10s / 1min / 5min restart).' -ForegroundColor Green

# ---------------------------------------------------------------------------
# 7. Start the service
# ---------------------------------------------------------------------------
Write-Host '  Starting service...' -ForegroundColor Cyan
Start-Service -Name $ServiceName
Start-Sleep -Seconds 4

$svc = Get-Service -Name $ServiceName
if ($svc.Status -eq 'Running') {
    Write-Host '' 
    Write-Host '  =========================================' -ForegroundColor Green
    Write-Host "  Service '$ServiceName' is RUNNING." -ForegroundColor Green
    Write-Host '  =========================================' -ForegroundColor Green
} else {
    Write-Warning "Service status: $($svc.Status). Check logs:"
    Write-Warning "  $LogDir\SiteOwlQA.wrapper.log"
    Write-Warning "  $LogDir\SiteOwlQA.out.log"
}

Write-Host ''
Write-Host '  Useful commands:' -ForegroundColor Cyan
Write-Host '    Get-Service SiteOwlQA              -- check status'
Write-Host '    Restart-Service SiteOwlQA          -- restart'
Write-Host '    Stop-Service SiteOwlQA             -- stop'
Write-Host "    Get-Content $LogDir\SiteOwlQA.out.log -Tail 50  -- live log"
Write-Host ''