@echo off
REM ============================================================
REM  VUES Pre-flight Check
REM  Validates environment before starting pipeline
REM  Called by launchers; can also run standalone
REM ============================================================
setlocal EnableDelayedExpansion

REM Resolve repo root
for %%I in ("%~dp0..\..") do set WORKDIR=%%~fI
cd /d "%WORKDIR%"

REM Find Python
if exist "%WORKDIR%\.venv\Scripts\python.exe" (
    set PYTHON=%WORKDIR%\.venv\Scripts\python.exe
) else (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        set PYTHON=%%P
        goto :python_found
    )
    echo [FAIL] Python not found
    exit /b 1
)
:python_found

REM Quick dependency check (imports only, no network)
"%PYTHON%" -c "import sys; sys.path.insert(0,'src'); from siteowlqa.config import load_config; from siteowlqa.airtable_client import AirtableClient; from siteowlqa.python_grader import grade_submission_in_python; from siteowlqa.poll_airtable import process_record; print('[OK] All modules import successfully')" 2>nul
if errorlevel 1 (
    echo [FAIL] Module import failed - run: pip install -r requirements.txt
    exit /b 1
)

REM Check critical dependencies
"%PYTHON%" -c "import pyairtable, pandas, openpyxl, google.cloud.bigquery, requests; print('[OK] Dependencies verified')" 2>nul
if errorlevel 1 (
    echo [FAIL] Missing dependencies - run: pip install -r requirements.txt
    exit /b 1
)

echo [OK] Pre-flight check passed
exit /b 0
