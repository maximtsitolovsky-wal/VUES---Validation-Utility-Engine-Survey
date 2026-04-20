@echo off
setlocal

REM Stop the background vues pipeline process.

REM Dynamically resolve WORKDIR from script location
cd /d "%~dp0..\.."
set WORKDIR=%CD%
set PIDFILE=%WORKDIR%\logs\vues.pid

echo.
echo Stopping vues background app...

powershell -NoProfile -ExecutionPolicy Bypass -File "%WORKDIR%\stop_vues_background.ps1" >nul

if errorlevel 1 (
  echo [WARN] Stop command completed with warnings.
) else (
  echo [OK] vues stopped.
)

timeout /t 2 /nobreak >nul
exit /b 0
