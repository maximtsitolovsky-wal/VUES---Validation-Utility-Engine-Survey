$ErrorActionPreference = 'Stop'

$opsDir     = Split-Path -Parent $MyInvocation.MyCommand.Path
$workdir    = (Resolve-Path (Join-Path $opsDir '..\..')).Path
# Prefer project venv; fall back to first python.exe from PATH
$venvPython = Join-Path $workdir '.venv\Scripts\python.exe'
$pythonCmd  = Get-Command python -ErrorAction SilentlyContinue
$python     = if (Test-Path $venvPython) { $venvPython } elseif ($pythonCmd) { $pythonCmd.Source } else { '' }

$logsDir    = Join-Path $workdir 'logs'
$stdoutLog  = Join-Path $logsDir 'siteowlqa.stdout.log'
$stderrLog  = Join-Path $logsDir 'siteowlqa.stderr.log'
$pidFile    = Join-Path $logsDir 'siteowlqa.pid'
$mainScript = Join-Path $workdir 'main.py'

if (-not $python) {
    Write-Error "No compatible Python interpreter found (missing required module: requests). Tried: $($candidates -join ', ')"
    exit 1
}

$mainScriptWildcard = ('*' + $mainScript.Replace('\\', '\\\\') + '*')
$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(\.exe)?$' -and (
        $_.CommandLine -like $mainScriptWildcard -or
        $_.CommandLine -match '(^|\s)main\.py(\s|$)'
    )
}

if ($existing) {
    Write-Output 'ALREADY_RUNNING'
    exit 0
}

# Set PYTHONIOENCODING so em-dashes and other Unicode chars survive the
# stdout redirect into the log file (Windows default is cp1252 otherwise).
$env:PYTHONIOENCODING = 'utf-8'

$process = Start-Process -FilePath $python `
    -ArgumentList '-u', $mainScript `
    -WorkingDirectory $workdir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

Start-Sleep -Milliseconds 800
if ($process.HasExited) {
    Write-Error "SiteOwlQA failed to start. ExitCode=$($process.ExitCode). Check logs: $stderrLog"
    exit 1
}

Set-Content -Path $pidFile -Value $process.Id
Write-Output 'STARTED'
exit 0
