#!/usr/bin/env python3
"""
Titan-7 Public File Server
Serves the entire Titan-7 folder over HTTP with download capabilities
"""

import os
import sys
import http.server
import socketserver
import argparse
from pathlib import Path
import threading
import socket

class TitanFileHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler with directory listing and download support"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=kwargs.pop('directory', None), **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()
    
    def do_GET(self):
        if self.path.endswith('?download'):
            self.path = self.path.replace('?download', '')
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(self.path)}"')
            self.end_headers()
            
            file_path = self.translate_path(self.path)
            if os.path.isfile(file_path):
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            return
        
        return super().do_GET()
    
    def list_directory(self, path):
        try:
            list_dir = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None
        
        list_dir.sort(key=lambda a: a.lower())
        
        displaypath = self.path
        enc = sys.getfilesystemencoding()
        title = f'Titan-7 File Server - {displaypath}'
        
        r = []
        r.append('<!DOCTYPE HTML>')
        r.append('<html><head>')
        r.append(f'<meta charset="{enc}">')
        r.append(f'<title>{title}</title>')
        r.append('<style>')
        r.append('body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }')
        r.append('h1 { color: #00ff88; border-bottom: 2px solid #00ff88; padding-bottom: 10px; }')
        r.append('a { color: #00aaff; text-decoration: none; }')
        r.append('a:hover { text-decoration: underline; }')
        r.append('table { width: 100%; border-collapse: collapse; margin-top: 20px; }')
        r.append('th { background: #2a2a2a; padding: 10px; text-align: left; border-bottom: 2px solid #00ff88; }')
        r.append('td { padding: 8px; border-bottom: 1px solid #333; }')
        r.append('tr:hover { background: #2a2a2a; }')
        r.append('.download-btn { background: #00ff88; color: #000; padding: 4px 12px; border-radius: 4px; margin-left: 10px; font-size: 0.9em; }')
        r.append('.download-btn:hover { background: #00cc66; }')
        r.append('.size { color: #888; font-size: 0.9em; }')
        r.append('.dir { color: #00ff88; font-weight: bold; }')
        r.append('</style>')
        r.append('</head><body>')
        r.append(f'<h1>{title}</h1>')
        r.append('<table>')
        r.append('<tr><th>Name</th><th>Size</th><th>Actions</th></tr>')
        
        if displaypath != '/':
            r.append('<tr><td colspan="3"><a href="../" class="dir">📁 Parent Directory</a></td></tr>')
        
        for name in list_dir:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
                size = "-"
                icon = "📁"
                download_link = ""
            else:
                size_bytes = os.path.getsize(fullname)
                if size_bytes < 1024:
                    size = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size = f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    size = f"{size_bytes / (1024 * 1024):.1f} MB"
                else:
                    size = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
                icon = "📄"
                download_link = f'<a href="{linkname}?download" class="download-btn">⬇ Download</a>'
            
            r.append(f'<tr>')
            r.append(f'<td>{icon} <a href="{linkname}">{displayname}</a></td>')
            r.append(f'<td class="size">{size}</td>')
            r.append(f'<td>{download_link}</td>')
            r.append(f'</tr>')
        
        r.append('</table>')
        r.append('<hr>')
        r.append('<p style="color: #888; font-size: 0.9em;">Titan-7 Public File Server | Click files to view or use Download button</p>')
        r.append('</body></html>')
        
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        self.send_response(200)
        self.send_header("Content-type", f"text/html; charset={enc}")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        return None


def get_local_ip():
    """Get the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def run_server(port=8000, host='0.0.0.0', directory=None):
    """Run the HTTP file server"""
    
    if directory is None:
        directory = os.getcwd()
    
    directory = os.path.abspath(directory)
    
    print("=" * 70)
    print("🚀 TITAN-7 PUBLIC FILE SERVER")
    print("=" * 70)
    print(f"📁 Serving directory: {directory}")
    print(f"🌐 Binding to: {host}:{port}")
    print()
    
    handler = lambda *args, **kwargs: TitanFileHandler(*args, directory=directory, **kwargs)
    
    with socketserver.TCPServer((host, port), handler) as httpd:
        local_ip = get_local_ip()
        
        print("✅ Server is running!")
        print()
        print("📡 Access URLs:")
        print(f"   Local:    http://localhost:{port}")
        print(f"   Network:  http://{local_ip}:{port}")
        if host == '0.0.0.0':
            print(f"   Public:   http://YOUR_PUBLIC_IP:{port}")
        print()
        print("⚠️  SECURITY WARNING:")
        print("   This server allows ANYONE with network access to download ALL files!")
        print("   Make sure your firewall is configured properly.")
        print()
        print("🛑 Press Ctrl+C to stop the server")
        print("=" * 70)
        print()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Server stopped by user")
            print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Titan-7 Public File Server - Share files over HTTP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Serve current directory on port 8000
  python titan_file_server.py
  
  # Serve specific directory on custom port
  python titan_file_server.py --port 9000 --dir /path/to/titan-7
  
  # Bind to specific interface
  python titan_file_server.py --host 192.168.1.100 --port 8080
        """
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='Port to bind to (default: 8000)'
    )
    
    parser.add_argument(
        '--host', '-H',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0 - all interfaces)'
    )
    
    parser.add_argument(
        '--dir', '-d',
        type=str,
        default=None,
        help='Directory to serve (default: current directory)'
    )
    
    args = parser.parse_args()
    
    run_server(port=args.port, host=args.host, directory=args.dir)


if __name__ == '__main__':
    main()
