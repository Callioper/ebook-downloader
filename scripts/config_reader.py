#!/usr/bin/env python3
"""
ebook-downloader 配置读取模块

功能：
1. 从 skill 根目录下的 config.yaml 读取配置（不依赖环境变量）
2. 提供类型安全的 getter 方法
3. mask_secrets() / show_config_summary() → 步骤6 调用，打码后展示

用法：
    from scripts.config_reader import ConfigReader

    cfg = ConfigReader()
    ebookdb_url = cfg.get_ebookdb_url()
    dm_url = cfg.get_download_manager_url()

    # 步骤6：显示已打码的配置状态
    print(cfg.show_channel_status())

配置位置：SKILL.md 同级目录下的 config.yaml
自动定位：本脚本所在目录的上一级（即 skill 根目录）
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Optional

# ── 尝试加载 yaml（内置库优先级：yaml > PyYAML > 报错提示安装） ──
try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


# ── 自动定位 skill 根目录 ──────────────────────────────────
# 本脚本位于 skill_dir/scripts/config_reader.py
# → skill 根目录 = 本文件所在目录的上一级
_SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = _SCRIPT_DIR.parent


def _mask(value: str, keep_front: int = 4, keep_back: int = 4) -> str:
    """打码敏感字符串：保留首尾各 N 位，中间替换为 ****"""
    if not value:
        return ""
    v = str(value).strip()
    if len(v) <= keep_front + keep_back:
        return "*" * len(v)
    return v[:keep_front] + "****" + v[-keep_back:]


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1", "on")
    return False


# ── 配置读取器 ────────────────────────────────────────────


class ConfigReader:
    """
    统一的配置读取器。从 skill 根目录下的 config.yaml 加载。

    所有 getter 方法都有默认值，配置缺失不会抛异常，
    而是返回 None 或空字符串，由调用方决定是否跳过对应步骤。
    """

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = SKILL_DIR / "config.yaml"
        self._path = config_path
        self._data: dict = {}
        self._last_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        """加载 YAML 配置到 self._data"""
        if not self._path.exists():
            self._data = {}
            return
        try:
            if yaml is None:
                raise ImportError("PyYAML 未安装，请运行: pip install pyyaml")
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        except Exception as e:
            self._data = {}
            self._last_error = str(e)

    def reload(self) -> None:
        """重新加载配置（运行时修改后调用）"""
        self._load()

    def get_raw(self) -> dict:
        """返回原始配置字典（只读副本）"""
        return dict(self._data)

    # ── 步骤①：EbookDatabase ───────────────────────────

    def get_ebookdb_url(self) -> str:
        """EbookDatabase API 地址，默认 http://127.0.0.1:10223"""
        return self._data.get("ebookdb", {}).get("url", "http://127.0.0.1:10223")

    # ── 步骤②：下载管理器 (stacks) ────────────────────

    def get_download_manager_url(self) -> str:
        """stacks 下载管理器地址，默认 http://127.0.0.1:7788"""
        return self._data.get("download_manager", {}).get("url", "http://127.0.0.1:7788")

    def get_download_api_key(self) -> Optional[str]:
        """stacks Admin API Key，可能为空"""
        return self._data.get("download_manager", {}).get("api_key") or None

    # ── 步骤③：OCR / MinerU ────────────────────────────

    def get_mineru_enabled(self) -> bool:
        """是否启用 MinerU（替代 ocrmypdf）"""
        return _boolish(self._data.get("mineru", {}).get("enabled", False))

    def get_mineru_webui_url(self) -> Optional[str]:
        """MinerU WebUI 地址"""
        return self._data.get("mineru", {}).get("webui_url") or None

    def get_mineru_api_url(self) -> Optional[str]:
        """MinerU API 地址"""
        return self._data.get("mineru", {}).get("api_url") or None

    # ── 步骤④：通知渠道 ────────────────────────────────

    def get_notify_enabled(self) -> bool:
        """是否启用通知"""
        return _boolish(self._data.get("notify", {}).get("enabled", False))

    def get_notify_channel(self) -> str:
        """通知渠道：qqbot / telegram / feishu / none"""
        return self._data.get("notify", {}).get("channel", "none")

    def get_qqbot_app_id(self) -> Optional[str]:
        return self._data.get("notify", {}).get("qqbot", {}).get("app_id") or None

    def get_qqbot_token(self) -> Optional[str]:
        return self._data.get("notify", {}).get("qqbot", {}).get("token") or None

    def get_qqbot_channel_id(self) -> Optional[str]:
        return self._data.get("notify", {}).get("qqbot", {}).get("channel_id") or None

    def get_telegram_bot_token(self) -> Optional[str]:
        return self._data.get("notify", {}).get("telegram", {}).get("bot_token") or None

    def get_telegram_chat_id(self) -> Optional[str]:
        return self._data.get("notify", {}).get("telegram", {}).get("chat_id") or None

    def get_feishu_webhook_url(self) -> Optional[str]:
        return self._data.get("notify", {}).get("feishu", {}).get("webhook_url") or None

    # ── 步骤⑤：代理 ───────────────────────────────────

    def get_http_proxy(self) -> Optional[str]:
        return self._data.get("proxy", {}).get("http") or None

    def get_https_proxy(self) -> Optional[str]:
        return self._data.get("proxy", {}).get("https") or None

    def get_no_proxy(self) -> str:
        return self._data.get("proxy", {}).get("no_proxy", "127.0.0.1,localhost")

    # ── 整体校验 ───────────────────────────────────────

    def is_ready(self) -> bool:
        """检查最小可用配置：EbookDatabase + stacks 必须配齐"""
        ebookdb_ok = bool(self.get_ebookdb_url())
        dm_ok = bool(self.get_download_manager_url()) and bool(
            self.get_download_api_key()
        )
        return ebookdb_ok and dm_ok

    def get_errors(self) -> list[str]:
        """返回配置缺失项列表"""
        errors = []
        if not self.get_ebookdb_url():
            errors.append("ebookdb.url 未配置")
        if not self.get_download_manager_url():
            errors.append("download_manager.url 未配置")
        if not self.get_download_api_key():
            errors.append("download_manager.api_key 未配置（stacks API 必需）")
        return errors

    # ── 步骤6：打码展示 ────────────────────────────────

    def show_channel_status(self) -> str:
        """
        返回各渠道配置状态（敏感字段已打码）。
        供步骤6调用，直接在终端打印或推送到通知渠道。
        """
        lines = []
        lines.append("ebook-downloader 渠道配置状态")
        lines.append("─" * 40)

        # 步骤① EbookDatabase
        lines.append(f"  EbookDatabase: {self.get_ebookdb_url()}")

        # 步骤② 下载管理器
        dm_key = self.get_download_api_key()
        key_display = (
            _mask(dm_key, keep_front=6, keep_back=4) if dm_key else "未配置 ⚠️"
        )
        lines.append(f"  stacks 下载器: {self.get_download_manager_url()}")
        lines.append(f"  API Key:      {key_display}")

        # 步骤③ OCR
        ocr_mode = "MinerU" if self.get_mineru_enabled() else "ocrmypdf+PaddleOCR"
        lines.append(f"  OCR 方案:     {ocr_mode}")
        if self.get_mineru_enabled():
            lines.append(
                f"  MinerU WebUI: {self.get_mineru_webui_url() or '未配置 ⚠️'}"
            )
            lines.append(
                f"  MinerU API:   {self.get_mineru_api_url() or '未配置 ⚠️'}"
            )

        # 步骤④ 通知
        channel = self.get_notify_channel()
        notify_enabled = self.get_notify_enabled()
        if not notify_enabled or channel == "none":
            lines.append(f"  通知渠道:     未启用")
        else:
            lines.append(f"  通知渠道:     {channel}")
            if channel == "qqbot":
                app_id = self.get_qqbot_app_id() or "未配置 ⚠️"
                token = (
                    _mask(self.get_qqbot_token(), keep_front=3, keep_back=3)
                    if self.get_qqbot_token()
                    else "未配置 ⚠️"
                )
                cid = self.get_qqbot_channel_id() or "未配置 ⚠️"
                lines.append(f"    AppID:       {app_id}")
                lines.append(f"    Token:       {token}")
                lines.append(f"    频道 ID:     {cid}")
            elif channel == "telegram":
                token = (
                    _mask(self.get_telegram_bot_token(), keep_front=3, keep_back=3)
                    if self.get_telegram_bot_token()
                    else "未配置 ⚠️"
                )
                chat_id = self.get_telegram_chat_id() or "未配置 ⚠️"
                lines.append(f"    Bot Token:   {token}")
                lines.append(f"    Chat ID:     {chat_id}")
            elif channel == "feishu":
                url = self.get_feishu_webhook_url() or "未配置 ⚠️"
                lines.append(f"    Webhook:     {url}")

        # 步骤⑤ 代理
        http_proxy = self.get_http_proxy()
        https_proxy = self.get_https_proxy()
        if http_proxy or https_proxy:
            lines.append(
                f"  HTTP 代理:    {_mask(http_proxy, keep_front=8, keep_back=0) if http_proxy else '无'}"
            )
            lines.append(
                f"  HTTPS 代理:   {_mask(https_proxy, keep_front=8, keep_back=0) if https_proxy else '无'}"
            )
        else:
            lines.append(f"  代理:         未配置（直连）")

        lines.append("─" * 40)

        # 校验结果
        if self.is_ready():
            lines.append("  状态: ✅ 最小配置可用")
        else:
            for err in self.get_errors():
                lines.append(f"  状态: ⚠️  {err}")

        return "\n".join(lines)


