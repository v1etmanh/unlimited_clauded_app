"""
tabs/tab_account.py — Tài khoản cá nhân
"""
import sys
import json
import tkinter as tk
from datetime import datetime, date
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).parent.parent))
from theme import C, lbl, btn, card, divider
from api_logger import get_stats

PROFILE_FILE = Path(__file__).parent.parent / "data" / "user_profile.json"


def _load_profile() -> dict:
    try:
        if PROFILE_FILE.exists():
            return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


class AccountTab(tk.Frame):
    def __init__(self, parent, license_info: dict, on_logout=None):
        super().__init__(parent, bg=C["base"])
        self.info       = license_info
        self.on_logout  = on_logout
        self.profile    = _load_profile()
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=C["mantle"], pady=20)
        hdr.pack(fill="x")
        lbl(hdr, "🧑‍💻  Tài khoản cá nhân", 15, bold=True, bg=C["mantle"]).pack()
        lbl(hdr, "Tổng quan tài khoản và quản lý phiên đăng nhập",
            9, color=C["subtext"], bg=C["mantle"]).pack(pady=4)

        # Scrollable canvas
        canvas = tk.Canvas(self, bg=C["base"], highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
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
        PAD = {"padx": 40}

        tk.Frame(p, bg=C["base"], height=24).pack()

        # ── User hero card ────────────────────────────────────────────────────
        hero = card(p)
        hero.pack(fill="x", **PAD, pady=(0, 16))
        hero_inner = tk.Frame(hero, bg=C["surface0"], padx=28, pady=24)
        hero_inner.pack(fill="x")

        # Avatar
        name    = self.profile.get("name") or self.info.get("email", "User")
        initials= "".join(w[0].upper() for w in name.split() if w)[:2] or "?"
        av_color= self.profile.get("avatar_color", C["blue"])

        av = tk.Canvas(hero_inner, width=64, height=64,
                       bg=C["surface0"], highlightthickness=0)
        av.pack(side="left")
        av.create_oval(2, 2, 62, 62, fill=av_color, outline="")
        av.create_text(32, 32, text=initials,
                       font=("Segoe UI", 18, "bold"), fill=C["crust"])

        info_col = tk.Frame(hero_inner, bg=C["surface0"], padx=20)
        info_col.pack(side="left", fill="y", pady=4)

        display_name = self.profile.get("name") or "Người dùng"
        lbl(info_col, display_name, 13, bold=True, bg=C["surface0"]).pack(anchor="w")
        lbl(info_col, self.info.get("email") or "—", 9,
            color=C["subtext"], bg=C["surface0"]).pack(anchor="w", pady=2)

        role = self.profile.get("role", "")
        if role:
            lbl(info_col, f"• {role}", 9,
                color=C["mauve"], bg=C["surface0"]).pack(anchor="w")

        # Status badge
        status_frame = tk.Frame(hero_inner, bg=C["surface0"])
        status_frame.pack(side="right", anchor="n")
        tk.Label(status_frame, text=" 🟢  Active ",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["green"], fg=C["crust"],
                 padx=8, pady=4).pack()

        # ── Usage stats ───────────────────────────────────────────────────────
        stats_title = tk.Frame(p, bg=C["base"])
        stats_title.pack(fill="x", **PAD, pady=(8, 6))
        lbl(stats_title, "📈  Thống kê sử dụng", 10, bold=True,
            color=C["blue"]).pack(side="left")

        stats = get_stats()
        stats_card = card(p)
        stats_card.pack(fill="x", **PAD, pady=(0, 16))
        stats_inner = tk.Frame(stats_card, bg=C["surface0"], padx=24, pady=20)
        stats_inner.pack(fill="x")

        stat_items = [
            ("Tổng API calls",   str(stats["total"]),             C["blue"]),
            ("Thành công",       f"{stats['success_rate']}%",     C["green"]),
            ("Avg latency",      f"{stats['avg_latency']} ms",    C["yellow"]),
            ("Tổng tokens",      f"{stats['total_tokens']:,}",    C["mauve"]),
        ]

        grid = tk.Frame(stats_inner, bg=C["surface0"])
        grid.pack(fill="x")

        for i, (label, val, color) in enumerate(stat_items):
            col_frame = tk.Frame(grid, bg=C["surface1"],
                                 padx=18, pady=14)
            col_frame.grid(row=0, column=i, padx=(0, 10), sticky="nsew")
            lbl(col_frame, val, 18, bold=True, color=color,
                bg=C["surface1"]).pack()
            lbl(col_frame, label, 8, color=C["subtext"],
                bg=C["surface1"]).pack(pady=2)
            grid.columnconfigure(i, weight=1)

        # ── Usage gauge ───────────────────────────────────────────────────────
        gauge_card = card(p)
        gauge_card.pack(fill="x", **PAD, pady=(0, 16))
        gauge_inner = tk.Frame(gauge_card, bg=C["surface0"], padx=24, pady=18)
        gauge_inner.pack(fill="x")

        total   = stats["total"]
        success = stats["success"]
        errors  = stats["error"]

        lbl(gauge_inner, "Phân bổ trạng thái calls", 9, bold=True,
            color=C["subtext"], bg=C["surface0"]).pack(anchor="w", pady=(0, 8))

        bar_canvas = tk.Canvas(gauge_inner, height=20,
                               bg=C["surface1"], highlightthickness=0)
        bar_canvas.pack(fill="x")

        def _draw_gauge(e=None):
            w = bar_canvas.winfo_width()
            bar_canvas.delete("all")
            bar_canvas.create_rectangle(0, 0, w, 20,
                                        fill=C["surface1"], outline="")
            if total > 0:
                ok_w = int(w * success / total)
                bar_canvas.create_rectangle(0, 0, ok_w, 20,
                                            fill=C["green"], outline="")
                if errors > 0:
                    err_w = int(w * errors / total)
                    bar_canvas.create_rectangle(ok_w, 0, ok_w + err_w, 20,
                                                fill=C["red"], outline="")

        bar_canvas.bind("<Configure>", _draw_gauge)

        legend = tk.Frame(gauge_inner, bg=C["surface0"])
        legend.pack(anchor="w", pady=4)
        for color, text in [(C["green"], f"✓ Thành công ({success})"),
                            (C["red"],   f"✗ Lỗi ({errors})")]:
            dot = tk.Label(legend, text="■", fg=color, bg=C["surface0"],
                           font=("Segoe UI", 10))
            dot.pack(side="left")
            lbl(legend, f" {text}   ", 8, color=C["subtext"],
                bg=C["surface0"]).pack(side="left")

        # ── License summary ───────────────────────────────────────────────────
        lic_title = tk.Frame(p, bg=C["base"])
        lic_title.pack(fill="x", **PAD, pady=(8, 6))
        lbl(lic_title, "🔑  License", 10, bold=True, color=C["blue"]).pack(side="left")

        lic_card = card(p)
        lic_card.pack(fill="x", **PAD, pady=(0, 16))
        lic_inner = tk.Frame(lic_card, bg=C["surface0"], padx=24, pady=18)
        lic_inner.pack(fill="x")

        days_left = self._days_left()
        exp_color = C["red"] if days_left <= 7 else (
                    C["yellow"] if days_left <= 30 else C["green"])

        rows = [
            ("Ngày hết hạn",  self.info.get("expires") or "—"),
            ("Còn lại",       f"{days_left} ngày"),
            ("Trạng thái",    "Đang hoạt động  🟢"),
        ]

        for i, (label, val) in enumerate(rows):
            row = tk.Frame(lic_inner, bg=C["surface0"])
            row.pack(fill="x", pady=5)
            lbl(row, label, 9, color=C["subtext"], bg=C["surface0"]).pack(side="left")
            color = exp_color if "ngày" in val else C["text"]
            lbl(row, val, 9, color=color, bg=C["surface0"]).pack(side="right")
            if i < len(rows) - 1:
                divider(lic_inner).pack(fill="x", pady=2)

        # ── Danger zone ───────────────────────────────────────────────────────
        danger_title = tk.Frame(p, bg=C["base"])
        danger_title.pack(fill="x", **PAD, pady=(8, 6))
        lbl(danger_title, "⚠️  Phiên đăng nhập", 10, bold=True,
            color=C["red"]).pack(side="left")

        danger_card = card(p)
        danger_card.pack(fill="x", **PAD, pady=(0, 40))
        danger_inner = tk.Frame(danger_card, bg=C["surface0"], padx=24, pady=18)
        danger_inner.pack(fill="x")

        lbl(danger_inner,
            "Đăng xuất sẽ xoá cache license. Bạn cần nhập lại key lần sau.",
            9, color=C["subtext"], bg=C["surface0"]).pack(anchor="w", pady=(0, 12))

        btn_row = tk.Frame(danger_inner, bg=C["surface0"])
        btn_row.pack(anchor="w")

        btn(btn_row, "🚪  Đăng xuất",
            self._logout,
            color=C["red"], fg=C["crust"], width=14).pack(side="left")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _days_left(self) -> int:
        try:
            exp = datetime.strptime(
                self.info.get("expires", ""), "%Y-%m-%d").date()
            return max(0, (exp - date.today()).days)
        except Exception:
            return 0

    def _logout(self):
        if messagebox.askyesno(
            "Đăng xuất",
            "Bạn có chắc muốn đăng xuất?\n"
            "Cache license sẽ bị xoá — cần nhập lại key lần sau.",
            icon="warning",
        ):
            # Xoá cache license
            from pathlib import Path
            cache = Path.home() / ".claude_browser_license"
            if cache.exists():
                cache.unlink()

            if self.on_logout:
                self.on_logout()
