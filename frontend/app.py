from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading

class AdBlockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Blocked by AdGuardX!")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multithreaded HTTP Server."""
    daemon_threads = True

def start_http_server(port=8080):
    server = ThreadedHTTPServer(("0.0.0.0", port), AdBlockHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"HTTP Server läuft auf Port {port}")
