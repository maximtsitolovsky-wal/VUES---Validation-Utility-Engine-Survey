#!/usr/bin/env python3
"""VUES Dashboard Server - Single instance, auto-finds port, opens browser."""

import http.server
import os
import socket
import socketserver
import sys
import webbrowser
import threading
from pathlib import Path

PORT_FILE = "dashboard.port"
PID_FILE = "dashboard.pid"
PREFERRED_PORT = 8765


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
    """Check if server is already running AND serving our dashboard.
    
    Returns port if running with valid data, None otherwise.
    """
    port_file = output_dir / PORT_FILE
    if not port_file.exists():
        return None
    
    try:
        port = int(port_file.read_text().strip())
        # Check if something is actually listening
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return None  # Not listening
        
        # Verify it's actually serving our dashboard (not some other app)
        import urllib.request
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
    
    # Stale or wrong server - remove the file
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
    """Show error to user (works with both pythonw and console)."""
    print(f"ERROR: {msg}", file=sys.stderr)
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, "VUES Dashboard", 0x10)
        except Exception:
            pass


def auto_pull_latest(repo_root: Path) -> bool:
    """Auto-pull latest data from git. Silent failure - won't block dashboard."""
    import subprocess
    git_dir = repo_root / '.git'
    if not git_dir.exists():
        return False  # Not a git repo (ZIP user)
    
    try:
        # Quick pull with timeout - don't hang the dashboard
        result = subprocess.run(
            ['git', 'pull', '--ff-only', '--quiet'],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=0x08000000 if sys.platform == 'win32' else 0,  # CREATE_NO_WINDOW
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def main():
    # Find UI directory (relative to script location)
    # UI folder is tracked in git - viewers can use it directly
    script_dir = Path(__file__).parent.parent.resolve()
    ui_dir = script_dir / 'ui'
    
    # AUTO-SYNC: Pull latest data from git before showing dashboard
    # This ensures viewers always see the freshest data
    auto_pull_latest(script_dir)
    
    # For viewers: serve from ui/ (tracked in git)
    # For admin: if output/ exists with data, prefer that for freshest data
    output_dir = script_dir / 'output'
    serve_dir = ui_dir  # Default to ui/
    
    # Admin mode: if output/ has the JSON data files, use it (fresher data)
    if (output_dir / 'team_dashboard_data.json').exists():
        serve_dir = output_dir
    
    # Verify required files exist
    if not serve_dir.exists():
        show_error(
            f"Dashboard directory not found:\n{serve_dir}\n\n"
            f"Run 'git pull' to get the latest files, or re-download the ZIP."
        )
        return
    
    data_file = serve_dir / 'team_dashboard_data.json'
    if not data_file.exists():
        show_error(
            f"Dashboard data file missing:\n{data_file}\n\n"
            f"Run 'git pull' to get the latest data."
        )
        return
    
    index_file = serve_dir / 'index.html'
    if not index_file.exists():
        show_error(
            f"Dashboard index.html missing:\n{index_file}\n\n"
            f"Run 'git pull' to get the latest files."
        )
        return
    
    # Check if already running - just open browser to existing server
    # Use output_dir for port file (if it exists), otherwise serve_dir
    port_file_dir = output_dir if output_dir.exists() else serve_dir
    existing_port = is_server_running(port_file_dir)
    if existing_port:
        webbrowser.open(f"http://localhost:{existing_port}/index.html")
        return
    
    # Find a free port
    port = find_free_port()
    
    # Change to serve directory
    os.chdir(serve_dir)
    
    # Write port file (to output dir if exists, for admin consistency)
    write_port_file(port_file_dir, port)
    
    # Create handler with no-cache headers so browser always shows fresh data
    class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            super().end_headers()

        def log_message(self, *args):
            pass  # Suppress logging for pythonw (no console)

    handler = NoCacheHandler
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            url = f"http://localhost:{port}/index.html"
            
            # Open browser after short delay
            def open_browser():
                import time
                time.sleep(0.5)
                webbrowser.open(url)
            
            threading.Thread(target=open_browser, daemon=True).start()
            
            httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    except OSError as e:
        show_error(f"Failed to start server on port {port}:\n{e}")
    except Exception as e:
        show_error(f"Unexpected error:\n{e}")
    finally:
        cleanup_files(port_file_dir)


if __name__ == "__main__":
    main()
