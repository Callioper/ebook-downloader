import sqlite3
import os
import shutil
from pathlib import Path

from config import AppConfig

config = AppConfig.load()


def _get_local_cache_dir() -> str:
    cache = os.path.join(config.tmp_dir, "db_cache")
    os.makedirs(cache, exist_ok=True)
    return cache


def _cache_db(src: str) -> str | None:
    """Copy DB to local cache (solves UNC locking issues). Returns local path."""
    if not src or not os.path.exists(src):
        return None
    cache_dir = _get_local_cache_dir()
    basename = os.path.basename(src)
    dst = os.path.join(cache_dir, basename)
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return dst
    shutil.copy2(src, dst)
    return dst


def _resolve_db_dir() -> str:
    cfg_path = getattr(config, 'ebook_db_path', '')
    if cfg_path and os.path.isdir(cfg_path):
        return cfg_path
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
        str(Path.home() / "EbookDatabase" / "instance"),
        r"\\wsl.localhost\Ubuntu\home\eclaw\EbookDatabase\instance",
        "/home/eclaw/EbookDatabase/instance",
    ]
    for p in candidates:
        if os.path.isdir(p):
            return p
    return ""


def _connect_db(db_name: str) -> sqlite3.Connection | None:
    db_dir = _resolve_db_dir()
    if not db_dir:
        return None
    src = os.path.join(db_dir, db_name)
    local_path = _cache_db(src)
    if not local_path or not os.path.exists(local_path):
        return None
    try:
        conn = sqlite3.connect(local_path, timeout=5, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA query_only=ON")
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _normalize_book(book: dict) -> dict:
    if "ISBN" in book:
        book["isbn"] = book.pop("ISBN")
    if "SS_code" in book:
        book["ss_code"] = book.pop("SS_code")
    return book


def _search_db(conn: sqlite3.Connection, field: str, query: str,
               limit: int = 50, offset: int = 0) -> tuple:
    field_map = {"title": "title", "author": "author", "publisher": "publisher",
                 "isbn": "ISBN", "sscode": "SS_code"}
    col = field_map.get(field, "title")
    pattern = "%" + query.replace("%", "%%") + "%"

    try:
        c = conn.execute("SELECT count(*) FROM books WHERE %s LIKE ?" % col, (pattern,))
        total = c.fetchone()[0]
        c = conn.execute("SELECT * FROM books WHERE %s LIKE ? ORDER BY id LIMIT ? OFFSET ?" % col,
                         (pattern, limit, offset))
        return [_normalize_book(dict(r)) for r in c.fetchall()], total
    except Exception:
        return [], 0


def search_books(field: str, query: str, fuzzy: bool = True,
                 page: int = 1, page_size: int = 20) -> dict:
    db_dir = _resolve_db_dir()
    if not db_dir:
        return {"books": [], "totalPages": 0, "totalRecords": 0,
                "error": "数据库目录未找到，请在环境配置中设置 ebook_db_path"}

    all_books = []
    total_records = 0
    db_list = []

    for db_name in ["DX_2.0-5.0.db", "DX_6.0.db"]:
        conn = _connect_db(db_name)
        if conn is None:
            continue
        db_list.append(db_name.replace(".db", ""))
        remaining = page_size - len(all_books)
        if remaining <= 0:
            conn.close()
            break
        offset = (page - 1) * page_size
        books, total = _search_db(conn, field, query, limit=remaining, offset=offset)
        for b in books:
            b["source"] = db_name.replace(".db", "")
        all_books.extend(books)
        total_records += total
        conn.close()

    # Deduplicate by ISBN + SS_code, keeping first occurrence
    seen = set()
    deduped = []
    for b in all_books:
        key = (b.get("isbn", ""), b.get("ss_code", ""))
        if key not in seen or not key[0]:
            seen.add(key)
            deduped.append(b)
    all_books = deduped
    total_records = len(all_books)

    return {
        "books": all_books,
        "totalPages": max(1, (total_records + page_size - 1) // page_size),
        "totalRecords": total_records,
        "dbs": db_list,
    }


def get_available_dbs() -> list:
    db_dir = _resolve_db_dir()
    if not db_dir:
        return []
    found = []
    for f in ["DX_2.0-5.0.db", "DX_6.0.db"]:
        if os.path.exists(os.path.join(db_dir, f)):
            found.append(f.replace(".db", ""))
    return found


def clear_cache():
    cache = _get_local_cache_dir()
    for f in os.listdir(cache):
        try:
            os.remove(os.path.join(cache, f))
        except Exception:
            pass
