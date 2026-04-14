@echo off
setlocal enabledelayedexpansion

set WORKDIR=C:\SiteOwlQA_App
set PORT_FILE=%WORKDIR%\output\dashboard.port
set FALLBACK_PORT=8765
set PYTHON=%WORKDIR%\.venv\Scripts\python.exe
set LOGDIR=%WORKDIR%\logs
set STDOUT_LOG=%LOGDIR%\siteowlqa.stdout.log
set STDERR_LOG=%LOGDIR%\siteowlqa.stderr.log

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
