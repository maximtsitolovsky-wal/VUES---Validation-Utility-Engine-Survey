@echo off
REM ============================================================
REM  run_scout_downloader.bat
REM  Wrapper called by Windows Task Scheduler.
REM  Runs Mon-Fri at 10:00 AM and 3:00 PM.
REM  Downloads Scout Airtable images to OneDrive via Walmart proxy.
REM ============================================================

set APP_DIR=C:\SiteOwlQA_App
set SCRIPT=%APP_DIR%\scripts\scout_downloader.py
set LOG_DIR=%APP_DIR%\logs
set LOG=%LOG_DIR%\scout_task.log

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [%DATE% %TIME%] Scout Downloader triggered by Task Scheduler >> "%LOG%"

cd /d "%APP_DIR%"
python -u "%SCRIPT%" >> "%LOG%" 2>&1

echo [%DATE% %TIME%] Scout Downloader finished. Exit: %ERRORLEVEL% >> "%LOG%"
