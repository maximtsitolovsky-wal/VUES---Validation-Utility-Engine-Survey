@echo off
setlocal

REM Thin wrapper around the PowerShell launcher.
REM Keep batch tiny; let PowerShell do the real work like an adult.

set WORKDIR=C:\SiteOwlQA_App
set LAUNCHER=%WORKDIR%\ops\windows\launch_siteowlqa_dashboard.ps1

if not exist "%LAUNCHER%" (
  echo [ERROR] Launcher script not found at %LAUNCHER%
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%LAUNCHER%"
exit /b %ERRORLEVEL%
