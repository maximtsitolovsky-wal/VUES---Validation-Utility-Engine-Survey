@echo off
REM SiteOwlQA Launcher
REM Starts the pipeline in background, then opens the localhost dashboard.
REM When already running: just opens the dashboard.

setlocal enabledelayedexpansion

REM ── Config ─────────────────────────────────────────────────────────────────
for %%I in ("%~dp0..\..") do set WORKDIR=%%~fI

set DASHBOARD_URL=http://127.0.0.1:8765/executive_dashboard.html
set LOGDIR=%WORKDIR%\logs
set STDOUT_LOG=%LOGDIR%\siteowlqa.stdout.log
set STDERR_LOG=%LOGDIR%\siteowlqa.stderr.log
set OUTPUT_DIR=%WORKDIR%\output

REM ── Python selection (venv first, then PATH) ────────────────────────────────
set PYTHON=
if exist "%WORKDIR%\.venv\Scripts\python.exe" (
  "%WORKDIR%\.venv\Scripts\python.exe" -c "import requests" >nul 2>nul
  if !errorlevel! equ 0 set PYTHON=%WORKDIR%\.venv\Scripts\python.exe
)
if not defined PYTHON (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    "%%P" -c "import requests" >nul 2>nul
    if !errorlevel! equ 0 (
      set PYTHON=%%P
      goto :python_found
    )
  )
)
:python_found

if not exist "%PYTHON%" (
  echo [ERROR] No compatible Python found. Install dependencies first.
  pause
  exit /b 1
)

REM ── Create required dirs ────────────────────────────────────────────────────
if not exist "%LOGDIR%"     mkdir "%LOGDIR%"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM ── Change to project root ──────────────────────────────────────────────────
cd /d "%WORKDIR%"
if !errorlevel! neq 0 (
  echo [ERROR] Cannot cd to %WORKDIR%
  pause
  exit /b 1
)

REM ── Check if pipeline is already running ────────────────────────────────────
wmic process where "name='python.exe' and commandline like '%%main.py%%' and commandline like '%%%WORKDIR:\=\\%%%'" get ProcessId /value 2>nul | find "=" >nul
if !errorlevel! equ 0 (
  echo [INFO] SiteOwlQA is already running.
  echo [INFO] Opening dashboard: %DASHBOARD_URL%
  start "" "%DASHBOARD_URL%"
  exit /b 0
)

REM ── Start the pipeline ──────────────────────────────────────────────────────
echo [INFO] Starting SiteOwlQA pipeline...
echo [INFO] Python : %PYTHON%
echo [INFO] Logs   : %STDOUT_LOG%
echo [INFO] Dashboard will open automatically at %DASHBOARD_URL%
echo.

REM PYTHONIOENCODING=utf-8 ensures em-dashes and other Unicode
REM characters are written correctly to the redirected log files.
set PYTHONIOENCODING=utf-8

start "SiteOwlQA Pipeline" /b "%PYTHON%" -u main.py >>"%STDOUT_LOG%" 2>>"%STDERR_LOG%"

REM main.py opens the dashboard in the browser automatically once the
REM first metrics refresh completes (~5-30 s). No need to race it here.
echo [INFO] Pipeline started. Dashboard will open in your browser shortly.
echo [INFO] To stop: run stop_pipeline.bat

exit /b 0
