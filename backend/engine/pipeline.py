import asyncio
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from config import AppConfig
from search_engine import search_books as _sqlite_search
from task_store import TaskStore
from ws_manager import WebSocketManager

async def _log(store: TaskStore, ws: WebSocketManager, task_id: str, msg: str):
    store.append_log(task_id, msg)
    try:
        await ws.send_log(task_id, msg)
    except Exception:
        pass


async def execute_pipeline(task_id: str, params: dict, store: TaskStore,
                           ws: WebSocketManager, config: AppConfig):
    """Run the full 7-step pipeline in a thread pool executor."""

    state = {
        "candidates": [],
        "pdf_path": None,
        "ocr_pdf_path": None,
        "compressed_pdf_path": None,
        "bookmarked_pdf_path": None,
        "expected_meta": {
            "title": params.get("title", ""),
            "authors": params.get("authors", []),
            "publisher": params.get("publisher", ""),
            "isbn": params.get("isbn", ""),
        },
        "bookmark": params.get("bookmark"),
        "direct_link": {},
        "steps_completed": [],
        "errors": [],
    }

    await _log(store, ws, task_id, f"[{_ts()}] 任务启动: {params.get('title', '')}")

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)

    pipeline_fns = [
        (1, "检索信息", _run_step1),
        (2, "下载 PDF", _run_step2),
        (3, "OCR PDF", _run_step3),
        (3.5, "PDF 压缩", _run_step3_5),
        (4, "生成书签", _run_step4),
        (5, "保存到本地", _run_step5),
        (6, "生成报告", _run_step6),
    ]

    for step_num, step_name, fn in pipeline_fns:
        store.update_status(task_id, "running", current_step=step_num, current_step_name=step_name)
        store.update_step(task_id, step_num, step_name, "running")

        await _log(store, ws, task_id, f"[{_ts()}] ■ 步骤 {step_num}/6: {step_name}")
        await ws.send_step_start(task_id, step_num, step_name)

        t0 = time.time()
        try:
            result = await loop.run_in_executor(executor, fn, state, params, config, task_id, store, ws)
            elapsed_ms = int((time.time() - t0) * 1000)

            if step_num == 1:
                state["candidates"] = result.get("candidates", [])
                if not state["candidates"]:
                    raise RuntimeError("步骤1 无候选结果")
            elif step_num == 2:
                state["pdf_path"] = result
            elif step_num == 3:
                state["ocr_pdf_path"] = result if result else state.get("pdf_path")
            elif step_num == 3.5:
                state["compressed_pdf_path"] = result if result else state.get("ocr_pdf_path")
            elif step_num == 4:
                state["bookmarked_pdf_path"] = result
            elif step_num == 5:
                state["direct_link"] = result
            elif step_num == 6:
                state["report"] = result

            state["steps_completed"].append(step_num)

            store.update_step(task_id, step_num, step_name, "completed", elapsed_ms=elapsed_ms)
            store.save_pipeline_state(task_id, state)
            await _log(store, ws, task_id, f"[{_ts()}] ✓ {step_name} 完成 (耗时 {elapsed_ms/1000:.1f}s)")
            await ws.send_step_complete(task_id, step_num, step_name, elapsed_ms=elapsed_ms)

        except Exception as e:
            elapsed_ms = int((time.time() - t0) * 1000)
            store.update_step(task_id, step_num, step_name, "failed")
            store.update_status(task_id, "failed", error=str(e))
            state["errors"].append({"step": step_num, "error": str(e)})
            store.save_pipeline_state(task_id, state)

            await _log(store, ws, task_id, f"[{_ts()}] ✗ {step_name} 失败: {e}")
            await ws.send_task_error(task_id, step_num, str(e))

            report = _build_partial_report(state, params)
            store.save_report(task_id, report)
            await ws.send_task_complete(task_id, report)
            return

    store.update_status(task_id, "completed")
    store.save_pipeline_state(task_id, state)
    report = _build_full_report(state, params)
    store.save_report(task_id, report)
    await _log(store, ws, task_id, f"[{_ts()}] ✓ 管道执行完成")
    await ws.send_task_complete(task_id, report)


def _ts() -> str:
    return time.strftime("%H:%M:%S")


# ─── Step 1: Search ───────────────────────────────────────────────────────

def _run_step1(state: dict, params: dict, config: AppConfig, task_id: str, store, ws) -> dict:
    """Three-mode search: title / ISBN / SS_code."""
    book_name = params.get("title", "").strip()
    isbn = params.get("isbn", "").strip()
    ss_code = params.get("ss_code", "").strip()

    if ss_code:
        return _search_by_sscode(ss_code, config)
    elif isbn:
        try:
            return _search_by_isbn(isbn, config)
        except RuntimeError:
            pass
    elif book_name:
        try:
            return _search_by_title(book_name, config)
        except RuntimeError:
            pass

    # Fallback: external books (AA / Z-Lib) with only title/author/isbn
    if book_name or isbn or ss_code:
        fallback = {
            "title": book_name or params.get("title", ""),
            "isbn": isbn,
            "ss_code": ss_code or None,
            "dxid": None,
            "publisher": params.get("publisher", ""),
            "authors": params.get("authors", []),
            "_fallback": True,
        }
        return {"candidates": [fallback], "count": 1}

    raise RuntimeError("至少提供书名、ISBN 或 SS码之一")


