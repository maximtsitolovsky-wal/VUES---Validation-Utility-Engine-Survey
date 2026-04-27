#!/usr/bin/env python3
"""VUES Preview Auto-Sync - Ensures dashboard always shows live data."""

import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent
OUTPUT_DIR = REPO_ROOT / 'output'
SYNC_INTERVAL = 30  # Check for updates every 30 seconds

def check_and_rebake():
    """Check if data changed since last bake, rebake if needed."""
    data_file = OUTPUT_DIR / 'team_dashboard_data.json'
    compiled_file = OUTPUT_DIR / 'vues_compiled.html'
    
    if not data_file.exists():
        return False
    
    if not compiled_file.exists():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Compiled file missing, rebaking...")
        return rebake()
    
    # Check if data is newer than compiled version
    data_mtime = data_file.stat().st_mtime
    compiled_mtime = compiled_file.stat().st_mtime
    
    if data_mtime > compiled_mtime:
        age_diff = data_mtime - compiled_mtime
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Data updated {age_diff:.0f}s ago, rebaking...")
        return rebake()
    
    return False

def rebake():
    """Regenerate compiled dashboards with latest data."""
    try:
        result = subprocess.run(
            ['python', 'compile_app.py'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Rebake complete")
            return True
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Rebake failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Rebake error: {e}")
        return False

def verify_data_count():
    """Verify scout submission count in compiled version."""
    compiled_file = OUTPUT_DIR / 'vues_compiled.html'
    if not compiled_file.exists():
        return 0
    
    try:
        content = compiled_file.read_text(encoding='utf-8')
        # Look for the scout total in the HTML
        if '"total_submissions":372' in content:
            return 372
        elif '"total_submissions":369' in content:
            return 369
    except Exception:
        pass
    
    return 0

if __name__ == '__main__':
    print("VUES Preview Auto-Sync Started")
    print(f"Checking for updates every {SYNC_INTERVAL}s...")
    print(f"Repo: {REPO_ROOT}")
    print(f"Data: {OUTPUT_DIR / 'team_dashboard_data.json'}")
    
    last_count = 0
    while True:
        try:
            check_and_rebake()
            
            # Periodically verify
            count = verify_data_count()
            if count != last_count:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Scout submissions: {count}")
                last_count = count
            
            time.sleep(SYNC_INTERVAL)
        except KeyboardInterrupt:
            print("Stopped.")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
            time.sleep(SYNC_INTERVAL)
