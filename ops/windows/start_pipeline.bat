@echo off
setlocal enabledelayedexpansion

REM Resolve repo root relative to this script so clones work anywhere
for %%I in ("%~dp0..\..") do set WORKDIR=%%~fI

set PORT_FILE=%WORKDIR%\output\dashboard.port
set FALLBACK_PORT=8765
set LOGDIR=%WORKDIR%\logs
set STDOUT_LOG=%LOGDIR%\siteowlqa.stdout.log
set STDERR_LOG=%LOGDIR%\siteowlqa.stderr.log

REM Prefer project venv; otherwise fall back to Python on PATH
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

if not exist "%LOGDIR%"         mkdir "%LOGDIR%"
if not exist "%WORKDIR%\output" mkdir "%WORKDIR%\output"
cd /d "%WORKDIR%"

REM Read port file if present
set PORT=%FALLBACK_PORT%
if exist "%PORT_FILE%" (
  set /p PORT=<"%PORT_FILE%"
  set PORT=!PORT: =!
)
set DASHBOARD_URL=http://127.0.0.1:!PORT!/executive_dashboard.html

REM If pipeline already running just open browser
wmic process where "name='python.exe' and commandline like '%%main.py%%'" get ProcessId /value 2>nul | find "=" >nul
if !errorlevel! equ 0 (
  start "" "!DASHBOARD_URL!"
  exit /b 0
)

REM Not running -- start it
set PYTHONIOENCODING=utf-8
start "SiteOwlQA" /b "%PYTHON%" -u main.py >>"%STDOUT_LOG%" 2>>"%STDERR_LOG%"

REM Wait up to 25s for port file then open browser
set /a WAITED=0
:wait
if exist "%PORT_FILE%" goto :open
if !WAITED! geq 25 goto :open
timeout /t 1 /nobreak >nul
set /a WAITED+=1
goto :wait

:open
if exist "%PORT_FILE%" (
  set /p PORT=<"%PORT_FILE%"
  set PORT=!PORT: =!
  set DASHBOARD_URL=http://127.0.0.1:!PORT!/executive_dashboard.html
)
start "" "!DASHBOARD_URL!"
exit /b 0
