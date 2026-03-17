"""
HOW_TO_INTEGRATE.py — Hướng dẫn tích hợp vào app.py
=====================================================
KHÔNG import file này — chỉ đọc để tham khảo.
"""

# ══════════════════════════════════════════════════════════════
# BƯỚC 1: Thêm vào đầu app.py
# ══════════════════════════════════════════════════════════════

"""
import time
from api_logger import log_request
from dashboard import Dashboard
"""

# ══════════════════════════════════════════════════════════════
# BƯỚC 2: Bọc endpoint chat_completions bằng log
# ══════════════════════════════════════════════════════════════

"""
@app.post("/v1/chat/completions")
@require_client
def chat_completions():
    _start = time.time()                          # ← thêm dòng này
    body: dict = request.get_json(silent=True) or {}
    messages: list[dict] = body.get("messages", [])

    if not messages:
        log_request(status=400, latency_ms=int((time.time()-_start)*1000))  # ← log lỗi
        return openai_error(...)

    # ... toàn bộ logic gốc giữ nguyên ...

    # Trước khi return response thành công:
    log_request(
        status=200,
        latency_ms    = int((time.time() - _start) * 1000),
        num_messages  = len(messages),
        tokens_in     = response_data.get("usage", {}).get("prompt_tokens", 0),
        tokens_out    = response_data.get("usage", {}).get("completion_tokens", 0),
        model         = body.get("model", ""),
    )
    return response
"""

# ══════════════════════════════════════════════════════════════
# BƯỚC 3: Khởi động Dashboard sau license check
# ══════════════════════════════════════════════════════════════

"""
if __name__ == "__main__":
    if not check_license():
        logger.critical("License không hợp lệ. Thoát.")
        sys.exit(1)

    # Chạy Flask trong background thread
    import threading
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, threaded=True),
        daemon=True,
    )
    flask_thread.start()

    # Mở Dashboard (blocking — Tkinter mainloop)
    dash = Dashboard(
        license_info = license_manager.info(),
        on_logout    = lambda: sys.exit(0),
    )
    dash.run()
"""

# ══════════════════════════════════════════════════════════════
# BƯỚC 4: Tạo demo data để test (chạy file này trực tiếp)
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json, random
    from pathlib import Path
    from datetime import datetime, timedelta
    from api_logger import log_request

    print("Tạo demo data...")
    Path("data").mkdir(exist_ok=True)

    models  = ["claude-3-5-sonnet", "claude-3-haiku", "gpt-4o"]
    statuses = [200]*12 + [400, 500]   # phần lớn thành công

    for i in range(40):
        delta   = timedelta(hours=random.randint(0, 72))
        ts_fake = (datetime.now() - delta).strftime("%Y-%m-%d %H:%M:%S")
        status  = random.choice(statuses)
        msgs    = random.randint(1, 8)
        lat     = random.randint(300, 3000)
        t_in    = random.randint(50, 500)
        t_out   = random.randint(100, 800)
        model   = random.choice(models)

        log_request(
            status=status,
            latency_ms=lat,
            num_messages=msgs,
            tokens_in=t_in,
            tokens_out=t_out,
            model=model,
        )

    print("✅ Đã tạo 40 records demo trong data/api_history.json")
    print("\n🚀 Chạy dashboard:")
    print("   python dashboard.py")
