# Agent Ebook Downloader — Build Script for Windows .exe
# Usage: python build_exe.py

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
OUTPUT_DIR = PROJECT_ROOT / "dist"


def step(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def build_frontend():
    step("Building frontend (Vite)...")
    subprocess.run(
        ["npm", "install"],
        cwd=str(FRONTEND_DIR),
        check=True,
        shell=True,
    )
    subprocess.run(
        ["npm", "run", "build"],
        cwd=str(FRONTEND_DIR),
        check=True,
        shell=True,
    )
    dist = FRONTEND_DIR / "dist"
    if not dist.exists():
        raise RuntimeError("Frontend build failed: dist/ not found")
    print(f"  Frontend built: {dist}")


def build_pyinstaller():
    step("Building PyInstaller executable...")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "agent-ebook-downloader.spec"],
        cwd=str(BACKEND_DIR),
        check=True,
    )
    exe = BACKEND_DIR / "dist" / "AgentEbookDownloader.exe"
    if not exe.exists():
        raise RuntimeError(f"PyInstaller build failed: {exe} not found")
    print(f"  Executable built: {exe}")
    return exe


def copy_output(exe_path: Path):
    step("Collecting output...")
    OUTPUT_DIR.mkdir(exist_ok=True)

    dest_exe = OUTPUT_DIR / "AgentEbookDownloader.exe"
    shutil.copy2(exe_path, dest_exe)

    config_default = BACKEND_DIR.parent / "config.default.json"
    if config_default.exists():
        shutil.copy2(config_default, OUTPUT_DIR / "config.default.json")

    readme = PROJECT_ROOT / "README.md"
    if readme.exists():
        shutil.copy2(readme, OUTPUT_DIR / "README.txt")

    print(f"\n  Output: {OUTPUT_DIR}")
    for f in sorted(OUTPUT_DIR.iterdir()):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"    {f.name} ({size_mb:.1f} MB)")


def main():
    os.chdir(str(PROJECT_ROOT))

    build_frontend()
    exe_path = build_pyinstaller()
    copy_output(exe_path)

    step("Build complete!")
    print(f"  Executable: {OUTPUT_DIR / 'AgentEbookDownloader.exe'}")
    print(f"  Run: {OUTPUT_DIR / 'AgentEbookDownloader.exe'}")
    print(f"  Web UI: http://localhost:8000")
    print(f"  API docs: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
