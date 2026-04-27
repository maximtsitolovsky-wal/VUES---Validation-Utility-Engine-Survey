#!/usr/bin/env python3
"""One-time data push to git (for when auto-push isn't running)."""

import subprocess
import json
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = REPO_ROOT / 'output'
DATA_FILE = OUTPUT_DIR / 'team_dashboard_data.json'

def get_scout_count():
    """Extract scout submission count."""
    try:
        d = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        return d.get('scout', {}).get('total_submissions', 0)
    except Exception:
        return 0

def push_now():
    """Push current data to git immediately."""
    count = get_scout_count()
    
    print(f"Pushing: {count} scout submissions")
    
    # Stage
    subprocess.run(
        ['git', 'add', 
         'output/team_dashboard_data.json',
         'output/vues_compiled.html',
         'output/vues_exact_clone.html'],
        cwd=REPO_ROOT
    )
    
    # Commit
    commit_msg = f'data: manual push - {count} submissions ({datetime.now().isoformat()})'
    subprocess.run(
        ['git', 'commit', '-m', commit_msg],
        cwd=REPO_ROOT
    )
    
    # Push
    result = subprocess.run(
        ['git', 'push', 'origin', 'main'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"SUCCESS: Pushed {count} submissions")
    else:
        print(f"FAILED: {result.stderr}")

if __name__ == '__main__':
    push_now()
