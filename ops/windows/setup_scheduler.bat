@echo off
REM Setup SiteOwlQA Windows Task Scheduler
REM This script creates an automated task that runs the pipeline at system startup
REM Must be run as Administrator

setlocal enabledelayedexpansion

REM Check for admin privileges
net session >nul 2>&1
if !errorlevel! neq 0 (
  echo [ERROR] This script must be run as Administrator
  echo Please right-click this file and select "Run as administrator"
  pause
  exit /b 1
)

for %%I in ("%~dp0..\..") do set WORKDIR=%%~fI
if exist "%WORKDIR%\.venv\Scripts\python.exe" (
  set PYTHON=%WORKDIR%\.venv\Scripts\python.exe
) else (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    set PYTHON=%%P
    goto :python_found
  )
  set PYTHON=
)
:python_found
set TASK_NAME=SiteOwlQA Pipeline

echo [INFO] Setting up Windows Task Scheduler...
echo [INFO] Workdir: %WORKDIR%
echo [INFO] Python: %PYTHON%
echo.

REM Verify Python exists
if not exist "%PYTHON%" (
  echo [ERROR] Python not found at %PYTHON%
  echo Please update the PYTHON variable in this script.
  pause
  exit /b 1
)

REM Verify project exists
if not exist "%WORKDIR%\main.py" (
  echo [ERROR] main.py not found in %WORKDIR%
  pause
  exit /b 1
)

REM Check if task already exists
echo [INFO] Checking for existing task...
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if !errorlevel! equ 0 (
  echo [INFO] Task already exists. Deleting old task...
  schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
)

REM Create the scheduled task
echo [INFO] Creating new scheduled task...
schtasks /create ^^
  /tn "%TASK_NAME%" ^^
  /tr "\"%PYTHON%\" -u \"%WORKDIR%\main.py\"" ^^
  /sc onstart ^^
  /ru SYSTEM ^^
  /f ^^
  /delay 0000:01 >nul 2>&1

if !errorlevel! equ 0 (
  echo [OK] Task created successfully!
) else (
  echo [ERROR] Failed to create task
  pause
  exit /b 1
)

REM Configure task settings
echo [INFO] Configuring task settings...
schtasks /change /tn "%TASK_NAME%" /disable >nul 2>&1
schtasks /change /tn "%TASK_NAME%" /enable >nul 2>&1

REM Verify task was created
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if !errorlevel! equ 0 (
  echo.
  echo ========================================
  echo [OK] Setup Complete!
  echo ========================================
  echo.
  echo Task Name: %TASK_NAME%
  echo Trigger: At startup
  echo Run As: SYSTEM (runs even when no user is logged in)
  echo.
  echo The pipeline will automatically start when your computer boots.
  echo.
  echo To view the task in Task Scheduler:
  echo   Press Windows+R, type: taskmgr
  echo   Or search: Task Scheduler
  echo.
  echo To manually start the pipeline now:
  echo   Double-click: start_pipeline.bat
  echo.
  echo To view logs:
  echo   %WORKDIR%\logs\siteowlqa.stdout.log
  echo.
  echo.
) else (
  echo [ERROR] Task creation failed
  pause
  exit /b 1
)

pause
exit /b 0
