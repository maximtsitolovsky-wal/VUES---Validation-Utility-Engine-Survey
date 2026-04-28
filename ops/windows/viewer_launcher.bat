@echo off
title VUES Viewer
cd /d "%~dp0..\.."

echo.
echo  ============================================
echo   VUES Dashboard Viewer
echo  ============================================
echo.

:: Check if Python exists
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Opening HTML directly...
    start "" "ui\index.html"
    goto :end
)

:: Check for venv
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

:: Find available port
set PORT=8765

echo [INFO] Starting local server on port %PORT%...
echo [INFO] Press Ctrl+C to stop
echo.

:: Start simple server and open browser
start "" "http://127.0.0.1:%PORT%/index.html"
%PYTHON% -m http.server %PORT% --directory ui

:end
pause
