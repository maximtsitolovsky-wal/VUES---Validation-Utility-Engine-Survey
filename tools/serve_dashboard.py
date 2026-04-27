#!/usr/bin/env python3
"""Simple dashboard server - finds free port and opens browser."""

import http.server
import socket
import socketserver
import webbrowser
import threading
from pathlib import Path

def find_free_port(preferred=8765):
    """Try preferred port first, fall back to any free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        if s.connect_ex(('127.0.0.1', preferred)) != 0:
            return preferred  # Port is free
    # Preferred taken, get any free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def main():
    # Find output directory
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / 'output'
    
    if not output_dir.exists():
        print(f"❌ Output directory not found: {output_dir}")
        print("   Run the pipeline first or check your working directory.")
        return
    
    port = find_free_port()
    
    # Change to output directory
    import os
    os.chdir(output_dir)
    
    # Create handler with no caching
    handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}/routing.html"
        print(f"")
        print(f"  🐕 VUES Dashboard Server")
        print(f"  ────────────────────────")
        print(f"  📍 Serving: {output_dir}")
        print(f"  🌐 URL: {url}")
        print(f"  ")
        print(f"  Press Ctrl+C to stop")
        print(f"")
        
        # Open browser after short delay
        def open_browser():
            import time
            time.sleep(0.5)
            webbrowser.open(url)
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  👋 Server stopped")

if __name__ == "__main__":
    main()
