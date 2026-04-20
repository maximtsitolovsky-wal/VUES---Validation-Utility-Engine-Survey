@echo off
setlocal

REM Thin wrapper around the PowerShell launcher.
REM Keep batch tiny; let PowerShell do the real work like an adult.

REM Dynamically resolve WORKDIR from script location
cd /d "%~dp0..\.."
set WORKDIR=%CD%
set LAUNCHER=%WORKDIR%\ops\windows\launch_vues_dashboard.ps1

if not exist "%LAUNCHER%" (
  echo [ERROR] Launcher script not found at %LAUNCHER%
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%LAUNCHER%"
exit /b %ERRORLEVEL%
