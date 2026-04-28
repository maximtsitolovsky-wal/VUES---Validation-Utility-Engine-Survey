@echo off
title VUES Dashboard - First Time Setup
color 0A
echo.
echo  ==========================================
echo   VUES Dashboard - First Time Setup
echo  ==========================================
echo.
echo  This will set up VUES Dashboard on your computer.
echo.

cd /d "%~dp0"

:: Check Python
echo  [1/4] Checking Python...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo.
    echo  ============================================
    echo   ERROR: Python is not installed!
    echo  ============================================
    echo.
    echo   To install Python:
    echo.
    echo   1. Open Microsoft Store (search in Start menu)
    echo   2. Search for "Python 3.11"
    echo   3. Click "Get" or "Install"
    echo   4. Wait for installation
    echo   5. Run this script again
    echo.
    echo   OR install from Software Center:
    echo   Search for "Python" and install
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo        Found: %PYVER%

:: Check if venv exists, create if not
echo.
echo  [2/4] Setting up virtual environment...
if not exist ".venv\Scripts\python.exe" (
    echo        Creating .venv...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo        [WARN] Could not create venv, using system Python
    ) else (
        echo        Created .venv successfully
    )
) else (
    echo        .venv already exists
)

:: Install dependencies
echo.
echo  [3/4] Installing dependencies...
if exist ".venv\Scripts\pip.exe" (
    .venv\Scripts\pip install --quiet --disable-pip-version-check -r requirements.txt 2>nul
    if %ERRORLEVEL% neq 0 (
        echo        [WARN] Some dependencies may be missing
    ) else (
        echo        Dependencies installed
    )
) else (
    python -m pip install --quiet --disable-pip-version-check -r requirements.txt 2>nul
    echo        Dependencies installed (system Python)
)

:: Create desktop shortcut
echo.
echo  [4/4] Creating desktop shortcut...
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT_NAME=VUES Dashboard.lnk
set SCRIPT_DIR=%~dp0

:: Use PowerShell to create shortcut
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\%SHORTCUT_NAME%'); $s.TargetPath = '%SCRIPT_DIR%run_dashboard.bat'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = '%SCRIPT_DIR%assets\vues_icon.ico'; $s.Description = 'VUES Dashboard'; $s.Save()" 2>nul

if exist "%DESKTOP%\%SHORTCUT_NAME%" (
    echo        Shortcut created on Desktop!
) else (
    echo        [WARN] Could not create shortcut
    echo        You can run "run_dashboard.bat" directly
)

echo.
echo  ==========================================
echo   Setup Complete!
echo  ==========================================
echo.
echo   To start the dashboard:
echo.
echo   - Double-click "VUES Dashboard" on your Desktop
echo   - OR double-click "run_dashboard.bat" in this folder
echo.
echo   Press any key to launch the dashboard now...
pause >nul

:: Launch the dashboard
call "%~dp0run_dashboard.bat"
