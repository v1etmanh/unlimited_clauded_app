"""
app.py  —  App chính tích hợp License Gate
-------------------------------------------
Khi khởi động:
  1. Thử load license từ cache → nếu OK, chạy luôn
  2. Nếu không có cache → hiện dialog nhập key
  3. Key hợp lệ → chạy Flask server
  4. Key sai → thoát
"""
import app_config
from app_config import FIREFOX_PROFILE
import logging
import sys
import tkinter as tk
from app import app, init_client   # ← lấy Flask app + init_client từ app.py
from tkinter import messagebox

# Import license validator
from license_validator import license_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── License Gate UI ───────────────────────────────────────────────────────────

class LicenseDialog:
    """Dialog nhập license key — hiện trước khi app chạy"""

    def __init__(self):
        self.result = False
        self.root   = tk.Tk()
        self.root.title("Kích hoạt phần mềm")
        self.root.geometry("480x260")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")
        self._center_window()
        self._build_ui()

    def _center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  // 2) - (480 // 2)
        y = (self.root.winfo_screenheight() // 2) - (260 // 2)
        self.root.geometry(f"480x260+{x}+{y}")

    def _build_ui(self):
        bg  = "#1e1e2e"
        fg  = "#cdd6f4"
        btn = "#89b4fa"
        inp = "#313244"

        tk.Label(
            self.root, text="🔐 Claude via Browser",
            font=("Segoe UI", 16, "bold"),
            bg=bg, fg=fg,
        ).pack(pady=(30, 4))

        tk.Label(
            self.root, text="Nhập license key để sử dụng phần mềm",
            font=("Segoe UI", 10),
            bg=bg, fg="#a6adc8",
        ).pack(pady=(0, 20))

        frame = tk.Frame(self.root, bg=bg)
        frame.pack(padx=40, fill="x")

        self.key_var = tk.StringVar()
        self.entry = tk.Entry(
            frame,
            textvariable=self.key_var,
            font=("Consolas", 12),
            bg=inp, fg=fg,
            insertbackground=fg,
            relief="flat",
            bd=6,
        )
        self.entry.pack(fill="x", ipady=6)
        self.entry.insert(0, "XXXXX-XXXXX-XXXXX-XXXXX-CCCC")
        self.entry.bind("<FocusIn>",  lambda e: self._clear_placeholder())
        self.entry.bind("<Return>",   lambda e: self._submit())

        self.status_var = tk.StringVar(value="")
        self.status_lbl = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            bg=bg, fg="#f38ba8",
        )
        self.status_lbl.pack(pady=8)

        btn_frame = tk.Frame(self.root, bg=bg)
        btn_frame.pack()

        tk.Button(
            btn_frame, text="Kích hoạt",
            font=("Segoe UI", 10, "bold"),
            bg=btn, fg="#1e1e2e",
            relief="flat", bd=0, padx=20, pady=6,
            cursor="hand2",
            command=self._submit,
        ).pack(side="left", padx=6)

        tk.Button(
            btn_frame, text="Thoát",
            font=("Segoe UI", 10),
            bg="#45475a", fg=fg,
            relief="flat", bd=0, padx=20, pady=6,
            cursor="hand2",
            command=self._exit,
        ).pack(side="left", padx=6)

    def _clear_placeholder(self):
        if self.key_var.get() == "XXXXX-XXXXX-XXXXX-XXXXX-CCCC":
            self.entry.delete(0, "end")

    def _submit(self):
        key = self.key_var.get().strip()
        if not key or key == "XXXXX-XXXXX-XXXXX-XXXXX-CCCC":
            self.status_var.set("⚠️  Vui lòng nhập license key")
            return

        self.status_var.set("⏳ Đang xác thực...")
        self.root.update()

        valid, msg = license_manager.activate(key)

        if valid:
            self.result = True
            messagebox.showinfo("Thành công", msg)
            self.root.destroy()
        else:
            self.status_var.set(msg)

    def _exit(self):
        self.result = False
        self.root.destroy()

    def show(self) -> bool:
        self.root.mainloop()
        return self.result


# ── License Gate ──────────────────────────────────────────────────────────────

def check_license() -> bool:
    """
    Kiểm tra license trước khi chạy app.
    Returns True nếu hợp lệ, False nếu không.
    """
    if license_manager.load_from_cache():
        info = license_manager.info()
        logger.info(
            "License OK từ cache  email=%s  expires=%s",
            info["email"], info["expires"],
        )
        return True

    logger.info("Chưa có license, hiện dialog kích hoạt…")
    dialog = LicenseDialog()
    return dialog.show()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import app_config
    app_config.ensure_defaults_saved()

    from setup_screen import run_setup_screen
    if not run_setup_screen():
        sys.exit(0)

    # ── Bước 1: Kiểm tra license ─────────────────────────────
    if not check_license():
        logger.critical("License không hợp lệ. Thoát.")
        sys.exit(1)

    logger.info("License hợp lệ ✓ — Khởi động server…")

    # ── Bước 2: Init Claude client — truyền model đã chọn ────
    # app_config.reload() đã được gọi bên trong setup_screen,
    # nên app_config.MODEL lúc này đã phản ánh lựa chọn của user.
    from loading_screen import run_with_loading
    if not run_with_loading(
        lambda: init_client(),   # ← truyền model
        title   = "Đang kết nối Claude",
        message = f"Model: {app_config.MODEL}",
        status  = "Mở Firefox profile...",
    ):
        logger.critical("Claude client lỗi.")
        messagebox.showerror(
            "Lỗi khởi động",
            "Không thể kết nối Claude.\nKiểm tra Firefox profile và thử lại.",
        )
        sys.exit(1)

    # ── Bước 3: Chạy Flask trong background thread ───────────
    import threading
    flask_thread = threading.Thread(
        target=lambda: app.run(
            host="0.0.0.0",
            port=app_config.FLASK_PORT,
            debug=False,
            threaded=True,
        ),
        daemon=True,
    )
    flask_thread.start()

    # ── Bước 4: Mở Dashboard ──────────────────────────────────
    from dashboard import Dashboard
    Dashboard(
        license_info=license_manager.info(),
        on_logout=lambda: sys.exit(0),
    ).run()