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
echo [5/5] Checking for credentials...

if exist "C:\VUES\.env.local" (
    echo [OK] .env.local found
) else (
    echo.
    echo [ACTION REQUIRED] You need to create C:\VUES\.env.local with your credentials!
    echo.
    echo Create the file with these contents:
    echo   SCOUT_AIRTABLE_API_KEY=your_token_here
    echo   SCOUT_AIRTABLE_BASE_ID=appAwgaX89x0JxG3Z
    echo   SCOUT_AIRTABLE_TABLE_ID=tblC4o9AvVulyxFMk
    echo.
    echo Get your API key from: https://airtable.com/account
    echo.
    
    REM Create a template file
    echo # VUES Local Credentials - DO NOT COMMIT > C:\VUES\.env.local.template
    echo # Copy this to .env.local and fill in your values >> C:\VUES\.env.local.template
    echo SCOUT_AIRTABLE_API_KEY=your_token_here >> C:\VUES\.env.local.template
    echo SCOUT_AIRTABLE_BASE_ID=appAwgaX89x0JxG3Z >> C:\VUES\.env.local.template
    echo SCOUT_AIRTABLE_TABLE_ID=tblC4o9AvVulyxFMk >> C:\VUES\.env.local.template
    
    echo [INFO] Created template at: C:\VUES\.env.local.template
)

echo.
echo  ============================================================
echo   SETUP COMPLETE!
echo  ============================================================
echo.
echo   Desktop shortcuts created:
echo     - SiteOwlQA Launcher (main app)
echo     - FIX SCOUT TASKS (admin tool)
echo.
echo   Next steps:
echo     1. Create .env.local with your Scout API credentials
echo     2. Double-click "SiteOwlQA Launcher" on your desktop
echo.
echo  ============================================================
echo.

pause
