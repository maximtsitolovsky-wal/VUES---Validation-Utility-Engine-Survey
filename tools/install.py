#!/usr/bin/env python3
"""VUES Installer - Creates desktop shortcut and sets up the app."""

# Fix Windows console encoding for emoji
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import sys
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
    if not icon_path.exists():
    print("  [WARN] Icon not found:", icon_path)
        print("     Shortcut will use default Python icon")
        icon_path = None
    
    # PowerShell script to create shortcut
    ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "pythonw.exe"
$Shortcut.Arguments = '"{target_script}"'
$Shortcut.WorkingDirectory = "{repo_root}"
$Shortcut.Description = "VUES - Survey Routing Dashboard"
{f'$Shortcut.IconLocation = "{icon_path}"' if icon_path else ''}
$Shortcut.Save()
'''
    
    # Run PowerShell
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
    print("  [OK] Desktop shortcut created:", shortcut_path)
        return True
    else:
    print("  [FAIL] Failed to create shortcut:", result.stderr)
        return False


def install_dependencies():
    """Install required Python packages."""
    repo_root = Path(__file__).parent.parent.resolve()
    requirements = repo_root / "requirements.txt"
    
    if not requirements.exists():
    print("  [WARN] requirements.txt not found, skipping")
        return True
    
    print("  [1/2] Installing dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements), "-q"],
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
    print("  VUES Installer")
    print("  ═════════════════════════════")
    print("")
    
    # Install dependencies
    install_dependencies()
    
    # Create desktop shortcut
    print("")
    print("  [2/2] Creating desktop shortcut...")
    create_desktop_shortcut()
    
    print("")
    print("  Installation complete!")
    print("")
    print("  Double-click 'VUES Dashboard' on your desktop to launch.")
    print("")


if __name__ == "__main__":
    main()
