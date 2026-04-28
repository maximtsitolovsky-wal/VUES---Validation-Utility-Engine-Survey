@echo off
setlocal EnableDelayedExpansion
title VUES Dashboard
cd /d "%~dp0"

:: Determine which Python to use
set PYTHON=
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    where python >nul 2>nul
    if !ERRORLEVEL! equ 0 (
        set PYTHON=python
    )
)

:: Check if we found Python
if "!PYTHON!"=="" (
    echo.
    echo  ============================================
    echo   ERROR: Python not found!
    echo  ============================================
    echo.
    echo   Please run INSTALL.bat first
    echo   OR install Python from Microsoft Store
    echo.
    pause
    exit /b 1
)

:: Check if serve_dashboard.py exists
if not exist "tools\serve_dashboard.py" (
    echo.
    echo  ============================================
    echo   ERROR: Dashboard files not found!
    echo  ============================================
    echo.
    echo   Make sure you extracted the full ZIP file.
    echo   The "tools" folder should exist.
    echo.
    pause
    exit /b 1
)

:: Run the dashboard (this will open the browser)
echo.
echo  Starting VUES Dashboard...
echo  (Browser will open automatically)
echo.
echo  Keep this window open while using the dashboard.
echo  Press Ctrl+C to stop the server.
echo.

"!PYTHON!" tools\serve_dashboard.py

:: If we get here, server stopped or errored
if %ERRORLEVEL% neq 0 (
    echo.
    echo  ============================================
    echo   Dashboard stopped or encountered an error
    echo  ============================================
    echo.
    echo   If the browser didn't open, try:
    echo   1. Run INSTALL.bat first
    echo   2. Make sure Python is installed
    echo.
    pause
)
