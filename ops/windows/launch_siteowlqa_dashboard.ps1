$ErrorActionPreference = 'Stop'

$workdir  = 'C:\SiteOwlQA_App'
$opsDir   = Join-Path $workdir 'ops\windows'
$launcher = Join-Path $opsDir 'start_siteowlqa_background.ps1'

# Prefer project venv; fall back to system Python 3.14
$venvPython   = Join-Path $workdir '.venv\Scripts\python.exe'
$systemPython = 'C:\Python314\python.exe'
$python = if (Test-Path $venvPython) { $venvPython } else { $systemPython }

$serverScript  = Join-Path $workdir 'tools\run_dashboard_server.py'
$dashboard     = Join-Path $workdir 'output\executive_dashboard.html'
$dashboardUrl  = 'http://127.0.0.1:8765/executive_dashboard.html'
$codePuppyDashboardUrl = 'https://puppy.walmart.com/sharing/vn59j7j/executive-dashboard-clean-working'
$rebuildScript = Join-Path $workdir 'tools\rebuild_current_dashboard.py'
$dataSignature = 'const raw = ['
$maxWaitSeconds = 30
$launchStartUtc = [DateTime]::UtcNow

if (-not (Test-Path $launcher)) {
    Write-Error "Launcher helper not found: $launcher"
    exit 1
}

if (-not (Test-Path $python)) {
    Write-Error "Python not found at $python (tried venv and $systemPython)"
    exit 1
}

if (-not (Test-Path $serverScript)) {
    Write-Error "Dashboard server script not found: $serverScript"
    exit 1
}

if (-not (Test-Path $rebuildScript)) {
    Write-Error "Dashboard rebuild script not found: $rebuildScript"
    exit 1
}

Write-Host ''
Write-Host 'Checking whether SiteOwlQA is already running...'
$startResult = & $launcher
$startResult = ($startResult | Select-Object -Last 1).ToString().Trim()

switch ($startResult) {
    'ALREADY_RUNNING' { Write-Host '[OK] SiteOwlQA is already running. Reusing existing process.' }
    'STARTED' { Write-Host '[OK] SiteOwlQA started in background.' }
    default {
        Write-Error "Failed to start SiteOwlQA. Result: $startResult"
        exit 1
    }
}

Write-Host 'Rebuilding dashboard artifacts so launch uses fresh realtime status...'
& $python $rebuildScript
$rebuildSucceeded = $LASTEXITCODE -eq 0
if (-not $rebuildSucceeded) {
    Write-Warning "Dashboard rebuild failed with exit code $LASTEXITCODE. Continuing with the latest generated dashboard so the app can still be controlled from localhost."
}

Write-Host 'Waiting for generated dashboard with embedded data...'
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$ready = $false

while ($stopwatch.Elapsed.TotalSeconds -lt $maxWaitSeconds) {
    if (Test-Path $dashboard) {
        try {
            $item = Get-Item $dashboard
            $hasFreshTimestamp = $item.LastWriteTimeUtc -ge $launchStartUtc
            $hasData = Select-String -Path $dashboard -SimpleMatch $dataSignature -Quiet
            if (($rebuildSucceeded -and $hasFreshTimestamp -and $hasData) -or ((-not $rebuildSucceeded) -and $hasData)) {
                $ready = $true
                break
            }
        }
        catch {
            # File may be mid-write; just retry.
        }
    }

    Start-Sleep -Milliseconds 500
}

if (-not $ready) {
    Write-Error "Generated dashboard was not ready within $maxWaitSeconds seconds: $dashboard"
    exit 1
}

Write-Host 'Ensuring canonical localhost dashboard server is running...'
$serverReady = $false
try {
    $response = Invoke-WebRequest -Uri $dashboardUrl -UseBasicParsing -Method Head -TimeoutSec 2
    if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
        $serverReady = $true
    }
}
catch {
    # Server is not ready yet.
}

if (-not $serverReady) {
    Start-Process -FilePath $python `
        -ArgumentList $serverScript, (Join-Path $workdir 'output'), '8765' `
        -WorkingDirectory $workdir `
        -WindowStyle Hidden | Out-Null

    $serverStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($serverStopwatch.Elapsed.TotalSeconds -lt 10) {
        try {
            $response = Invoke-WebRequest -Uri $dashboardUrl -UseBasicParsing -Method Head -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                $serverReady = $true
                break
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
}

if (-not $serverReady) {
    Write-Error "Local dashboard server was not reachable at $dashboardUrl"
    exit 1
}

Write-Host 'Opening canonical localhost dashboard in your default browser...'
Start-Process -FilePath $dashboardUrl | Out-Null

Write-Host ''
Write-Host 'Done.'
Write-Host '- Pipeline stays running in background'
Write-Host "- Local dashboard URL: $dashboardUrl"
Write-Host "- CodePuppy live-share page (V3): $codePuppyDashboardUrl"
exit 0
