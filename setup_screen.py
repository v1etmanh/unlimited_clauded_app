# setup_screen.py
"""
Màn hình Setup — hiện MỌI LẦN khởi động (trước License check).
- Tự động kiểm tra port hiện tại
- Nếu port OK  → nút Skip khả dụng
- Nếu port lỗi → bắt buộc nhập port mới trước khi tiếp tục
- Cho phép đổi Firefox profile bất kỳ lúc nào
"""
import json
import os
import socket
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from app_config import (
    FIREFOX_PROFILE,
    CLIENT_TIMEOUT,
    MAX_HISTORY_MESSAGES,
    MAX_RETRIES,
    FLASK_PORT
)
_PROFILE_FILE = Path(__file__).parent / "data" / "user_profile.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_cfg() -> dict:
    try:
        if _PROFILE_FILE.exists():
            return json.loads(_PROFILE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_cfg(patch: dict):
    _PROFILE_FILE.parent.mkdir(exist_ok=True)
    existing = _load_cfg()
    merged = {**existing, **patch}
    _PROFILE_FILE.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _port_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", port)) != 0
    except Exception:
        return False


# ── Setup Screen ──────────────────────────────────────────────────────────────

class SetupScreen:
    """
    Trả về True  → tiếp tục khởi động
    Trả về False → user bấm Thoát
    """

    BG  = "#1e1e2e"
    FG  = "#cdd6f4"
    SUB = "#a6adc8"
    INP = "#313244"
    ACC = "#89b4fa"
    OK  = "#a6e3a1"
    ERR = "#f38ba8"
    BTN = "#45475a"

    def __init__(self):
        
        
        self.result = False
        self._cfg   = _load_cfg()

    # ── Tạo root TRƯỚC, rồi mới tạo Variables ──
        self.root = tk.Tk()
        self.root.title("Khởi động — Kiểm tra cấu hình")
        self.root.geometry("520x370")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)

    # IntVar / StringVar phải sau tk.Tk()
        self._port_var    = tk.IntVar(value=self._cfg.get("flask_port",FLASK_PORT ))
        self._profile_var = tk.StringVar(value=self._cfg.get("firefox_profile", FIREFOX_PROFILE))
        self._port_ok     = False

        self._center()
        self._build()
        self.root.after(200, self._auto_check)
    # ── Layout ────────────────────────────────────────────────────────────────

    def _center(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - 520) // 2
        y = (self.root.winfo_screenheight() - 370) // 2
        self.root.geometry(f"520x370+{x}+{y}")

    def _label(self, parent, text, size=10, bold=False, color=None, anchor="w"):
        return tk.Label(
            parent, text=text,
            font=("Segoe UI", size, "bold" if bold else "normal"),
            bg=self.BG, fg=color or self.FG, anchor=anchor,
        )

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        self._label(self.root, "⚙  Kiểm tra cấu hình khởi động",
                    size=14, bold=True, anchor="center").pack(pady=(22, 3))
        self._label(self.root, "Xác nhận port và Firefox profile trước khi chạy",
                    color=self.SUB, anchor="center").pack(pady=(0, 18))

        body = tk.Frame(self.root, bg=self.BG)
        body.pack(padx=36, fill="x")
        body.columnconfigure(0, weight=1)

        # ── PORT ──────────────────────────────────────────────────────────────
        self._label(body, "Flask port", bold=True).grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        port_row = tk.Frame(body, bg=self.BG)
        port_row.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self._port_entry = tk.Spinbox(
            port_row, from_=1024, to=65535,
            textvariable=self._port_var,
            font=("Consolas", 12),
            bg=self.INP, fg=self.FG,
            insertbackground=self.FG,
            relief="flat", bd=4, width=8,
            command=self._on_port_change,   # khi bấm mũi tên spinbox
        )
        self._port_entry.pack(side="left")
        self._port_entry.bind("<KeyRelease>", lambda e: self._on_port_change())

        tk.Button(
            port_row, text="Kiểm tra port",
            font=("Segoe UI", 9),
            bg=self.BTN, fg=self.FG,
            relief="flat", padx=12, pady=4, cursor="hand2",
            command=self._check_port,
        ).pack(side="left", padx=(10, 0))

        # Badge trạng thái port
        self._port_badge = tk.Label(
            port_row, text="", font=("Segoe UI", 9, "bold"),
            bg=self.BG, fg=self.OK, anchor="w",
        )
        self._port_badge.pack(side="left", padx=(10, 0))

        # Dòng mô tả lỗi port
        self._port_hint = tk.Label(
            body, text="", font=("Segoe UI", 8),
            bg=self.BG, fg=self.ERR, anchor="w",
        )
        self._port_hint.grid(row=2, column=0, sticky="w", pady=(0, 14))

        # ── FIREFOX PROFILE ───────────────────────────────────────────────────
        self._label(body, "Firefox profile", bold=True).grid(
            row=3, column=0, sticky="w", pady=(0, 4))

        prof_row = tk.Frame(body, bg=self.BG)
        prof_row.grid(row=4, column=0, sticky="ew", pady=(0, 4))
        prof_row.columnconfigure(0, weight=1)

        tk.Entry(
            prof_row, textvariable=self._profile_var,
            font=("Consolas", 9),
            bg=self.INP, fg=self.FG,
            insertbackground=self.FG,
            relief="flat", bd=4,
        ).grid(row=0, column=0, sticky="ew", ipady=5)

        tk.Button(
            prof_row, text="Chọn...",
            font=("Segoe UI", 9),
            bg=self.BTN, fg=self.FG,
            relief="flat", padx=10, pady=4, cursor="hand2",
            command=self._browse,
        ).grid(row=0, column=1, padx=(8, 0))

        default_path = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")
        self._label(body,
                    f"Thường ở: {default_path}",
                    size=8, color="#585b70").grid(
            row=5, column=0, sticky="w", pady=(2, 0))

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=self.BG)
        btn_frame.pack(pady=22)

        self._skip_btn = tk.Button(
            btn_frame, text="Skip — tiếp tục",
            font=("Segoe UI", 10, "bold"),
            bg=self.ACC, fg="#1e1e2e",
            relief="flat", padx=18, pady=7, cursor="hand2",
            command=self._skip,
            state="disabled",         # disabled cho đến khi port OK
        )
        self._skip_btn.pack(side="left", padx=6)

        tk.Button(
            btn_frame, text="Lưu & tiếp tục",
            font=("Segoe UI", 10),
            bg="#313244", fg=self.FG,
            relief="flat", padx=18, pady=7, cursor="hand2",
            command=self._save_and_continue,
        ).pack(side="left", padx=6)

        tk.Button(
            btn_frame, text="Thoát",
            font=("Segoe UI", 10),
            bg=self.BTN, fg=self.FG,
            relief="flat", padx=18, pady=7, cursor="hand2",
            command=self.root.destroy,
        ).pack(side="left", padx=6)

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _auto_check(self):
        """Tự kiểm tra port ngay khi màn hình vừa mở."""
        self._check_port(silent=True)

    def _on_port_change(self):
        """Reset trạng thái khi user thay đổi port."""
        self._port_ok = False
        self._port_badge.config(text="", fg=self.OK)
        self._port_hint.config(text="")
        self._skip_btn.config(state="disabled")

    def _check_port(self, silent=False):
        try:
            port = int(self._port_entry.get())
            if not (1024 <= port <= 65535):
                raise ValueError
        except (ValueError, tk.TclError):
            self._set_port_status(ok=False, badge="✗ Port không hợp lệ",
                                  hint="Port phải là số nguyên từ 1024 đến 65535.")
            return

        if _port_free(port):
            self._set_port_status(ok=True, badge=f"✓ Port {port} sẵn sàng")
        else:
            self._set_port_status(
                ok=False,
                badge=f"✗ Port {port} đang bị chiếm",
                hint="Nhập port khác và bấm 'Kiểm tra port' lại.",
            )

    def _set_port_status(self, ok: bool, badge: str, hint: str = ""):
        self._port_ok = ok
        self._port_badge.config(text=badge, fg=self.OK if ok else self.ERR)
        self._port_hint.config(text=hint)
        # Skip chỉ khả dụng khi port OK
        self._skip_btn.config(state="normal" if ok else "disabled")

    def _browse(self):
        default = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")
        path = filedialog.askdirectory(
            title="Chọn thư mục Firefox profile",
            initialdir=default if os.path.isdir(default) else "/",
        )
        if path:
            self._profile_var.set(path)

    def _validate_profile(self) -> bool:
        profile = self._profile_var.get().strip()
        if not profile:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn Firefox profile.")
            return False
        if not os.path.isdir(profile):
            return messagebox.askyesno(
                "Cảnh báo",
                f"Thư mục không tồn tại:\n{profile}\n\nVẫn tiếp tục?",
            )
        return True

    def _skip(self):
        """Port OK, không cần lưu — dùng config hiện tại."""
        if not self._validate_profile():
            return
        # Vẫn lưu profile nếu user vừa đổi, nhưng giữ port cũ
        _save_cfg({
            "firefox_profile": self._profile_var.get().strip(),
            "flask_port":      self._port_var.get(),
        })
        import app_config
        app_config.reload()
        self.result = True
        self.root.destroy()

    def _save_and_continue(self):
        """Lưu port + profile mới rồi tiếp tục."""
        if not self._port_ok:
            messagebox.showwarning(
                "Port chưa kiểm tra",
                "Vui lòng bấm 'Kiểm tra port' để xác nhận port khả dụng.",
            )
            return
        if not self._validate_profile():
            return

        _save_cfg({
            "flask_port":      self._port_var.get(),
            "firefox_profile": self._profile_var.get().strip(),
        })
        import app_config
        app_config.reload()
        self.result = True
        self.root.destroy()

    # ── Run ───────────────────────────────────────────────────────────────────

    def show(self) -> bool:
        self.root.mainloop()
        return self.result


# ── Shortcut ──────────────────────────────────────────────────────────────────

def run_setup_screen() -> bool:
    """Gọi từ main — trả về True nếu OK để tiếp tục."""
    return SetupScreen().show()