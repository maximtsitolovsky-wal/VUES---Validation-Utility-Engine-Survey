$ErrorActionPreference = 'Stop'

$workdir    = 'C:\SiteOwlQA_App'
# Prefer project venv; fall back to system Python 3.14
$venvPython   = Join-Path $workdir '.venv\Scripts\python.exe'
$systemPython = 'C:\Python314\python.exe'
$python = if (Test-Path $venvPython) { $venvPython } else { $systemPython }

$stdoutLog  = 'C:\SiteOwlQA_App\logs\siteowlqa.stdout.log'
$stderrLog  = 'C:\SiteOwlQA_App\logs\siteowlqa.stderr.log'
$pidFile    = 'C:\SiteOwlQA_App\logs\siteowlqa.pid'
$mainScript = 'C:\SiteOwlQA_App\main.py'

if (-not (Test-Path $python)) {
    Write-Error "Python not found at $python"
    exit 1
}

$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(\.exe)?$' -and (
        $_.CommandLine -like '*C:\SiteOwlQA_App\main.py*' -or
        $_.CommandLine -match '(^|\s)main\.py(\s|$)'
    )
}

if ($existing) {
    Write-Output 'ALREADY_RUNNING'
    exit 0
}

$process = Start-Process -FilePath $python `
    -ArgumentList '-u', $mainScript `
    -WorkingDirectory $workdir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

Set-Content -Path $pidFile -Value $process.Id
Write-Output 'STARTED'
exit 0