def _resolve_geter_path(config: AppConfig) -> str:
    """Resolve EbookDataGeter path from config or auto-detect."""
    if config.ebook_data_geter_path and config.ebook_data_geter_path != "auto":
        if os.path.isdir(config.ebook_data_geter_path):
            return config.ebook_data_geter_path
    # PyInstaller bundle: data files extracted to sys._MEIPASS
    meipass = getattr(sys, '_MEIPASS', '')
    if meipass:
        bundled = os.path.join(meipass, 'nlc')
        if os.path.isdir(bundled):
            return bundled
    # Development mode: project-local nlc/ directory
    try:
        dev_nlc = str(Path(__file__).resolve().parent.parent / "nlc")
        if os.path.isdir(dev_nlc):
            return dev_nlc
    except Exception:
        pass
    # Fallback common locations
    candidates = [str(Path.home() / "EbookDataGeter")]
    user = os.environ.get("USER", os.environ.get("USERNAME", ""))
    if user:
        candidates.append(f"/home/{user}/EbookDataGeter")
    for p in candidates:
        if os.path.isdir(p):
            return p
    return ""


def _search_by_title(book_name: str, config: AppConfig) -> dict:
    main_title = re.split(r"[：———·\u30fb]", book_name)[0].strip()
    geter_path = _resolve_geter_path(config)
    if not geter_path:
        raise RuntimeError(
            f"EbookDataGeter 路径未配置。请在「环境配置」中设置 ebook_data_geter_path，"
            f"或将 nlc_isbn / bookmarkget 模块放到 {Path.home()/'EbookDataGeter'}"
        )
    sys.path.insert(0, geter_path)
    try:
        from nlc_isbn import isbn2meta
        from bookmarkget import get_book_details
    except ImportError as e:
        raise RuntimeError(
            f"nlc_isbn / bookmarkget 导入失败 ({geter_path}): {e}。"
            f"请检查路径是否正确，或安装依赖 pip install beautifulsoup4"
        )

    def _query_db(field: str, q: str) -> tuple:
        """Returns (books_list, error_message_or_None) — uses direct SQLite."""
        all_books = []
        first_error = None
        for pg in range(1, 6):
            result = _sqlite_search(field, q, fuzzy=True, page=pg, page_size=50)
            books = result.get("books", [])
            if not books and result.get("error"):
                first_error = result.get("error")
            if not books:
                break
            all_books.extend(books)
            if pg >= result.get("totalPages", 1):
                break
        return all_books, first_error

    candidates, db_error = _query_db("title", main_title)
    if not candidates:
        if db_error:
            raise RuntimeError(f"数据库查询失败: {db_error}")
        raise RuntimeError("数据库未命中")

    from concurrent.futures import as_completed

    def _enrich_one(book):
        ib = book.get("isbn", "")
        if not ib:
            return {**book, "nlc_verified": False, "nlc_note": "no_isbn"}
        try:
            meta = isbn2meta(ib, lambda x: None)
        except Exception:
            return {**book, "nlc_verified": False, "nlc_note": "nlc_error"}
        if not meta:
            return {**book, "nlc_verified": False, "nlc_note": "not_found"}
        score = sum(1 for f in ["authors", "publisher", "pubdate", "comments"] if meta.get(f))
        return {
            **book, "nlc_verified": True, "nlc_score": score,
            "nlc_authors": meta.get("authors", []), "nlc_publisher": meta.get("publisher", ""),
            "nlc_pubdate": meta.get("pubdate", ""), "nlc_comments": meta.get("comments", ""),
            "nlc_tags": meta.get("tags", []),
        }

    enriched = []
    with ThreadPoolExecutor(max_workers=config.nlc_max_workers) as ex:
        futures = {ex.submit(_enrich_one, b): b for b in candidates[:10]}
        for f in as_completed(futures):
            try:
                enriched.append(f.result())
            except Exception:
                enriched.append(futures[f])

    enriched.sort(key=lambda b: (b.get("nlc_verified", False), b.get("nlc_score", 0)), reverse=True)

    if enriched:
        ib = enriched[0].get("isbn", "")
        if ib:
            try:
                bm = get_book_details(ib)
                if "未找到" not in bm and "出错" not in bm:
                    enriched[0]["bookmark"] = bm
                    enriched[0]["bookmark_status"] = "ok"
                    enriched[0]["bookmark_preview"] = bm[:200]
                else:
                    enriched[0]["bookmark_status"] = "not_found"
                    enriched[0]["bookmark"] = None
                    enriched[0]["bookmark_preview"] = None
            except Exception:
                enriched[0]["bookmark_status"] = "unavailable"
                enriched[0]["bookmark"] = None
                enriched[0]["bookmark_preview"] = None

    return {"candidates": enriched, "count": len(enriched)}


