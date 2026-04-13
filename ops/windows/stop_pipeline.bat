@echo off
REM Stop SiteOwlQA Pipeline
REM Gracefully terminates the background pipeline process

setlocal enabledelayedexpansion

echo [INFO] Stopping SiteOwlQA pipeline...

REM Find and kill python.exe processes running main.py
REM This is a simple approach - you can refine by checking command line
for /f "tokens=2" %%A in ('tasklist /fi "imagename eq python.exe" /fo table ^| findstr python') do (
  echo [INFO] Terminating process %%A
  taskkill /pid %%A /t /f
)

if !errorlevel! equ 0 (
  echo [INFO] Pipeline stopped successfully.
) else (
  echo [WARN] Could not find running pipeline process.
)

exit /b 0
