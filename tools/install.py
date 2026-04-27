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


def get_desktop_path():
    """Get the actual Desktop path (handles OneDrive redirection)."""
    # Use PowerShell to get the real Desktop path
    result = subprocess.run(
        ["powershell", "-Command", "[Environment]::GetFolderPath('Desktop')"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    # Fallback
    return Path(os.environ.get("USERPROFILE", "~")) / "Desktop"


def create_desktop_shortcut():
    """Create a desktop shortcut for VUES Dashboard."""
    
    # Get paths
    repo_root = Path(__file__).parent.parent.resolve()
    icon_path = repo_root / "assets" / "vues_icon.ico"
    target_script = repo_root / "tools" / "serve_dashboard.py"
    desktop = get_desktop_path()
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


def check_data_files():
    """Check if dashboard data files exist."""
    repo_root = Path(__file__).parent.parent.resolve()
    ui_dir = repo_root / "ui"
    data_file = ui_dir / "team_dashboard_data.json"
    
    if data_file.exists():
        size_kb = data_file.stat().st_size / 1024
        print(f"  [OK] Dashboard data found ({size_kb:.0f} KB)")
        return True
    else:
        print("  [WARN] No dashboard data found!")
        print("         Try: git pull (or re-download the ZIP)")
        return False


def install_dependencies():
    """Install required Python packages (only if requirements.txt exists)."""
    repo_root = Path(__file__).parent.parent.resolve()
    requirements = repo_root / "requirements.txt"
    
    # Check if this is admin (has full source) or viewer (just dashboard)
    src_dir = repo_root / "src" / "siteowlqa"
    is_admin = src_dir.exists()
    
    if not is_admin:
        print("  [OK] Viewer mode - no dependencies needed")
        return True
    
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
    
    # Check for data files
    print("  [1/3] Checking dashboard data...")
    check_data_files()
    
    # Install dependencies (only for admin/full install)
    print("")
    print("  [2/3] Checking dependencies...")
    install_dependencies()
    
    # Create desktop shortcut
    print("")
    print("  [3/3] Creating desktop shortcut...")
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
