#!/usr/bin/env python3

import json
import logging
import gzip
import os
import re
import base64
import random
from functools import lru_cache
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from io import BytesIO
import threading
import ssl
import urllib3

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging Configuration
logging.basicConfig(filename="server_activity.log", level=logging.INFO, format="%(asctime)s %(message)s")

# In-Memory Cache
CACHE = {}

# Dummy Base64 Content
SINGLE_BASE64_IMAGE = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAOxD1vwAAAAASUVORK5CYII=")
SINGLE_BASE64_VIDEO = base64.b64decode("GkXfo59ChoEBQveBAULy38ICAgICAAAAAQAAAEAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAEAAABA...")
SINGLE_BASE64_FLASH = base64.b64decode("Cws1RgAAAAIBAwABAAAAAAAAAAEAAQAAAABwZmZyABAAAwIBAAABAAQBBgAHBAgACAgLDAwAAwM=")
SINGLE_BASE64_PDF = base64.b64decode("JVBERi0xLjQKJcfsj6IKMSAwIG9iago8PC9UeXBlL1BhZ2UvUGFyZW50IDEgMCBSL0NvbnRlbnRzIDIgMCBSCj4+")
SINGLE_BASE64_FONT = base64.b64decode("AAEAAAALAIAAAwAwT1MvMhgBBkUAAAC8AAAAYGNtYXAAYxoAAAAqAAAACGZnbXAAa5w9AAAAMAAAAGRnYXNwAAAAEAAAACgAAAANnZXQgAAAABwAAAJgAAAA")

# Helper: Gzip Compression
def gzip_response(content):
    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as gz:
        gz.write(content)
    return buffer.getvalue()

# Dummy Response Generators
def generate_dummy_image():
    return gzip_response(SINGLE_BASE64_IMAGE)

def generate_dummy_video():
    return gzip_response(SINGLE_BASE64_VIDEO)

def generate_dummy_flash():
    return gzip_response(SINGLE_BASE64_FLASH)

def generate_dummy_pdf():
    return gzip_response(SINGLE_BASE64_PDF)

def generate_dummy_font():
    return gzip_response(SINGLE_BASE64_FONT)

# Static Dummy Responses
RESPONSES = {
    "image": generate_dummy_image(),
    "video": generate_dummy_video(),
    "flash": generate_dummy_flash(),
    "pdf": generate_dummy_pdf(),
    "font": generate_dummy_font(),
    "html": gzip_response(b"<html><body><h1>Blocked by AdBlocker Server</h1></body></html>"),
    "tracking": gzip_response(b'{"status": "blocked", "tracker_id": "dummy"}'),
    "ads": gzip_response(b"<html><body><h1>Dummy Ad Response</h1></body></html>"),
    "default": gzip_response(b"<html><body><h1>Default Response</h1></body></html>")
}

# Rate Limiting Configuration
REQUEST_COUNTS = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 100
RATE_LIMIT_LOCK = threading.Lock()

# Endpoint Configuration
LEARNED_ENDPOINTS_FILE = "learned_endpoints.json"
if os.path.exists(LEARNED_ENDPOINTS_FILE):
    with open(LEARNED_ENDPOINTS_FILE, "r") as f:
        learned_endpoints = json.load(f)
else:
    learned_endpoints = {}

# Blocked Paths
BLOCKED_PATHS = [
    ".env", ".git", "/cgi-bin/", "/wp-config.php", "/config.yml", "/phpinfo.php",
    "/dump.sql", "/server-status", "/database.sql", "/user_secrets.yml", "/.aws/credentials",
    "/etc/passwd", "/.ssh/", "/backup/", "/config/", "/logs/", "/libs/js/iframe.js",
    "/debug/default/view", "/druid/index.html", "/auth/login.php", "/auth/login.php?page="
]

# Ad & Tracking Servers
KNOWN_AD_TRACKERS = [
    "ads.js", "pagead.js", "analytics.js", "track.js", "facebook.com/tr",
    "google-analytics.com", "adservice.google.com", "doubleclick.net", "stats.wp.com",
    "hotjar.com", "sentry.io", "amazon-adsystem.com", "bing.com", "tiktok.com",
    "yahoo.com", "pinterest.com"
]

