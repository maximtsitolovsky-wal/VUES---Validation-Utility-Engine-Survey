@echo off
REM ============================================================
REM  VUES Data Watchdog - Daily Health Check
REM  Schedule via Task Scheduler to run daily at 6 AM
REM ============================================================

setlocal EnableDelayedExpansion

for %%I in ("%~dp0..\..") do set WORKDIR=%%~fI
cd /d "%WORKDIR%"

set LOGDIR=%WORKDIR%\logs
set LOGFILE=%LOGDIR%\watchdog_%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%.log

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

if exist "%WORKDIR%\.venv\Scripts\python.exe" (
    set PYTHON=%WORKDIR%\.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo ============================================================ >> "%LOGFILE%"
echo WATCHDOG RUN: %DATE% %TIME% >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"

"%PYTHON%" scripts/data_watchdog.py >> "%LOGFILE%" 2>&1
set EXITCODE=%errorlevel%

if %EXITCODE% neq 0 (
    echo [CRITICAL] Watchdog found issues - check %LOGFILE%
    exit /b %EXITCODE%
)

echo [OK] Watchdog completed successfully
exit /b 0
