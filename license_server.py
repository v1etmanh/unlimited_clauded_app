"""
license_server.py  —  Server xác thực license online
------------------------------------------------------
Deploy lên: Railway / Render / VPS bất kỳ (miễn phí)

Endpoints:
  POST /verify      → app gọi để xác thực key
  GET  /ping        → app gọi định kỳ để check còn active không
  GET  /admin/list  → bạn xem danh sách (cần ADMIN_TOKEN)
"""

import hashlib
import hmac
import json
import os
from datetime import datetime

from flask import Flask, request, jsonify

# ---------------------------------------------------------------------------
# ⚠️  PHẢI GIỐNG VỚI SECRET TRONG keygen.py
SECRET_KEY   = "MY_SUPER_SECRET_KEY_CHANGE_THIS_2024"
ADMIN_TOKEN  = "MY_ADMIN_TOKEN_CHANGE_THIS"          # để bảo vệ /admin
DB_FILE      = "licenses.json"
# ---------------------------------------------------------------------------

app = Flask(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_db() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f:
            return json.load(f)
    return {}


def sign_payload(payload: str) -> str:
    return hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:16].upper()


def check_license(key: str) -> tuple[bool, str]:
    """
    Returns (is_valid, reason)
    """
    db = load_db()
    key = key.upper().strip()

    if key not in db:
        return False, "Key không tồn tại"

    rec = db[key]

    if rec.get("revoked"):
        return False, "Key đã bị thu hồi"

    expires = rec.get("expires_at", "")
    if expires < datetime.utcnow().strftime("%Y-%m-%d"):
        return False, f"Key đã hết hạn ngày {expires}"

    # Verify signature
    raw_key   = "-".join(key.split("-")[:4])
    payload   = f"{raw_key}:{rec['email']}:{rec['expires_at']}"
    expected  = sign_payload(payload)
    if rec.get("signature") != expected:
        return False, "Signature không hợp lệ"

    return True, "OK"


# ── Routes ───────────────────────────────────────────────────────────────────

@app.post("/verify")
def verify():
    """App gọi lần đầu khi user nhập key"""
    data = request.get_json(silent=True) or {}
    key  = data.get("key", "")

    if not key:
        return jsonify({"valid": False, "reason": "Thiếu key"}), 400

    valid, reason = check_license(key)

    if valid:
        db  = load_db()
        rec = db[key.upper()]
        return jsonify({
            "valid":      True,
            "email":      rec["email"],
            "expires_at": rec["expires_at"],
            "reason":     "OK",
        })

    return jsonify({"valid": False, "reason": reason}), 403


@app.post("/ping")
def ping():
    """App gọi định kỳ (mỗi 24h) để check key còn hiệu lực"""
    data = request.get_json(silent=True) or {}
    key  = data.get("key", "")

    valid, reason = check_license(key)
    return jsonify({"valid": valid, "reason": reason})


@app.get("/admin/list")
def admin_list():
    """Xem tất cả key — cần header Authorization: Bearer <ADMIN_TOKEN>"""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    db  = load_db()
    now = datetime.utcnow().strftime("%Y-%m-%d")
    out = []
    for rec in db.values():
        status = "revoked" if rec["revoked"] else (
            "expired" if rec["expires_at"] < now else "active"
        )
        out.append({**rec, "status": status})

    return jsonify(out)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
