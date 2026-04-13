$ErrorActionPreference = 'Stop'

$workdir = 'C:\SiteOwlQA_App'
$python = 'python'
$rebuildScript = Join-Path $workdir 'tools\rebuild_current_dashboard.py'
$exportScript = Join-Path $workdir 'tools\export_share_dashboard.py'
$shareFile = Join-Path $workdir 'share\executive_dashboard_live_share.html'
$logDir = Join-Path $workdir 'logs'
$logFile = Join-Path $logDir 'republish-dashboard.log'
$shareUrl = 'https://puppy.walmart.com/sharing/vn59j7j/executive-dashboard-clean-working'
$publishPrompt = @"
Update the EXISTING Puppy Share page using versioning from this local file: '$shareFile'.
Target the exact existing page at: $shareUrl
Use:
- business: 'vn59j7j'
- name: 'executive-dashboard-clean-working'
- access_level: 'business'

Requirements:
- create a NEW VERSION of the existing page content
- keep the SAME stable URL/path
- keep the SAME slug
- do NOT create a second dashboard
- do NOT create a sibling page
- do NOT open a browser
"@

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Log([string]$message) {
    $timestamp = Get-Date -Format s
    "$timestamp $message" | Tee-Object -FilePath $logFile -Append
}

Set-Location $workdir
Write-Log 'Starting dashboard republish job.'

if (-not (Test-Path $rebuildScript)) {
    throw "Rebuild script not found: $rebuildScript"
}

if (-not (Test-Path $exportScript)) {
    throw "Export script not found: $exportScript"
}

Write-Log 'Rebuilding current dashboard output from live sources.'
& $python $rebuildScript 2>&1 | Tee-Object -FilePath $logFile -Append

Write-Log 'Exporting self-contained share dashboard.'
& $python $exportScript 2>&1 | Tee-Object -FilePath $logFile -Append

if (-not (Test-Path $shareFile)) {
    throw "Expected share HTML was not generated: $shareFile"
}

code-puppy -p $publishPrompt --agent share-puppy 2>&1 | Tee-Object -FilePath $logFile -Append

Write-Log 'Dashboard republish job completed.'