def _search_by_sscode(ss_code: str, config: AppConfig) -> dict:
    result = _sqlite_search("sscode", ss_code, fuzzy=False, page=1, page_size=10)
    candidates = result.get("books", [])
    if not candidates:
        raise RuntimeError("数据库未命中（SS码无效）")
    return _search_by_title(candidates[0].get("title", ss_code), config)


def _search_by_isbn(isbn: str, config: AppConfig) -> dict:
    candidates = []
    for field in ["isbn", "title"]:
        result = _sqlite_search(field, isbn, fuzzy=(field == "title"), page=1, page_size=20)
        candidates.extend(result.get("books", []))

    if candidates:
        return _search_by_title(candidates[0].get("title", isbn), config)

    # ── 第2步：EbookDatabase 未命中 → NLC fallback ──
    geter_path = _resolve_geter_path(config)
    if not geter_path:
        raise RuntimeError(
            f"EbookDataGeter 路径未配置。请在「环境配置」中设置 ebook_data_geter_path"
        )
    sys.path.insert(0, geter_path)
    from nlc_isbn import isbn2meta
    from bookmarkget import get_book_details

    meta = isbn2meta(isbn, lambda x: None)
    bm_text = None
    bm_status = "not_found"
    try:
        bm_text = get_book_details(isbn)
        if "未找到" not in bm_text and "出错" not in bm_text:
            bm_status = "ok"
        else:
            bm_text = None
    except Exception:
        pass
    if not meta:
        raise RuntimeError(f"NLC 也无 ISBN {isbn} 的记录")
    fallback = {
        "title": meta.get("title", ""), "isbn": isbn, "ss_code": None,
        "dxid": None, "publisher": meta.get("publisher", ""),
        "authors": meta.get("authors", []), "nlc_verified": True,
        "nlc_score": sum(1 for f in ["authors", "publisher", "pubdate", "comments"] if meta.get(f)),
        "nlc_authors": meta.get("authors", []), "nlc_publisher": meta.get("publisher", ""),
        "nlc_pubdate": meta.get("pubdate", ""), "nlc_comments": meta.get("comments", ""),
        "nlc_tags": meta.get("tags", []), "bookmark": bm_text,
        "bookmark_status": bm_status, "bookmark_preview": bm_text[:200] if bm_text else None,
        "_fallback": True,
    }
    return {"candidates": [fallback], "count": 1}


# ─── Step 2: Download ─────────────────────────────────────────────────────

def _run_step2(state: dict, params: dict, config: AppConfig, task_id: str, store, ws) -> str:
    """Download PDF: AA fast → AA slow → IPFS → Z-Lib → aria2c BT → manual."""
    try:
        return _do_download(state, params, config, task_id, store, ws)
    except Exception as e:
        raise RuntimeError(str(e))


def _do_download(state, params, config, task_id, store, ws) -> str:
    candidates = state.get("candidates", [])
    if not candidates:
        raise RuntimeError("无候选，无法下载")

    info = candidates[0]
    title = info.get("title", "")
    isbn = info.get("isbn", "")
    ss_code = info.get("ss_code", "")

    search_query = isbn or title or ss_code
    if not search_query:
        raise RuntimeError("无 ISBN/书名用于下载搜索")

    output_dir = config.download_dir
    os.makedirs(output_dir, exist_ok=True)

    # If finished PDF already exists, skip download
    for fname in os.listdir(config.finished_dir or output_dir):
        if isbn and isbn in fname and fname.lower().endswith('.pdf'):
            return os.path.join(config.finished_dir or output_dir, fname)

    errors = []
    detail_lines = []

    # ── Step 1: 搜索 Anna's Archive 获取 MD5 ──
    md5_list = _search_annas_archive(search_query, config)
    if not md5_list:
        errors.append("Anna's Archive: 搜索无结果 (9787561789322)")
    else:
        detail_lines.append(f"AA搜索找到 {len(md5_list)} 个MD5: " + ", ".join(md5_list[i]["md5"][:12] for i in range(min(3, len(md5_list)))))

    tried = set()
    for md5_entry in (md5_list or [])[:5]:
        md5 = md5_entry.get("md5", "")
        if not md5 or md5 in tried:
            continue
        tried.add(md5)

        filepath = _download_via_aa_fast(md5, output_dir, config)
        if filepath:
            return filepath
        errors.append(f"AA高速下载: {md5[:12]}... (无Key或失效)")

        filepath = _download_via_aa_slow(md5, output_dir, config, task_id, ws)
        if filepath:
            return filepath
        errors.append(f"AA慢速下载: {md5[:12]}... 失败")

        filepath = _download_via_ipfs_gateway(md5, output_dir, config)
        if filepath:
            return filepath
        errors.append(f"IPFS网关: {md5[:12]}... (无CID或403)")

        filepath = _download_via_zlib(md5, output_dir, config, search_query=search_query)
        if filepath:
            return filepath
        errors.append(f"Z-Library: {md5[:12]}... 未登录或无此书")

        filepath = _download_via_aria2(md5, output_dir, config)
        if filepath:
            return filepath
        errors.append(f"aria2c(BT): {md5[:12]}... (无seed或超时)")

    aa_url = f"https://annas-archive.gd/search?q={urllib.parse.quote(search_query)}"
    detail = "\n".join(detail_lines + errors) if (detail_lines or errors) else "未找到任何下载源"
    raise RuntimeError(
        f"所有下载方式均失败: {search_query}\n{detail}\n\n"
        f"手动下载: {aa_url}\n\n"
        f"自动下载配置:\n"
        f"  AA会员: 访问 https://annas-archive.gd/donate 注册会员获取Key\n"
        f"  Z-Library: 访问 https://z-lib.sk 注册, 配置 zlib_remix_userid + zlib_remix_userkey\n"
        f"  AA Cookie: 浏览器中访问 {aa_url}, 用Cookie Editor扩展导出cookie"
    )


