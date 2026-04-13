$ErrorActionPreference = 'Stop'

$workdir       = 'C:\SiteOwlQA_App'
$opsDir        = Join-Path $workdir 'ops\windows'
$launcher      = Join-Path $opsDir  'start_siteowlqa_background.ps1'
$outputDir     = Join-Path $workdir 'output'
$portFile      = Join-Path $outputDir 'dashboard.port'
$dashboard     = Join-Path $outputDir 'executive_dashboard.html'
$serverScript  = Join-Path $workdir  'tools\run_dashboard_server.py'
$rebuildScript = Join-Path $workdir  'tools\rebuild_current_dashboard.py'
$maxWaitSeconds = 30
$launchStartUtc = [DateTime]::UtcNow

$venvPython   = Join-Path $workdir '.venv\Scripts\python.exe'
$systemPython = 'C:\Python314\python.exe'
$python = if (Test-Path $venvPython) { $venvPython } else { $systemPython }

if (-not (Test-Path $launcher))     { Write-Error "Launcher helper not found: $launcher"; exit 1 }
if (-not (Test-Path $python))       { Write-Error "Python not found: $python"; exit 1 }
if (-not (Test-Path $serverScript)) { Write-Error "Server script not found: $serverScript"; exit 1 }

# Find first available port starting from preferred
function Find-FreePort([int]$Preferred = 8765) {
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $tcp.ConnectAsync('127.0.0.1', $Preferred).Wait(300) | Out-Null
        if ($tcp.Connected) {
            $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 0)
            $listener.Start()
            $free = $listener.LocalEndpoint.Port
            $listener.Stop()
            return $free
        }
    } catch { }
    finally { $tcp.Dispose() }
    return $Preferred
}

# Check if existing server is still healthy
$existingPort = $null
if (Test-Path $portFile) {
    $raw = (Get-Content $portFile -Raw).Trim()
    if ($raw -match '^\d+$') { $existingPort = [int]$raw }
}

$serverReady = $false
$activePort  = $null

if ($existingPort) {
    $checkUrl = "http://127.0.0.1:$existingPort/executive_dashboard.html"
    try {
        $resp = Invoke-WebRequest -Uri $checkUrl -UseBasicParsing -Method Head -TimeoutSec 2
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
            $serverReady = $true
            $activePort  = $existingPort
            Write-Host "[OK] Server already running on port $activePort"
        }
    } catch { }
}

# Start pipeline
Write-Host ''
Write-Host 'Checking pipeline...'
$startResult = (& $launcher | Select-Object -Last 1).ToString().Trim()
switch ($startResult) {
    'ALREADY_RUNNING' { Write-Host '[OK] Pipeline already running.' }
    'STARTED'         { Write-Host '[OK] Pipeline started.' }
    default           { Write-Warning "Unexpected launcher result: $startResult" }
}

# Rebuild dashboard
if (Test-Path $rebuildScript) {
    Write-Host 'Rebuilding dashboard...'
    & $python $rebuildScript | Out-Null
}

# Wait for dashboard HTML
Write-Host 'Waiting for dashboard data...'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while ($sw.Elapsed.TotalSeconds -lt $maxWaitSeconds) {
    if (Test-Path $dashboard) {
        $item = Get-Item $dashboard
        if ($item.LastWriteTimeUtc -ge $launchStartUtc -and
            (Select-String -Path $dashboard -SimpleMatch 'const teamDashboardData' -Quiet)) {
            break
        }
    }
    Start-Sleep -Milliseconds 500
}

# Start server on free port if not already up
if (-not $serverReady) {
    $activePort = Find-FreePort 8765
    Write-Host "Starting server on port $activePort..."
    [System.IO.File]::WriteAllText($portFile, "$activePort", [System.Text.Encoding]::ASCII)

    Start-Process -FilePath $python `
        -ArgumentList $serverScript, $outputDir, $activePort `
        -WorkingDirectory $workdir `
        -WindowStyle Hidden

    $dashUrl = "http://127.0.0.1:$activePort/executive_dashboard.html"
    $sw2 = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw2.Elapsed.TotalSeconds -lt 10) {
        try {
            $resp = Invoke-WebRequest -Uri $dashUrl -UseBasicParsing -Method Head -TimeoutSec 2
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) { $serverReady = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 250
    }
}

if (-not $serverReady) {
    Write-Error ("Server did not respond on port " + $activePort)
    exit 1
}

$dashboardUrl = "http://127.0.0.1:$activePort/executive_dashboard.html"
Write-Host "Opening: $dashboardUrl"
Start-Process -FilePath $dashboardUrl | Out-Null

Write-Host ''
Write-Host ("Done. Dashboard on port " + $activePort)
exit 0
