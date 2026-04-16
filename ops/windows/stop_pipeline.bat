@echo off
REM Stop SiteOwlQA Pipeline
REM Gracefully terminates the background pipeline process and git autopush

setlocal enabledelayedexpansion

echo [INFO] Stopping SiteOwlQA pipeline and git autopush...

REM Resolve repo root relative to this script so clones work anywhere
for %%I in ("%~dp0..\..") do set WORKDIR=%%~fI

REM Find only python.exe processes running THIS repo's main.py
set KILLED=0
for /f "tokens=2 delims==" %%A in ('wmic process where "name='python.exe' and commandline like '%%main.py%%' and commandline like '%%%WORKDIR:\=\\%%%'" get ProcessId /value 2^>nul ^| find "="') do (
  echo [INFO] Terminating SiteOwlQA process %%A
  taskkill /pid %%A /t /f >nul 2>&1
  if !errorlevel! equ 0 set KILLED=1
)

if "!KILLED!"=="1" (
  echo [INFO] Pipeline stopped successfully.
) else (
  echo [WARN] Could not find a running SiteOwlQA pipeline process for %WORKDIR%.
)

REM Find and stop git_autopush.py
set AUTOPUSH_KILLED=0
for /f "tokens=2 delims==" %%A in ('wmic process where "name='python.exe' and commandline like '%%git_autopush.py%%' and commandline like '%%%WORKDIR:\=\\%%%'" get ProcessId /value 2^>nul ^| find "="') do (
  echo [INFO] Terminating git-autopush process %%A
  taskkill /pid %%A /t /f >nul 2>&1
  if !errorlevel! equ 0 set AUTOPUSH_KILLED=1
)

if "!AUTOPUSH_KILLED!"=="1" (
  echo [INFO] Git autopush stopped successfully.
) else (
  echo [INFO] Git autopush was not running.
)

exit /b 0
