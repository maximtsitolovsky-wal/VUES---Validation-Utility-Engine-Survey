#!/usr/bin/env python3
"""Auto-publish viewer data to git (for truly live viewer experience).

This script monitors output/team_dashboard_data.json and when it changes:
1. Copies data from output/ to ui/ (what viewers get)
2. Bakes data into HTML files
3. Commits and pushes to git

Viewers will see updates within ~30 seconds of data changing.
"""

import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
import sys

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = REPO_ROOT / 'output'
DATA_FILE = OUTPUT_DIR / 'team_dashboard_data.json'
COMPILED_FILE = OUTPUT_DIR / 'vues_compiled.html'

def get_last_committed_hash(filepath: Path) -> str:
    """Get last committed hash of a file."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', f'HEAD:{filepath.relative_to(REPO_ROOT)}'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ''

def get_current_hash(filepath: Path) -> str:
    """Get hash of current file content."""
    if not filepath.exists():
        return ''
    try:
        result = subprocess.run(
            ['git', 'hash-object', str(filepath)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ''

def get_scout_count() -> int:
    """Extract scout submission count from data file."""
    try:
        if not DATA_FILE.exists():
            return 0
        d = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        return d.get('scout', {}).get('total_submissions', 0)
    except Exception:
        return 0

def publish_to_viewers() -> bool:
    """Run publish_viewer_data.py to sync output/ -> ui/ and push."""
    publish_script = REPO_ROOT / 'tools' / 'publish_viewer_data.py'
    if not publish_script.exists():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: publish_viewer_data.py not found")
        return False
    
    try:
        result = subprocess.run(
            ['python', str(publish_script)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )
        return 'pushed to repository' in result.stdout.lower() or 'already up to date' in result.stdout.lower()
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Publish error: {e}")
        return False

def push_changes(count: int) -> bool:
    """Publish viewer data (copies output/ -> ui/, bakes HTML, commits, pushes)."""
    try:
        # Use the proper publish script instead of direct git commands
        if publish_to_viewers():
            print(f"[{datetime.now().strftime('%H:%M:%S')}] PUBLISHED: {count} submissions to viewers")
            return True
        return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
        return False

def push_changes_OLD(count: int) -> bool:
    """OLD: Commit and push data + compiled changes (doesn't work because output/ is gitignored)."""
    try:
        # Stage files
        subprocess.run(
            ['git', 'add', 
             'output/team_dashboard_data.json',
             'output/vues_compiled.html',
             'output/vues_exact_clone.html'],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=5
        )
        
        # Check if there are staged changes
        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            cwd=REPO_ROOT,
            timeout=5
        )
        
        if result.returncode != 0:  # Changes exist
            # Commit
            commit_msg = f'data: live scout sync - {count} submissions ({datetime.now().isoformat()})'
            result = subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Push
                result = subprocess.run(
                    ['git', 'push', 'origin', 'main'],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] PUSHED: {count} submissions")
                    return True
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Push failed: {result.stderr}")
                    return False
        
        return False
    except subprocess.TimeoutExpired:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Git operation timeout")
        return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
        return False

def watch_and_push(check_interval: int = 15):
    """Watch data file and push when it changes."""
    print("VUES Auto-Push Started (Truly Live Mode)")
    print(f"Checking for changes every {check_interval}s...")
    print(f"Repo: {REPO_ROOT}")
    print(f"Data: {DATA_FILE}")
    print(f"Compiled: {COMPILED_FILE}")
    print()
    
    last_count = 0
    consecutive_fails = 0
    
    while True:
        try:
            count = get_scout_count()
            
            # Log count changes
            if count != last_count:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Scout submissions changed: {last_count} → {count}")
                last_count = count
            
            # Check if data file is different from committed version
            data_committed = get_last_committed_hash(DATA_FILE)
            data_current = get_current_hash(DATA_FILE)
            
            if data_committed != data_current:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Data changed, pushing...")
                if push_changes(count):
                    consecutive_fails = 0
                else:
                    consecutive_fails += 1
                    if consecutive_fails >= 3:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Push failed 3x, check git/network")
            
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Unexpected error: {e}")
            time.sleep(check_interval)

if __name__ == '__main__':
    watch_and_push(check_interval=15)
