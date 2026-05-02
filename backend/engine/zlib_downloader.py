"""Z-Library downloader using curl_cffi (browser TLS impersonation, works through proxy)."""

import os

from curl_cffi import requests as cffi_requests


def _session(proxy: str = ""):
    """Create a curl_cffi session with browser TLS impersonation."""
    s = cffi_requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    s.impersonate = "chrome120"
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def zlib_login(email: str, password: str, proxy: str = "") -> dict:
    """Login to Z-Library with email+password via eAPI."""
    try:
        s = _session(proxy)
        r = s.post(
            "https://z-lib.sk/eapi/user/login",
            data={"email": email, "password": password},
            timeout=15,
        )
        data = r.json()
        if data.get("success"):
            user = data.get("user", {})
            return {
                "success": True,
                "user": {
                    "id": str(user.get("id", "")),
                    "remix_userid": str(user.get("id", "")),
                    "remix_userkey": user.get("remix_userkey", ""),
                },
            }
        return {"success": False, "error": data.get("error", "邮箱或密码错误")}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


def zlib_search(query: str, email: str, password: str, proxy: str = "",
                limit: int = 5) -> list:
    """Search Z-Library by query. Returns list of book dicts."""
    try:
        s = _session(proxy)
        r = s.post(
            "https://z-lib.sk/eapi/book/search",
            data={"message": query, "limit": str(limit)},
            cookies={
                "remix_userid": email,  # Will be set properly after login
                "remix_userkey": "",
            },
            timeout=15,
        )
        data = r.json()
        return data.get("books", [])
    except Exception:
        return []


def zlib_download_book(book: dict, output_dir: str, proxy: str = "") -> str | None:
    """Download a single book. Returns file path or None."""
    book_id = book.get("id")
    book_hash = book.get("hash")
    if not book_id or not book_hash:
        return None

    try:
        s = _session(proxy)
        r = s.get(
            f"https://z-lib.sk/eapi/book/{book_id}/{book_hash}/file",
            timeout=15,
        )
        file_info = r.json()
        dl_url = file_info.get("file", {}).get("downloadLink", "")
        if not dl_url:
            return None

        name = file_info["file"].get("description", "book")
        ext = file_info["file"].get("extension", "epub")
        dest = os.path.join(output_dir, f"{name}.{ext}")

        r2 = s.get(dl_url, timeout=120, stream=True)
        with open(dest, "wb") as f:
            for chunk in r2.iter_content(chunk_size=65536):
                f.write(chunk)
        if os.path.getsize(dest) > 10240:
            return dest
        os.remove(dest)
    except Exception:
        pass
    return None


def zlib_get_limits(email: str, password: str, proxy: str = "") -> dict:
    """Get download limits via eAPI profile."""
    try:
        s = _session(proxy)
        # First login to get remix tokens
        login_r = s.post(
            "https://z-lib.sk/eapi/user/login",
            data={"email": email, "password": password},
            timeout=15,
        )
        login_data = login_r.json()
        if not login_data.get("success"):
            return {}
        user = login_data.get("user", {})
        uid = str(user.get("id", ""))
        ukey = user.get("remix_userkey", "")

        # Then get profile
        profile_r = s.get(
            "https://z-lib.sk/eapi/user/profile",
            cookies={"remix_userid": uid, "remix_userkey": ukey},
            timeout=15,
        )
        profile = profile_r.json()
        if not profile.get("success"):
            return {}
        pu = profile.get("user", {})
        return {
            "downloads_limit": pu.get("downloads_limit", 10),
            "downloads_today": pu.get("downloads_today", 0),
        }
    except Exception:
        return {}
