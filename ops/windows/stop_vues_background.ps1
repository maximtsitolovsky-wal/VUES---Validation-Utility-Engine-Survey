$ErrorActionPreference = 'SilentlyContinue'

$pidFile = 'C:\SiteOwlQA_App\logs\siteowlqa.pid'

if (Test-Path $pidFile) {
    $appPid = (Get-Content $pidFile | Select-Object -First 1).Trim()
    if ($appPid) {
        Stop-Process -Id ([int]$appPid) -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(\.exe)?$' -and (
        $_.CommandLine -like '*C:\SiteOwlQA_App\main.py*' -or
        $_.CommandLine -match '(^|\s)main\.py(\s|$)'
    )
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Output 'STOPPED'
exit 0
