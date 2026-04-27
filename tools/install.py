#!/usr/bin/env python3
"""VUES Installer - Creates desktop shortcut and sets up the app."""

# Fix Windows console encoding
import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import os
import subprocess
from pathlib import Path


def create_desktop_shortcut():
    """Create a desktop shortcut for VUES Dashboard."""
    
    # Get paths
    repo_root = Path(__file__).parent.parent.resolve()
    icon_path = repo_root / "assets" / "vues_icon.ico"
    target_script = repo_root / "tools" / "serve_dashboard.py"
    desktop = Path(os.environ.get("USERPROFILE", "~")) / "Desktop"
    shortcut_path = desktop / "VUES Dashboard.lnk"
    
    # Check if icon exists
    icon_arg = ""
    if icon_path.exists():
        icon_arg = f'$Shortcut.IconLocation = "{icon_path}"'
    else:
        print("  [WARN] Icon not found:", icon_path)
        print("         Shortcut will use default icon")
    
    # Get Python path
    python_exe = Path(sys.executable)
    pythonw_exe = python_exe.parent / "pythonw.exe"
    if not pythonw_exe.exists():
        pythonw_exe = python_exe  # Fall back to python.exe
    
    # PowerShell script to create shortcut
    ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{pythonw_exe}"
$Shortcut.Arguments = '"{target_script}"'
$Shortcut.WorkingDirectory = "{repo_root}"
$Shortcut.Description = "VUES - Survey Routing Dashboard"
{icon_arg}
$Shortcut.Save()
'''
    
    # Run PowerShell
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("  [OK] Desktop shortcut created!")
        print("       Location:", shortcut_path)
        return True
    else:
        print("  [FAIL] Failed to create shortcut")
        print("        ", result.stderr[:200] if result.stderr else "Unknown error")
        return False


def install_dependencies():
    """Install required Python packages."""
    repo_root = Path(__file__).parent.parent.resolve()
    requirements = repo_root / "requirements.txt"
    
    if not requirements.exists():
        print("  [SKIP] No requirements.txt found")
        return True
    
    print("  [1/2] Installing dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements), "-q",
         "--index-url", "https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple",
         "--trusted-host", "pypi.ci.artifacts.walmart.com"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("  [OK] Dependencies installed")
        return True
    else:
        print("  [WARN] Some dependencies may have failed")
        return True  # Continue anyway


def main():
    print("")
    print("  ============================================")
    print("   VUES Installer")
    print("   Validation Utility Engine Survey")
    print("  ============================================")
    print("")
    
    # Install dependencies
    install_dependencies()
    
    # Create desktop shortcut
    print("")
    print("  [2/2] Creating desktop shortcut...")
    create_desktop_shortcut()
    
    print("")
    print("  ============================================")
    print("   Installation complete!")
    print("  ============================================")
    print("")
    print("  Double-click 'VUES Dashboard' on your desktop to launch.")
    print("")


if __name__ == "__main__":
    main()
