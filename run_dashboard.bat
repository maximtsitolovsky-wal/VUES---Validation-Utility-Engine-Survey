@echo off
title VUES Dashboard
echo.
echo  ========================================
echo   VUES Dashboard - Starting...
echo  ========================================
echo.

cd /d "%~dp0"

:: Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Python not found!
    echo.
    echo  Please install Python from Software Center
    echo  or Microsoft Store (search "Python 3.11")
    echo.
    pause
    exit /b 1
)

:: Check if serve_dashboard.py exists
if not exist "tools\serve_dashboard.py" (
    echo  [ERROR] serve_dashboard.py not found!
    echo.
    echo  Make sure you extracted the ZIP completely.
    echo.
    pause
    exit /b 1
)

echo  Starting dashboard server...
echo.
python tools\serve_dashboard.py

:: If we get here, something went wrong
echo.
echo  [ERROR] Dashboard failed to start.
echo  Check that Python is installed correctly.
echo.
pause
