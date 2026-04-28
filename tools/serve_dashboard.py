#!/usr/bin/env python3
"""VUES Dashboard Server - With Airtable sync for shared routing edits.

Features:
- Auto-pulls from git on launch (viewers get latest data)
- Auto-syncs every hour (continuous updates while running)
- Airtable API for shared routing table edits
- Single instance per machine (reuses existing server)
"""

import http.server
import json
import os
import socket
import socketserver
import sys
import time
import webbrowser
import threading
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

PORT_FILE = "dashboard.port"
PID_FILE = "dashboard.pid"
PREFERRED_PORT = 8765
AUTO_SYNC_INTERVAL = 3600  # Sync every hour (in seconds)

# Airtable config - loaded from user config
AIRTABLE_CONFIG = {}


def load_airtable_config():
    """Load Airtable config from user's config.json."""
    global AIRTABLE_CONFIG
    config_path = Path.home() / '.siteowlqa' / 'config.json'
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            AIRTABLE_CONFIG = {
                'token': config.get('scout_airtable_token', ''),
                'base_id': config.get('scout_airtable_base_id', ''),
                'table_name': 'Survey Routing',
            }
            return True
        except Exception as e:
            print(f"Warning: Could not load Airtable config: {e}")
    return False


def find_free_port():
    """Try preferred port first, fall back to any free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        if s.connect_ex(('127.0.0.1', PREFERRED_PORT)) != 0:
            return PREFERRED_PORT
    # Preferred taken, get any free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def is_server_running(output_dir: Path) -> int | None:
    """Check if server is already running AND serving our dashboard."""
    port_file = output_dir / PORT_FILE
    if not port_file.exists():
        return None
    
    try:
        port = int(port_file.read_text().strip())
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return None
        
        try:
            req = urllib.request.Request(
                f'http://127.0.0.1:{port}/team_dashboard_data.json',
                method='HEAD'
            )
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    return port
        except Exception:
            pass
    except (ValueError, OSError):
        pass
    
    try:
        port_file.unlink(missing_ok=True)
    except OSError:
        pass
    return None


def write_port_file(output_dir: Path, port: int):
    """Write the port file so other instances know we're running."""
    try:
        (output_dir / PORT_FILE).write_text(str(port))
        (output_dir / PID_FILE).write_text(str(os.getpid()))
    except OSError:
        pass


def cleanup_files(output_dir: Path):
    """Clean up port/pid files on shutdown."""
    try:
        (output_dir / PORT_FILE).unlink(missing_ok=True)
        (output_dir / PID_FILE).unlink(missing_ok=True)
    except OSError:
        pass


def show_error(msg: str):
    """Show error to user."""
    print(f"ERROR: {msg}", file=sys.stderr)
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, "VUES Dashboard", 0x10)
        except Exception:
            pass


