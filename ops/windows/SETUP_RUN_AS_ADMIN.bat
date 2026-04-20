@echo off
REM =============================================================
REM  vues — Task Scheduler Registration
REM  RIGHT-CLICK this file → "Run as administrator"
REM =============================================================

echo.
echo  vues Pipeline — Task Scheduler Setup
echo  ==========================================
echo.

REM Remove existing task if present
schtasks /Delete /TN "vues Pipeline" /F 2>nul
if %errorlevel% == 0 (
    echo  [OK] Old task removed.
) else (
    echo  [OK] No existing task to remove.
)

REM Import the XML task definition
echo  Registering task from XML...
schtasks /Create /TN "VUES Pipeline" /XML "C:\VUES\ops\windows\VUES_Task.xml" /F

if %errorlevel% == 0 (
    echo.
    echo  [OK] Task registered successfully!
    echo.
    schtasks /Query /TN "vues Pipeline" /FO LIST
    echo.
    echo  ============================================================
    echo  SETUP COMPLETE.
    echo  The vues Pipeline will start automatically at boot.
    echo.
    echo  To start it RIGHT NOW (without rebooting), run:
    echo    schtasks /Run /TN "vues Pipeline"
    echo.
    echo  To check logs:
    echo    type C:\VUES\logs\vues.log
    echo  ============================================================
) else (
    echo.
    echo  [ERROR] Task registration failed.
    echo  Make sure you right-clicked and chose 'Run as administrator'.
)

echo.
pause
