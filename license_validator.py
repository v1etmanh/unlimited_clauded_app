"""
license_validator.py  —  Nhúng vào app chính để validate license
-----------------------------------------------------------------
Flow mới (RSA JWT):
  1. Lần đầu chạy → hiện dialog nhập key
  2. Gọi server /issue-token → nhận JWT token ký bằng RSA private key
  3. Verify token bằng PUBLIC_KEY nhúng cứng trong code (offline)
  4. Lưu token vào local cache
  5. Mỗi 24h ping server /ping → nhận token mới nếu còn hợp lệ
"""

import base64
import hashlib
import logging
import os
import platform
import threading
import time
from datetime import datetime
from pathlib import Path

import jwt
import requests

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

LICENSE_SERVER = "https://license-server-production-adff.up.railway.app"
PING_INTERVAL  = 86_400   # 24h
_CACHE_FILE    = Path.home() / ".claude_browser_license"

# Public key nhúng cứng vào code — chỉ verify được, không tạo được token giả
# Paste nội dung file public_key.pem vào đây
PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtYRjWGP9caD8aWGJisOQ
kzLXlNR9kda8xTxM+7z3TWpAyBOiF2VMv+7eW80efJUIKvKbJVvrdipXLWFTwI32
yDCfYdSPyduTbSwo4uGcMUPaxuHPD4s+A8aBoD/gkaR2mT0lBUIcpir9MEsAC/mR
xr+u2rmqwRmaJpoGpCll7ZSkVvJpXNza+19VwE7bKx+3hcYzzQ9IbsrowQubMYdQ
8RshKLj1TzxUrIfvsZUcNU1SBx93Sq929VjkjSDJVM3WguE2g2L0GyP4969ot6WA
wC31KyGRHUG/oEioZEaaVRXR1W5aSmgyn5e7n8hehxg6Un9r7dQf4Xh2LzE7FJl4
7wIDAQAB
-----END PUBLIC KEY-----"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_machine_id() -> str:
    """ID máy tính — dùng để ràng buộc token với máy cụ thể"""
    raw = platform.node() + platform.machine() + str(Path.home())
    return hashlib.md5(raw.encode()).hexdigest()[:12].upper()


def _obfuscate(data: str) -> str:
    return base64.b64encode(data.encode()).decode()


def _deobfuscate(data: str) -> str:
    return base64.b64decode(data.encode()).decode()


# ── Cache — lưu JWT token ─────────────────────────────────────────────────────

def _save_cache(token: str):
    """Lưu JWT token vào file cache (obfuscated)"""
    _CACHE_FILE.write_text(_obfuscate(token))


def _load_cache() -> str | None:
    """Đọc JWT token từ cache"""
    try:
        if _CACHE_FILE.exists():
            return _deobfuscate(_CACHE_FILE.read_text().strip())
    except Exception:
        pass
    return None


def _clear_cache():
    if _CACHE_FILE.exists():
        _CACHE_FILE.unlink()


# ── Token helpers ─────────────────────────────────────────────────────────────

def verify_token_local(token: str, machine_id: str) -> tuple[bool, dict]:
    """
    Verify JWT bằng public key — hoàn toàn offline.
    Không thể fake vì cần private key để tạo.
    """
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
        if payload.get("machine_id") != machine_id:
            logger.warning("machine_id không khớp — token bị share hoặc giả mạo")
            return False, {}
        return True, payload
    except jwt.ExpiredSignatureError:
        logger.info("Token hết hạn 24h — cần xin token mới")
        return False, {}
    except jwt.InvalidTokenError as e:
        logger.warning("Token không hợp lệ: %s", e)
        return False, {}


def request_token(key: str, machine_id: str) -> tuple[str | None, str]:
    """Gọi server /issue-token để lấy JWT token mới"""
    try:
        resp = requests.post(
            f"{LICENSE_SERVER}/issue-token",
            json={"key": key, "machine_id": machine_id},
            timeout=10,
        )
        try:
            data = resp.json()
        except Exception:
            return None, f"Server lỗi (HTTP {resp.status_code})"

        if resp.status_code == 200:
            return data.get("token"), "OK"
        return None, data.get("error", f"Lỗi {resp.status_code}")

    except requests.exceptions.ConnectionError:
        return None, "OFFLINE"
    except requests.exceptions.Timeout:
        return None, "OFFLINE"
    except Exception as e:
        return None, str(e)


