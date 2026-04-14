@echo off
REM System Bottleneck Auditor — double-click to run a full architecture audit
REM Scans the codebase, calls Element LLM Gateway if configured, opens report in browser.
REM
REM Usage:
REM   Double-click this file                  → full LLM audit (if configured) + browser
REM   Drag onto CMD and add --no-llm          → static structural scan only
REM   Drag onto CMD and add --no-browser      → audit without opening browser

setlocal enabledelayedexpansion

for %%I in ("%~dp0..") do set WORKDIR=%%~fI

if exist "%WORKDIR%\.venv\Scripts\python.exe" (
  set PYTHON=%WORKDIR%\.venv\Scripts\python.exe
) else (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    set PYTHON=%%P
    goto :python_found
  )
  echo [ERROR] Python not found. Create .venv first.
  pause
  exit /b 1
)
:python_found

echo [INFO] Running System Bottleneck Auditor ...
echo [INFO] Working directory: %WORKDIR%
echo.

"%PYTHON%" "%WORKDIR%\tools\system_bottleneck_auditor.py" %*

if !errorlevel! neq 0 (
  echo [ERROR] Auditor exited with error code !errorlevel!
  pause
  exit /b !errorlevel!
)

exit /b 0
