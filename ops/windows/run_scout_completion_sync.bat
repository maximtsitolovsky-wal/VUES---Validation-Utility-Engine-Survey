@echo off
REM Manual test run of Scout Completion Sync
REM Does not require admin rights

echo === Scout Completion Sync - Manual Test Run ===
echo.
echo This will sync completion status from Airtable to Excel NOW.
echo.
echo IMPORTANT: Please close ScoutSurveyLab.xlsm in Excel before running!
echo.
pause

cd /d "%~dp0..\.."

echo [*] Running sync script...
echo.

python scripts\scout_completion_sync.py

echo.
echo.
if %errorlevel% equ 0 (
    echo [OK] Sync completed successfully!
) else (
    echo [ERROR] Sync failed. See error message above.
)
echo.
echo Check logs\scout_completion_sync.log for details.
echo.
pause
