# loading_screen.py
"""
Loading screen với spinner — hiện trong khi init_client() chạy background.
Dùng:
    ok = run_with_loading(init_client, title="Đang kết nối Claude...")
"""
import tkinter as tk
import threading


class LoadingScreen:
    BG  = "#1e1e2e"
    FG  = "#cdd6f4"
    SUB = "#a6adc8"
    ACC = "#89b4fa"

    DOTS = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]  # braille spinner

    def __init__(self, title: str, message: str):
        self.root = tk.Tk()
        self.root.title("Đang khởi động")
        self.root.geometry("380x180")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)  # chặn đóng tay
        self._center()

        self._dot_idx = 0
        self._done    = False

        self._build(title, message)

    def _center(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - 380) // 2
        y = (self.root.winfo_screenheight() - 180) // 2
        self.root.geometry(f"380x180+{x}+{y}")

    def _build(self, title: str, message: str):
        tk.Label(self.root, text=title,
                 font=("Segoe UI", 13, "bold"),
                 bg=self.BG, fg=self.FG).pack(pady=(32, 6))

        tk.Label(self.root, text=message,
                 font=("Segoe UI", 9),
                 bg=self.BG, fg=self.SUB).pack()

        # Spinner + status trên cùng 1 hàng
        row = tk.Frame(self.root, bg=self.BG)
        row.pack(pady=18)

        self._spinner_lbl = tk.Label(
            row, text=self.DOTS[0],
            font=("Consolas", 18),
            bg=self.BG, fg=self.ACC,
        )
        self._spinner_lbl.pack(side="left", padx=(0, 10))

        self._status_lbl = tk.Label(
            row, text="Đang khởi tạo...",
            font=("Segoe UI", 9),
            bg=self.BG, fg=self.SUB,
        )
        self._status_lbl.pack(side="left")

    def _animate(self):
        if self._done:
            return
        self._dot_idx = (self._dot_idx + 1) % len(self.DOTS)
        self._spinner_lbl.config(text=self.DOTS[self._dot_idx])
        self.root.after(80, self._animate)

    def set_status(self, text: str):
        """Cập nhật dòng trạng thái từ bất kỳ thread nào."""
        self.root.after(0, lambda: self._status_lbl.config(text=text))

    def close(self):
        self._done = True
        self.root.after(0, self.root.destroy)

    def run(self):
        self._animate()
        self.root.mainloop()


# ── Public helper ─────────────────────────────────────────────────────────────

def run_with_loading(
    fn,
    title:   str = "Đang khởi động",
    message: str = "Vui lòng chờ...",
    status:  str = "Đang khởi tạo...",
) -> bool:
    """
    Chạy fn() trong background thread, hiện loading spinner.
    Trả về kết quả bool của fn().
    """
    result = [False]
    screen = LoadingScreen(title=title, message=message)
    screen.set_status(status)

    def worker():
        result[0] = fn()
        screen.close()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    screen.run()   # block cho đến khi close() được gọi
    return result[0]