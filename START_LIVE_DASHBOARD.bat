@echo off
:: VUES Live Dashboard - Auto-starts refresh daemon + server
:: This runs minimized on Windows startup

cd /d "%~dp0"

:: Kill any existing instances (but not Teams on 8080)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F 2>nul
)

:: Start refresh daemon (pulls from Airtable every 30 seconds)
start /min "VUES-Refresh" cmd /c "python refresh_dashboard.py --watch --interval 30"

:: Wait for first refresh
timeout /t 5 /nobreak >nul

:: Copy fresh data to output
copy /Y output\team_dashboard_data.json output\ 2>nul
copy /Y ui\*.html output\ 2>nul

:: Start live server on port 8765
start /min "VUES-Server" cmd /c "set VUES_LIVE_RELOAD=1 && python tools/run_dashboard_server.py output 8765"

:: Wait for server to start
timeout /t 2 /nobreak >nul

:: Open dashboard in browser
start "" "http://127.0.0.1:8765/analytics.html"

echo.
echo ========================================
echo   VUES LIVE DASHBOARD RUNNING
echo ========================================
echo.
echo   Refresh: Every 30 seconds from Airtable
echo   Server:  http://127.0.0.1:8765
echo   
echo   Dashboard pages:
echo     - http://127.0.0.1:8765/analytics.html
echo     - http://127.0.0.1:8765/index.html
echo     - http://127.0.0.1:8765/scout.html
echo     - http://127.0.0.1:8765/survey.html
echo.
echo   Press any key to close this window
echo   (servers will keep running in background)
echo ========================================
pause >nul