def ping_server(token: str) -> tuple[bool, str, str | None]:
    """
    Ping định kỳ 24h — gửi token cũ, nhận token mới nếu còn hợp lệ.
    Trả về (valid, reason, new_token)
    """
    try:
        resp = requests.post(
            f"{LICENSE_SERVER}/ping",
            json={"token": token},
            timeout=10,
        )
        try:
            data = resp.json()
        except Exception:
            return True, "offline", None   # parse lỗi → cho qua

        valid     = data.get("valid", False)
        reason    = data.get("reason", "")
        new_token = data.get("token")
        return valid, reason, new_token

    except Exception:
        return True, "offline", None   # không ping được → grace period


# ── LicenseManager ────────────────────────────────────────────────────────────

class LicenseManager:
    def __init__(self):
        self._token:   str | None = None
        self._key:     str | None = None
        self._valid:   bool       = False
        self._expires: str | None = None
        self._email:   str | None = None
        self._ping_thread: threading.Thread | None = None

    def _load_from_payload(self, payload: dict, token: str):
        self._token   = token
        self._key     = payload.get("key")
        self._valid   = True
        self._expires = payload.get("expires_at")
        self._email   = payload.get("email")

    def activate(self, key: str) -> tuple[bool, str]:
        """Kích hoạt license key — xin JWT token từ server rồi verify local"""
        key        = key.upper().strip()
        machine_id = _get_machine_id()

        # 1. Xin token từ server
        token, reason = request_token(key, machine_id)

        if reason == "OFFLINE":
            # Fallback: dùng token cũ trong cache nếu chưa hết hạn
            cached_token = _load_cache()
            if cached_token:
                ok, payload = verify_token_local(cached_token, machine_id)
                if ok:
                    self._load_from_payload(payload, cached_token)
                    self._start_ping()
                    return True, f"✅ License hợp lệ (offline) — hết hạn {self._expires}"
            return False, "❌ Cần kết nối internet để kích hoạt lần đầu"

        if token is None:
            return False, f"❌ {reason}"

        # 2. Verify token bằng public key (offline, không gọi server nữa)
        ok, payload = verify_token_local(token, machine_id)
        if not ok:
            return False, "❌ Token không hợp lệ — liên hệ hỗ trợ"

        # 3. Lưu token + khởi động ping thread
        _save_cache(token)
        self._load_from_payload(payload, token)
        self._start_ping()

        return True, f"✅ License hợp lệ — hết hạn {self._expires}"

    def load_from_cache(self) -> bool:
        """Tải license từ cache khi app khởi động — tránh nhập key mỗi lần"""
        cached_token = _load_cache()
        if not cached_token:
            return False

        machine_id = _get_machine_id()

        # Verify token local trước
        ok, payload = verify_token_local(cached_token, machine_id)
        if not ok:
            # Token hết hạn 24h → ping server xin token mới
            valid, reason, new_token = ping_server(cached_token)
            if not valid and reason != "offline":
                logger.warning("License revoked: %s", reason)
                _clear_cache()
                return False
            if new_token:
                ok2, payload2 = verify_token_local(new_token, machine_id)
                if ok2:
                    _save_cache(new_token)
                    self._load_from_payload(payload2, new_token)
                    self._start_ping()
                    return True
            _clear_cache()
            return False

        # Token còn hạn → ping server check revoke
        valid, reason, new_token = ping_server(cached_token)
        if not valid and reason != "offline":
            logger.warning("License revoked: %s", reason)
            _clear_cache()
            return False

        # Cập nhật token mới nếu server trả về
        if new_token:
            ok2, payload2 = verify_token_local(new_token, machine_id)
            if ok2:
                _save_cache(new_token)
                payload  = payload2
                cached_token = new_token

        self._load_from_payload(payload, cached_token)
        self._start_ping()
        return True

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
                if not self._token:
                    break
                valid, reason, new_token = ping_server(self._token)
                if not valid and reason != "offline":
                    logger.warning("License bị revoke: %s", reason)
                    self._valid = False
                    _clear_cache()
                    break
                if new_token:
                    machine_id = _get_machine_id()
                    ok, payload = verify_token_local(new_token, machine_id)
                    if ok:
                        _save_cache(new_token)
                        self._token   = new_token
                        self._expires = payload.get("expires_at")

        self._ping_thread = threading.Thread(target=_loop, daemon=True)
        self._ping_thread.start()


# Singleton
license_manager = LicenseManager()