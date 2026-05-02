import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Query, HTTPException, UploadFile, File
from pydantic import BaseModel

from config import AppConfig
from search_engine import search_books as sqlite_search_books
from search_engine import get_available_dbs as sqlite_get_dbs
from search_engine import _resolve_db_dir
from engine.pipeline import _search_annas_archive
from engine.zlib_downloader import zlib_search

router = APIRouter()
config = AppConfig.load()


def _fetch_md5_page_info(md5: str, config: AppConfig) -> dict:
    info = {
        "title": "", "author": "", "publisher": "",
        "year": "", "language": "", "format": "",
        "size": "", "isbn": "", "md5": md5, "source": "annas_archive"
    }
    try:
        url = f"https://annas-archive.gd/md5/{md5}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": config.http_proxy, "https": config.http_proxy}) if config.http_proxy
            else urllib.request.ProxyHandler({})
        )
        resp = opener.open(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')

        def _strip_html(text: str) -> str:
            return re.sub(r'<[^>]+>', ' ', text)

        def _clean(text: str) -> str:
            return re.sub(r'\s+', ' ', text).strip()

        # ── Title from <title> tag ──
        title_match = re.search(r'<title>(.*?)</title>', html, re.I | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            title = re.sub(r'\s*[-–—|]\s*Ann?a\'?s?\s*Archive.*$', '', title, flags=re.I).strip()
            info["title"] = title

        # ── Author ──
        author_match = re.search(r'<meta\s+name="author"\s+content="([^"]+)"', html, re.I)
        if author_match and author_match.group(1).strip():
            info["author"] = author_match.group(1).strip()
        if not info["author"]:
            for pat in [
                r'<span[^>]*class="[^"]*italic[^"]*"[^>]*>([^<]{1,100})</span>',
                r'<span[^>]*class="[^"]*author[^"]*"[^>]*>([^<]+)</span>',
            ]:
                m = re.search(pat, html, re.I)
                if m:
                    author = m.group(1).strip()
                    if author and len(author) > 1 and not author.startswith('<'):
                        info["author"] = author
                        break

        # ── Metadata line: language, format, size, year ──
        meta_div_pat = r'<div[^>]*class="[^"]*text-gray-800[^"]*font-semibold[^"]*text-sm[^"]*"[^>]*>(.*?)</div>'
        for match in re.finditer(meta_div_pat, html, re.I | re.DOTALL):
            text = _clean(_strip_html(match.group(1)))
            m = re.search(
                r'(\w[\w\s]*?)\s*(?:\[(\w+)\])?\s*[·•·|⚫.,]\s*(PDF|EPUB|MOBI|DJVU|AZW3|FB2|CBZ|CBR)\s*[·•·|⚫.,]\s*(\d+\.?\d*\s*[MGK]B)\s*[·•·|⚫.,]\s*(\d{4})',
                text, re.I,
            )
            if m:
                info["language"] = m.group(1).strip()
                info["format"] = m.group(3).upper()
                info["size"] = m.group(4).replace(' ', '').upper()
                info["year"] = m.group(5)
                break
            fallback = re.search(r'(PDF|EPUB|MOBI|DJVU|AZW3|FB2|CBZ|CBR)', text, re.I)
            if fallback:
                info["format"] = fallback.group(1).upper()
            fb_sz = re.search(r'(\d+\.?\d*\s*[MGK]B)', text, re.I)
            if fb_sz:
                info["size"] = fb_sz.group(1).replace(' ', '').upper()
            fb_yr = re.search(r'\b(\d{4})\b', text)
            if fb_yr:
                info["year"] = fb_yr.group(1)
            if not info["language"]:
                fb_lang = re.search(r'^(\w[\w\s]+?)\s*(?:\[|$)', text)
                if fb_lang:
                    info["language"] = fb_lang.group(1).strip()

        # ── ISBN from key-value spans ──
        isbn_block = re.search(
            r'ISBN[- ]?13.{0,200}?(\d{3}[\d\-]{7,20})', html, re.I | re.DOTALL,
        )
        if isbn_block:
            info["isbn"] = re.sub(r'[^0-9X]', '', isbn_block.group(1))[:13]

        # ── Publisher ──
        pub_match = re.search(
            r'(?:Publisher|出版社|出版者)[^<]*</[^>]+>\s*<[^>]+>\s*([^<]{1,120})', html, re.I,
        )
        if pub_match:
            pub_text = pub_match.group(1).strip()
            if pub_text and len(pub_text) > 1:
                info["publisher"] = pub_text

        return info
    except Exception:
        return info


@router.get("/api/v1/search")
async def search_books(
    field: str = Query("title"),
    query: str = Query(""),
    fuzzy: bool = Query(True),
    fields: list[str] = Query(None, alias="fields[]"),
    queries: list[str] = Query(None, alias="queries[]"),
    logics: list[str] = Query(None, alias="logics[]"),
    fuzzies: list[str] = Query(None, alias="fuzzies[]"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    t0 = time.time()

    if not query and not queries:
        raise HTTPException(status_code=400, detail="query or queries[] is required")

    is_advanced = fields and queries and len(fields) > 1

    if is_advanced:
        all_books = []
        for i in range(len(queries)):
            if i >= len(fields):
                break
            f = fields[i]
            q = queries[i]
            result = sqlite_search_books(f, q, page=1, page_size=50)
            all_books.extend(result.get("books", []))
        result = {"books": all_books, "totalRecords": len(all_books), "totalPages": 1}
    else:
        result = sqlite_search_books(field, query, fuzzy=fuzzy, page=page, page_size=page_size)

    external_books = []
    if result.get("totalRecords", 0) == 0 and not is_advanced and query:
        aa_results = _search_annas_archive(query, config)
        for md5_entry in aa_results[:10]:
            md5 = md5_entry.get("md5", "")
            page_info = _fetch_md5_page_info(md5, config)
            ext_title = page_info.get("title", "")
            ext_author = page_info.get("author", "")
            if ext_title:
                external_books.append({
                    "id": md5,
                    "title": ext_title,
                    "authors": [ext_author] if ext_author else [],
                    "publisher": page_info.get("publisher", ""),
                    "publish_date": page_info.get("year", ""),
                    "isbn": page_info.get("isbn", ""),
                    "language": page_info.get("language", ""),
                    "format": page_info.get("format", ""),
                    "size": page_info.get("size", ""),
                    "ss_code": "",
                    "dxid": "",
                    "source": "annas_archive",
                    "has_cover": False,
                    "can_download": True,
                    "nlc_verified": False,
                    "nlc_authors": [],
                    "nlc_publisher": "",
                    "nlc_pubdate": "",
                    "nlc_comments": "",
                    "nlc_tags": [],
                    "bookmark_status": "",
                    "bookmark_preview": None,
                    "bookmark": None,
                })

        zlib_email = (config.zlib_email or "").strip()
        zlib_pass = (config.zlib_password or "").strip()
        if zlib_email and zlib_pass:
            try:
                zlib_results = zlib_search(query, zlib_email, zlib_pass, config.http_proxy, limit=10)
                for book in zlib_results:
                    external_books.append({
                        "id": f"zl_{book.get('id', '')}",
                        "title": book.get("title", ""),
                        "authors": [book.get("author", "")] if book.get("author") else [],
                        "publisher": book.get("publisher", ""),
                        "publish_date": str(book.get("year", "")),
                        "isbn": book.get("isbn", ""),
                        "ss_code": "",
                        "dxid": "",
                        "source": "zlibrary",
                        "has_cover": False,
                        "can_download": True,
                        "nlc_verified": False,
                        "nlc_authors": [],
                        "nlc_publisher": "",
                        "nlc_pubdate": "",
                        "nlc_comments": "",
                        "nlc_tags": [],
                        "bookmark_status": "",
                        "bookmark_preview": None,
                        "bookmark": None,
                    })
            except Exception:
                pass

    search_time_ms = int((time.time() - t0) * 1000)

    db_path = _resolve_db_dir()
    dbs = sqlite_get_dbs()

    return {
        "books": result.get("books", []),
        "totalPages": result.get("totalPages", 0),
        "totalRecords": result.get("totalRecords", 0),
        "searchTimeMs": search_time_ms,
        "external_books": external_books,
        "serviceStatus": {
            "ebookDatabase": {
                "reachable": bool(db_path),
                "path": db_path or "",
                "dbs": dbs,
            }
        },
        "error": result.get("error"),
    }


@router.get("/api/v1/available-dbs")
async def available_dbs():
    dbs = sqlite_get_dbs()
    return {"dbs": dbs}


@router.get("/api/v1/config")
async def get_config():
    return {
        k: v for k, v in config.__dict__.items()
        if not k.startswith("_") and not callable(v)
    }


@router.post("/api/v1/config")
async def update_config(data: dict):
    for key, value in data.items():
        if hasattr(config, key):
            setattr(config, key, value)
    config.save()
    return {"status": "ok"}


@router.post("/api/v1/upload-cookies")
async def upload_cookies(file: UploadFile = File(...)):
    """Accept Cookie-Editor JSON export and save to cookie-annas-archive-gd.json."""
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are accepted")
    try:
        content = await file.read()
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    cookies_path = Path(config.tmp_dir) / "cookie-annas-archive-gd.json"
    cookies_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cookies_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return {"status": "ok", "path": str(cookies_path), "count": len(data) if isinstance(data, list) else 0}


@router.get("/api/v1/detect-paths")
async def detect_paths():
    db_files = ["DX_2.0-5.0.db", "DX_6.0.db"]
    candidates = []

    home = Path.home()

    candidates.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
    candidates.append(str(home / "EbookDatabase" / "instance"))

    candidates.append("/home/%s/EbookDatabase/instance" % os.environ.get("USER", os.environ.get("USERNAME", "eclaw")))
    candidates.append("/home/eclaw/EbookDatabase/instance")

    wsl_paths = []
    wsl_homes = [
        r"\\wsl.localhost\Ubuntu\home",
        r"\\wsl$\Ubuntu\home",
        r"\\wsl.localhost\Debian\home",
        r"\\wsl$\Debian\home",
    ]
    for base in wsl_homes:
        for user_dir in ["eclaw", os.environ.get("USER", ""), os.environ.get("USERNAME", ""), "*"]:
            if user_dir and user_dir != "*":
                wsl_paths.append(os.path.join(base, user_dir, "EbookDatabase", "instance"))
            elif user_dir == "*":
                try:
                    for entry in os.scandir(base) if os.path.isdir(base) else []:
                        candidate = os.path.join(base, entry.name, "EbookDatabase", "instance")
                        wsl_paths.append(candidate)
                except Exception:
                    pass

    candidates.extend(wsl_paths)

    user_dirs = ["Documents", "Downloads", "Desktop"]
    for d in user_dirs:
        candidates.append(str(home / d / "EbookDatabase" / "instance"))

    ebook_data_geter = getattr(config, "ebook_data_geter_path", "")
    if ebook_data_geter and ebook_data_geter != "auto":
        candidates.append(str(Path(ebook_data_geter) / "instance"))
        candidates.append(str(Path(ebook_data_geter) / "EbookDatabase" / "instance"))

    seen = set()
    found = []
    for p in candidates:
        norm = os.path.normpath(p)
        if norm in seen:
            continue
        seen.add(norm)
        if os.path.isdir(p):
            dbs = [db for db in db_files if os.path.exists(os.path.join(p, db))]
            found.append({"path": p, "dbs": dbs, "exists": True})
        else:
            found.append({"path": p, "dbs": [], "exists": False})

    return {"paths": found}


@router.get("/api/v1/status")
async def service_status():
    dbs = sqlite_get_dbs()
    return {
        "ebookDatabase": {
            "reachable": bool(_resolve_db_dir()),
            "dbs": dbs,
        },
    }


def _check_url_via_proxy(url: str, proxy: str, timeout: int = 5) -> dict:
    t0 = time.time()
    try:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}) if proxy
            else urllib.request.ProxyHandler({})
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = opener.open(req, timeout=timeout)
        resp.read()
        return {"reachable": True, "latency_ms": int((time.time() - t0) * 1000)}
    except Exception:
        return {"reachable": False, "latency_ms": 0}


def _check_zlib_credentials(proxy: str, userid: str, userkey: str, timeout: int = 10) -> bool:
    try:
        cookie_str = f"remix_userid={userid}; remix_userkey={userkey}"
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}) if proxy
            else urllib.request.ProxyHandler({})
        )
        req = urllib.request.Request(
            "https://z-lib.sk/eapi/user/profile",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Cookie": cookie_str,
            },
        )
        resp = opener.open(req, timeout=timeout)
        data = json.loads(resp.read())
        if isinstance(data, dict):
            if data.get("error"):
                return False
            if data.get("success") is False:
                return False
            if data.get("user") or data.get("id"):
                return True
        return False
    except Exception:
        return False


