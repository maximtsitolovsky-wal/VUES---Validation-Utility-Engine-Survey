#!/usr/bin/env python3
"""VUES Diagnostic Tool - Verifies dashboard setup is working."""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def check(label, condition, fix=None):
    """Print check result."""
    status = "[OK]  " if condition else "[FAIL]"
    print(f"  {status} {label}")
    if not condition and fix:
        print(f"         Fix: {fix}")
    return condition


def main():
    print("")
    print("  ============================================")
    print("   VUES Dashboard Diagnostic")
    print("  ============================================")
    print("")
    
    repo_root = Path(__file__).parent.parent.resolve()
    print(f"  Repo location: {repo_root}")
    print("")
    
    all_ok = True
    
    # Check 1: ui/ folder exists
    ui_dir = repo_root / "ui"
    all_ok &= check("ui/ folder exists", ui_dir.exists(),
                    "Re-clone or re-download the repo")
    
    # Check 2: HTML files
    for html in ["index.html", "survey.html", "scout.html", "summary.html"]:
        f = ui_dir / html
        all_ok &= check(f"ui/{html} exists", f.exists(),
                        "Re-pull the repo")
    
    # Check 3: JSON data files
    json_files = {
        "team_dashboard_data.json": 100_000,  # min 100KB
        "survey_routing_data.json": 10_000,   # min 10KB
    }
    for fname, min_size in json_files.items():
        f = ui_dir / fname
        if not f.exists():
            all_ok &= check(f"ui/{fname} exists", False,
                            "Run 'git pull' or re-download ZIP")
            continue
        size = f.stat().st_size
        ok = size >= min_size
        all_ok &= check(f"ui/{fname} ({size//1024} KB)", ok,
                        "Data file is too small - re-pull")
    
    # Check 4: serve_dashboard.py
    server_script = repo_root / "tools" / "serve_dashboard.py"
    all_ok &= check("tools/serve_dashboard.py exists", server_script.exists(),
                    "Re-pull the repo")
    
    # Check 5: Python version
    py_ver = sys.version_info
    ok = py_ver >= (3, 9)
    all_ok &= check(f"Python {py_ver.major}.{py_ver.minor} (>= 3.9)", ok,
                    "Install Python 3.9+ from python.org")
    
    # Check 6: pythonw.exe (for desktop shortcut)
    if sys.platform == 'win32':
        pythonw = Path(sys.executable).parent / "pythonw.exe"
        check(f"pythonw.exe exists", pythonw.exists(),
              "May need to use python.exe for shortcut instead")
    
    # Check 7: Test JSON parses correctly
    try:
        import json
        data = json.loads((ui_dir / "team_dashboard_data.json").read_text(encoding='utf-8'))
        survey_count = len(data.get('survey', {}).get('records', []))
        scout_count = len(data.get('scout', {}).get('records', []))
        print("")
        print(f"  Data summary:")
        print(f"    Survey records:  {survey_count}")
        print(f"    Scout records:   {scout_count}")
        print(f"    Vendor configs:  {len(data.get('vendor_assignments', {}).get('vendors', []))}")
        check("JSON parses successfully", True)
    except Exception as e:
        all_ok = False
        check("JSON parses successfully", False, f"Error: {e}")
    
    # Check 8: Stale port files
    port_files = [repo_root / "output" / "dashboard.port",
                  ui_dir / "dashboard.port"]
    for pf in port_files:
        if pf.exists():
            print(f"  [INFO] Port file exists: {pf}")
            print(f"         If dashboard is broken, delete this file")
    
    print("")
    print("  ============================================")
    if all_ok:
        print("   [OK] All checks passed!")
        print("        Dashboard should work.")
        print("        Click your 'VUES Dashboard' desktop shortcut.")
    else:
        print("   [FAIL] Some checks failed - see above")
    print("  ============================================")
    print("")


if __name__ == "__main__":
    main()
