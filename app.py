"""
Claude → OpenAI-Compatible Flask API  (Optimized)
---------------------------------------------------
Optimizations applied:
  1. Reuse a single persistent chat instead of create/delete each request
  2. Auto-reconnect if the persistent chat goes stale
  3. Reduced timeout from 240s → 60s
  4. Message history trimming (last N messages only) to keep prompt short
  5. threaded=True on app.run for safety
  6. Structured JSON logging
  7. /health now reports chat_id status

Endpoints:
  POST  /v1/chat/completions
  GET   /v1/models
  GET   /health

Run:
    python app.py
"""
from license_validator import license_manager
from api_logger import log_request
from dashboard import Dashboard
import time
import uuid
import logging
# Thêm vào đầu file
import json
from flask import Flask, request, jsonify, Response  # thêm Response
from functools import wraps


from claude_api.client import ClaudeAPIClient, SendMessageResponse
from claude_api.session import SessionData, get_session_data
from claude_api.errors import ClaudeAPIError, MessageRateLimitError, OverloadError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config  ← chỉnh ở đây
# ---------------------------------------------------------------------------
import app_config
MODEL_ID = "claude-via-browser"

# Giảm từ 240s → 60s; nếu Claude không trả lời trong 60s coi như lỗi
CLIENT_TIMEOUT = app_config.CLIENT_TIMEOUT

# Chỉ giữ N messages cuối cùng trước khi gửi (tránh prompt quá dài)
MAX_HISTORY_MESSAGES = app_config.MAX_HISTORY_MESSAGES

# Số lần retry khi chat_id bị stale
MAX_RETRIES = app_config.MAX_RETRIES

# ---------------------------------------------------------------------------
# App & global state
# ---------------------------------------------------------------------------
app = Flask(__name__)

session: SessionData | None = None
client: ClaudeAPIClient | None = None
persistent_chat_id: str | None = None   # ← reuse 1 chat duy nhất

import threading
_client_lock = threading.Lock()  # bảo vệ init_client() khỏi race condition


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
def init_client() -> bool:
    global session, client, persistent_chat_id
    if not _client_lock.acquire(blocking=False):
        logger.warning("init_client() đang chạy ở thread khác, bỏ qua.")
        return False
    try:
        # Cleanup chat cũ trước khi tạo mới
        if client is not None and persistent_chat_id is not None:
            try:
                client.delete_chat(persistent_chat_id)
                logger.info("Old chat deleted  id=%s", persistent_chat_id)
            except Exception:
                pass
            persistent_chat_id = None

        logger.info("Initialising Claude session…")
        session = get_session_data(profile=app_config.FIREFOX_PROFILE)
        client = ClaudeAPIClient(session, timeout=CLIENT_TIMEOUT)
        logger.info("Claude client ready ✓")

        # Tạo 1 chat persistent ngay lúc khởi động
        persistent_chat_id = client.create_chat()
        if not persistent_chat_id:
            logger.error("Could not create persistent chat on startup.")
            return False

        logger.info("Persistent chat created  id=%s ✓", persistent_chat_id)
        return True

    except Exception as exc:
        logger.error("Failed to initialise Claude client: %s", exc)
        return False
    finally:
        _client_lock.release()