class ProxyRequest(BaseModel):
    http_proxy: str = ""

@router.post("/api/v1/check-proxy")
async def check_proxy(req: ProxyRequest):
    proxy = req.http_proxy or config.http_proxy
    annas = _check_url_via_proxy("https://annas-archive.gd/", proxy)

    # Z-Library check uses curl_cffi (browser TLS) because urllib is blocked
    zlib_reachable = False
    try:
        from engine.zlib_downloader import zlib_login
        test = zlib_login("test@test.com", "wrong", proxy)
        err = str(test.get("error", "")).lower()
        zlib_reachable = "incorrect" in err or "error" in err or "password" in err
    except Exception:
        pass

    email = (config.zlib_email or "").strip()
    password = (config.zlib_password or "").strip()
    configured = bool(email and password)
    api_available = False
    if configured and zlib_reachable:
        try:
            result = zlib_login(email, password, proxy)
            api_available = result.get("success", False)
        except Exception:
            pass

    zlib = {
        "configured": configured,
        "api_reachable": zlib_reachable,
        "api_available": api_available,
    }
    return {"annas_archive": annas, "zlibrary": zlib}


class ZLibFetchTokensRequest(BaseModel):
    email: str
    password: str

@router.post("/api/v1/zlib-fetch-tokens")
async def zlib_fetch_tokens(req: ZLibFetchTokensRequest):
    from engine.zlib_downloader import zlib_login
    result = zlib_login(req.email, req.password, config.http_proxy)
    if result.get("success"):
        return {"success": True, "remix_userid": req.email, "remix_userkey": ""}
    return result

