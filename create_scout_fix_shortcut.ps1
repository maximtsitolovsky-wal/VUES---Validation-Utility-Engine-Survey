$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "FIX SCOUT TASKS.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "C:\SiteOwlQA_App\ops\windows\FIX_SCOUT_TASKS.bat"
$Shortcut.WorkingDirectory = "C:\SiteOwlQA_App\ops\windows"
$Shortcut.Description = "Fix Scout scheduled tasks (requires admin)"
$Shortcut.IconLocation = "shell32.dll,21"
$Shortcut.Save()

Write-Host "✅ Desktop shortcut created: FIX SCOUT TASKS" -ForegroundColor Green
