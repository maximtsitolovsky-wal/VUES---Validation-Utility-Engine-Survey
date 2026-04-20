# update_shortcut.ps1 — rebuilds the VUES desktop shortcut
# Run once: powershell -ExecutionPolicy Bypass -File ops\windows\update_shortcut.ps1
#
# Target: launch_vues_dashboard.ps1 (via PowerShell)
#   This script is the authoritative launcher: it starts the pipeline,
#   rebuilds the dashboard, spins up run_dashboard_server.py on a free port,
#   verifies the server is alive, then opens the browser.
#   Do NOT point the shortcut at start_pipeline.bat — that bat never starts
#   run_dashboard_server.py, so the browser would open to a dead port.

# Dynamically resolve paths from script location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$workDir = (Resolve-Path (Join-Path $scriptDir '..\..')).Path

$lnkPath  = Join-Path $env:USERPROFILE 'OneDrive - Walmart Inc\Desktop\vues Launcher.lnk'
$ps1Path  = Join-Path $workDir 'ops\windows\launch_vues_dashboard.ps1'
$exePath  = Join-Path $workDir 'VUES.exe'
$psExe    = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

$sh  = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut($lnkPath)

$lnk.TargetPath       = $psExe
$lnk.Arguments        = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ps1Path`""
$lnk.WorkingDirectory = $workDir
$lnk.Description      = 'VUES - starts pipeline and opens dashboard'
$lnk.IconLocation     = "$exePath,0"
$lnk.WindowStyle      = 1   # normal — PowerShell handles its own Hidden flag

$lnk.Save()
Write-Host ''
Write-Host '✓ Shortcut saved.' -ForegroundColor Green
Write-Host ''

# Verify
$v = $sh.CreateShortcut($lnkPath)
Write-Host "  Target  : $($v.TargetPath)"
Write-Host "  Args    : $($v.Arguments)"
Write-Host "  WorkDir : $($v.WorkingDirectory)"
Write-Host "  Icon    : $($v.IconLocation)"
Write-Host "  Desc    : $($v.Description)"
Write-Host "  Window  : $($v.WindowStyle)"
Write-Host ''
