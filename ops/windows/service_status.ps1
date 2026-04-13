<#
.SYNOPSIS
    Shows SiteOwlQA service status and tails the last 60 lines of output log.
#>

$ServiceName = 'SiteOwlQA'
$LogDir      = 'C:\SiteOwlQA_App\logs'
$OutLog      = Join-Path $LogDir 'SiteOwlQA.out.log'
$WrapLog     = Join-Path $LogDir 'SiteOwlQA.wrapper.log'

Write-Host ''
Write-Host '=========================================' -ForegroundColor Cyan
Write-Host '  SiteOwlQA Service Status               ' -ForegroundColor Cyan
Write-Host '=========================================' -ForegroundColor Cyan

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "  NOT INSTALLED" -ForegroundColor Red
    Write-Host "  Run: .\install_service.ps1 (as Administrator)"
} else {
    $colour = if ($svc.Status -eq 'Running') { 'Green' } else { 'Red' }
    Write-Host "  Status    : $($svc.Status)" -ForegroundColor $colour
    Write-Host "  StartType : $($svc.StartType)"
}

Write-Host ''
Write-Host '--- Last 60 lines: SiteOwlQA.out.log ---' -ForegroundColor Cyan
if (Test-Path $OutLog) {
    Get-Content $OutLog -Tail 60
} else {
    Write-Host '  (log not yet created)'
}

Write-Host ''
Write-Host '--- Last 20 lines: SiteOwlQA.wrapper.log ---' -ForegroundColor Cyan
if (Test-Path $WrapLog) {
    Get-Content $WrapLog -Tail 20
} else {
    Write-Host '  (wrapper log not yet created)'
}
Write-Host ''