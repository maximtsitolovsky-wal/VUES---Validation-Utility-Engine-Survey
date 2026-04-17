@echo off
REM Scheduled Task Wrapper for Scout Completion Sync
REM Loads environment variables from .env then runs the script

cd /d "%~dp0..\.."

REM Set Scout Airtable credentials
REM TODO: Move these to .env file for security
set SCOUT_AIRTABLE_API_KEY=patPR0WWxXCE0loRO.d18126548ad25b8aaf9fd43e2ac69479b1378e46d7f8c6efbdd88f7197a4d495
set SCOUT_AIRTABLE_BASE_ID=appAwgaX89x0JxG3Z
set SCOUT_AIRTABLE_TABLE_ID=tblC4o9AvVulyxFMk

REM Run the sync script
python scripts\scout_completion_sync_com.py >> logs\scout_completion_sync.log 2>&1

exit /b %errorlevel%
