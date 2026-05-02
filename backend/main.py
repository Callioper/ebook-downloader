#!/usr/bin/env python3
"""Book Downloader Web Server — FastAPI entry point."""

import atexit
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import AppConfig
from task_store import TaskStore
from ws_manager import WebSocketManager
from api import search as search_api
from api import tasks as tasks_api
from api import ws as ws_api

config = AppConfig.load()
config.save()

task_store = TaskStore(config)
ws_manager = WebSocketManager()

search_api.config = config
tasks_api.init(task_store, ws_manager)
ws_api.init(task_store, ws_manager)

def _get_static_dir() -> Path:
    """Resolve frontend dist path (PyInstaller safe)."""
    meipass = getattr(sys, '_MEIPASS', '')
    if meipass:
        bundled = Path(meipass) / "frontend" / "dist"
        if (bundled / "index.html").exists():
            return bundled
    dev = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    return dev

STATIC_DIR = _get_static_dir()

_child_processes = []
_server = None


def _cleanup():
    """Kill all child processes on exit and stop server."""
    global _server
    if _server:
        _server.should_exit = True

    from engine.flaresolverr import _stop_flaresolverr
    _stop_flaresolverr()

    for p in list(_child_processes):
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    _child_processes.clear()


atexit.register(_cleanup)

try:
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
except (ValueError, AttributeError):
    pass
try:
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
except (ValueError, AttributeError):
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(config.download_dir, exist_ok=True)
    os.makedirs(config.tmp_dir, exist_ok=True)
    os.makedirs(config.finished_dir, exist_ok=True)

    from engine.flaresolverr import start_flaresolverr
    flare_ok = start_flaresolverr(config, _child_processes)
    if flare_ok:
        print("  FlareSolverr: started (Cloudflare bypass enabled)")

    yield

    from engine.flaresolverr import _stop_flaresolverr
    _stop_flaresolverr()


app = FastAPI(title="Book Downloader", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_api.router)
app.include_router(tasks_api.router)
app.include_router(ws_api.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


if STATIC_DIR.exists() and (STATIC_DIR / "index.html").is_file():

    @app.get("/")
    @app.get("/favicon.ico")
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str = ""):
        if full_path.startswith("api/") or full_path.startswith("ws/") or full_path.startswith("openapi"):
            return {"detail": "Not Found"}
        from fastapi.responses import HTMLResponse
        # Try exact file match first
        file_path = STATIC_DIR / (full_path or "index.html")
        if file_path.is_file():
            content = file_path.read_bytes()
            ext = file_path.suffix.lower()
            media_types = {
                ".html": "text/html", ".js": "application/javascript",
                ".css": "text/css", ".json": "application/json",
                ".png": "image/png", ".svg": "image/svg+xml",
                ".ico": "image/x-icon", ".woff2": "font/woff2",
                ".map": "application/json",
            }
            return HTMLResponse(content=content, media_type=media_types.get(ext, "text/plain"))
        # SPA fallback
        idx = STATIC_DIR / "index.html"
        if idx.is_file():
            return HTMLResponse(content=idx.read_bytes())
        return {"message": "Book Downloader API", "docs": "/docs", "frontend": "not found"}

else:
    @app.get("/")
    async def root():
        return {"message": "Book Downloader API", "docs": "/docs", "frontend": "not built"}


def run_server():
    global _server
    import uvicorn
    uvc = uvicorn.Config(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
    )
    _server = uvicorn.Server(uvc)
    _server.run()


def main():
    run_server()


if __name__ == "__main__":
    import sys
    import threading
    import time
    import webbrowser
    import subprocess

    if "--no-gui" in sys.argv or "--no-browser" in sys.argv:
        main()
    else:
        server_thread = threading.Thread(target=run_server, daemon=False)
        server_thread.start()

        url = f"http://localhost:{config.port}"
        print(f"\n  Book Downloader: {url}\n")

        # Wait for server to be ready
        for _ in range(50):
            try:
                import urllib.request
                urllib.request.urlopen(f"{url}/api/v1/status", timeout=0.5)
                break
            except Exception:
                time.sleep(0.1)

        # Try Edge app mode first (clean window), fallback to default browser
        opened = False
        for edge_path in [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]:
            if __import__("os").path.exists(edge_path):
                try:
                    edge_proc = subprocess.Popen(
                        [edge_path, f"--app={url}", "--new-window", "--window-size=1200,800"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    _child_processes.append(edge_proc)
                    opened = True
                    break
                except Exception:
                    pass

        if not opened:
            webbrowser.open(url)

        # Keep alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            _cleanup()
            server_thread.join(timeout=5)
            sys.exit(0)
