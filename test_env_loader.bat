@echo off
REM Quick test to verify .env.local is loaded correctly

cd /d "%~dp0"

echo === Testing .env.local loader ===
echo.

if exist .env.local (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env.local") do (
        if not "%%b"=="" set %%a=%%b
    )
)

echo Checking loaded environment variables:
echo.
echo SCOUT_AIRTABLE_API_KEY=%SCOUT_AIRTABLE_API_KEY%
echo SCOUT_AIRTABLE_BASE_ID=%SCOUT_AIRTABLE_BASE_ID%
echo SCOUT_AIRTABLE_TABLE_ID=%SCOUT_AIRTABLE_TABLE_ID%
echo.

if "%SCOUT_AIRTABLE_API_KEY%"=="" (
    echo [ERROR] API key not loaded!
    exit /b 1
) else (
    echo [OK] Environment variables loaded successfully!
    exit /b 0
)
