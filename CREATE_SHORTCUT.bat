@echo off
title VUES - Create Shortcut
echo.
echo  ==========================================
echo   VUES - Creating Desktop Shortcut
echo  ==========================================
echo.

cd /d "%~dp0"

:: Check Python exists
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Python not found!
    echo.
    echo  Install Python from Microsoft Store:
    echo  Search for "Python 3.11" and click Install
    echo.
    pause
    exit /b 1
)

echo  Creating shortcut...

:: Get script directory (remove trailing backslash)
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Write PowerShell script to temp file
set "PS_SCRIPT=%TEMP%\create_vues_shortcut.ps1"

echo $desktop = [Environment]::GetFolderPath('Desktop') > "%PS_SCRIPT%"
echo $ws = New-Object -ComObject WScript.Shell >> "%PS_SCRIPT%"
echo $shortcut = $ws.CreateShortcut("$desktop\VUES Dashboard.lnk") >> "%PS_SCRIPT%"
echo $shortcut.TargetPath = 'pythonw' >> "%PS_SCRIPT%"
echo $shortcut.Arguments = '"%SCRIPT_DIR%\tools\serve_dashboard.py"' >> "%PS_SCRIPT%"
echo $shortcut.WorkingDirectory = '%SCRIPT_DIR%' >> "%PS_SCRIPT%"
echo $shortcut.Description = 'VUES Dashboard' >> "%PS_SCRIPT%"
echo $iconPath = '%SCRIPT_DIR%\assets\vues_icon.ico' >> "%PS_SCRIPT%"
echo if (Test-Path $iconPath) { $shortcut.IconLocation = $iconPath } >> "%PS_SCRIPT%"
echo $shortcut.Save() >> "%PS_SCRIPT%"
echo Write-Host '  [OK] Shortcut created on Desktop!' >> "%PS_SCRIPT%"

:: Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Failed to create shortcut
    del "%PS_SCRIPT%" 2>nul
    pause
    exit /b 1
)

:: Cleanup
del "%PS_SCRIPT%" 2>nul

echo.
echo  ==========================================
echo   Done! 
echo  ==========================================
echo.
echo  Double-click "VUES Dashboard" on your Desktop!
echo.
echo  Press any key to launch the dashboard now...
pause >nul

:: Launch it
start "" pythonw "%SCRIPT_DIR%\tools\serve_dashboard.py"
