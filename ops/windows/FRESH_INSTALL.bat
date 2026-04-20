@echo off
REM ============================================================
REM  VUES Fresh Install Script
REM  One-click setup for a new machine
REM  
REM  Usage: Right-click -> Run as Administrator (first time)
REM         Or just double-click if Python already installed
REM ============================================================

setlocal EnableDelayedExpansion
title VUES Fresh Install

echo.
echo  ============================================================
echo   VUES - Validation Utility Engine Survey
echo   Fresh Install Script
echo  ============================================================
echo.

REM Check if we're already in C:\VUES or need to clone
if exist "C:\VUES\main.py" (
    echo [OK] VUES already cloned at C:\VUES
    cd /d C:\VUES
) else (
    echo [1/5] Cloning VUES repository...
    
    REM Check if git is available
    where git >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [ERROR] Git is not installed!
        echo         Install Git for Windows from: https://git-scm.com/download/win
        echo         Or via winget: winget install Git.Git
        echo.
        pause
        exit /b 1
    )
    
    git clone https://gecgithub01.walmart.com/vn59j7j/VUES---Validation-Utility-Engine-Survey C:\VUES
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to clone repository!
        echo         Make sure you're on Walmart VPN or Eagle WiFi.
        echo.
        pause
        exit /b 1
    )
    cd /d C:\VUES
    echo [OK] Repository cloned to C:\VUES
)

echo.
echo [2/5] Checking Python installation...

REM Try to find Python
set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :python_found
)

if exist "C:\Python314\python.exe" (
    set "PYTHON_CMD=C:\Python314\python.exe"
    goto :python_found
)

if exist "C:\Python312\python.exe" (
    set "PYTHON_CMD=C:\Python312\python.exe"
    goto :python_found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :python_found
)

REM Python not found - try to install
echo [WARN] Python not found. Attempting to install...

REM Try winget first
where winget >nul 2>&1
if not errorlevel 1 (
    echo Installing Python via winget...
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 (
        echo [OK] Python installed via winget
        echo [INFO] Please restart this script to continue setup.
        pause
        exit /b 0
    )
)

echo.
echo [ERROR] Could not auto-install Python.
echo         Please install Python 3.12+ manually:
echo         1. Download from: https://www.python.org/downloads/
echo         2. Run installer WITH "Add Python to PATH" checked
echo         3. Re-run this script
echo.
pause
exit /b 1

:python_found
echo [OK] Found Python: %PYTHON_CMD%
%PYTHON_CMD% --version

echo.
echo [3/5] Installing Python dependencies...

REM Upgrade pip first
%PYTHON_CMD% -m pip install --upgrade pip --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple --trusted-host pypi.ci.artifacts.walmart.com >nul 2>&1

REM Install requirements
%PYTHON_CMD% -m pip install -r requirements.txt --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple --trusted-host pypi.ci.artifacts.walmart.com
if errorlevel 1 (
    echo [WARN] Some packages may have failed. Continuing...
)

REM Install watchdog for git autopush
%PYTHON_CMD% -m pip install watchdog --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple --trusted-host pypi.ci.artifacts.walmart.com
echo [OK] Dependencies installed

echo.
echo [4/5] Creating desktop shortcuts...

REM Create the main launcher shortcut
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$desktop = [Environment]::GetFolderPath('Desktop'); ^
     $sh = New-Object -ComObject WScript.Shell; ^
     $lnk = $sh.CreateShortcut(\"$desktop\SiteOwlQA Launcher.lnk\"); ^
     $lnk.TargetPath = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'; ^
     $lnk.Arguments = '-ExecutionPolicy Bypass -WindowStyle Hidden -File \"C:\VUES\ops\windows\launch_vues_dashboard.ps1\"'; ^
     $lnk.WorkingDirectory = 'C:\VUES'; ^
     $lnk.IconLocation = 'C:\VUES\VUES.exe,0'; ^
     $lnk.Description = 'VUES - starts pipeline and opens dashboard'; ^
     $lnk.Save(); ^
     Write-Host '[OK] Created: SiteOwlQA Launcher.lnk'"

REM Create the fix scout tasks shortcut
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$desktop = [Environment]::GetFolderPath('Desktop'); ^
     $sh = New-Object -ComObject WScript.Shell; ^
     $lnk = $sh.CreateShortcut(\"$desktop\FIX SCOUT TASKS.lnk\"); ^
     $lnk.TargetPath = 'C:\VUES\ops\windows\FIX_SCOUT_TASKS.bat'; ^
     $lnk.WorkingDirectory = 'C:\VUES\ops\windows'; ^
     $lnk.IconLocation = 'shell32.dll,21'; ^
     $lnk.Description = 'Fix Scout scheduled tasks (requires admin)'; ^
     $lnk.Save(); ^
     Write-Host '[OK] Created: FIX SCOUT TASKS.lnk'"

echo.
echo [5/5] Setting up credentials...

REM Create .env.local with team credentials (read-only access)
echo # VUES Team Credentials - Auto-generated by FRESH_INSTALL.bat > C:\VUES\.env.local
echo # Scout Airtable credentials for scheduled tasks >> C:\VUES\.env.local
echo SCOUT_AIRTABLE_API_KEY=patPR0WWxXCE0loRO.d18126548ad25b8aaf9fd43e2ac69479b1378e46d7f8c6efbdd88f7197a4d495 >> C:\VUES\.env.local
echo SCOUT_AIRTABLE_BASE_ID=appAwgaX89x0JxG3Z >> C:\VUES\.env.local
echo SCOUT_AIRTABLE_TABLE_ID=tblC4o9AvVulyxFMk >> C:\VUES\.env.local
echo [OK] Credentials configured

echo.
echo  ============================================================
echo   SETUP COMPLETE!
echo  ============================================================
echo.
echo   Desktop shortcuts created:
echo     - SiteOwlQA Launcher (main app)
echo     - FIX SCOUT TASKS (admin tool)
echo.
echo   Credentials: Auto-configured (using team access)
echo.
echo   Ready to go! Double-click "SiteOwlQA Launcher" on desktop.
echo.
echo  ============================================================
echo.

pause
