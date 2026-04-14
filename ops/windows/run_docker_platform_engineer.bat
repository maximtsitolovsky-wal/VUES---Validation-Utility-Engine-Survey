@echo off
REM Docker and Multi-User Platform Engineer
REM Scans the codebase and writes Docker infrastructure to infra/
REM
REM  Double-click  → full LLM design (if Element Gateway configured) + browser report
REM  --no-llm      → static hardened artifacts only (no LLM needed)
REM  --no-browser  → write files without opening report in browser

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

echo [INFO] Docker and Multi-User Platform Engineer
echo [INFO] Working directory: %WORKDIR%
echo.

"%PYTHON%" "%WORKDIR%\tools\docker_platform_engineer.py" %*

if !errorlevel! neq 0 (
  echo [ERROR] Agent exited with error code !errorlevel!
  pause
  exit /b !errorlevel!
)

exit /b 0
