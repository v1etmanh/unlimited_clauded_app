"""
tabs/tab_license.py — Thời gian license còn lại (live countdown)
"""
import sys
import tkinter as tk
import threading
import time
import webbrowser
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from theme import C, lbl, btn, card, divider

RENEW_URL = "https://your-site.com/renew"   # ← thay URL gia hạn thật của bạn
WARN_DAYS = 7


class LicenseTab(tk.Frame):
    def __init__(self, parent, license_info: dict):
        super().__init__(parent, bg=C["base"])
        self.info      = license_info
        self._running  = True
        self._build()
        self._start_clock()

    # ── Countdown logic ───────────────────────────────────────────────────────

    def _days_left(self) -> int:
        try:
            exp = datetime.strptime(self.info.get("expires", ""), "%Y-%m-%d").date()
            return max(0, (exp - date.today()).days)
        except Exception:
            return 0

    def _time_breakdown(self) -> tuple[int, int, int, int]:
        """Trả về (days, hours, mins, secs) còn lại"""
        try:
            exp  = datetime.strptime(self.info.get("expires", ""), "%Y-%m-%d")
            diff = exp - datetime.now()
            if diff.total_seconds() <= 0:
                return 0, 0, 0, 0
            total   = int(diff.total_seconds())
            days    = total // 86400
            hours   = (total % 86400) // 3600
            mins    = (total % 3600) // 60
            secs    = total % 60
            return days, hours, mins, secs
        except Exception:
            return 0, 0, 0, 0

    def _total_days(self) -> int:
        """Ước tính tổng số ngày license (365 nếu không biết activated_at)"""
        return 365

    def _progress_pct(self) -> float:
        left  = self._days_left()
        total = self._total_days()
        if total == 0:
            return 0
        used = total - left
        return max(0, min(1, used / total))

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=C["mantle"], pady=20)
        hdr.pack(fill="x")
        lbl(hdr, "⏳  Thời gian License", 15, bold=True, bg=C["mantle"]).pack()
        lbl(hdr, "Theo dõi hạn sử dụng của bạn",
            9, color=C["subtext"], bg=C["mantle"]).pack(pady=4)

        # Center container
        center = tk.Frame(self, bg=C["base"])
        center.pack(fill="both", expand=True, padx=60, pady=30)

        # ── Countdown display card ────────────────────────────────────────────
        count_card = card(center)
        count_card.pack(fill="x", pady=(0, 20))

        count_inner = tk.Frame(count_card, bg=C["surface0"], padx=30, pady=30)
        count_inner.pack(fill="x")

        lbl(count_inner, "Còn lại", 10, color=C["subtext"],
            bg=C["surface0"]).pack()

        # 4 flip-style blocks: DD HH MM SS
        blocks_frame = tk.Frame(count_inner, bg=C["surface0"])
        blocks_frame.pack(pady=16)

        self._unit_labels = {}
        units = [("days", "Ngày"), ("hours", "Giờ"), ("mins", "Phút"), ("secs", "Giây")]

        for i, (key, label) in enumerate(units):
            block = tk.Frame(blocks_frame, bg=C["surface1"],
                             padx=20, pady=12)
            block.pack(side="left", padx=8)

            val_lbl = tk.Label(
                block, text="00",
                font=("Consolas", 36, "bold"),
                bg=C["surface1"], fg=C["blue"],
            )
            val_lbl.pack()
            tk.Label(
                block, text=label,
                font=("Segoe UI", 8),
                bg=C["surface1"], fg=C["subtext"],
            ).pack()

            self._unit_labels[key] = val_lbl

            if i < 3:
                tk.Label(blocks_frame, text=":",
                         font=("Consolas", 28, "bold"),
                         bg=C["surface0"], fg=C["overlay"]).pack(side="left", padx=2)

        # Progress bar
        prog_frame = tk.Frame(count_inner, bg=C["surface0"])
        prog_frame.pack(fill="x", pady=(12, 4))

        self._prog_canvas = tk.Canvas(
            prog_frame, height=8,
            bg=C["surface1"], highlightthickness=0,
        )
        self._prog_canvas.pack(fill="x")
        self._prog_canvas.bind("<Configure>", lambda e: self._draw_progress())

        self._prog_lbl = lbl(prog_frame, "", 8, color=C["subtext"],
                             bg=C["surface0"])
        self._prog_lbl.pack(anchor="e", pady=2)

        # ── Info card ─────────────────────────────────────────────────────────
        info_card = card(center)
        info_card.pack(fill="x", pady=(0, 20))

        info_inner = tk.Frame(info_card, bg=C["surface0"], padx=24, pady=20)
        info_inner.pack(fill="x")

        lbl(info_inner, "Chi tiết License", 10, bold=True,
            color=C["blue"], bg=C["surface0"]).pack(anchor="w", pady=(0, 12))

        key_raw = self.info.get("key") or "—"
        key_display = self._mask_key(key_raw)

        rows = [
            ("License Key",    key_display),
            ("Email đăng ký",  self.info.get("email")   or "—"),
            ("Ngày hết hạn",   self.info.get("expires") or "—"),
            ("Trạng thái",     "🟢 Đang hoạt động"),
        ]

        for label, value in rows:
            row = tk.Frame(info_inner, bg=C["surface0"])
            row.pack(fill="x", pady=4)
            lbl(row, label, 9, color=C["subtext"],
                bg=C["surface0"]).pack(side="left", padx=(0, 16))
            lbl(row, value, 9, bg=C["surface0"]).pack(side="right")
            divider(info_inner).pack(fill="x", pady=2)

        # ── Warning / Renew ───────────────────────────────────────────────────
        self._warn_frame = tk.Frame(center, bg=C["base"])
        self._warn_frame.pack(fill="x", pady=(0, 20))
        self._build_warn_section()

    def _build_warn_section(self):
        for w in self._warn_frame.winfo_children():
            w.destroy()

        days = self._days_left()

        if days <= 0:
            # Expired
            exp_card = tk.Frame(self._warn_frame, bg=C["red"],
                                padx=24, pady=16)
            exp_card.pack(fill="x")
            lbl(exp_card, "❌  License đã hết hạn", 11, bold=True,
                color=C["crust"], bg=C["red"]).pack()
            btn(exp_card, "🔄  Gia hạn ngay",
                lambda: webbrowser.open(RENEW_URL),
                color=C["crust"], fg=C["red"], width=16).pack(pady=8)

        elif days <= WARN_DAYS:
            # Warning
            warn_card = tk.Frame(self._warn_frame, bg=C["yellow"],
                                 padx=24, pady=14)
            warn_card.pack(fill="x")
            lbl(warn_card, f"⚠️  Chỉ còn {days} ngày — Hãy gia hạn sớm!",
                10, bold=True, color=C["crust"], bg=C["yellow"]).pack(side="left")
            btn(warn_card, "Gia hạn",
                lambda: webbrowser.open(RENEW_URL),
                color=C["crust"], fg=C["yellow"], width=10).pack(side="right")
        else:
            # OK
            ok_row = tk.Frame(self._warn_frame, bg=C["base"])
            ok_row.pack(fill="x")
            btn(ok_row, "🔄  Gia hạn / Nâng cấp",
                lambda: webbrowser.open(RENEW_URL),
                color=C["surface1"], fg=C["text"], width=18).pack(side="right")

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw_progress(self):
        w = self._prog_canvas.winfo_width()
        if w <= 1:
            return
        self._prog_canvas.delete("all")
        pct   = self._progress_pct()
        used  = int(w * pct)
        days  = self._days_left()
        color = C["red"] if days <= WARN_DAYS else C["blue"]
        self._prog_canvas.create_rectangle(0, 0, w, 8, fill=C["surface1"], outline="")
        if used > 0:
            self._prog_canvas.create_rectangle(0, 0, used, 8,
                                               fill=color, outline="")
        self._prog_lbl.config(text=f"{int(pct*100)}% đã dùng  •  còn {days} ngày")

    def _update_display(self):
        days, hours, mins, secs = self._time_breakdown()
        color = C["red"] if days <= WARN_DAYS else C["blue"]
        self._unit_labels["days"].config( text=f"{days:02d}",  fg=color)
        self._unit_labels["hours"].config(text=f"{hours:02d}", fg=color)
        self._unit_labels["mins"].config( text=f"{mins:02d}",  fg=color)
        self._unit_labels["secs"].config( text=f"{secs:02d}",  fg=color)
        self._draw_progress()

    # ── Clock thread ──────────────────────────────────────────────────────────

    def _start_clock(self):
        def _tick():
            while self._running:
                try:
                    self.after(0, self._update_display)
                except Exception:
                    break
                time.sleep(1)

        t = threading.Thread(target=_tick, daemon=True)
        t.start()

    def destroy(self):
        self._running = False
        super().destroy()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _mask_key(key: str) -> str:
        parts = key.split("-")
        if len(parts) == 5:
            return f"****-****-****-{parts[3]}-{parts[4]}"
        return key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
