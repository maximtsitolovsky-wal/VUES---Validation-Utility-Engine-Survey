@echo off
REM Register Scout Completion Sync Task
REM Must run as Administrator

echo === Scout Completion Sync Task Registration ===
echo.
echo This will create a scheduled task to sync Airtable completion
echo status to Excel at 10 AM and 3 PM Monday-Friday.
echo.
echo Checking admin rights...

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Please run as Administrator!
    echo Right-click and select "Run as Administrator"
    pause
    exit /b 1
)

echo [OK] Running as Administrator
echo.

powershell.exe -ExecutionPolicy Bypass -File "%~dp0register_scout_completion_sync_task.ps1"

pause