def _build_opener(config: AppConfig):
    """Build a urllib opener with optional proxy."""
    if config.http_proxy:
        proxy = urllib.request.ProxyHandler({"http": config.http_proxy, "https": config.http_proxy})
        return urllib.request.build_opener(proxy)
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _search_annas_archive(query: str, config: AppConfig) -> list:
    """Search Anna's Archive and extract MD5 hashes."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://annas-archive.gd/search?q={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        opener = _build_opener(config)
        resp = opener.open(req, timeout=20)
        html = resp.read().decode('utf-8', errors='replace')
        md5s = re.findall(r'href="(/md5/([a-f0-9]{32}))"', html)
        return [{"md5": m[1], "md5_url": f"https://annas-archive.gd/md5/{m[1]}"} for m in md5s]
    except Exception:
        return []


def _load_aa_cookies(config: AppConfig) -> dict:
    """Load cached Anna's Archive cookies for Cloudflare bypass.

    Cookie file format (from Cookie-Editor extension):
    {"cookies": [{"name": "xxx", "value": "yyy", "domain": ".annas-archive.gd"}, ...]}
    or simple dict: {"__ddg1_": "xxx", "__ddg8_": "yyy", ...}
    """
    cookie_paths = [
        os.path.join(config.tmp_dir, "cookie-annas-archive-gd.json"),
        os.path.join(str(Path.home()), ".agent-ebook-downloader", "aa_cookies.json"),
    ]
    for cp in cookie_paths:
        if not os.path.exists(cp):
            continue
        try:
            with open(cp, "r") as f:
                data = json.load(f)
            if "cookies" in data:
                # Cookie-Editor format: list of cookie objects
                return {c["name"]: c["value"] for c in data["cookies"]}
            # Simple dict format
            return {k: v for k, v in data.items() if k not in ("timestamp",)}
        except Exception:
            pass
    return {}


def _download_via_aa_fast(md5: str, output_dir: str, config: AppConfig) -> str | None:
    key = config.aa_membership_key
    if not key:
        return None
    try:
        opener = _build_opener(config)
        api_url = f"https://annas-archive.gd/dyn/api/fast_download.json?md5={md5}&key={urllib.parse.quote(key)}"
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
        resp = opener.open(req, timeout=20)
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
        download_url = data.get("download_url", "")
        if not download_url:
            return None
        dest = os.path.join(output_dir, md5)
        dl_req = urllib.request.Request(download_url, headers={
            "User-Agent": "Mozilla/5.0",
        })
        dl_resp = opener.open(dl_req, timeout=300)
        with open(dest, "wb") as f:
            for chunk in iter(lambda: dl_resp.read(65536), b""):
                f.write(chunk)
        if os.path.getsize(dest) > 10240:
            return _detect_and_normalize(dest)
        os.remove(dest)
        return None
    except Exception:
        return None


def _download_via_aa_slow(md5: str, output_dir: str, config: AppConfig,
                          task_id: str = None, ws: WebSocketManager = None) -> str | None:
    """Download via AA slow_download. Uses FlareSolverr if available, else cookies."""
    from engine.flaresolverr import is_flaresolverr_ready, solve_cloudflare

    cookies = _load_aa_cookies(config)
    opener = _build_opener(config)
    use_flare = is_flaresolverr_ready()

    # Step 1: Get MD5 page
    try:
        md5_url = f"https://annas-archive.gd/md5/{md5}"
        if use_flare:
            # Use FlareSolverr to get the page (bypasses Cloudflare)
            result = solve_cloudflare(md5_url, proxy=config.http_proxy, timeout=30000)
            if result:
                html = result["html"]
                # Update cookies from FlareSolverr response
                cookies.update(result.get("cookies", {}))
            else:
                return None
        else:
            req = urllib.request.Request(md5_url, headers={"User-Agent": "Mozilla/5.0"})
            if cookies:
                req.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()))
            resp = opener.open(req, timeout=15)
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None

    # Extract slow_download links
    slow_links = re.findall(r'href="(/slow_download/[^"]+)"', html)
    if not slow_links:
        return None

    # Step 2: Try each slow_download link
    for link in slow_links[:3]:
        slow_url = "https://annas-archive.gd" + link
        slow_html = ""
        try:
            if use_flare:
                result = solve_cloudflare(slow_url, proxy=config.http_proxy, timeout=60000)
                if result:
                    slow_html = result["html"]
                    cookies.update(result.get("cookies", {}))
                else:
                    continue
            else:
                req = urllib.request.Request(slow_url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": md5_url,
                })
                if cookies:
                    req.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()))
                resp = opener.open(req, timeout=30)
                slow_html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            continue

        # Step 3: Parse the actual download link
        # Method 1: <a href> with MD5 prefix
        dl_match = re.search(
            rf'href="(https?://[^"]*{re.escape(md5[:12])}[^"]*)"',
            slow_html, re.I,
        )
        if not dl_match:
            # Method 2: clipboard button
            dl_match = re.search(r"writeText\('(https?://[^']+)'\)", slow_html)
        if not dl_match:
            # Method 3: any file download link
            for m in re.finditer(r'href="(https?://[^"]+)"', slow_html):
                url = m.group(1)
                if any(ext in url.lower() for ext in [".epub", ".pdf", ".mobi", "/file/", "/dl/"]):
                    if "annas-archive" not in url.lower():
                        dl_match = m
                        break

        if not dl_match:
            continue

        download_url = dl_match.group(1) if isinstance(dl_match, re.Match) else dl_match

        # Check if file already exists
        dest = os.path.join(output_dir, md5)
        if os.path.exists(dest) and os.path.getsize(dest) > 10240:
            return _detect_and_normalize(dest)

        # Step 4: Download file (pass cookies from FlareSolverr)
        try:
            req = urllib.request.Request(download_url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": slow_url,
            })
            if cookies:
                req.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()))
            resp = opener.open(req, timeout=120)
            if "text/html" in resp.headers.get("Content-Type", ""):
                continue
            with open(dest, "wb") as f:
                for chunk in iter(lambda: resp.read(65536), b""):
                    f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if ws and task_id and total_size > 0 and now - last_report >= 2:
                        elapsed = now - dl_start
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        pct = min(int(downloaded / total_size * 100), 100)
                        if speed > 0:
                            eta = (total_size - downloaded) / speed
                            if eta < 60:
                                eta_str = f"预计剩余 {eta:.0f} 秒"
                            else:
                                eta_str = f"预计剩余 {eta / 60:.1f} 分钟"
                        else:
                            eta_str = ""
                        msg = (f"已下载 {downloaded / 1024 / 1024:.1f}MB / {total_size / 1024 / 1024:.1f}MB"
                               f" ({speed / 1024 / 1024:.1f} MB/s) {eta_str}")
                        try:
                            asyncio.run_coroutine_threadsafe(
                                ws.send_step_progress(task_id, 2, "下载 PDF", pct, msg),
                                asyncio.get_event_loop(),
                            )
                        except Exception:
                            pass
                        last_report = now
            if os.path.getsize(dest) > 10240:
                return _detect_and_normalize(dest)
            os.remove(dest)
        except Exception:
            continue

    return None


def _resolve_aria2_path() -> str:
    """Get path to aria2c executable."""
    meipass = getattr(sys, "_MEIPASS", "")
    candidates = [
        os.path.join(meipass, "tools", "aria2c.exe"),
        os.path.join(os.path.dirname(__file__), "..", "tools", "aria2c.exe"),
        os.path.join(os.path.dirname(__file__), "..", "aria2c.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return "aria2c"


def _download_via_aria2(md5: str, output_dir: str, config: AppConfig) -> str | None:
    """Download via BitTorrent using aria2c.
    
    Parses the Anna's Archive MD5 page to find the torrent URL and filename,
    then downloads just that file from the torrent using aria2c.
    """
    import tempfile
    import bencodepy

    opener = _build_opener(config)

    # ── Step 1: 从 AA MD5 页面获取 torrent URL 和文件名 ──
    try:
        md5_url = f"https://annas-archive.gd/md5/{md5}"
        req = urllib.request.Request(md5_url, headers={
            "User-Agent": "Mozilla/5.0",
        })
        resp = opener.open(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None

    # Extract torrent URL from the external downloads section
    torrent_match = re.search(
        r'href="(/dyn/small_file/torrents/[^"]+\.torrent)"',
        html,
    )
    if not torrent_match:
        return None
    torrent_url = "https://annas-archive.gd" + torrent_match.group(1)

    # Extract file name from the external downloads section
    # Pattern: file&nbsp;"aacid__..."
    LQ = "\u201c"   # left curly double quote "
    RQ = "\u201d"   # right curly double quote "
    file_match = re.search(
        r"file.{0,20}[" + LQ + '"](aacid__[a-zA-Z0-9_]+)[' + RQ + '"]',
        html,
    )
    if not file_match:
        return None
    file_name = file_match.group(1)

    # ── Step 2: 下载 torrent 文件 ──
    try:
        req = urllib.request.Request(torrent_url, headers={"User-Agent": "Mozilla/5.0"})
        resp = opener.open(req, timeout=30)
        torrent_data = resp.read()
    except Exception:
        return None

    # ── Step 3: 解析 torrent 找到文件索引 ──
    torrent = bencodepy.decode(torrent_data)
    info_dict = torrent[b"info"]
    files = info_dict[b"files"]
    file_index = None
    for i, f in enumerate(files):
        path = b"/".join(f[b"path"]).decode()
        if file_name in path:
            file_index = i + 1  # aria2c 1-based
            break

    if file_index is None:
        return None

    # ── Step 4: aria2c 下载 ──
    torrent_file = os.path.join(tempfile.gettempdir(), f"bdw_{md5[:8]}.torrent")
    with open(torrent_file, "wb") as f:
        f.write(torrent_data)

    aria2 = _resolve_aria2_path()
    cmd = [aria2]
    if config.http_proxy:
        cmd.append("--http-proxy=" + config.http_proxy)
    cmd += [
        "--select-file", str(file_index),
        "--seed-time", "0",
        "--console-log-level", "error",
        "--summary-interval", "0",
        "-d", output_dir,
        torrent_file,
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=120,
                       encoding="utf-8", errors="replace")
    except Exception:
        pass  # aria2c failure is non-fatal; fall through to check for partial downloads

    try:
        os.remove(torrent_file)
    except Exception:
        pass  # best-effort cleanup

    # Find downloaded file (exclude .aria2 control files)
    for fname in os.listdir(output_dir):
        if fname.endswith(".aria2"):
            continue
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath) and os.path.getsize(fpath) > 10240:
            if time.time() - os.path.getmtime(fpath) < 180:
                return _detect_and_normalize(fpath)

    return None


def _download_via_zlib(md5: str, output_dir: str, config: AppConfig, search_query: str = "") -> str | None:
    """Download from Z-Library using eAPI with curl_cffi (browser TLS)."""
    from engine.zlib_downloader import zlib_search, zlib_download_book

    zlib_email = config.zlib_email or os.environ.get("ZLIB_EMAIL", "")
    zlib_pass = config.zlib_password or os.environ.get("ZLIB_PASS", "")
    if not zlib_email or not zlib_pass:
        return None

    try:
        # Try MD5 first, then title search
        results = zlib_search(md5, zlib_email, zlib_pass, config.http_proxy, limit=5)
        if not results and search_query:
            results = zlib_search(search_query, zlib_email, zlib_pass, config.http_proxy, limit=5)

        for book in results[:5]:
            path = zlib_download_book(book, output_dir, config.http_proxy)
            if path:
                return _detect_and_normalize(path)
    except Exception:
        pass

    return None


IPFS_GATEWAYS = [
    "https://ipfs.io/ipfs/{cid}?filename=book.pdf",
    "https://dweb.link/ipfs/{cid}?filename=book.pdf",
    "https://cloudflare-ipfs.com/ipfs/{cid}",
    "https://gateway.pinata.cloud/ipfs/{cid}",
    "https://ipfs.fleek.co/ipfs/{cid}",
]


def _download_via_ipfs_gateway(md5: str, output_dir: str, config: AppConfig) -> str | None:
    """Resolve MD5 to IPFS CID via Anna's Archive metadata, then download from IPFS gateways."""
    opener = _build_opener(config)

    # ── Resolve MD5 → IPFS CID via Anna's Archive metadata API ──
    ipfs_cid = None
    try:
        aa_url = f"https://annas-archive.gd/db/aarecord_elasticsearch/md5:{md5}.json.html"
        req = urllib.request.Request(aa_url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://annas-archive.gd/datasets",
        })
        resp = opener.open(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
        cid_match = re.search(r'"ipfs_cid"\s*:\s*\[\s*"([^"]+)"', html)
        if cid_match:
            ipfs_cid = cid_match.group(1)
    except Exception:
        pass

    if not ipfs_cid:
        return None

    # ── Download from IPFS gateways ──
    dest = os.path.join(output_dir, md5)
    for gateway_url in IPFS_GATEWAYS:
        url = gateway_url.format(cid=ipfs_cid)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = opener.open(req, timeout=120)
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" in content_type:
                continue
            with open(dest, "wb") as f:
                for chunk in iter(lambda: resp.read(65536), b""):
                    f.write(chunk)
            if os.path.getsize(dest) > 10240:
                return _detect_and_normalize(dest)
            os.remove(dest)
        except Exception:
            continue

    return None


def _detect_and_normalize(input_path: str) -> str:
    """Detect file type and normalize to PDF."""
    if not os.path.exists(input_path):
        return input_path
    with open(input_path, "rb") as f:
        header = f.read(8)
    base = os.path.splitext(input_path)[0]
    if header.startswith(b"%PDF"):
        new_path = base + ".pdf"
        if new_path != input_path:
            try:
                if os.path.exists(new_path):
                    os.remove(new_path)
                os.rename(input_path, new_path)
            except Exception:
                pass
        return new_path
    return input_path


# ─── Step 3: OCR ──────────────────────────────────────────────────────────

def _run_step3(state: dict, params: dict, config: AppConfig, task_id: str, store, ws) -> str:
    """OCR the downloaded PDF."""
    pdf_path = state.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        raise RuntimeError("PDF 文件不存在")

    # Check if OCR tool is installed
    try:
        subprocess.run([sys.executable, "-m", "ocrmypdf", "--version"],
                       capture_output=True, timeout=5)
    except Exception:
        return pdf_path  # Skip OCR, continue with original PDF

    try:
        import fitz
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
    except ImportError:
        total_pages = 0

    if not _is_scanned(pdf_path):
        return pdf_path

    output_pdf = pdf_path.replace(".pdf", "_ocr.pdf")

    python_bin = sys.executable

    tmp_dir = config.tmp_dir
    os.makedirs(tmp_dir, exist_ok=True)

    cmd = [
        python_bin, "-m", "ocrmypdf",
        "--plugin", "ocrmypdf_paddleocr",
        "-l", config.ocr_languages,
        "--jobs", str(config.ocr_jobs),
        "--mode", "force",
        "--output-type", "pdf",
        pdf_path, output_pdf,
    ]

    env = {**os.environ, "TMPDIR": tmp_dir}

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env,
    )

    lines_buffer = []
    ocr_start = time.time()
    for line in process.stderr:
        lines_buffer.append(line.strip())
        if len(lines_buffer) > 10:
            lines_buffer.pop(0)

        page_match = re.search(r'Page\s+(\d+)/(\d+)', line)
        if page_match and total_pages > 0:
            current = int(page_match.group(1))
            total = int(page_match.group(2))
            progress = int(current / total * 100)
            elapsed = time.time() - ocr_start
            if current > 0 and elapsed > 0:
                eta = (elapsed / current) * (total - current)
                if eta < 60:
                    eta_str = f"预计剩余 {eta:.0f} 秒"
                else:
                    eta_str = f"预计剩余 {eta / 60:.1f} 分钟"
            else:
                eta_str = ""
            try:
                asyncio.run_coroutine_threadsafe(
                    ws.send_step_progress(task_id, 3, "OCR PDF", progress,
                                          f"已处理 {current}/{total} 页 ({progress}%) {eta_str}"),
                    asyncio.get_event_loop(),
                )
            except Exception:
                pass

    process.wait(timeout=config.ocr_timeout)

    if process.returncode != 0:
        errors = [l for l in lines_buffer if "error" in l.lower() or "Error" in l]
        raise RuntimeError(f"OCR 失败 (exit {process.returncode}): {'; '.join(errors[:3])}")

    if _is_ocr_readable(output_pdf):
        return output_pdf

    return output_pdf


