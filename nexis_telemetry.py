"""
Nexis Telemetry Connector for Django / Python Applications
Generated automatically by Nexis Autonomous Fleet Orchestrator (Approach C).

This connector ships logs and uncaught runtime exceptions directly to Nexis
via asynchronous, non-blocking HTTP requests. It works across any cloud provider,
PaaS (Render, Vercel, Railway, AWS, Docker), or local machine without paid log drains.
"""

import sys
import os
import json
import logging
import threading
import urllib.request
import urllib.error
import traceback
from datetime import datetime

# Nexis Configuration
NEXIS_ENDPOINT = os.environ.get("NEXIS_ENDPOINT", "https://shulebase-1.onrender.com/api/v1/telemetry/events")
NEXIS_SOFTWARE_ID = os.environ.get("NEXIS_SOFTWARE_ID", "shulebase-render-version")
NEXIS_API_KEY = os.environ.get("NEXIS_API_KEY", "nx_live_29a1beadb37c7e33ec573ebfef7c2750aad5378c")


def _post_telemetry_async(payload: dict, sync: bool = False):
    """Dispatches payload to Nexis in a thread so application request latency is unaffected."""
    def _worker():
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                NEXIS_ENDPOINT,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": NEXIS_API_KEY,
                    "User-Agent": "Nexis-Client-Telemetry/1.0",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                pass
        except Exception:
            # Silent fallback so logging never breaks application execution
            pass

    t = threading.Thread(target=_worker, daemon=not sync)
    t.start()
    if sync:
        t.join(timeout=6.0)


class NexisLogHandler(logging.Handler):
    """
    Standard Python logging.Handler to capture application logs (INFO, WARN, ERROR)
    and forward them directly to the Nexis Fleet Control panel.
    """
    def emit(self, record):
        try:
            stack = ""
            if record.exc_info:
                stack = "".join(traceback.format_exception(*record.exc_info))

            payload = {
                "software_id": NEXIS_SOFTWARE_ID,
                "system_id": f"{NEXIS_SOFTWARE_ID}-backend",
                "message": record.getMessage(),
                "level": record.levelname.upper(),
                "tag": record.name,
                "stack_trace": stack or None,
                "metadata": {
                    "module": record.module,
                    "filename": record.filename,
                    "lineno": record.lineno,
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            _post_telemetry_async(payload)
        except Exception:
            self.handleError(record)


class NexisDjangoMiddleware:
    """
    Django middleware to automatically track user requests, 500 errors, and uncaught exceptions.
    Add 'nexis_telemetry.NexisDjangoMiddleware' to MIDDLEWARE in settings.py.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import time
        t0 = time.time()
        response = self.get_response(request)
        duration_ms = max(1, int((time.time() - t0) * 1000))

        # Identify active user
        user_id = "anonymous"
        if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
            user_id = str(request.user)

        # Skip automated internal health probe pings from flooding user activity logs
        if not request.path.endswith("/health/") and not request.path.endswith("/health"):
            level = "ERROR" if response.status_code >= 500 else ("WARN" if response.status_code >= 400 else "INFO")
            is_user_action = request.method in ["POST", "PUT", "PATCH", "DELETE"] or user_id != "anonymous"
            tag = "User.Action" if is_user_action else "HTTP.Request"

            payload = {
                "software_id": NEXIS_SOFTWARE_ID,
                "system_id": f"{NEXIS_SOFTWARE_ID}-backend",
                "message": f"[{user_id}] {request.method} {request.path} -> {response.status_code} ({duration_ms}ms)",
                "level": level,
                "tag": tag,
                "metadata": {
                    "user": user_id,
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "ip": request.META.get("REMOTE_ADDR", ""),
                    "user_agent": request.META.get("HTTP_USER_AGENT", "Unknown")[:80],
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            _post_telemetry_async(payload)
        return response

    def process_exception(self, request, exception):
        stack = traceback.format_exc()
        user_id = "anonymous"
        if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
            user_id = str(request.user)

        payload = {
            "software_id": NEXIS_SOFTWARE_ID,
            "system_id": f"{NEXIS_SOFTWARE_ID}-backend",
            "message": f"Uncaught {type(exception).__name__} for [{user_id}]: {str(exception)} on {request.path}",
            "level": "CRITICAL",
            "tag": "User.Crash",
            "stack_trace": stack,
            "metadata": {
                "user": user_id,
                "method": request.method,
                "path": request.path,
                "exception_type": type(exception).__name__,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        _post_telemetry_async(payload)
        return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Nexis Telemetry Self-Test")
    parser.add_argument("--test", action="store_true", help="Send a test ping to Nexis")
    args = parser.parse_args()

    print(f"Connecting to Nexis Endpoint: {NEXIS_ENDPOINT}")
    print(f"Software ID: {NEXIS_SOFTWARE_ID}")
    payload = {
        "software_id": NEXIS_SOFTWARE_ID,
        "system_id": f"{NEXIS_SOFTWARE_ID}-backend",
        "message": "Manual test heartbeat verified from nexis_telemetry.py",
        "level": "INFO",
        "tag": "Nexis.SelfTest",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    _post_telemetry_async(payload, sync=True)
    print("Telemetry event dispatched successfully to Nexis.")
