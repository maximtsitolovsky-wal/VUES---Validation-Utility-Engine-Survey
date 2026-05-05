#!/usr/bin/env python3
"""
VUES Orchestrator - Keeps all HTML files synced with live data.

Watches data files, auto-bakes HTML, and serves with live reload.
Run: uv run python tools/orchestrator.py
"""

import os
import sys
import json
import time
import shutil
import hashlib
import threading
import subprocess
import http.server
import socketserver
from pathlib import Path
from datetime import datetime

# === CONFIG ===
ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
UI_DIR = ROOT / "ui"
PORT = 58396
WATCH_INTERVAL = 5  # seconds between checks
AUTO_BAKE = True
AUTO_OPEN = True

# Files to watch for changes
WATCH_FILES = [
    OUTPUT_DIR / "team_dashboard_data.json",
    OUTPUT_DIR / "survey_routing_data.json",
]

# Track file hashes to detect changes
file_hashes = {}

def get_file_hash(filepath):
    """Get MD5 hash of file contents."""
    if not filepath.exists():
        return None
    return hashlib.md5(filepath.read_bytes()).hexdigest()

def check_for_changes():
    """Check if any watched files have changed."""
    changed = []
    for f in WATCH_FILES:
        current_hash = get_file_hash(f)
        if f in file_hashes and file_hashes[f] != current_hash:
            changed.append(f.name)
        file_hashes[f] = current_hash
    return changed

def sync_data_files():
    """Ensure ui/ has latest data from output/."""
    synced = []
    for src in WATCH_FILES:
        if src.exists():
            dst = UI_DIR / src.name
            if not dst.exists() or get_file_hash(src) != get_file_hash(dst):
                shutil.copy(src, dst)
                synced.append(src.name)
    return synced

def bake_html():
    """Run the bake script to embed data into HTML files."""
    bake_script = ROOT / "tools" / "bake_data_into_html.py"
    if not bake_script.exists():
        print("  [ERROR] bake_data_into_html.py not found!")
        return False
    
    result = subprocess.run(
        [sys.executable, str(bake_script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  [ERROR] Bake failed: {result.stderr}")
        return False
    
    return True

def copy_html_to_output():
    """Copy baked HTML from ui/ to output/."""
    copied = 0
    for html_file in UI_DIR.glob("*.html"):
        dst = OUTPUT_DIR / html_file.name
        shutil.copy(html_file, dst)
        copied += 1
    return copied

def regenerate_routing():
    """Regenerate routing data from sources."""
    regen_script = ROOT / "tools" / "regenerate_routing.py"
    if not regen_script.exists():
        return False
    
    result = subprocess.run(
        [sys.executable, str(regen_script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True
    )
    return result.returncode == 0

def print_status():
    """Print current data status."""
    print("\n" + "=" * 60)
    print("  VUES ORCHESTRATOR STATUS")
    print("=" * 60)
    
    # Check routing data
    routing_file = OUTPUT_DIR / "survey_routing_data.json"
    if routing_file.exists():
        data = json.loads(routing_file.read_text())
        summary = data.get("summary", {})
        print(f"  Routing Data:")
        print(f"    Ready to Assign: {summary.get('ready_to_assign', 0)}")
        print(f"    Pending Scout:   {summary.get('pending_scout', 0)}")
        print(f"    Surveys Complete: {summary.get('surveys_complete', 0)}")
        print(f"    Total Sites:     {summary.get('total_sites', 0)}")
    
    # Check team dashboard
    team_file = OUTPUT_DIR / "team_dashboard_data.json"
    if team_file.exists():
        data = json.loads(team_file.read_text())
        scout = data.get("scout", {})
        va = data.get("vendor_assignments", {})
        print(f"  Scout Data:")
        print(f"    Completion:      {scout.get('completion_rate', 0)}%")
        print(f"    Vendors:         {len(va.get('vendors', []))}")
    
    print(f"\n  Server: http://127.0.0.1:{PORT}/")
    print(f"  Watching: {len(WATCH_FILES)} files every {WATCH_INTERVAL}s")
    print("=" * 60 + "\n")

def watch_loop():
    """Background thread that watches for file changes."""
    print("[WATCH] Starting file watcher...")
    
    # Initialize hashes
    for f in WATCH_FILES:
        file_hashes[f] = get_file_hash(f)
    
    while True:
        time.sleep(WATCH_INTERVAL)
        
        changed = check_for_changes()
        if changed:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] 🔄 Changes detected: {', '.join(changed)}")
            
            # Sync and rebake
            synced = sync_data_files()
            if synced:
                print(f"  [SYNC] Copied to ui/: {', '.join(synced)}")
            
            if AUTO_BAKE:
                print("  [BAKE] Re-baking HTML files...")
                if bake_html():
                    copied = copy_html_to_output()
                    print(f"  [DONE] Baked and copied {copied} HTML files")
                    print("  [LIVE] Refresh your browser to see changes!")
                else:
                    print("  [ERROR] Bake failed!")

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that serves from output/ with minimal logging."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUTPUT_DIR), **kwargs)
    
    def log_message(self, format, *args):
        # Only log errors and HTML requests
        if args[1] == '200' and '.html' in args[0]:
            print(f"  [HTTP] {args[0]}")
        elif args[1] != '200':
            print(f"  [HTTP] {args[1]} - {args[0]}")

def run_server():
    """Run the HTTP server."""
    with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
        print(f"[SERVER] Running on http://127.0.0.1:{PORT}/")
        httpd.serve_forever()

def full_sync():
    """Do a full sync: regenerate routing, bake, copy."""
    print("\n[SYNC] Running full data sync...")
    
    # 1. Regenerate routing data
    print("  [1/3] Regenerating routing data...")
    if regenerate_routing():
        print("        ✓ Routing data regenerated")
    else:
        print("        ⚠ Routing regeneration skipped/failed")
    
    # 2. Sync data files to ui/
    print("  [2/3] Syncing data files...")
    synced = sync_data_files()
    print(f"        ✓ Synced {len(synced)} files")
    
    # 3. Bake HTML
    print("  [3/3] Baking HTML files...")
    if bake_html():
        copied = copy_html_to_output()
        print(f"        ✓ Baked and copied {copied} HTML files")
    else:
        print("        ✗ Bake failed!")
    
    print("[SYNC] Full sync complete!\n")

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    VUES ORCHESTRATOR                         ║
║         Keeping all your dashboards in sync!                 ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Initial full sync
    full_sync()
    
    # Print current status
    print_status()
    
    # Start file watcher in background
    watcher = threading.Thread(target=watch_loop, daemon=True)
    watcher.start()
    
    # Open browser
    if AUTO_OPEN:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
    
    # Run server (blocking)
    print("[READY] Orchestrator is running. Press Ctrl+C to stop.\n")
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n[STOP] Orchestrator stopped.")

if __name__ == "__main__":
    main()
