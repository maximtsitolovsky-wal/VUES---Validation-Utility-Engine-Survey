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
    """Check if server is already running. Returns port if running, None otherwise."""
    port_file = output_dir / PORT_FILE
    if not port_file.exists():
        return None
    
    try:
        port = int(port_file.read_text().strip())
        # Check if something is actually listening
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(('127.0.0.1', port)) == 0:
                return port  # Server is running
    except (ValueError, OSError):
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


def main():
    # Find UI directory (relative to script location)
    # UI folder is tracked in git - viewers can use it directly
    script_dir = Path(__file__).parent.parent.resolve()
    ui_dir = script_dir / 'ui'
    
    # For viewers: serve from ui/ (tracked in git)
    # For admin: if output/ exists with data, prefer that for freshest data
    output_dir = script_dir / 'output'
    serve_dir = ui_dir  # Default to ui/
    
    # Admin mode: if output/ has the JSON data files, use it (fresher data)
    if (output_dir / 'team_dashboard_data.json').exists():
        serve_dir = output_dir
    
    if not serve_dir.exists():
        # Try creating a simple message for pythonw (no console)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, 
                f"Dashboard directory not found:\n{serve_dir}\n\nCheck your installation.",
                "VUES Dashboard", 
                0x10  # MB_ICONERROR
            )
        except Exception:
            pass
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
    
    # Create handler
    handler = http.server.SimpleHTTPRequestHandler
    
    # Suppress logging for pythonw (no console)
    handler.log_message = lambda *args: None
    
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
    except Exception:
        pass
    finally:
        cleanup_files(port_file_dir)


if __name__ == "__main__":
    main()
