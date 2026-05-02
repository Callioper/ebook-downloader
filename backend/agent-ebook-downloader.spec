# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

BACKEND_DIR = Path(SPECPATH)
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"
NLC_DIR = BACKEND_DIR / "nlc"

a = Analysis(
    [str(BACKEND_DIR / "main.py")],
    pathex=[str(BACKEND_DIR)],
    binaries=[],
    datas=[
        (str(FRONTEND_DIST), "frontend/dist"),
        (str(NLC_DIR / "nlc_isbn.py"), "nlc/nlc_isbn.py"),
        (str(NLC_DIR / "bookmarkget.py"), "nlc/bookmarkget.py"),
        (str(NLC_DIR / "headers.py"), "nlc/headers.py"),
        (str(NLC_DIR / "formatting.py"), "nlc/formatting.py"),
        (str(BACKEND_DIR / "engine"), "engine"),
        (str(BACKEND_DIR / "tools/aria2c.exe"), "tools/aria2c.exe"),
    ],
    hiddenimports=[
        'uvicorn.logging', 'uvicorn.lifespan', 'uvicorn.protocols',
        'fastapi', 'pydantic',
        'bs4', 'bs4.builder', 'bs4.element',
        'requests', 'urllib3',
        'engine', 'engine.pipeline',
        'search_engine',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebChannel',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter','matplotlib','numpy.testing','cx_Freeze','ttkbootstrap'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    [], name='AgentEbookDownloader', debug=False, strip=False,
    upx=False, console=True, runtime_tmpdir=None,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
