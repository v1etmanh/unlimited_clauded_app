"""
keygen.py  —  Công cụ TẠO license key (chỉ bạn dùng)
------------------------------------------------------
Cách dùng:
    python keygen.py --email user@gmail.com --days 30
    python keygen.py --email user@gmail.com --days 365
    python keygen.py --list          # xem tất cả key đã tạo
    python keygen.py --revoke KEY    # thu hồi key
"""

import argparse
import hashlib
import hmac
import json
import os
import random
import string
import sys
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# ⚠️  ĐỔI SECRET NÀY THÀNH CHUỖI BÍ MẬT CỦA BẠN — KHÔNG CHIA SẺ CHO AI
SECRET_KEY = "MY_SUPER_SECRET_KEY_CHANGE_THIS_2024"
# ---------------------------------------------------------------------------

DB_FILE = "licenses.json"   # file lưu toàn bộ key đã cấp


# ── Helpers ─────────────────────────────────────────────────────────────────

def load_db() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}


def save_db(db: dict):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def generate_raw_key() -> str:
    """Tạo chuỗi ngẫu nhiên dạng XXXXX-XXXXX-XXXXX-XXXXX"""
    chars = string.ascii_uppercase + string.digits
    groups = ["".join(random.choices(chars, k=5)) for _ in range(4)]
    return "-".join(groups)


def sign_payload(payload: str) -> str:
    """Tạo HMAC-SHA256 signature từ payload"""
    return hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:16].upper()


def create_license(email: str, days: int) -> dict:
    """Tạo 1 license record hoàn chỉnh"""
    raw_key    = generate_raw_key()
    expires_at = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Payload để ký: key + email + expires
    payload   = f"{raw_key}:{email}:{expires_at}"
    signature = sign_payload(payload)

    # License key cuối = raw_key + checksum 4 ký tự
    checksum    = signature[:4]
    license_key = f"{raw_key}-{checksum}"

    return {
        "key":        license_key,
        "email":      email,
        "expires_at": expires_at,
        "created_at": created_at,
        "revoked":    False,
        "signature":  signature,
    }


def verify_signature(record: dict) -> bool:
    """Kiểm tra signature của 1 record có hợp lệ không"""
    raw_key  = "-".join(record["key"].split("-")[:4])
    payload  = f"{raw_key}:{record['email']}:{record['expires_at']}"
    expected = sign_payload(payload)
    return record["signature"] == expected


# ── CLI commands ─────────────────────────────────────────────────────────────

def cmd_create(email: str, days: int):
    db      = load_db()
    record  = create_license(email, days)
    key     = record["key"]
    db[key] = record
    save_db(db)

    print("\n✅ License key đã tạo thành công!")
    print("─" * 50)
    print(f"  Key     : {key}")
    print(f"  Email   : {email}")
    print(f"  Expires : {record['expires_at']}  ({days} ngày)")
    print(f"  Created : {record['created_at']}")
    print("─" * 50)
    print("→ Gửi KEY này cho khách hàng.\n")


def cmd_list():
    db = load_db()
    if not db:
        print("Chưa có license nào.")
        return

    print(f"\n{'KEY':<27} {'EMAIL':<30} {'EXPIRES':<12} {'STATUS'}")
    print("─" * 85)
    for rec in db.values():
        status = "❌ REVOKED" if rec["revoked"] else (
            "⚠️  EXPIRED" if rec["expires_at"] < datetime.utcnow().strftime("%Y-%m-%d")
            else "✅ ACTIVE"
        )
        print(f"{rec['key']:<27} {rec['email']:<30} {rec['expires_at']:<12} {status}")
    print()


def cmd_revoke(key: str):
    db = load_db()
    key = key.upper()
    if key not in db:
        print(f"❌ Không tìm thấy key: {key}")
        return
    db[key]["revoked"] = True
    save_db(db)
    print(f"✅ Đã revoke key: {key}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="License Key Generator")
    parser.add_argument("--email",  help="Email khách hàng")
    parser.add_argument("--days",   type=int, default=30, help="Số ngày hiệu lực (default: 30)")
    parser.add_argument("--list",   action="store_true", help="Liệt kê tất cả key")
    parser.add_argument("--revoke", metavar="KEY", help="Thu hồi key")
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.revoke:
        cmd_revoke(args.revoke)
    elif args.email:
        cmd_create(args.email, args.days)
    else:
        parser.print_help()
