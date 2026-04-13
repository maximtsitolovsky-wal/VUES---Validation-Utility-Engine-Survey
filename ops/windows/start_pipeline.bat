@echo off
REM SiteOwlQA Dashboard Launcher
REM Starts the pipeline in background and opens the dashboard in browser
REM This is the user-friendly launcher for daily use

setlocal enabledelayedexpansion

REM Configuration
set WORKDIR=C:\SiteOwlQA_App
REM Prefer project venv; fall back to system Python 3.14 if venv not present
if exist "%WORKDIR%\.venv\Scripts\python.exe" (
  set PYTHON=%WORKDIR%\.venv\Scripts\python.exe
) else (
  set PYTHON=C:\Python314\python.exe
)
set LOGDIR=%WORKDIR%\logs
set STDOUT_LOG=%LOGDIR%\siteowlqa.stdout.log
set STDERR_LOG=%LOGDIR%\siteowlqa.stderr.log
set PIDFILE=%LOGDIR%\siteowlqa.pid
set OUTPUT_DIR=%WORKDIR%\output
set DASHBOARD_FILE=%OUTPUT_DIR%\executive_dashboard.html

REM Validate Python
if not exist "%PYTHON%" (
  echo [ERROR] Python not found at %PYTHON%
  exit /b 1
)

REM Create directories
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM Change to project directory
cd /d "%WORKDIR%"
if !errorlevel! neq 0 (
  echo [ERROR] Failed to change to %WORKDIR%
  exit /b 1
)

REM Check if already running (look for python process with main.py)
for /f "tokens=2" %%A in ('tasklist /fi "imagename eq python.exe" /fo table ^| findstr python') do (
  echo [INFO] Pipeline appears to be running already (PID: %%A)
  echo [INFO] Opening dashboard in browser...
  timeout /t 2 /nobreak
  if exist "%DASHBOARD_FILE%" (
    start "" "%DASHBOARD_FILE%"
  ) else (
    echo [WARN] Dashboard file not found yet at %DASHBOARD_FILE%
    echo [INFO] Dashboard will be generated once the first submission is processed.
  )
  exit /b 0
)

REM Start the pipeline in background
echo [INFO] Starting SiteOwlQA pipeline in background...
echo [INFO] Log output: %STDOUT_LOG%
echo.

start "SiteOwlQA Pipeline" /b "%PYTHON%" -u main.py >>"!STDOUT_LOG!" 2>>"!STDERR_LOG!"

REM Give it a moment to start
timeout /t 3 /nobreak

REM Wait for dashboard to be generated
echo [INFO] Waiting for dashboard to be generated...
for /L %%N in (1,1,30) do (
  if exist "%DASHBOARD_FILE%" (
    echo [INFO] Dashboard ready! Opening in browser...
    start "" "%DASHBOARD_FILE%"
    echo [INFO] Pipeline is running. Check logs at:
    echo   %STDOUT_LOG%
    exit /b 0
  )
  timeout /t 1 /nobreak
)

echo [WARN] Dashboard not generated within 30 seconds.
  echo [INFO] Pipeline is starting. Dashboard will be generated after the first submission.
  echo [INFO] Check logs at: %STDOUT_LOG%

exit /b 0