def auto_pull_latest(repo_root: Path) -> tuple[bool, str]:
    """Auto-pull latest data from git."""
    import subprocess
    git_dir = repo_root / '.git'
    if not git_dir.exists():
        return False, "Not a git clone - auto-updates disabled"
    
    try:
        result = subprocess.run(
            ['git', 'pull', '--ff-only', '--quiet'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=0x08000000 if sys.platform == 'win32' else 0,
        )
        if result.returncode == 0:
            return True, "Updated to latest"
        else:
            return False, f"Pull failed: {result.stderr[:100] if result.stderr else 'unknown error'}"
    except subprocess.TimeoutExpired:
        return False, "Git pull timed out"
    except FileNotFoundError:
        return False, "Git not installed"
    except OSError as e:
        return False, f"OS error: {e}"


def start_background_sync(repo_root: Path, interval: int = AUTO_SYNC_INTERVAL):
    """Start background sync thread."""
    def sync_loop():
        while True:
            time.sleep(interval)
            try:
                auto_pull_latest(repo_root)
            except Exception:
                pass
    
    sync_thread = threading.Thread(target=sync_loop, daemon=True)
    sync_thread.start()
    return sync_thread


# ============== AIRTABLE API FUNCTIONS ==============

def airtable_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make request to Airtable API."""
    if not AIRTABLE_CONFIG.get('token'):
        return {'error': 'Airtable not configured'}
    
    base_id = AIRTABLE_CONFIG['base_id']
    table = urllib.parse.quote(AIRTABLE_CONFIG['table_name'])
    url = f"https://api.airtable.com/v0/{base_id}/{table}{endpoint}"
    
    headers = {
        'Authorization': f"Bearer {AIRTABLE_CONFIG['token']}",
        'Content-Type': 'application/json',
    }
    
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return {'error': f"HTTP {e.code}: {error_body[:200]}"}
    except Exception as e:
        return {'error': str(e)}


def airtable_list_all() -> list:
    """Fetch all records from Airtable Survey Routing table."""
    all_records = []
    offset = None
    
    while True:
        endpoint = f"?pageSize=100"
        if offset:
            endpoint += f"&offset={offset}"
        
        result = airtable_request('GET', endpoint)
        if 'error' in result:
            return []
        
        all_records.extend(result.get('records', []))
        offset = result.get('offset')
        if not offset:
            break
    
    return all_records


def airtable_find_by_site(site: str) -> dict | None:
    """Find a record by site number."""
    endpoint = f"?filterByFormula={{Site}}='{site}'&maxRecords=1"
    result = airtable_request('GET', endpoint)
    records = result.get('records', [])
    return records[0] if records else None


def airtable_update_record(record_id: str, fields: dict) -> dict:
    """Update a single record in Airtable."""
    return airtable_request('PATCH', f"/{record_id}", {'fields': fields})


# ============== HTTP HANDLER WITH API ==============

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with Airtable API endpoints."""
    
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def log_message(self, *args):
        pass  # Suppress logging
    
    def send_json(self, data: dict, status: int = 200):
        """Send JSON response."""
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path.startswith('/api/survey-routing/list'):
            self.handle_routing_list()
        else:
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path.startswith('/api/survey-routing/update'):
            self.handle_routing_update()
        else:
            self.send_error(404, 'Not Found')
    
    def handle_routing_list(self):
        """GET /api/survey-routing/list - Fetch all routing data from Airtable."""
        records = airtable_list_all()
        
        # Convert Airtable format to our format
        rows = []
        for rec in records:
            fields = rec.get('fields', {})
            rows.append({
                'id': rec['id'],
                'site': fields.get('Site', ''),
                'vendor': fields.get('Vendor', ''),
                'status': fields.get('Status', ''),
                'survey_type': fields.get('Survey Type', ''),
                'survey_required': 'YES' if fields.get('Survey Required') else 'NO',
                'notes': fields.get('Notes', ''),
                'days_to_construction': str(fields.get('Days to Construction', '')),
            })
        
        self.send_json({'rows': rows, 'count': len(rows)})
    
    def handle_routing_update(self):
        """POST /api/survey-routing/update - Update a routing record in Airtable."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
        except Exception as e:
            self.send_json({'error': f'Invalid JSON: {e}'}, 400)
            return
        
        site = data.get('site')
        updates = data.get('updates', {})
        
        if not site:
            self.send_json({'error': 'Missing site'}, 400)
            return
        
        # Find the record by site
        record = airtable_find_by_site(site)
        if not record:
            self.send_json({'error': f'Site {site} not found'}, 404)
            return
        
        # Map our field names to Airtable field names
        field_map = {
            'status': 'Status',
            'survey_type': 'Survey Type',
            'notes': 'Notes',
            'survey_required': 'Survey Required',
            'survey_complete': 'Survey Required',  # Using same field
        }
        
        airtable_fields = {}
        for key, value in updates.items():
            if key in field_map:
                airtable_fields[field_map[key]] = value
        
        if not airtable_fields:
            self.send_json({'error': 'No valid fields to update'}, 400)
            return
        
        # Update in Airtable
        result = airtable_update_record(record['id'], airtable_fields)
        
        if 'error' in result:
            self.send_json({'error': result['error']}, 500)
        else:
            self.send_json({'success': True, 'site': site})


def main():
    script_dir = Path(__file__).parent.parent.resolve()
    ui_dir = script_dir / 'ui'
    
    # Load Airtable config for shared routing
    if load_airtable_config():
        print("Airtable config loaded - shared routing enabled")
    else:
        print("Warning: Airtable config not found - routing edits will be local only")
    
    # Auto-pull from git
    auto_pull_latest(script_dir)
    
    # Start background sync
    start_background_sync(script_dir)
    
    # Determine serve directory
    output_dir = script_dir / 'output'
    serve_dir = ui_dir
    if (output_dir / 'team_dashboard_data.json').exists():
        serve_dir = output_dir
    
    # Verify files exist
    if not serve_dir.exists():
        show_error(f"Dashboard directory not found: {serve_dir}")
        return
    
    data_file = serve_dir / 'team_dashboard_data.json'
    if not data_file.exists():
        show_error(f"Dashboard data file missing: {data_file}")
        return
    
    # Check for existing server
    port_file_dir = output_dir if output_dir.exists() else serve_dir
    existing_port = is_server_running(port_file_dir)
    if existing_port:
        webbrowser.open(f"http://localhost:{existing_port}/index.html")
        return
    
    # Start server
    port = find_free_port()
    os.chdir(serve_dir)
    write_port_file(port_file_dir, port)
    
    try:
        with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
            url = f"http://localhost:{port}/index.html"
            
            def open_browser():
                time.sleep(0.5)
                webbrowser.open(url)
            
            threading.Thread(target=open_browser, daemon=True).start()
            print(f"VUES Dashboard running at {url}")
            print("Routing changes will sync via Airtable")
            httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        show_error(f"Server error: {e}")
    finally:
        cleanup_files(port_file_dir)


if __name__ == "__main__":
    main()
