@echo off
echo.
echo ═══════════════════════════════════════════════════════════
echo   SCOUT TASK FIX - DOUBLE-CLICK LAUNCHER
echo ═══════════════════════════════════════════════════════════
echo.
echo This will fix your Scout scheduled tasks so they run flawlessly.
echo.
echo IMPORTANT: This requires Administrator privileges!
echo.
echo If you see "Access Denied" errors, you need to:
echo   1. Right-click this file
echo   2. Select "Run as administrator"
echo.
pause

REM Try to run with admin rights
powershell -Command "Start-Process PowerShell -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -File ""%~dp0fix_scout_tasks_bulletproof.ps1""'"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to launch with admin rights!
    echo.
    echo Please try again by right-clicking this file and selecting
    echo "Run as administrator"
    echo.
    pause
)
