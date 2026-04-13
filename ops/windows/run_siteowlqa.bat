@echo off
REM SiteOwlQA Pipeline Launcher
REM Runs the automated vendor QA pipeline in the background
REM Can be scheduled via Windows Task Scheduler or run manually

setlocal enabledelayedexpansion

REM Configuration
set WORKDIR=C:\SiteOwlQA_App
REM Prefer the project venv; fall back to system Python 3.14 if it doesn't exist
if exist "%WORKDIR%\.venv\Scripts\python.exe" (
  set PYTHON=%WORKDIR%\.venv\Scripts\python.exe
) else (
  set PYTHON=C:\Python314\python.exe
)
set LOGDIR=%WORKDIR%\logs
set STDOUT_LOG=%LOGDIR%\siteowlqa.stdout.log
set STDERR_LOG=%LOGDIR%\siteowlqa.stderr.log
set PIDFILE=%LOGDIR%\siteowlqa.pid

REM Validate Python installation
if not exist "%PYTHON%" (
  echo [ERROR] Python not found at %PYTHON%
  echo Please update the PYTHON path in this script to match your installation.
  echo You can find Python with: where python
  exit /b 1
)

REM Create log directory if it doesn't exist
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM Check if already running
for /f "tokens=*" %%A in ('tasklist ^| findstr /i "python.exe"') do (
  REM Simple check: if python is running and main.py exists, assume we're running
  if exist "%WORKDIR%\main.py" (
    REM Could add more sophisticated PID checking here
  )
)

REM Change to project directory
cd /d "%WORKDIR%"
if !errorlevel! neq 0 (
  echo [ERROR] Failed to change directory to %WORKDIR%
  exit /b 1
)

REM Run the pipeline
echo [INFO] Starting SiteOwlQA pipeline...
echo [INFO] Workdir: %WORKDIR%
echo [INFO] Log: %STDOUT_LOG%
echo.

"%PYTHON%" -u main.py >>"!STDOUT_LOG!" 2>>"!STDERR_LOG!"
set EXITCODE=!errorlevel!

if not "!EXITCODE!"=="0" (
  echo [ERROR] SiteOwlQA exited with code !EXITCODE!
  echo [ERROR] Check logs at:
  echo   - Stdout: %STDOUT_LOG%
  echo   - Stderr: %STDERR_LOG%
  exit /b !EXITCODE!
)

exit /b 0
