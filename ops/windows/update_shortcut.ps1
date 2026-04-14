# update_shortcut.ps1 — rebuilds the SiteOwlQA desktop shortcut
# Run once: powershell -ExecutionPolicy Bypass -File ops\windows\update_shortcut.ps1

$lnkPath = Join-Path $env:USERPROFILE 'OneDrive - Walmart Inc\Desktop\SiteOwlQA Launcher.lnk'
$batPath  = 'C:\SiteOwlQA_App\ops\windows\start_pipeline.bat'
$exePath  = 'C:\SiteOwlQA_App\SiteOwlQA.exe'

$sh  = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut($lnkPath)

$lnk.TargetPath       = 'C:\Windows\System32\cmd.exe'
$lnk.Arguments        = "/c `"$batPath`""
$lnk.WorkingDirectory = 'C:\SiteOwlQA_App'
$lnk.Description      = 'SiteOwlQA — starts pipeline, bottleneck auditor, docker platform engineer, and opens dashboard'
$lnk.IconLocation     = "$exePath,0"
$lnk.WindowStyle      = 7   # minimised — launcher window flashes and hides

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