def _is_scanned(path: str, sample_pages: int = 5) -> bool:
    try:
        import fitz
        doc = fitz.open(path)
        blank_count = 0
        for i in range(min(sample_pages, len(doc))):
            text = doc[i].get_text()
            non_ws = sum(1 for c in text if c.strip())
            if len(text) == 0 or non_ws < len(text) * 0.6:
                blank_count += 1
        doc.close()
        return blank_count >= sample_pages * 0.6
    except Exception:
        return False


def _is_ocr_readable(pdf_path: str, sample_pages: int = 5, min_cjk_ratio: float = 0.15) -> bool:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        total = doc.page_count
        if total == 0:
            return True
        indices = [int(total * i / (sample_pages + 1)) for i in range(1, sample_pages + 1)]
        readable = 0
        for idx in indices:
            if idx >= total:
                continue
            text = doc[idx].get_text()
            if not text.strip():
                continue
            total_chars = sum(1 for c in text if not c.isspace())
            cjk = sum(1 for c in text
                      if '\u4e00' <= c <= '\u9fff'
                      or '\u3400' <= c <= '\u4dbf'
                      or '\uf900' <= c <= '\ufaff')
            if total_chars > 0 and cjk / total_chars >= min_cjk_ratio:
                readable += 1
        doc.close()
        return readable >= max(1, sample_pages * 0.6)
    except Exception:
        return True


