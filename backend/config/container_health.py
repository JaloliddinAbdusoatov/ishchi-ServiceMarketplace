"""Dependency-free loopback liveness probe; never checks external services."""
import os
import urllib.request


def main():
    host = os.environ.get("HEALTHCHECK_HOST", "").strip()
    if not host or any(char in host for char in "\r\n/ "):
        return 1
    request = urllib.request.Request("http://127.0.0.1:8000/api/v1/health/live/", headers={"Host": host})
    # Proxy environment variables must not redirect this local probe externally.
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=3) as response:
            return 0 if response.status == 200 else 1
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
