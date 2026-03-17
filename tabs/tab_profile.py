"""
tabs/tab_profile.py — Tab thiết lập hồ sơ cá nhân
"""
import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from theme import C, lbl, entry, btn, card, divider, section_header

PROFILE_FILE = Path(__file__).parent.parent / "data" / "user_profile.json"
ROLES = ["Developer", "Business", "Student", "Researcher", "Personal", "Other"]
AVATAR_COLORS = [
    C["blue"], C["mauve"], C["green"], C["peach"],
    C["teal"], C["red"], C["yellow"], C["sky"],
]


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


class ProfileTab(tk.Frame):
    def __init__(self, parent, license_info: dict):
        super().__init__(parent, bg=C["base"])
        self.license_info = license_info
        self.profile      = _load_profile()
        self._avatar_color = self.profile.get("avatar_color", C["blue"])
        self._build()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        # Scrollable canvas
        canvas = tk.Canvas(self, bg=C["base"], highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview,
                          bg=C["surface1"], troughcolor=C["surface0"])
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        container = tk.Frame(canvas, bg=C["base"])
        win_id = canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        def _on_frame(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _on_resize)
        container.bind("<Configure>", _on_frame)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._build_content(container)

    def _build_content(self, p):
        pad = {"padx": 40}   # ← bỏ pady khỏi dict

        # ── Page title ────────────────────────────────────────────────────────
        hdr = tk.Frame(p, bg=C["mantle"], pady=24)
        hdr.pack(fill="x")
        lbl(hdr, "👤  Thiết lập hồ sơ", 15, bold=True, bg=C["mantle"]).pack()
        lbl(hdr, "Quản lý thông tin cá nhân của bạn", 9,
            color=C["subtext"], bg=C["mantle"]).pack(pady=4)

        # ── Avatar section ────────────────────────────────────────────────────
        tk.Frame(p, bg=C["base"], height=24).pack()
        av_card = card(p)
        av_card.pack(fill="x", **pad, pady=(0, 12))

        inner = tk.Frame(av_card, bg=C["surface0"], padx=24, pady=20)
        inner.pack(fill="x")

        # Avatar circle (canvas)
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
                            bg=C["surface0"], highlightthickness=0,
                            cursor="hand2")
            dot.pack(side="left", padx=3)
            dot.create_oval(2, 2, 22, 22, fill=color, outline="")
            dot.bind("<Button-1>", lambda e, c=color: self._set_avatar_color(c))

        # ── Form fields ───────────────────────────────────────────────────────
        form_card = card(p)
        form_card.pack(fill="x", **pad, pady=8)

        form_inner = tk.Frame(form_card, bg=C["surface0"], padx=24, pady=20)
        form_inner.pack(fill="x")

        lbl(form_inner, "Thông tin cơ bản", 10, bold=True,
            color=C["blue"], bg=C["surface0"]).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        fields = [
            ("Họ và tên",       "name",    False, ""),
            ("Email",           "email",   True,  self.license_info.get("email", "")),
            ("Số điện thoại",   "phone",   False, ""),
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
                    row=i*2, column=0, columnspan=2,
                    sticky="ew", pady=(6, 0))

        form_inner.columnconfigure(1, weight=1)

        # ── Role dropdown ─────────────────────────────────────────────────────
        role_card = card(p)
        role_card.pack(fill="x", **pad, pady=8)

        role_inner = tk.Frame(role_card, bg=C["surface0"], padx=24, pady=20)
        role_inner.pack(fill="x")

        lbl(role_inner, "Vai trò", 9, color=C["subtext"],
            bg=C["surface0"]).pack(anchor="w")

        self._role_var = tk.StringVar(
            value=self.profile.get("role", ROLES[0]))
        role_frame = tk.Frame(role_inner, bg=C["surface0"])
        role_frame.pack(anchor="w", pady=8)

        for role in ROLES:
            rb = tk.Radiobutton(
                role_frame, text=role,
                variable=self._role_var, value=role,
                font=("Segoe UI", 9),
                bg=C["surface0"], fg=C["text"],
                selectcolor=C["surface1"],
                activebackground=C["surface0"],
                activeforeground=C["blue"],
                cursor="hand2",
            )
            rb.pack(side="left", padx=(0, 16))

        # ── Save button ───────────────────────────────────────────────────────
        btn_row = tk.Frame(p, bg=C["base"])
        btn_row.pack(fill="x", **pad, pady=20)

        btn(btn_row, "💾  Lưu hồ sơ", self._save, width=16).pack(side="right")
        btn(btn_row, "↺  Đặt lại",
            self._reset, color=C["surface1"], fg=C["text"], width=12).pack(
            side="right", padx=(0, 10))

    # ── Actions ───────────────────────────────────────────────────────────────

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
        data = {k: v.get().strip() for k, v in self._vars.items()}
        data["role"]         = self._role_var.get()
        data["avatar_color"] = self._avatar_color
        _save_profile(data)
        self._draw_avatar()
        messagebox.showinfo("Đã lưu", "✅ Hồ sơ đã được cập nhật!")

    def _reset(self):
        if messagebox.askyesno("Đặt lại", "Xoá toàn bộ thông tin đã nhập?"):
            for k, v in self._vars.items():
                if k == "email":
                    continue
                v.set("")
            self._role_var.set(ROLES[0])
