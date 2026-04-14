@echo off
REM Specialist Output Validator
REM Reviews the latest outputs from all specialist agents and issues pass/fail.
REM Run AFTER the other agents have had time to produce their outputs.
REM
REM  Double-click  → LLM validation (if Element Gateway configured) + browser
REM  --no-llm      → structural checks only (no LLM needed)
REM  --no-browser  → write report without opening browser

setlocal enabledelayedexpansion

for %%I in ("%~dp0..\..") do set WORKDIR=%%~fI

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

echo [INFO] Specialist Output Validator
echo [INFO] Working directory: %WORKDIR%
echo.

"%PYTHON%" "%WORKDIR%\tools\specialist_output_validator.py" %*

if !errorlevel! neq 0 (
  echo [ERROR] Validator exited with code !errorlevel!
  pause
  exit /b !errorlevel!
)

exit /b 0
