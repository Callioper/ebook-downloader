"""FlareSolverr integration for Cloudflare/DDoS-Guard bypass."""

import subprocess
import time
import urllib.request
import json
import os
import shutil
import atexit


_flare_process = None


def start_flaresolverr(config, process_list=None) -> bool:
    """Start FlareSolverr as a subprocess if the binary exists."""
    global _flare_process

    flare_paths = [
        os.path.join(os.path.dirname(__file__), "..", "tools", "flaresolverr", "flaresolverr.exe"),
        os.path.join(os.path.dirname(__file__), "tools", "flaresolverr", "flaresolverr.exe"),
        # User may have downloaded FlareSolverr to a known location
        os.path.join(os.path.expanduser("~"), "flaresolverr", "flaresolverr.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "FlareSolverr", "flaresolverr.exe"),
        os.path.join("C:\\", "FlareSolverr", "flaresolverr.exe"),
        # Check PATH
        shutil.which("flaresolverr.exe") or "",
        shutil.which("flaresolverr") or "",
    ]
    flare_bin = None
    for p in flare_paths:
        if os.path.exists(p):
            flare_bin = p
            break

    if not flare_bin:
        return False

    try:
        _flare_process = subprocess.Popen(
            [flare_bin, "--port", "8191"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )

        if process_list is not None:
            process_list.append(_flare_process)

        # Wait for it to be ready (max 30s)
        for _ in range(60):
            if is_flaresolverr_ready():
                atexit.register(_stop_flaresolverr)
                return True
            time.sleep(0.5)

        return False
    except Exception:
        return False


def _stop_flaresolverr():
    global _flare_process
    if _flare_process:
        try:
            _flare_process.terminate()
            _flare_process.wait(timeout=5)
        except Exception:
            try:
                _flare_process.kill()
            except Exception:
                pass
        _flare_process = None


def is_flaresolverr_ready() -> bool:
    """Check if FlareSolverr is reachable."""
    try:
        req = urllib.request.Request(
            "http://localhost:8191/v1",
            data=json.dumps({
                "cmd": "request.get",
                "url": "https://www.google.com/",
                "maxTimeout": 5000,
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return data.get("status") == "ok"
    except Exception:
        return False


def solve_cloudflare(url: str, proxy: str = "", timeout: int = 60000) -> dict | None:
    """Solve a Cloudflare/DDoS-Guard challenge and return cookies + content."""
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": timeout,
    }
    if proxy:
        payload["proxy"] = {"url": proxy}

    try:
        req = urllib.request.Request(
            "http://localhost:8191/v1",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=timeout / 1000 + 30)
        data = json.loads(resp.read())
        if data.get("status") == "ok":
            solution = data.get("solution", {})
            return {
                "cookies": {c["name"]: c["value"] for c in solution.get("cookies", [])},
                "html": solution.get("response", ""),
                "url": solution.get("url", url),
                "user_agent": solution.get("userAgent", ""),
            }
    except Exception:
        pass
    return None