@router.get("/api/v1/zlib-quota")
async def zlib_quota():
    zlib_email = (config.zlib_email or "").strip()
    zlib_pass = (config.zlib_password or "").strip()
    if not zlib_email or not zlib_pass:
        raise HTTPException(status_code=400, detail="Z-Library credentials not configured")
    try:
        from engine.zlib_downloader import zlib_get_limits
        limits = zlib_get_limits(zlib_email, zlib_pass, config.http_proxy)
        if not limits:
            return {"downloads_left": 10, "downloads_limit": 10}
        limit = int(limits.get("downloads_limit", 0) or limits.get("daily_allowed", 10))
        today = int(limits.get("downloads_today", 0) or limits.get("daily_amount", 0))
        return {
            "downloads_left": max(0, limit - today),
            "downloads_limit": limit,
        }
    except Exception:
        return {"downloads_left": 10, "downloads_limit": 10}


@router.get("/api/v1/check-ocr")
async def check_ocr():
    result = {"installed": False, "version": "", "engines": {}}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "ocrmypdf", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0:
            ver_output = proc.stdout.strip() or proc.stderr.strip()
            version = ver_output.split("\n")[0].strip() if ver_output else ""
            result["installed"] = True
            result["version"] = version
            result["engines"]["tesseract"] = {"available": True}
        else:
            result["installed"] = False
            result["version"] = ""
            result["engines"]["tesseract"] = {"available": False}
            result["engines"]["paddleocr"] = {"available": False}
            result["engines"]["easyocr"] = {"available": False}
            result["engines"]["appleocr"] = {"available": False}
            return result
    except Exception:
        result["installed"] = False
        result["version"] = ""
        result["engines"]["tesseract"] = {"available": False}
        result["engines"]["paddleocr"] = {"available": False}
        result["engines"]["easyocr"] = {"available": False}
        result["engines"]["appleocr"] = {"available": False}
        return result

    engine_checks = {
        "paddleocr": 'import paddleocr; print("ok")',
        "easyocr": 'import easyocr; print("ok")',
        "appleocr": 'import ocrmypdf_appleocr; print("ok")',
    }
    for name, code in engine_checks.items():
        try:
            r = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=15,
            )
            result["engines"][name] = {"available": r.returncode == 0}
        except Exception:
            result["engines"][name] = {"available": False}

    return result


