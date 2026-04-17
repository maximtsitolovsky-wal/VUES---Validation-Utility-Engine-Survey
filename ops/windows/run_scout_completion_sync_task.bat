@echo off
REM Scheduled Task Wrapper for Scout Completion Sync
REM Loads environment variables from .env.local then runs the script

cd /d "%~dp0..\.."

REM Load Scout Airtable credentials from .env.local (gitignored)
REM Create this file with:
REM   SCOUT_AIRTABLE_API_KEY=your_token_here
REM   SCOUT_AIRTABLE_BASE_ID=appAwgaX89x0JxG3Z
REM   SCOUT_AIRTABLE_TABLE_ID=tblC4o9AvVulyxFMk

if exist .env.local (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env.local") do (
        if not "%%b"=="" set %%a=%%b
    )
)

REM Run the sync script
python scripts\scout_completion_sync_com.py >> logs\scout_completion_sync.log 2>&1

exit /b %errorlevel%
