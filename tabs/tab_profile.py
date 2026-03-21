"""
tabs/tab_profile.py — Tab thiết lập hồ sơ cá nhân
"""
import json
import socket
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from theme import C, lbl, entry, btn, card, divider, section_header

PROFILE_FILE = Path(__file__).parent.parent / "data" / "user_profile.json"
ROLES = ["Developer", "Business", "Student", "Researcher", "Personal", "Other"]
AVATAR_COLORS = [
    C["blue"], C["mauve"], C["green"], C["peach"],
    C["teal"], C["red"], C["yellow"], C["sky"],
]

DEFAULTS = {
    "firefox_profile":      "",
    "flask_port":           5000,
    "client_timeout":       240,
    "max_history_messages": 10,
    "max_retries":          2,
}


def _load_profile() -> dict:
    try:
        if PROFILE_FILE.exists():
            return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_profile(data: dict):
    PROFILE_FILE.parent.mkdir(exist_ok=True)
    PROFILE_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _is_port_available(port: int) -> bool:
    """Kiểm tra port có đang bị dùng không"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


class ProfileTab(tk.Frame):
    def __init__(self, parent, license_info: dict):
        super().__init__(parent, bg=C["base"])
        self.license_info  = license_info
        self.profile       = _load_profile()
        self._avatar_color = self.profile.get("avatar_color", C["blue"])
        self._build()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        canvas = tk.Canvas(self, bg=C["base"], highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview,
                          bg=C["surface1"], troughcolor=C["surface0"])
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        container = tk.Frame(canvas, bg=C["base"])
        win_id = canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_resize(e): canvas.itemconfig(win_id, width=e.width)
        def _on_frame(e):  canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _on_resize)
        container.bind("<Configure>", _on_frame)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        self._build_content(container)

    def _build_content(self, p):
        pad = {"padx": 40}

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(p, bg=C["mantle"], pady=24)
        hdr.pack(fill="x")
        lbl(hdr, "👤  Thiết lập hồ sơ", 15, bold=True, bg=C["mantle"]).pack()
        lbl(hdr, "Quản lý thông tin cá nhân và cấu hình kết nối", 9,
            color=C["subtext"], bg=C["mantle"]).pack(pady=4)

        tk.Frame(p, bg=C["base"], height=24).pack()

        # ── Avatar ────────────────────────────────────────────────────────────
        av_card = card(p)
        av_card.pack(fill="x", **pad, pady=(0, 12))
        inner = tk.Frame(av_card, bg=C["surface0"], padx=24, pady=20)
        inner.pack(fill="x")

        av_canvas = tk.Canvas(inner, width=80, height=80,
                              bg=C["surface0"], highlightthickness=0)
        av_canvas.pack(side="left")
        self._av_canvas = av_canvas
        self._draw_avatar()

        av_right = tk.Frame(inner, bg=C["surface0"], padx=16)
        av_right.pack(side="left", fill="y", pady=4)
        lbl(av_right, "Màu avatar", 9, bold=True,
            color=C["subtext"], bg=C["surface0"]).pack(anchor="w")

        colors_row = tk.Frame(av_right, bg=C["surface0"])
        colors_row.pack(anchor="w", pady=6)
        for color in AVATAR_COLORS:
            dot = tk.Canvas(colors_row, width=24, height=24,
                            bg=C["surface0"], highlightthickness=0, cursor="hand2")
            dot.pack(side="left", padx=3)
            dot.create_oval(2, 2, 22, 22, fill=color, outline="")
            dot.bind("<Button-1>", lambda e, c=color: self._set_avatar_color(c))

        # ── Thông tin cơ bản ──────────────────────────────────────────────────
        form_card = card(p)
        form_card.pack(fill="x", **pad, pady=8)
        form_inner = tk.Frame(form_card, bg=C["surface0"], padx=24, pady=20)
        form_inner.pack(fill="x")

        lbl(form_inner, "Thông tin cơ bản", 10, bold=True,
            color=C["blue"], bg=C["surface0"]).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        fields = [
            ("Họ và tên",        "name",    False, ""),
            ("Email",            "email",   True,  self.license_info.get("email", "")),
            ("Số điện thoại",    "phone",   False, ""),
            ("Công ty / Tổ chức","company", False, ""),
        ]

        self._vars = {}
        for i, (label, key, readonly, default) in enumerate(fields, start=1):
            lbl(form_inner, label, 9, color=C["subtext"],
                bg=C["surface0"]).grid(
                row=i*2-1, column=0, sticky="w", pady=(10, 2), padx=(0, 30))
            val = self.profile.get(key, default)
            var = tk.StringVar(value=val)
            self._vars[key] = var
            e = entry(form_inner, textvariable=var, width=34, readonly=readonly)
            e.grid(row=i*2-1, column=1, sticky="ew", pady=(10, 2))
            if i < len(fields):
                divider(form_inner, C["surface1"]).grid(
                    row=i*2, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        form_inner.columnconfigure(1, weight=1)

        # ── Vai trò ───────────────────────────────────────────────────────────
        role_card = card(p)
        role_card.pack(fill="x", **pad, pady=8)
        role_inner = tk.Frame(role_card, bg=C["surface0"], padx=24, pady=20)
        role_inner.pack(fill="x")

        lbl(role_inner, "Vai trò", 9, color=C["subtext"],
            bg=C["surface0"]).pack(anchor="w")
        self._role_var = tk.StringVar(value=self.profile.get("role", ROLES[0]))
        role_frame = tk.Frame(role_inner, bg=C["surface0"])
        role_frame.pack(anchor="w", pady=8)

        for role in ROLES:
            tk.Radiobutton(
                role_frame, text=role,
                variable=self._role_var, value=role,
                font=("Segoe UI", 9),
                bg=C["surface0"], fg=C["text"],
                selectcolor=C["surface1"],
                activebackground=C["surface0"],
                activeforeground=C["blue"],
                cursor="hand2",
            ).pack(side="left", padx=(0, 16))

        # ── Cài đặt kết nối ───────────────────────────────────────────────────
        conn_card = card(p)
        conn_card.pack(fill="x", **pad, pady=8)
        conn_inner = tk.Frame(conn_card, bg=C["surface0"], padx=24, pady=20)
        conn_inner.pack(fill="x")

        lbl(conn_inner, "🔌  Cài đặt kết nối", 10, bold=True,
            color=C["blue"], bg=C["surface0"]).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))

        # Firefox Profile
        lbl(conn_inner, "Firefox Profile", 9, color=C["subtext"],
            bg=C["surface0"]).grid(row=1, column=0, sticky="w", padx=(0, 20), pady=6)

        self._firefox_var = tk.StringVar(
            value=self.profile.get("firefox_profile", ""))
        firefox_entry = tk.Entry(
            conn_inner, textvariable=self._firefox_var,
            font=("Consolas", 9),
            bg=C["surface1"], fg=C["text"],
            insertbackground=C["text"],
            relief="flat", bd=6,
        )
        firefox_entry.grid(row=1, column=1, sticky="ew", pady=6)

        # Firefox status indicator
        self._firefox_status = lbl(conn_inner, "", 8, color=C["green"],
                                   bg=C["surface0"])
        self._firefox_status.grid(row=1, column=2, sticky="w", padx=(8, 0))

        btn(conn_inner, "📁", self._browse_firefox,
            color=C["surface1"], fg=C["text"], width=3).grid(
            row=1, column=3, padx=(6, 0), pady=6)

        self._firefox_var.trace_add("write", lambda *a: self._validate_firefox())

        divider(conn_inner, C["surface1"]).grid(
            row=2, column=0, columnspan=4, sticky="ew", pady=4)

        # Flask Port
        lbl(conn_inner, "Flask Port", 9, color=C["subtext"],
            bg=C["surface0"]).grid(row=3, column=0, sticky="w", padx=(0, 20), pady=6)

        port_frame = tk.Frame(conn_inner, bg=C["surface0"])
        port_frame.grid(row=3, column=1, sticky="w", pady=6)

        self._port_var = tk.StringVar(
            value=str(self.profile.get("flask_port", DEFAULTS["flask_port"])))
        tk.Spinbox(
            port_frame,
            textvariable=self._port_var,
            from_=1024, to=65535, increment=1,
            font=("Segoe UI", 9), width=8,
            bg=C["surface1"], fg=C["text"],
            buttonbackground=C["surface0"],
            relief="flat",
        ).pack(side="left")

        self._port_status = lbl(port_frame, "", 8, color=C["green"],
                                bg=C["surface0"])
        self._port_status.pack(side="left", padx=(8, 0))

        btn(conn_inner, "Kiểm tra", self._check_port,
            color=C["surface1"], fg=C["text"], width=8).grid(
            row=3, column=2, columnspan=2, padx=(8, 0), pady=6, sticky="w")

        divider(conn_inner, C["surface1"]).grid(
            row=4, column=0, columnspan=4, sticky="ew", pady=4)

        # Spinbox settings
        spin_fields = [
            ("Client Timeout (giây)", "client_timeout",       DEFAULTS["client_timeout"],       30,  600, 5,  "row5"),
            ("Max History Messages",  "max_history_messages", DEFAULTS["max_history_messages"],  1,   50,  1,  "row6"),
            ("Max Retries",           "max_retries",          DEFAULTS["max_retries"],           0,   10,  1,  "row7"),
        ]

        self._spin_vars = {}
        for i, (label, key, default, mn, mx, inc, _) in enumerate(spin_fields):
            row = 5 + i * 2
            lbl(conn_inner, label, 9, color=C["subtext"],
                bg=C["surface0"]).grid(row=row, column=0, sticky="w",
                                       padx=(0, 20), pady=6)
            var = tk.StringVar(value=str(self.profile.get(key, default)))
            self._spin_vars[key] = var
            tk.Spinbox(
                conn_inner,
                textvariable=var,
                from_=mn, to=mx, increment=inc,
                font=("Segoe UI", 9), width=8,
                bg=C["surface1"], fg=C["text"],
                buttonbackground=C["surface0"],
                relief="flat",
            ).grid(row=row, column=1, sticky="w", pady=6)

            hint = {
                "client_timeout":       "giây — timeout khi Claude không trả lời",
                "max_history_messages": "messages cuối giữ lại trước khi gửi",
                "max_retries":          "lần retry khi chat_id bị stale",
            }.get(key, "")
            lbl(conn_inner, hint, 8, color=C["overlay"],
                bg=C["surface0"]).grid(row=row, column=2, columnspan=2,
                                       sticky="w", padx=(8, 0))

            if i < len(spin_fields) - 1:
                divider(conn_inner, C["surface1"]).grid(
                    row=row+1, column=0, columnspan=4, sticky="ew", pady=2)

        conn_inner.columnconfigure(1, weight=1)

        # ── Refresh Client ────────────────────────────────────────────────────
        refresh_card = card(p)
        refresh_card.pack(fill="x", **pad, pady=8)
        refresh_inner = tk.Frame(refresh_card, bg=C["surface0"], padx=24, pady=20)
        refresh_inner.pack(fill="x")

        lbl(refresh_inner, "🔄  Kết nối Claude", 10, bold=True,
            color=C["blue"], bg=C["surface0"]).pack(anchor="w", pady=(0, 10))

        status_row = tk.Frame(refresh_inner, bg=C["surface0"])
        status_row.pack(fill="x", pady=(0, 10))

        lbl(status_row, "Trạng thái:", 9, color=C["subtext"],
            bg=C["surface0"]).pack(side="left")
        self._conn_status_var = tk.StringVar(value="—")
        self._conn_status_lbl = tk.Label(
            status_row,
            textvariable=self._conn_status_var,
            font=("Segoe UI", 9),
            bg=C["surface0"], fg=C["overlay"],
        )
        self._conn_status_lbl.pack(side="left", padx=(8, 0))

        self._refresh_btn = btn(
            refresh_inner, "🔄  Refresh Client",
            self._do_refresh_client, width=20,
        )
        self._refresh_btn.pack(anchor="w")

        # ── Save / Reset buttons ──────────────────────────────────────────────
        btn_row = tk.Frame(p, bg=C["base"])
        btn_row.pack(fill="x", **pad, pady=20)

        btn(btn_row, "💾  Lưu hồ sơ", self._save, width=16).pack(side="right")
        btn(btn_row, "↺  Đặt lại",
            self._reset, color=C["surface1"], fg=C["text"], width=12).pack(
            side="right", padx=(0, 10))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _browse_firefox(self):
        path = filedialog.askdirectory(title="Chọn thư mục Firefox Profile")
        if path:
            self._firefox_var.set(path)

    def _validate_firefox(self):
        path = self._firefox_var.get().strip()
        if not path:
            self._firefox_status.config(text="", fg=C["overlay"])
        elif Path(path).exists():
            self._firefox_status.config(text="✅ Hợp lệ", fg=C["green"])
        else:
            self._firefox_status.config(text="❌ Không tìm thấy", fg=C["red"])

    def _check_port(self):
        try:
            port = int(self._port_var.get())
            if not (1024 <= port <= 65535):
                self._port_status.config(text="⚠️ Ngoài range", fg=C["yellow"])
                return
            if _is_port_available(port):
                self._port_status.config(text=f"✅ Port {port} trống", fg=C["green"])
            else:
                self._port_status.config(text=f"❌ Port {port} đang bị dùng", fg=C["red"])
        except ValueError:
            self._port_status.config(text="⚠️ Không hợp lệ", fg=C["yellow"])

    def _draw_avatar(self):
        c = self._av_canvas
        c.delete("all")
        c.create_oval(4, 4, 76, 76, fill=self._avatar_color, outline="")
        name = self._vars["name"].get() if hasattr(self, "_vars") else \
               self.profile.get("name", "")
        initials = "".join(w[0].upper() for w in name.split() if w)[:2] or "?"
        c.create_text(40, 40, text=initials,
                      font=("Segoe UI", 22, "bold"), fill=C["crust"])

    def _set_avatar_color(self, color: str):
        self._avatar_color = color
        self._draw_avatar()

    def _save(self):
        # Validate firefox profile
        firefox = self._firefox_var.get().strip()
        if firefox and not Path(firefox).exists():
            if not messagebox.askyesno(
                "Cảnh báo",
                "Đường dẫn Firefox Profile không tồn tại.\nVẫn lưu?",
                icon="warning",
            ):
                return

        # Validate port
        try:
            port = int(self._port_var.get())
            assert 1024 <= port <= 65535
        except (ValueError, AssertionError):
            messagebox.showerror("Lỗi", "Flask Port không hợp lệ (1024–65535)")
            return

        # Collect all data
        data = {k: v.get().strip() for k, v in self._vars.items()}
        data["role"]         = self._role_var.get()
        data["avatar_color"] = self._avatar_color

        # Connection settings
        data["firefox_profile"]      = firefox
        data["flask_port"]           = port
        data["client_timeout"]       = int(self._spin_vars["client_timeout"].get())
        data["max_history_messages"] = int(self._spin_vars["max_history_messages"].get())
        data["max_retries"]          = int(self._spin_vars["max_retries"].get())

        _save_profile(data)

        # Reload global config nếu app_config tồn tại
        try:
            import app_config
            app_config.reload()
        except ImportError:
            pass

        self._draw_avatar()
        messagebox.showinfo(
            "Đã lưu",
            "✅ Cài đặt đã được lưu!\n\n"
            "⚠️ Firefox Profile và Flask Port\n"
            "có hiệu lực lần khởi động tiếp theo."
        )

    def _do_refresh_client(self):
        import threading
        try:
            from app import init_client
        except ImportError:
            self._conn_status_var.set("❌ Không thể import init_client")
            self._conn_status_lbl.config(fg=C["red"])
            return

        self._refresh_btn.config(state="disabled")
        self._conn_status_var.set("⏳ Đang kết nối lại...")
        self._conn_status_lbl.config(fg=C["yellow"])
        self.update_idletasks()

        def _run():
            ok = init_client()
            def _update():
                if ok:
                    self._conn_status_var.set("✅ Kết nối thành công")
                    self._conn_status_lbl.config(fg=C["green"])
                else:
                    self._conn_status_var.set("❌ Kết nối thất bại")
                    self._conn_status_lbl.config(fg=C["red"])
                self._refresh_btn.config(state="normal")
            self.after(0, _update)

        threading.Thread(target=_run, daemon=True).start()

    def _reset(self):
        if messagebox.askyesno("Đặt lại", "Xoá toàn bộ thông tin đã nhập?"):
            for k, v in self._vars.items():
                if k == "email":
                    continue
                v.set("")
            self._role_var.set(ROLES[0])
            self._firefox_var.set("")
            self._port_var.set(str(DEFAULTS["flask_port"]))
            for key, var in self._spin_vars.items():
                var.set(str(DEFAULTS[key]))
            self._port_status.config(text="")
            self._firefox_status.config(text="")