class InstallOCRRequest(BaseModel):
    engine: str = "tesseract"


@router.post("/api/v1/install-ocr")
async def install_ocr(req: InstallOCRRequest):
    engine = req.engine.lower()
    packages = {
        "tesseract": ["ocrmypdf"],
        "paddleocr": ["ocrmypdf", "ocrmypdf_paddleocr", "paddleocr"],
        "easyocr": ["ocrmypdf_pdfeasyocr", "easyocr"],
        "appleocr": ["ocrmypdf_appleocr"],
    }
    if engine not in packages:
        raise HTTPException(status_code=400, detail=f"Unknown engine: {engine}")

    cmd = ["pip", "install"] + packages[engine]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            return {"status": "failed", "message": result.stderr.strip()[-500:]}
    except subprocess.TimeoutExpired:
        return {"status": "failed", "message": "安装超时"}
    except Exception as e:
        return {"status": "failed", "message": str(e)}

    verify_imports = {
        "tesseract": 'import ocrmypdf; print("ok")',
        "paddleocr": 'import paddleocr; print("ok")',
        "easyocr": 'import easyocr; print("ok")',
        "appleocr": 'import ocrmypdf_appleocr; print("ok")',
    }
    if engine in verify_imports:
        try:
            v = subprocess.run(
                [sys.executable, "-c", verify_imports[engine]],
                capture_output=True, text=True, timeout=15,
            )
            if v.returncode == 0:
                return {"status": "ok", "message": f"{engine} 安装成功"}
            else:
                return {"status": "warning", "message": f"{engine} pip 安装完成，但导入验证失败"}
        except Exception:
            return {"status": "warning", "message": f"{engine} pip 安装完成，但导入验证异常"}

    return {"status": "ok", "message": f"{engine} 安装成功"}


@router.get("/api/v1/check-flare")
async def check_flare():
    try:
        req = urllib.request.Request(
            "http://localhost:8191/v1",
            data=json.dumps({
                "cmd": "request.get",
                "url": "https://annas-archive.gd/",
                "maxTimeout": 5000,
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("status") == "ok":
            return {"available": True}
        return {"available": False}
    except Exception:
        return {"available": False}
