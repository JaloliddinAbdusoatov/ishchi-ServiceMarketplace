"""Small WSGI deployment; polling chat needs no WebSocket server."""
import os

bind = "127.0.0.1:8000"
worker_class = "gthread"
workers = int(os.environ.get("WEB_WORKERS", "2"))
threads = int(os.environ.get("WEB_THREADS", "2"))
if not 1 <= workers <= 8 or not 1 <= threads <= 8:
    raise ValueError("WEB_WORKERS and WEB_THREADS must be between 1 and 8.")
timeout = 45
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
worker_tmp_dir = "/tmp"
preload_app = False
accesslog = None  # Django logs route/status/request ID, never raw query strings.
errorlog = "-"
loglevel = "warning"
capture_output = False
forwarded_allow_ips = "127.0.0.1"  # nginx shares the backend network namespace.
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}
