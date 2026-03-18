# app_config.py — nguồn config duy nhất cho toàn app
import json
from pathlib import Path

_PROFILE_FILE = Path(__file__).parent / "data" / "user_profile.json"

# ── Defaults ──────────────────────────────────────────────────────────────────
_DEFAULTS = {
    "firefox_profile":      "",
    "flask_port":           5000,
    "client_timeout":       240,
    "max_history_messages": 10,
    "max_retries":          2,
}


def _load() -> dict:
    try:
        if _PROFILE_FILE.exists():
            data = json.loads(_PROFILE_FILE.read_text(encoding="utf-8"))
            return {**_DEFAULTS, **data}   # merge, defaults làm fallback
    except Exception:
        pass
    return _DEFAULTS.copy()


# ── Global vars — import từ đây ───────────────────────────────────────────────
_cfg = _load()

FIREFOX_PROFILE      = _cfg["firefox_profile"]
FLASK_PORT           = _cfg["flask_port"]
CLIENT_TIMEOUT       = _cfg["client_timeout"]
MAX_HISTORY_MESSAGES = _cfg["max_history_messages"]
MAX_RETRIES          = _cfg["max_retries"]


def reload():
    """Gọi sau khi user lưu setting mới — cập nhật global vars"""
    global FIREFOX_PROFILE, FLASK_PORT, CLIENT_TIMEOUT
    global MAX_HISTORY_MESSAGES, MAX_RETRIES
    cfg = _load()
    FIREFOX_PROFILE      = cfg["firefox_profile"]
    FLASK_PORT           = cfg["flask_port"]
    CLIENT_TIMEOUT       = cfg["client_timeout"]
    MAX_HISTORY_MESSAGES = cfg["max_history_messages"]
    MAX_RETRIES          = cfg["max_retries"]


def ensure_defaults_saved():
    """
    Gọi 1 lần khi khởi động — đảm bảo user_profile.json tồn tại
    với đầy đủ các key mặc định, không ghi đè giá trị user đã lưu.
    """
    _PROFILE_FILE.parent.mkdir(exist_ok=True)

    existing = {}
    if _PROFILE_FILE.exists():
        try:
            existing = json.loads(_PROFILE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Chỉ thêm key còn thiếu, không đụng vào key đã có
    merged = {**_DEFAULTS, **existing}

    if merged != existing:
        _PROFILE_FILE.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )