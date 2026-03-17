"""
api_logger.py — Ghi log mỗi API call vào data/api_history.json
--------------------------------------------------------------
app.py chỉ cần import log_request() — không biết gì về dashboard.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).parent / "data" / "api_history.json"
MAX_RECORDS = 500   # giữ tối đa 500 records gần nhất


def _load() -> list:
    try:
        if LOG_FILE.exists():
            return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save(records: list):
    LOG_FILE.parent.mkdir(exist_ok=True)
    LOG_FILE.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def log_request(
    *,
    endpoint: str = "/v1/chat/completions",
    status: int   = 200,
    latency_ms: int = 0,
    num_messages: int = 0,
    tokens_in: int  = 0,
    tokens_out: int = 0,
    model: str      = "",
):
    """
    Ghi 1 record vào api_history.json.
    Gọi ở cuối mỗi endpoint trong app.py:

        log_request(
            status=200,
            latency_ms=int((time.time() - start) * 1000),
            num_messages=len(messages),
            tokens_in=prompt_tokens,
            tokens_out=completion_tokens,
        )
    """
    records = _load()
    records.insert(0, {
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "endpoint":     endpoint,
        "model":        model,
        "num_messages": num_messages,
        "latency_ms":   latency_ms,
        "status":       status,
        "tokens_in":    tokens_in,
        "tokens_out":   tokens_out,
    })
    _save(records[:MAX_RECORDS])


def get_records(limit: int = 200) -> list:
    """Dashboard dùng để đọc lịch sử"""
    return _load()[:limit]


def get_stats() -> dict:
    """Thống kê tổng hợp cho tab Account"""
    records = _load()
    if not records:
        return {
            "total": 0, "success": 0, "error": 0,
            "avg_latency": 0, "total_tokens": 0,
            "success_rate": 0,
        }

    total    = len(records)
    success  = sum(1 for r in records if r.get("status", 0) < 400)
    error    = total - success
    avg_lat  = int(sum(r.get("latency_ms", 0) for r in records) / total)
    total_tk = sum(r.get("tokens_in", 0) + r.get("tokens_out", 0) for r in records)

    return {
        "total":        total,
        "success":      success,
        "error":        error,
        "avg_latency":  avg_lat,
        "total_tokens": total_tk,
        "success_rate": round(success / total * 100, 1),
    }