# Pattern Based Endpoints
PATTERN_BASED_ENDPOINTS = {
    re.compile(r"^/vendor/phpunit/.*"): "php",
    re.compile(r"^/user/.*"): "html",
    re.compile(r"^/containers/.*"): "html",
    re.compile(r"/tracking"): "tracking",
    re.compile(r"/ads"): "ads",
    re.compile(r"/extra/.*"): "threat",
    re.compile(r"/wp-includes/.*"): "default",
    re.compile(r"/actuator/.*"): "html",
    re.compile(r"/cgi-bin/.*"): "threat",
    re.compile(r"/social/.*"): "html",
    re.compile(r"/embed/.*"): "video",
    re.compile(r"/login"): "auth",
    re.compile(r"\.js$"): "javascript",
    re.compile(r"\.swf$"): "flash",
    re.compile(r"\.xml$"): "xml",
    re.compile(r"\.yaml$"): "yaml",
    re.compile(r"\.yml$"): "yaml",
    re.compile(r"\.json$"): "json",
    re.compile(r"\.jsonp$"): "jsonp",
    re.compile(r"\.webp$"): "webp",
    re.compile(r"\.wasm$"): "wasm",
    re.compile(r"\.pdf$"): "pdf",
    re.compile(r"/autodiscover/.*"): "autodiscover",
}

# HTTP Handler
class AdBlockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        original_host = self.headers.get("Host", "")
        path = self.path
        logging.info(f"GET request: Host={original_host}, Path={path}")

        # 1. Blockierte Pfade prüfen
        if any(blocked in path for blocked in BLOCKED_PATHS):
            logging.info(f"Blocked path detected: {path}")
            self.send_response(403)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            self.wfile.write(RESPONSES["html"])
            return

        # 2. Ad & Tracking Server prüfen
        if any(tracker in original_host for tracker in KNOWN_AD_TRACKERS):
            logging.info(f"Tracking/Ad server detected: {original_host}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            self.wfile.write(RESPONSES["tracking"])
            return

        # 3. Dynamische Antwort basierend auf Path
        if path in learned_endpoints:
            response_type = learned_endpoints[path]
            logging.info(f"Known endpoint {path} detected with type {response_type}")
        else:
            # Versuche anhand von Mustern zu matchen
            matched_type = next(
                (rtype for pattern, rtype in PATTERN_BASED_ENDPOINTS.items() if pattern.match(path)),
                None
            )
            response_type = matched_type if matched_type else "default"
            learned_endpoints[path] = response_type
            with open(LEARNED_ENDPOINTS_FILE, "w") as f:
                json.dump(learned_endpoints, f)
            logging.info(f"New endpoint {path} learned as type {response_type}")

        # 4. Antwort basierend auf dem erkannten Typ
        response = RESPONSES.get(response_type, RESPONSES["default"])
        self.send_response(200)
        self.send_header("Content-Type", "application/json" if response_type == "tracking" else "text/html")
        self.send_header("Content-Encoding", "gzip")
        self.end_headers()
        self.wfile.write(response)

# Threaded HTTP Server
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# Server-Funktionen
def start_http_server():
    server_address = ("127.0.0.1", 8082)  # HTTP-Port
    httpd = ThreadedHTTPServer(server_address, AdBlockHandler)
    logging.info("HTTP server running on port 8082")
    httpd.serve_forever()

def start_https_server():
    server_address = ("127.0.0.1", 8443)  # HTTPS-Port
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="/etc/letsencrypt/live/proxy.tue-hauptclan.eu/fullchain.pem",
                            keyfile="/etc/letsencrypt/live/proxy.tue-hauptclan.eu/privkey.pem")

    def ignore_sni(*args, **kwargs):
        return None

    context.set_servername_callback(ignore_sni)

    httpd = ThreadedHTTPServer(server_address, AdBlockHandler)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    logging.info("HTTPS server running on port 8443")
    httpd.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=start_http_server).start()
    threading.Thread(target=start_https_server).start()