# ── CLI 测试入口 ──────────────────────────────────────

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(f"ebook-downloader 配置读取工具")
        print(f"")
        print(f"  配置文件: {SKILL_DIR / 'config.yaml'}")
        print(f"")
        print(f"  用法: python {__file__} [--json] [--check]")
        print(f"    --json    输出完整配置（已打码）")
        print(f"    --check   仅检查配置是否完整，exit code 反映结果")
        print(f"    无参数    显示渠道配置状态")
        sys.exit(0)

    cfg = ConfigReader()

    if "--json" in sys.argv:
        raw = cfg.get_raw()
        masked = {
            "ebookdb": {"url": raw.get("ebookdb", {}).get("url", "")},
            "download_manager": {
                "url": raw.get("download_manager", {}).get("url", ""),
                "api_key": _mask(
                    raw.get("download_manager", {}).get("api_key", ""),
                    keep_front=6,
                    keep_back=4,
                ),
            },
            "mineru": raw.get("mineru", {}),
            "notify": {
                "enabled": raw.get("notify", {}).get("enabled", False),
                "channel": raw.get("notify", {}).get("channel", "none"),
                "qqbot": {
                    "app_id": raw.get("notify", {}).get("qqbot", {}).get("app_id", ""),
                    "token": _mask(
                        raw.get("notify", {}).get("qqbot", {}).get("token", ""),
                        keep_front=3,
                        keep_back=3,
                    ),
                    "channel_id": raw.get("notify", {})
                    .get("qqbot", {})
                    .get("channel_id", ""),
                },
            },
            "proxy": {
                "http": _mask(
                    raw.get("proxy", {}).get("http", ""), keep_front=8, keep_back=0
                ),
                "https": _mask(
                    raw.get("proxy", {}).get("https", ""), keep_front=8, keep_back=0
                ),
            },
        }
        print(json.dumps(masked, indent=2, ensure_ascii=False))
        sys.exit(0)

    if "--check" in sys.argv:
        if cfg.is_ready():
            print("✅ 配置完整")
            sys.exit(0)
        else:
            for err in cfg.get_errors():
                print(f"❌ {err}")
            sys.exit(1)

    print(cfg.show_channel_status())
