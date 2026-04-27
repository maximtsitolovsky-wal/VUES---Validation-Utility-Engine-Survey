#!/usr/bin/env python3
"""
Publish fresh data to viewers.

Run this when you want viewers to get your latest dashboard data.
Copies JSON from output/ to ui/ and commits.
"""
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
OUTPUT_DIR = REPO_ROOT / 'output'
UI_DIR = REPO_ROOT / 'ui'

DATA_FILES = [
    'team_dashboard_data.json',
    'survey_routing_data.json',
]


def main():
    print("")
    print("  ===========================================")
    print("   VUES - Publish Viewer Data")
    print("  ===========================================")
    print("")
    
    # Check output exists
    if not OUTPUT_DIR.exists():
        print("  [ERROR] output/ folder not found!")
        print("     Run the pipeline first to generate data.")
        return 1
    
    # Copy each data file
    copied = 0
    for filename in DATA_FILES:
        src = OUTPUT_DIR / filename
        dst = UI_DIR / filename
        if src.exists():
            shutil.copy2(src, dst)
            size_kb = src.stat().st_size / 1024
            print(f"  [OK] {filename} ({size_kb:.1f} KB)")
            copied += 1
        else:
            print(f"  [WARN] {filename} not found in output/")
    
    if copied == 0:
        print("")
        print("  [ERROR] No data files to publish!")
        return 1
    
    print("")
    print("  ─────────────────────────────────────────")
    print(f"  Copied {copied} file(s) to ui/")
    print("")
    
    # Git add + commit + push
    print("  Committing and pushing...")
    try:
        subprocess.run(['git', 'add'] + [f'ui/{f}' for f in DATA_FILES], 
                       cwd=REPO_ROOT, check=True, capture_output=True)
        
        result = subprocess.run(
            ['git', 'commit', '-m', 'data: publish latest dashboard data for viewers'],
            cwd=REPO_ROOT, capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # Push
            subprocess.run(['git', 'push'], cwd=REPO_ROOT, check=True, capture_output=True)
            print("  [OK] Data pushed to repository!")
            print("")
            print("  ===========================================")
            print("   Viewers can now git pull or re-download")
            print("   to see your latest data!")
            print("  ===========================================")
        else:
            if "nothing to commit" in result.stdout:
                print("  [INFO] No changes - data already up to date")
            else:
                print(f"  [WARN] Git commit: {result.stderr[:100]}")
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Git error: {e}")
    
    print("")
    return 0


if __name__ == "__main__":
    exit(main())
