@echo off
REM Register vues Pipeline as a Task Scheduler task
REM Run this as Administrator

REM Dynamically resolve WORKDIR from script location
cd /d "%~dp0..\.."
set WORKDIR=%CD%
set TASKNAME=vues Pipeline

echo Deleting old task if exists...
schtasks /Delete /TN "%TASKNAME%" /F 2>nul

echo Creating task...
schtasks /Create /TN "%TASKNAME%" ^
  /TR "cmd.exe /c %WORKDIR%\run_vues.bat" ^
  /SC ONSTART ^
  /DELAY 0001:00 ^
  /RL HIGHEST ^
  /RU SYSTEM ^
  /F

echo.
echo Task created. Verifying...
schtasks /Query /TN "%TASKNAME%" /FO LIST
echo.
echo Done! The task will run automatically at every startup.
echo To start it NOW without rebooting, run:
echo   schtasks /Run /TN "vues Pipeline"
