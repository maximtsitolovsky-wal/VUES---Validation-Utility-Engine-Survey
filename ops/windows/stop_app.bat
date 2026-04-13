@echo off
setlocal

REM Stop the background SiteOwlQA pipeline process.

set WORKDIR=C:\SiteOwlQA_App
set PIDFILE=%WORKDIR%\logs\siteowlqa.pid

echo.
echo Stopping SiteOwlQA background app...

powershell -NoProfile -ExecutionPolicy Bypass -File "%WORKDIR%\stop_siteowlqa_background.ps1" >nul

if errorlevel 1 (
  echo [WARN] Stop command completed with warnings.
) else (
  echo [OK] SiteOwlQA stopped.
)

timeout /t 2 /nobreak >nul
exit /b 0
