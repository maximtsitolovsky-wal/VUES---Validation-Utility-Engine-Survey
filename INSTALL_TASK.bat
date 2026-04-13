@echo off
REM INSTALL_TASK.bat — One-time setup: registers SiteOwlQA in Task Scheduler
REM Just double-click this and click Yes on the UAC prompt.

:: Check if already running as admin
net session >nul 2>&1
if %errorlevel% == 0 goto :ELEVATED

:: Not admin — re-launch ourselves elevated via PowerShell UAC prompt
echo Requesting administrator privileges...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b 0

:ELEVATED
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\SiteOwlQA_App\register_task.ps1"