# ─── Step 3.5: Compress ───────────────────────────────────────────────────

def _run_step3_5(state: dict, params: dict, config: AppConfig, task_id: str, store, ws) -> str:
    """Optional compression with qpdf."""
    pdf_path = state.get("ocr_pdf_path") or state.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        return pdf_path

    output_pdf = pdf_path.replace("_ocr.pdf", "_compressed.pdf").replace(".pdf", "_compressed.pdf")

    try:
        subprocess.run(
            ["qpdf", "--recompress-flate", "--object-streams=generate",
             pdf_path, output_pdf],
            capture_output=True, text=True, timeout=120, check=True, encoding='utf-8', errors='replace',
        )
        if os.path.exists(output_pdf):
            return output_pdf
    except Exception:
        pass

    return pdf_path


# ─── Step 4: Bookmarks ────────────────────────────────────────────────────

def _run_step4(state: dict, params: dict, config: AppConfig, task_id: str, store, ws) -> str:
    """Generate and inject bookmarks."""
    pdf_path = state.get("compressed_pdf_path") or state.get("ocr_pdf_path") or state.get("pdf_path")
    bookmark_text = params.get("bookmark") or ""
    candidates = state.get("candidates", [])
    info = candidates[0] if candidates else {}

    if not bookmark_text or bookmark_text == "not_found":
        try:
            import fitz
            doc = fitz.open(pdf_path)
            for i in range(min(30, len(doc))):
                if doc[i].get_label() == '!00001.jpg':
                    toc = [[1, "目 录", i + 1]]
                    doc.set_toc(toc)
                    output = pdf_path.replace(".pdf", "_bookmarked.pdf")
                    doc.save(output, encryption=fitz.PDF_ENCRYPT_NONE)
                    doc.close()
                    return output
            doc.close()
        except Exception:
            pass
        return pdf_path

    try:
        import fitz
        from scripts.parse_bookmark_hierarchy import parse_bookmark_hierarchy

        structured = parse_bookmark_hierarchy(bookmark_text)

        doc = fitz.open(pdf_path)
        offset = 0
        toc = []

        for i in range(min(30, len(doc))):
            if doc[i].get_label() == '!00001.jpg':
                toc.append([1, "目 录", i + 1])
                break

        for title, sk_page, level in structured:
            page_num = sk_page + offset
            page_num = max(1, min(page_num, len(doc)))
            toc.append([level, title, page_num])

        if toc:
            doc.set_toc(toc)

        output = pdf_path.replace(".pdf", "_bookmarked.pdf")
        if output == pdf_path:
            output = pdf_path.replace(".pdf", "_bkmk.pdf")
        doc.save(output, encryption=fitz.PDF_ENCRYPT_NONE)
        doc.close()
        return output
    except ImportError:
        return pdf_path
    except Exception:
        return pdf_path


