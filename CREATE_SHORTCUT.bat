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

:: Get paths
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

:: Use PowerShell to create shortcut
powershell -ExecutionPolicy Bypass -Command ^
  "$desktop = [Environment]::GetFolderPath('Desktop'); ^
   $ws = New-Object -ComObject WScript.Shell; ^
   $shortcut = $ws.CreateShortcut(\"$desktop\VUES Dashboard.lnk\"); ^
   $shortcut.TargetPath = 'pythonw'; ^
   $shortcut.Arguments = '\"%SCRIPT_DIR%\tools\serve_dashboard.py\"'; ^
   $shortcut.WorkingDirectory = '%SCRIPT_DIR%'; ^
   $shortcut.Description = 'VUES Dashboard'; ^
   if (Test-Path '%SCRIPT_DIR%\assets\vues_icon.ico') { $shortcut.IconLocation = '%SCRIPT_DIR%\assets\vues_icon.ico' }; ^
   $shortcut.Save(); ^
   Write-Host '  [OK] Shortcut created on Desktop!'"

if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Failed to create shortcut
    pause
    exit /b 1
)

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