def refresh_chat() -> bool:
    """Xóa chat cũ (nếu còn) và tạo chat mới. Gọi khi chat bị stale."""
    global persistent_chat_id
    try:
        if persistent_chat_id:
            try:
                client.delete_chat(persistent_chat_id)
                logger.info("Stale chat deleted  id=%s", persistent_chat_id)
            except Exception:
                pass  # không cần xử lý nếu xóa thất bại

        persistent_chat_id = client.create_chat()
        if not persistent_chat_id:
            return False

        logger.info("Chat refreshed  new_id=%s", persistent_chat_id)
        return True

    except Exception as exc:
        logger.error("refresh_chat failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def require_client(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if client is None or persistent_chat_id is None:
            return openai_error(
                "Claude client is not initialised. Check server logs.",
                code="service_unavailable",
                status=503,
            )
        return fn(*args, **kwargs)
    return wrapper


def openai_error(message: str, code: str = "internal_error", status: int = 500):
    return jsonify({
        "error": {
            "message": message,
            "type":    "api_error",
            "code":    code,
        }
    }), status


def build_chat_response(answer: str, model: str) -> dict:
    return {
        "id":      f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object":  "chat.completion",
        "created": int(time.time()),
        "model":   model,
        "choices": [
            {
                "index":         0,
                "message":       {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "total_tokens":      0,
        },
    }


def messages_to_prompt(messages: list[dict]) -> str:
    """
    Trim history xuống MAX_HISTORY_MESSAGES rồi flatten thành 1 prompt string.
    Luôn giữ system message (nếu có) + N messages cuối.
    """
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system  = [m for m in messages if m.get("role") != "system"]

    # Chỉ lấy N messages cuối (tránh prompt phình to theo thời gian)
    trimmed = non_system[-MAX_HISTORY_MESSAGES:]

    final_messages = system_msgs + trimmed

    parts = []
    for msg in final_messages:
        role    = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"[System]: {content}")
        elif role == "assistant":
            parts.append(f"[Assistant]: {content}")
        else:
            parts.append(f"[User]: {content}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return jsonify({
        "status":       "ok",
        "client_ready": client is not None,
        "chat_id":      persistent_chat_id,
    })


@app.get("/v1/models")
def list_models():
    now = int(time.time())
    return jsonify({
        "object": "list",
        "data": [
            {
                "id":         MODEL_ID,
                "object":     "model",
                "created":    now,
                "owned_by":   "claude-browser",
                "permission": [],
                "root":       MODEL_ID,
                "parent":     None,
            }
        ],
    })
@app.post("/v1/chat/completions")
@require_client
def chat_completions():
    if not license_manager.is_valid():
        return openai_error(
            "License không hợp lệ hoặc chưa được kích hoạt.",
            code="license_error",
            status=403,
        )
    _start = time.time()
    body: dict = request.get_json(silent=True) or {}

    messages: list[dict] = body.get("messages", [])
    if not messages:
        return openai_error(
            "'messages' is required and must not be empty.",
            code="invalid_request_error",
            status=400,
        )

    model: str  = body.get("model", MODEL_ID)
    stream: bool = body.get("stream", False)  # ← đọc stream flag
    prompt = messages_to_prompt(messages)

    logger.info(
        "Request  model=%s  messages=%d  prompt_chars=%d  stream=%s",
        model, len(messages), len(prompt), stream,
    )

    # ── Gửi message, retry nếu chat stale ──────────────────────────────────
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res: SendMessageResponse = client.send_message(persistent_chat_id, prompt)

            if res.answer:
                logger.info("Answer received  attempt=%d  chars=%d", attempt, len(res.answer))

                # ── Streaming response ──────────────────────────────────────
                if stream:
                    def generate(answer=res.answer, model=model):
                        chunk_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
                        created  = int(time.time())

                        # Chunk 1: role
                        yield "data: " + json.dumps({
                            "id": chunk_id, "object": "chat.completion.chunk",
                            "created": created, "model": model,
                            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
                        }) + "\n\n"

                        # Chunk 2: content (gửi từng 20 ký tự để thấy stream)
                        chunk_size = 20
                        for i in range(0, len(answer), chunk_size):
                            yield "data: " + json.dumps({
                                "id": chunk_id, "object": "chat.completion.chunk",
                                "created": created, "model": model,
                                "choices": [{"index": 0, "delta": {"content": answer[i:i+chunk_size]}, "finish_reason": None}]
                            }) + "\n\n"

                        # Chunk 3: finish
                        yield "data: " + json.dumps({
                            "id": chunk_id, "object": "chat.completion.chunk",
                            "created": created, "model": model,
                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                        }) + "\n\n"

                        yield "data: [DONE]\n\n"
                    log_request(status=200, latency_ms=int((time.time()-_start)*1000),
                num_messages=len(messages), tokens_in=len(prompt), tokens_out=len(res.answer))

                    return Response(
                        generate(),
                        mimetype="text/event-stream",
                        headers={
                            "X-Accel-Buffering": "no",
                            "Cache-Control":     "no-cache",
                            "Connection":        "keep-alive",
                        },
                    )

                # ── Non-streaming response ──────────────────────────────────
                return jsonify(build_chat_response(res.answer, model))

            logger.warning("Empty answer  attempt=%d — refreshing chat…", attempt)
            refresh_chat()

        except MessageRateLimitError as exc:
            logger.warning("Rate limit: resets at %s", exc.reset_date)
            return openai_error(
                f"Message rate limit reached. Resets at {exc.reset_date}.",
                code="rate_limit_exceeded", status=429,
            )
        except OverloadError as exc:
            logger.error("Claude overloaded: %s", exc)
            return openai_error(
                "Claude is currently overloaded. Please try again later.",
                code="service_unavailable", status=503,
            )
        except ClaudeAPIError as exc:
            logger.warning("ClaudeAPIError attempt=%d: %s", attempt, exc)
            last_error = exc
            refresh_chat()
        except Exception as exc:
            logger.exception("Unexpected error  attempt=%d", attempt)
            last_error = exc
            refresh_chat()

    logger.error("All %d attempts failed. Last error: %s", MAX_RETRIES, last_error)
    return openai_error(
        f"Claude failed after {MAX_RETRIES} attempts: {last_error}",
        code="upstream_error", status=502,
    )


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_):
    return openai_error("Endpoint not found.", code="not_found", status=404)

@app.errorhandler(405)
def method_not_allowed(_):
    return openai_error("HTTP method not allowed.", code="method_not_allowed", status=405)

@app.errorhandler(500)
def internal_error(exc):
    logger.exception("Unhandled exception")
    return openai_error(str(exc), status=500)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
# if __name__ == "__main__":
#     if not init_client():
#         logger.critical("Aborting — Claude client could not be initialised.")
#         raise SystemExit(1)

#     app.run(
#         host="0.0.0.0",
#         port=5000,
#         debug=False,
#         threaded=True,   # an toàn hơn dù chỉ 1 user
#     )