# ─── Step 5: Save locally ─────────────────────────────────────────────────

def _run_step5(state: dict, params: dict, config: AppConfig, task_id: str, store, ws) -> dict:
    """Copy the final bookmarked PDF to the finished directory."""
    pdf_path = state.get("bookmarked_pdf_path") or state.get("compressed_pdf_path") or \
               state.get("ocr_pdf_path") or state.get("pdf_path")

    if not pdf_path or not os.path.exists(pdf_path):
        raise RuntimeError("无可保存的 PDF 文件")

    filename = os.path.basename(pdf_path)
    file_size = os.path.getsize(pdf_path)

    finished_dir = config.finished_dir
    os.makedirs(finished_dir, exist_ok=True)

    finished_path = os.path.join(finished_dir, filename)
    import shutil
    shutil.copy2(pdf_path, finished_path)

    state["finished_path"] = finished_path

    return {
        "finished_path": finished_path,
        "filename": filename,
        "size_mb": round(file_size / 1024 / 1024, 1),
    }


# ─── Step 6: Report ───────────────────────────────────────────────────────

def _run_step6(state: dict, params: dict, config: AppConfig, task_id: str, store, ws) -> dict:
    """Generate structured execution report."""
    return _build_full_report(state, params, config)


def _build_full_report(state: dict, params: dict, config: AppConfig = None) -> dict:
    candidates = state.get("candidates", [])
    info = candidates[0] if candidates else {}
    dl = state.get("direct_link", {})

    return {
        "title": info.get("title", params.get("title", "")),
        "authors": info.get("nlc_authors") or info.get("authors") or params.get("authors", []),
        "publisher": info.get("nlc_publisher") or info.get("publisher") or params.get("publisher", ""),
        "isbn": info.get("isbn") or params.get("isbn", ""),
        "ss_code": info.get("ss_code", ""),
        "direct_link_internal": dl.get("internal", dl.get("finished_path", "")),
        "direct_link_external": dl.get("external", ""),
        "filename": dl.get("filename", os.path.basename(state.get("finished_path", ""))),
        "file_size_mb": dl.get("size_mb", 0),
        "finished_path": state.get("finished_path", dl.get("finished_path", "")),
        "steps_completed": state.get("steps_completed", []),
        "errors": state.get("errors", []),
    }


def _build_partial_report(state: dict, params: dict) -> dict:
    report = _build_full_report(state, params)
    report["status"] = "partial"
    return report
