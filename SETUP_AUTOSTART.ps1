# Create startup shortcut for VUES Live Dashboard
# This makes the dashboard auto-start when Windows logs in

$WScriptShell = New-Object -ComObject WScript.Shell
$StartupFolder = [Environment]::GetFolderPath('Startup')
$ShortcutPath = Join-Path $StartupFolder "VUES Live Dashboard.lnk"
$TargetPath = Join-Path $PSScriptRoot "START_LIVE_DASHBOARD.bat"

# Create the shortcut
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.WindowStyle = 7  # Minimized
$Shortcut.Description = "VUES Live Dashboard - Auto-refresh from Airtable"
$Shortcut.Save()

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VUES LIVE DASHBOARD AUTO-START SETUP" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  [OK] Startup shortcut created:" -ForegroundColor Green
Write-Host "       $ShortcutPath" -ForegroundColor White
Write-Host ""
Write-Host "  The dashboard will now auto-start when you log in."
Write-Host ""
Write-Host "  To start now, run:" -ForegroundColor Yellow
Write-Host "       .\START_LIVE_DASHBOARD.bat" -ForegroundColor White
Write-Host ""
Write-Host "  To remove auto-start:" -ForegroundColor Yellow
Write-Host "       Remove-Item '$ShortcutPath'" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
