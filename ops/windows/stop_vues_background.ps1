$ErrorActionPreference = 'SilentlyContinue'

# Dynamically resolve paths from script location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$workDir = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
$pidFile = Join-Path $workDir 'logs\vues.pid'

if (Test-Path $pidFile) {
    $appPid = (Get-Content $pidFile | Select-Object -First 1).Trim()
    if ($appPid) {
        Stop-Process -Id ([int]$appPid) -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(\.exe)?$' -and (
        $mainPy = Join-Path $workDir 'main.py'
        $_.CommandLine -like "*$mainPy*" -or
        $_.CommandLine -match '(^|\s)main\.py(\s|$)'
    )
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Output 'STOPPED'
exit 0
