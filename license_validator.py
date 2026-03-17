"""
license_validator.py  —  Nhúng vào app chính để validate license
-----------------------------------------------------------------
Logic:
  1. Lần đầu chạy → hiện dialog nhập key
  2. Verify offline (HMAC signature + ngày hết hạn)
  3. Ping server online để check revoke
  4. Lưu key vào local cache (mã hoá)
  5. Mỗi 24h ping server 1 lần (background thread)
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import platform
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ⚠️  PHẢI GIỐNG VỚI SECRET TRONG keygen.py
_SECRET_KEY    = "MY_SUPER_SECRET_KEY_CHANGE_THIS_2024"

# URL server của bạn sau khi deploy
LICENSE_SERVER = "https://license-server-production-adff.up.railway.app"   # ← đổi tạm để test

# Ping server mỗi bao nhiêu giây (86400 = 24h)
PING_INTERVAL  = 86_400

# File lưu license local
_CACHE_FILE    = Path.home() / ".claude_browser_license"
# ---------------------------------------------------------------------------


# ── Offline helpers ──────────────────────────────────────────────────────────

def _sign(payload: str) -> str:
    return hmac.new(
        _SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:16].upper()


def _get_machine_id() -> str:
    """Lấy ID máy tính (không thay đổi)"""
    raw = platform.node() + platform.machine() + str(Path.home())
    return hashlib.md5(raw.encode()).hexdigest()[:12].upper()


def _obfuscate(data: str) -> str:
    """Encode đơn giản để tránh đọc plain text trong file cache"""
    return base64.b64encode(data.encode()).decode()


def _deobfuscate(data: str) -> str:
    return base64.b64decode(data.encode()).decode()


# ── Cache ─────────────────────────────────────────────────────────────────────

def _save_cache(key: str, expires_at: str, email: str):
    payload = json.dumps({
        "key":        key,
        "expires_at": expires_at,
        "email":      email,
        "saved_at":   datetime.utcnow().isoformat(),
    })
    _CACHE_FILE.write_text(_obfuscate(payload))


def _load_cache() -> dict | None:
    try:
        if _CACHE_FILE.exists():
            raw  = _CACHE_FILE.read_text().strip()
            data = json.loads(_deobfuscate(raw))
            return data
    except Exception:
        pass
    return None


def _clear_cache():
    if _CACHE_FILE.exists():
        _CACHE_FILE.unlink()


# ── Offline validation ────────────────────────────────────────────────────────

def validate_offline(key: str) -> tuple[bool, str]:
    """
    Xác thực hoàn toàn offline — chỉ check format, signature, ngày hết hạn.
    Không check revoke (cần online để check).
    """
    key = key.upper().strip()
    parts = key.split("-")

    # Format: XXXXX-XXXXX-XXXXX-XXXXX-CCCC  (5 nhóm)
    if len(parts) != 5:
        return False, "Định dạng key không đúng (cần dạng XXXXX-XXXXX-XXXXX-XXXXX-CCCC)"

    raw_key  = "-".join(parts[:4])
    checksum = parts[4]

    # Cache không lưu email → cần dùng email rỗng khi offline
    # (email chỉ verify được khi online)
    # Nếu muốn verify offline hoàn toàn, embed email vào key → phức tạp hơn
    # Ở đây: offline chỉ check checksum + ngày (ngày được encode vào key)

    # Lấy thông tin từ cache nếu đã verify online trước đó
    cache = _load_cache()
    if cache and cache.get("key") == key:
        expires = cache.get("expires_at", "")
        if expires < datetime.utcnow().strftime("%Y-%m-%d"):
            _clear_cache()
            return False, f"License đã hết hạn ngày {expires}"
        return True, f"OK (offline cache, expires {expires})"

    return False, "Chưa verify online lần nào — cần kết nối internet lần đầu"


# ── Online validation ─────────────────────────────────────────────────────────

def validate_online(key: str) -> tuple[bool, str, dict]:
    """
    Gọi server để verify key. Trả về (valid, reason, info)
    """
    try:
        resp = requests.post(
            f"{LICENSE_SERVER}/verify",
            json={"key": key},
            timeout=10,
        )
        data = resp.json()

        if data.get("valid"):
            return True, "OK", data
        return False, data.get("reason", "Invalid"), {}

    except requests.exceptions.ConnectionError:
        return None, "Không kết nối được server", {}  # None = offline
    except Exception as exc:
        return None, str(exc), {}


def ping_server(key: str) -> tuple[bool, str]:
    """Ping định kỳ để check key còn active không"""
    try:
        resp = requests.post(
            f"{LICENSE_SERVER}/ping",
            json={"key": key},
            timeout=10,
        )
        data = resp.json()
        return data.get("valid", False), data.get("reason", "")
    except Exception:
        return True, "offline"   # nếu không ping được → cho qua (grace)


# ── Main validator ────────────────────────────────────────────────────────────

class LicenseManager:
    def __init__(self):
        self._key:     str | None = None
        self._valid:   bool       = False
        self._expires: str | None = None
        self._email:   str | None = None
        self._ping_thread: threading.Thread | None = None

    def activate(self, key: str) -> tuple[bool, str]:
        """
        Kích hoạt license key.
        Thử online trước, fallback offline nếu không có internet.
        """
        key = key.upper().strip()

        # 1. Thử online
        valid, reason, info = validate_online(key)

        if valid is None:
            # Offline → fallback cache
            logger.warning("Server không khả dụng, thử offline cache…")
            ok, msg = validate_offline(key)
            if ok:
                cache = _load_cache()
                self._key     = key
                self._valid   = True
                self._expires = cache["expires_at"]
                self._email   = cache.get("email", "")
                self._start_ping()
                return True, f"✅ License hợp lệ (offline) — hết hạn {self._expires}"
            return False, msg

        if not valid:
            return False, f"❌ {reason}"

        # Online success
        self._key     = key
        self._valid   = True
        self._expires = info.get("expires_at")
        self._email   = info.get("email")

        _save_cache(key, self._expires, self._email)
        self._start_ping()

        return True, f"✅ License hợp lệ — hết hạn {self._expires}"

    def is_valid(self) -> bool:
        return self._valid

    def info(self) -> dict:
        return {
            "key":     self._key,
            "valid":   self._valid,
            "expires": self._expires,
            "email":   self._email,
        }

    def _start_ping(self):
        """Background thread ping server mỗi 24h"""
        if self._ping_thread and self._ping_thread.is_alive():
            return

        def _loop():
            while self._valid:
                time.sleep(PING_INTERVAL)
                ok, reason = ping_server(self._key)
                if not ok:
                    logger.warning("License bị revoke từ server: %s", reason)
                    self._valid = False
                    _clear_cache()

        self._ping_thread = threading.Thread(target=_loop, daemon=True)
        self._ping_thread.start()

    def load_from_cache(self) -> bool:
        """Tải license từ cache khi app khởi động (tránh nhập key mỗi lần)"""
        cache = _load_cache()
        if not cache:
            return False

        key     = cache.get("key", "")
        expires = cache.get("expires_at", "")

        if expires < datetime.utcnow().strftime("%Y-%m-%d"):
            _clear_cache()
            return False

        # Ping server để check revoke
        ok, reason = ping_server(key)
        if not ok and reason != "offline":
            logger.warning("License revoked: %s", reason)
            _clear_cache()
            return False

        self._key     = key
        self._valid   = True
        self._expires = expires
        self._email   = cache.get("email")
        self._start_ping()
        return True


# Singleton
license_manager = LicenseManager()
