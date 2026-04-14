@echo off
setlocal enabledelayedexpansion

REM =========================================================================
REM  SiteOwlQA — Master Launcher
REM  Starts every component of the platform as a standalone process:
REM    1. System Bottleneck Auditor  (background, no browser)
REM    2. Docker Platform Engineer   (background, no browser)
REM    3. Specialist Output Validator (background, 90s delayed start)
REM    4. SiteOwlQA Pipeline         (background, logs to logs/)
REM    5. Opens dashboard in browser (waits for port file)
REM =========================================================================

REM --- resolve repo root from script location (works from any clone path) ---
for %%I in ("%~dp0..\..") do set WORKDIR=%%~fI

REM --- resolve Python (venv first, then PATH) --------------------------------
if exist "%WORKDIR%\.venv\Scripts\python.exe" (
  set PYTHON=%WORKDIR%\.venv\Scripts\python.exe
) else (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    set PYTHON=%%P
    goto :python_found
  )
  echo [ERROR] Python not found. Install Python 3.11+ or create .venv.
  pause
  exit /b 1
)
:python_found

REM --- paths -----------------------------------------------------------------
set LOGDIR=%WORKDIR%\logs
set PORT_FILE=%WORKDIR%\output\dashboard.port
set FALLBACK_PORT=8765
set STDOUT_LOG=%LOGDIR%\siteowlqa.stdout.log
set STDERR_LOG=%LOGDIR%\siteowlqa.stderr.log
set AUDIT_LOG=%LOGDIR%\bottleneck_audit.log
set DOCKER_LOG=%LOGDIR%\docker_platform.log
set VALIDATOR_LOG=%LOGDIR%\specialist_validator.log

if not exist "%LOGDIR%"          mkdir "%LOGDIR%"
if not exist "%WORKDIR%\output"  mkdir "%WORKDIR%\output"
cd /d "%WORKDIR%"
set PYTHONIOENCODING=utf-8

echo.
echo  =========================================
echo    SiteOwlQA Platform Launcher
echo  =========================================
echo.

REM --- check if pipeline is already running ---------------------------------
wmic process where "name='python.exe' and commandline like '%%main.py%%'" get ProcessId /value 2>nul | find "=" >nul
if !errorlevel! equ 0 (
  echo [INFO] Pipeline already running. Opening dashboard ...
  goto :open_browser
)

REM =========================================================================
REM  1. System Bottleneck Auditor — fire and forget, writes to logs/
REM =========================================================================
if exist "%WORKDIR%\tools\system_bottleneck_auditor.py" (
  echo [START] System Bottleneck Auditor ...
  start "SiteOwlQA-BottleneckAudit" /b cmd /c ^
    ""%PYTHON%" -u "%WORKDIR%\tools\system_bottleneck_auditor.py" --no-browser >> "%AUDIT_LOG%" 2>&1"
) else (
  echo [SKIP]  system_bottleneck_auditor.py not found
)

REM =========================================================================
REM  2. Docker Platform Engineer — fire and forget, writes to logs/
REM =========================================================================
if exist "%WORKDIR%\tools\docker_platform_engineer.py" (
  echo [START] Docker Platform Engineer ...
  start "SiteOwlQA-DockerPlatform" /b cmd /c ^
    ""%PYTHON%" -u "%WORKDIR%\tools\docker_platform_engineer.py" --no-browser >> "%DOCKER_LOG%" 2>&1"
) else (
  echo [SKIP]  docker_platform_engineer.py not found
)

REM =========================================================================
REM  3. Specialist Output Validator — waits 90s so tools above finish first
REM =========================================================================
if exist "%WORKDIR%\tools\specialist_output_validator.py" (
  echo [START] Specialist Output Validator (90s delayed start) ...
  start "SiteOwlQA-Validator" /b cmd /c ^
    "timeout /t 90 /nobreak >nul && "%PYTHON%" -u "%WORKDIR%\tools\specialist_output_validator.py" --no-browser >> "%VALIDATOR_LOG%" 2>&1"
) else (
  echo [SKIP]  specialist_output_validator.py not found
)

REM =========================================================================
REM  4. SiteOwlQA Pipeline — background, logs to logs/siteowlqa.*.log
REM =========================================================================
echo [START] SiteOwlQA Pipeline ...
start "SiteOwlQA" /b "%PYTHON%" -u main.py >>"%STDOUT_LOG%" 2>>"%STDERR_LOG%"

echo.
echo [INFO] All components started. Waiting for dashboard ...
echo [INFO] Logs:
echo         Pipeline  : %STDOUT_LOG%
echo         Audit     : %AUDIT_LOG%
echo         Docker    : %DOCKER_LOG%
echo         Validator : %VALIDATOR_LOG% (starts after 90s)
echo.

REM =========================================================================
REM  4. Wait for port file then open browser (up to 30s)
REM =========================================================================
set /a WAITED=0
:wait
if exist "%PORT_FILE%" goto :open_browser
if !WAITED! geq 30 goto :open_browser
timeout /t 1 /nobreak >nul
set /a WAITED+=1
goto :wait

:open_browser
set PORT=%FALLBACK_PORT%
if exist "%PORT_FILE%" (
  set /p PORT=<"%PORT_FILE%"
  set PORT=!PORT: =!
)
set DASHBOARD_URL=http://127.0.0.1:!PORT!/executive_dashboard.html
echo [INFO] Opening: !DASHBOARD_URL!
start "" "!DASHBOARD_URL!"
exit /b 0
