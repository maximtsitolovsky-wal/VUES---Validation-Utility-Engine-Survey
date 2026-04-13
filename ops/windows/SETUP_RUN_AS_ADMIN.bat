@echo off
REM =============================================================
REM  SiteOwlQA — Task Scheduler Registration
REM  RIGHT-CLICK this file → "Run as administrator"
REM =============================================================

echo.
echo  SiteOwlQA Pipeline — Task Scheduler Setup
echo  ==========================================
echo.

REM Remove existing task if present
schtasks /Delete /TN "SiteOwlQA Pipeline" /F 2>nul
if %errorlevel% == 0 (
    echo  [OK] Old task removed.
) else (
    echo  [OK] No existing task to remove.
)

REM Import the XML task definition
echo  Registering task from XML...
schtasks /Create /TN "SiteOwlQA Pipeline" /XML "C:\SiteOwlQA_App\SiteOwlQA_Task.xml" /F

if %errorlevel% == 0 (
    echo.
    echo  [OK] Task registered successfully!
    echo.
    schtasks /Query /TN "SiteOwlQA Pipeline" /FO LIST
    echo.
    echo  ============================================================
    echo  SETUP COMPLETE.
    echo  The SiteOwlQA Pipeline will start automatically at boot.
    echo.
    echo  To start it RIGHT NOW (without rebooting), run:
    echo    schtasks /Run /TN "SiteOwlQA Pipeline"
    echo.
    echo  To check logs:
    echo    type C:\SiteOwlQA_App\logs\siteowl_qa.log
    echo  ============================================================
) else (
    echo.
    echo  [ERROR] Task registration failed.
    echo  Make sure you right-clicked and chose 'Run as administrator'.
)

echo.
pause
