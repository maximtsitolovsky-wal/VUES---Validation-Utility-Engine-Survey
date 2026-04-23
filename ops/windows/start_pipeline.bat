@echo off
setlocal enabledelayedexpansion

REM =========================================================================
REM  vues — Master Launcher
REM  Starts every component of the platform as a standalone process:
REM    1. System Bottleneck Auditor  (background, no browser)
REM    1.5. Git Autopush             (visible window, auto-commits changes)
REM    2. Docker Platform Engineer   (background, no browser)
REM    3. Specialist Output Validator (background, 90s delayed start)
REM    4. vues Pipeline         (background, logs to logs/)
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
set STDOUT_LOG=%LOGDIR%\vues.stdout.log
set STDERR_LOG=%LOGDIR%\vues.stderr.log
set AUDIT_LOG=%LOGDIR%\bottleneck_audit.log
set DOCKER_LOG=%LOGDIR%\docker_platform.log
set VALIDATOR_LOG=%LOGDIR%\specialist_validator.log
set AUTOPUSH_LOG=%LOGDIR%\git_autopush.log

if not exist "%LOGDIR%"          mkdir "%LOGDIR%"
if not exist "%WORKDIR%\output"  mkdir "%WORKDIR%\output"
cd /d "%WORKDIR%"
set PYTHONIOENCODING=utf-8

echo.
echo  =========================================
echo    vues Platform Launcher
echo  =========================================
echo.

REM --- Pre-flight dependency check ------------------------------------------
echo [CHECK] Running pre-flight validation...
"%PYTHON%" -c "import sys; sys.path.insert(0,'src'); import pyairtable, pandas, openpyxl, google.cloud.bigquery, requests; from siteowlqa.config import load_config; from siteowlqa.airtable_client import AirtableClient; print('[OK] Dependencies verified')" 2>nul
if errorlevel 1 (
    echo [FAIL] Missing dependencies! Run:
    echo        cd C:\VUES ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

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
  start "vues-BottleneckAudit" /b cmd /c ^
    ""%PYTHON%" -u "%WORKDIR%\tools\system_bottleneck_auditor.py" --no-browser >> "%AUDIT_LOG%" 2>&1"
) else (
  echo [SKIP]  system_bottleneck_auditor.py not found
)

REM =========================================================================
REM  1.5. Git Autopush — watches for changes and auto-commits (optional)
REM =========================================================================
if exist "%WORKDIR%\scripts\git_autopush.py" (
  echo [START] Git Autopush (auto-commit watcher) ...
  start "git-autopush" cmd /c ^
    ""%PYTHON%" -u "%WORKDIR%\scripts\git_autopush.py" >> "%AUTOPUSH_LOG%" 2>&1"
) else (
  echo [SKIP]  git_autopush.py not found
)

REM =========================================================================
REM  2. Docker Platform Engineer — fire and forget, writes to logs/
REM =========================================================================
if exist "%WORKDIR%\tools\docker_platform_engineer.py" (
  echo [START] Docker Platform Engineer ...
  start "vues-DockerPlatform" /b cmd /c ^
    ""%PYTHON%" -u "%WORKDIR%\tools\docker_platform_engineer.py" --no-browser >> "%DOCKER_LOG%" 2>&1"
) else (
  echo [SKIP]  docker_platform_engineer.py not found
)

REM =========================================================================
REM  3. Specialist Output Validator — waits 90s so tools above finish first
REM =========================================================================
if exist "%WORKDIR%\tools\specialist_output_validator.py" (
  echo [START] Specialist Output Validator (90s delayed start) ...
  start "vues-Validator" /b cmd /c ^
    "timeout /t 90 /nobreak >nul && "%PYTHON%" -u "%WORKDIR%\tools\specialist_output_validator.py" --no-browser >> "%VALIDATOR_LOG%" 2>&1"
) else (
  echo [SKIP]  specialist_output_validator.py not found
)

REM =========================================================================
REM  4. vues Pipeline — background, logs to logs/vues.*.log
REM =========================================================================
echo [START] vues Pipeline ...
start "vues" /b "%PYTHON%" -u main.py >>"%STDOUT_LOG%" 2>>"%STDERR_LOG%"

echo.
echo [INFO] All components started. Waiting for dashboard ...
echo [INFO] Logs:
echo         Pipeline  : %STDOUT_LOG%
echo         Audit     : %AUDIT_LOG%
echo         Docker    : %DOCKER_LOG%
echo         Validator : %VALIDATOR_LOG% (starts after 90s)
echo         Autopush  : %AUTOPUSH_LOG%
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
