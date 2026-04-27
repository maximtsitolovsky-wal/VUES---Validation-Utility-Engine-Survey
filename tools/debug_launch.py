#!/usr/bin/env python3
"""Debug launcher - shows everything in console so we can see what's wrong."""

import sys
import os
import socket
import urllib.request
import json
import time
import webbrowser
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

print("")
print("  ============================================")
print("   VUES Dashboard - DEBUG MODE")
print("  ============================================")
print("")

repo_root = Path(__file__).parent.parent.resolve()
ui_dir = repo_root / "ui"
output_dir = repo_root / "output"

print(f"  Repo: {repo_root}")
print(f"  UI dir: {ui_dir}")
print(f"  Python: {sys.executable}")
print("")

# Clean up ALL stale port files
for port_file in [ui_dir / "dashboard.port", output_dir / "dashboard.port"]:
    if port_file.exists():
        try:
            port_file.unlink()
            print(f"  [CLEANED] Removed stale: {port_file}")
        except Exception as e:
            print(f"  [WARN] Couldn't remove {port_file}: {e}")

# Decide serve directory
serve_dir = output_dir if (output_dir / "team_dashboard_data.json").exists() else ui_dir
print(f"  Serving from: {serve_dir}")

# Verify data file
data_file = serve_dir / "team_dashboard_data.json"
if not data_file.exists():
    print(f"  [FATAL] Data file not found: {data_file}")
    input("  Press Enter to exit...")
    sys.exit(1)

print(f"  Data file: {data_file.stat().st_size // 1024} KB")
print("")

# Find free port (try 8765 first, then random)
def find_port():
    for p in [8765, 8766, 8767, 8768, 0]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', p))
                return s.getsockname()[1]
        except OSError:
            continue
    return None

port = find_port()
if not port:
    print("  [FATAL] No free port available!")
    input("  Press Enter to exit...")
    sys.exit(1)

print(f"  Starting server on port {port}...")
print("")

# Start the server
import http.server
import socketserver
import threading

os.chdir(serve_dir)

class LoggingHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"  [HTTP] {self.address_string()} - {format % args}")

# Write port file
(serve_dir / "dashboard.port").write_text(str(port))

# Open browser after a delay
def open_browser():
    time.sleep(1)
    url = f"http://localhost:{port}/index.html"
    print(f"  Opening browser: {url}")
    webbrowser.open(url)
    
    # Test that JSON loads
    time.sleep(1)
    try:
        r = urllib.request.urlopen(f"http://localhost:{port}/team_dashboard_data.json", timeout=5)
        size = len(r.read())
        print(f"  [TEST] JSON loaded: {size} bytes, status {r.status}")
        print("")
        print("  [SUCCESS] Dashboard should be working in your browser!")
        print("")
        print("  If browser shows 'Loading...' forever:")
        print("    1. Hard refresh: Ctrl+Shift+R")
        print("    2. Try Edge or Chrome (not IE)")
        print("    3. Check the [HTTP] logs above for errors")
    except Exception as e:
        print(f"  [TEST FAIL] Could not load JSON: {e}")

threading.Thread(target=open_browser, daemon=True).start()

print("  Press Ctrl+C to stop the server")
print("  -" * 22)

try:
    with socketserver.TCPServer(("", port), LoggingHandler) as httpd:
        httpd.serve_forever()
except KeyboardInterrupt:
    print("")
    print("  Stopped.")
finally:
    try:
        (serve_dir / "dashboard.port").unlink(missing_ok=True)
    except Exception:
        pass
