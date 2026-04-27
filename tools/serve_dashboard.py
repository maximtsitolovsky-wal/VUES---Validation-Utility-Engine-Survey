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
    # Find output directory (relative to script location)
    script_dir = Path(__file__).parent.parent.resolve()
    output_dir = script_dir / 'output'
    
    if not output_dir.exists():
        # Try creating a simple message for pythonw (no console)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, 
                f"Output directory not found:\n{output_dir}\n\nRun the pipeline first.",
                "VUES Dashboard", 
                0x10  # MB_ICONERROR
            )
        except Exception:
            pass
        return
    
    # Check if already running - just open browser to existing server
    existing_port = is_server_running(output_dir)
    if existing_port:
        webbrowser.open(f"http://localhost:{existing_port}/routing.html")
        return
    
    # Find a free port
    port = find_free_port()
    
    # Change to output directory
    os.chdir(output_dir)
    
    # Write port file
    write_port_file(output_dir, port)
    
    # Create handler
    handler = http.server.SimpleHTTPRequestHandler
    
    # Suppress logging for pythonw (no console)
    handler.log_message = lambda *args: None
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            url = f"http://localhost:{port}/routing.html"
            
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
        cleanup_files(output_dir)


if __name__ == "__main__":
    main()
