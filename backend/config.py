import json
import os
from pathlib import Path
from dataclasses import dataclass

CONFIG_DIR = Path(os.environ.get("BDW_CONFIG_DIR", Path.home() / ".book-downloader"))
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "download_dir": str(Path.home() / "Downloads" / "book-downloader"),
    "finished_dir": str(Path.home() / "Downloads" / "book-downloader" / "finished"),
    "tmp_dir": str(Path.home() / "tmp" / "bdw"),
    "stacks_base_url": "http://localhost:7788",
    "zfile_base_url": "http://192.168.0.7:32771",
    "zfile_external_url": "https://zfile.vip.cpolar.top",
    "zfile_storage_key": "1",
    "http_proxy": "http://127.0.0.1:6244",
    "ocr_jobs": 1,
    "ocr_languages": "chi_sim+eng",
    "ocr_timeout": 7200,
    "nlc_max_workers": 5,
    "ebook_data_geter_path": "auto",
    "ebook_db_path": "",
    "zlib_email": "",
    "zlib_password": "",
    "zlib_remix_userid": "",
    "zlib_remix_userkey": "",
    "aa_membership_key": "",
    "ocr_engine": "tesseract",
}


@dataclass
class AppConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    download_dir: str = str(Path.home() / "Downloads" / "book-downloader")
    finished_dir: str = str(Path.home() / "Downloads" / "book-downloader" / "finished")
    tmp_dir: str = str(Path.home() / "tmp" / "bdw")
    stacks_base_url: str = "http://localhost:7788"
    zfile_base_url: str = "http://192.168.0.7:32771"
    zfile_external_url: str = "https://zfile.vip.cpolar.top"
    zfile_storage_key: str = "1"
    http_proxy: str = "http://127.0.0.1:6244"
    ocr_jobs: int = 1
    ocr_languages: str = "chi_sim+eng"
    ocr_timeout: int = 7200
    nlc_max_workers: int = 5
    ebook_data_geter_path: str = "auto"
    ebook_db_path: str = ""
    zlib_email: str = ""
    zlib_password: str = ""
    zlib_remix_userid: str = ""
    zlib_remix_userkey: str = ""
    aa_membership_key: str = ""
    ocr_engine: str = "tesseract"

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "AppConfig":
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()

    def save(self, path: Path = CONFIG_FILE):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump({k: v for k, v in self.__dict__.items() if not k.startswith("_")}, f, indent=2, ensure_ascii=False)


def load_auth() -> dict:
    """Load credentials from auth.json (legacy format from Hermes)."""
    auth_path = Path.home() / ".hermes" / "auth.json"
    if not auth_path.exists():
        return {}
    with open(auth_path) as f:
        return json.load(f)


def get_zfile_credentials(auth: dict = None) -> tuple:
    """Extract Z-File credentials from auth or environment. Fallback to env vars."""
    if auth is None:
        auth = load_auth()
    username = os.environ.get("ZFILE_USER", "")
    password = os.environ.get("ZFILE_PASS", "")
    token = None
    for cred in auth.get("credential_pool", {}).get("zfile", []):
        if cred.get("label") == "ZFILE_TOKEN":
            token = cred.get("access_token")
            break
    if not token and not username:
        for cred in auth.get("credential_pool", {}).get("zfile", []):
            if cred.get("username"):
                username = cred.get("username")
                password = cred.get("password", "")
                break
    return username, password, token


def get_stacks_api_key(auth: dict = None) -> str:
    """Extract stacks API key from auth."""
    if auth is None:
        auth = load_auth()
    for cred in auth.get("credential_pool", {}).get("stacks", []):
        if cred.get("id") == "stacks-admin":
            return cred.get("access_token", "")
    return ""


ZFILE_USER, ZFILE_PASS, ZFILE_TOKEN = get_zfile_credentials()
STACKS_API_KEY = get_stacks_api_key()
