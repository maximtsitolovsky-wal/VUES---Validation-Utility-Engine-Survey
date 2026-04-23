@echo off
REM ============================================================
REM  VUES Fresh Install Script v2.0
REM  One-click setup with proper venv and dependency validation
REM  
REM  Usage: Right-click -> Run as Administrator (first time)
REM         Or just double-click if Python already installed
REM ============================================================

setlocal EnableDelayedExpansion
title VUES Fresh Install

echo.
echo  ============================================================
echo   VUES - Validation Utility Engine Survey
echo   Fresh Install Script v2.0
echo  ============================================================
echo.

REM ============================================================
REM  STEP 1: Clone or locate repository
REM ============================================================
if exist "C:\VUES\main.py" (
    echo [OK] VUES already cloned at C:\VUES
    cd /d C:\VUES
) else (
    echo [1/6] Cloning VUES repository...
    
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

REM ============================================================
REM  STEP 2: Find or install Python
REM ============================================================
echo.
echo [2/6] Checking Python installation...

set "PYTHON_CMD="

REM Check common locations
where python >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%P in ('where python') do (
        set "PYTHON_CMD=%%P"
        goto :python_found
    )
)

for %%V in (314 313 312 311) do (
    if exist "C:\Python%%V\python.exe" (
        set "PYTHON_CMD=C:\Python%%V\python.exe"
        goto :python_found
    )
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        goto :python_found
    )
)

REM Python not found - try to install
echo [WARN] Python not found. Attempting to install...
where winget >nul 2>&1
if not errorlevel 1 (
    echo Instg Python 3.12 via winget...
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
echo         Please install Python 3.12+ manually from python.org
pause
exit /b 1

:python_found
echo [OK] Found Python: %PYTHON_CMD%
%PYTHON_CMD% --version

REM Verify version
for /f "tokens=2 delims= " %%V in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%V
for /f "tokens=1,2 delims=." %%A in ("%PYVER%") do (
    if %%A LSS 3 (
        echo [ERROR] Python 3.11+ required, found %PYVER%
        pause
        exit /b 1
    )
    if %%A EQU 3 if %%B LSS 11 (
        echo [ERROR] Python 3.11+ required, found %PYVER%
        pause
        exit /b 1
    )
)

REM ============================================================
REM  STEP 3: Create virtual environment
REM ============================================================
echo.
echo [3/6] Creating virtual environment...

if exist "C:\VUES\.venv\Scripts\python.exe" (
    echo [OK] Virtual environment already exists
) else (
    %PYTHON_CMD% -m venv C:\VUES\.venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created at C:\VUES\.venv
)

set VENV_PYTHON=C:\VUES\.venv\Scripts\python.exe

REM ============================================================
REM  STEP 4: Install dependencies
REM ============================================================
echo.
echo [4/6] Installing Python dependencies...

REM Upgrade pip first
"%VENV_PYTHON%" -m pip install --upgrade pip ^
    --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple ^
    --trusted-host pypi.ci.artifacts.walmart.com >nul 2>&1

REM Install requirements
"%VENV_PYTHON%" -m pip install -r requirements.txt ^
    --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple ^
    --trusted-host pypi.ci.artifacts.walmart.com

if errorlevel 1 (
    echo [WARN] Some packages may have failed. Continuing...
)

REM Install watchdog for git autopush
"%VENV_PYTHON%" -m pip install watchdog ^
    --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple ^
    --trusted-host pypi.ci.artifacts.walmart.com >nul 2>&1

echo [OK] Dependencies installed

REM ============================================================
REM  STEP 5: Validate installation
REM ============================================================
echo.
echo [5/6] Validating installation...

"%VENV_PYTHON%" -c "import sys; sys.path.insert(0,'src'); from siteowlqa.config import load_config; print('[OK] Config module')"
if errorlevel 1 (
    echo [FAIL] Config module failed to import
    goto :validation_failed
)

"%VENV_PYTHON%" -c "import pyairtable; print('[OK] pyairtable')"
if errorlevel 1 goto :validation_failed

"%VENV_PYTHON%" -c "import pandas; print('[OK] pandas')"
if errorlevel 1 goto :validation_failed

"%VENV_PYTHON%" -c "import openpyxl; print('[OK] openpyxl')"
if errorlevel 1 goto :validation_failed

"%VENV_PYTHON%" -c "import google.cloud.bigquery; print('[OK] google-cloud-bigquery')"
if errorlevel 1 goto :validation_failed

"%VENV_PYTHON%" -c "import win32com.client; print('[OK] pywin32')"
if errorlevel 1 goto :validation_failed

"%VENV_PYTHON%" -c "import requests; print('[OK] requests')"
if errorlevel 1 goto :validation_failed

echo [OK] All dependencies validated
goto :validation_passed

:validation_failed
echo.
echo [ERROR] Dependency validation failed!
echo         Try running manually:
echo         C:\VUES\.venv\Scripts\pip install -r requirements.txt
pause
exit /b 1

:validation_passed

REM ============================================================
REM  STEP 6: Create desktop shortcuts
REM ============================================================
echo.
echo [6/6] Creating desktop shortcuts...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$desktop = [Environment]::GetFolderPath('Desktop'); ^
     $sh = New-Object -ComObject WScript.Shell; ^
     $lnk = $sh.CreateShortcut(\"$desktop\VUES Launcher.lnk\"); ^
     $lnk.TargetPath = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'; ^
     $lnk.Arguments = '-ExecutionPolicy Bypass -WindowStyle Hidden -File \"C:\VUES\ops\windows\launch_vues_dashboard.ps1\"'; ^
     $lnk.WorkingDirectory = 'C:\VUES'; ^
     $lnk.Description = 'VUES - starts pipeline and opens dashboard'; ^
     $lnk.Save(); ^
     Write-Host '[OK] Created: VUES Launcher.lnk'"

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

REM ============================================================
REM  COMPLETE
REM ============================================================
echo.
echo  ============================================================
echo   SETUP COMPLETE!
echo  ============================================================
echo.
echo   Python:       %PYVER%
echo   Virtual Env:  C:\VUES\.venv
echo   Dependencies: Validated
echo.
echo   Desktop shortcuts:
echo     - VUES Launcher (main app)
echo     - FIX SCOUT TASKS (admin tool)
echo.
echo   Next steps:
echo     1. Run: python -m siteowlqa.setup_config
echo        (to configure Airtable/BigQuery credentials)
echo     2. Double-click "VUES Launcher" on desktop
echo.
echo  ============================================================
echo.

pause
