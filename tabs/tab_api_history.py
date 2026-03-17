"""
tabs/tab_api_history.py — Lịch sử API calls
Columns: Timestamp | Messages | Latency | Status | Tokens In | Tokens Out
"""
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
import csv
import io

sys.path.insert(0, str(Path(__file__).parent.parent))
from theme import C, lbl, btn, card, badge, apply_treeview_style
from api_logger import get_records, get_stats


STATUS_COLOR = {
    "2xx": C["green"],
    "4xx": C["yellow"],
    "5xx": C["red"],
}

def _status_color(code: int) -> str:
    if code < 400: return C["green"]
    if code < 500: return C["yellow"]
    return C["red"]

def _status_label(code: int) -> str:
    if code < 400: return "✓"
    if code < 500: return "⚠"
    return "✗"


class ApiHistoryTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=C["base"])
        apply_treeview_style()
        self._filter_status = "all"
        self._build()
        self.refresh()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C["mantle"], pady=20)
        hdr.pack(fill="x")
        lbl(hdr, "📊  Lịch sử API Calls", 15, bold=True, bg=C["mantle"]).pack()
        lbl(hdr, "Theo dõi toàn bộ request đến model của bạn",
            9, color=C["subtext"], bg=C["mantle"]).pack(pady=4)

        # ── Stats row ─────────────────────────────────────────────────────────
        self._stats_frame = tk.Frame(self, bg=C["base"])
        self._stats_frame.pack(fill="x", padx=24, pady=16)
        self._stat_labels = {}
        self._build_stats_row()

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = tk.Frame(self, bg=C["base"])
        toolbar.pack(fill="x", padx=24, pady=(0, 8))

        # Filter buttons
        filter_frame = tk.Frame(toolbar, bg=C["base"])
        filter_frame.pack(side="left")

        lbl(filter_frame, "Lọc:", 9, color=C["subtext"]).pack(side="left", padx=(0,8))
        for label, val in [("Tất cả", "all"), ("Thành công", "ok"), ("Lỗi", "err")]:
            b = tk.Button(
                filter_frame, text=label,
                font=("Segoe UI", 9),
                bg=C["surface0"], fg=C["text"],
                relief="flat", bd=0,
                padx=12, pady=4,
                cursor="hand2",
                command=lambda v=val: self._set_filter(v),
            )
            b.pack(side="left", padx=3)

        # Search
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._apply_filter())
        search_entry = tk.Entry(
            toolbar,
            textvariable=self._search_var,
            font=("Segoe UI", 9),
            bg=C["surface0"], fg=C["text"],
            insertbackground=C["text"],
            relief="flat", bd=6, width=20,
        )
        search_entry.pack(side="left", padx=(16, 0))
        lbl(toolbar, "🔍", bg=C["base"]).pack(side="left", padx=(4,0))

        # Right buttons
        btn(toolbar, "↺  Refresh", self.refresh,
            color=C["surface1"], fg=C["text"], width=10).pack(side="right")
        btn(toolbar, "⬇  Export CSV", self._export_csv,
            color=C["teal"], fg=C["crust"], width=12).pack(side="right", padx=(0, 8))

        # ── Treeview table ────────────────────────────────────────────────────
        table_frame = tk.Frame(self, bg=C["surface0"])
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        cols = ("time", "messages", "latency", "status", "tokens_in", "tokens_out")
        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            style="Dark.Treeview",
            selectmode="browse",
        )

        headers = {
            "time":       ("🕐  Thời gian",    160),
            "messages":   ("💬  Messages",       90),
            "latency":    ("⚡  Latency (ms)",  110),
            "status":     ("📶  Status",         80),
            "tokens_in":  ("↑ Tokens In",       100),
            "tokens_out": ("↓ Tokens Out",      100),
        }
        for col, (heading, width) in headers.items():
            self.tree.heading(col, text=heading, anchor="w")
            self.tree.column(col, width=width, anchor="w", minwidth=60)

        # Scrollbar
        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Row tags
        self.tree.tag_configure("ok",  foreground=C["green"])
        self.tree.tag_configure("err", foreground=C["red"])
        self.tree.tag_configure("warn",foreground=C["yellow"])
        self.tree.tag_configure("alt", background=C["mantle"])

        # ── Empty state label ─────────────────────────────────────────────────
        self._empty_lbl = lbl(
            self, "Chưa có dữ liệu — gọi API để bắt đầu ghi log",
            10, color=C["overlay"],
        )

    def _build_stats_row(self):
        for w in self._stats_frame.winfo_children():
            w.destroy()

        stats = get_stats()
        items = [
            ("Tổng calls",    str(stats["total"]),              C["blue"]),
            ("Thành công",    str(stats["success"]),            C["green"]),
            ("Lỗi",           str(stats["error"]),              C["red"]),
            ("Avg Latency",   f"{stats['avg_latency']} ms",     C["yellow"]),
            ("Tổng Tokens",   f"{stats['total_tokens']:,}",     C["mauve"]),
            ("Success Rate",  f"{stats['success_rate']}%",      C["teal"]),
        ]

        for label, value, color in items:
            c = card(self._stats_frame)
            c.pack(side="left", padx=(0, 10), fill="y")
            inner = tk.Frame(c, bg=C["surface0"], padx=16, pady=10)
            inner.pack()
            lbl(inner, value, 16, bold=True, color=color,
                bg=C["surface0"]).pack()
            lbl(inner, label, 8, color=C["subtext"],
                bg=C["surface0"]).pack()

    # ── Data ─────────────────────────────────────────────────────────────────

    def refresh(self):
        self._records = get_records()
        self._build_stats_row()
        self._apply_filter()

    def _set_filter(self, val: str):
        self._filter_status = val
        self._apply_filter()

    def _apply_filter(self):
        keyword = self._search_var.get().lower()
        records = self._records

        if self._filter_status == "ok":
            records = [r for r in records if r.get("status", 0) < 400]
        elif self._filter_status == "err":
            records = [r for r in records if r.get("status", 0) >= 400]

        if keyword:
            records = [r for r in records
                       if keyword in r.get("timestamp", "").lower()
                       or keyword in str(r.get("status", ""))]

        self._populate(records)

    def _populate(self, records: list):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not records:
            self._empty_lbl.place(relx=0.5, rely=0.65, anchor="center")
            return

        self._empty_lbl.place_forget()

        for i, r in enumerate(records):
            status = r.get("status", 0)
            tag    = "ok" if status < 400 else ("warn" if status < 500 else "err")
            tags   = (tag, "alt") if i % 2 == 1 else (tag,)
            self.tree.insert("", "end", values=(
                r.get("timestamp", ""),
                r.get("num_messages", 0),
                f"{r.get('latency_ms', 0):,}",
                f"{_status_label(status)} {status}",
                f"{r.get('tokens_in', 0):,}",
                f"{r.get('tokens_out', 0):,}",
            ), tags=tags)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="api_history.csv",
        )
        if not path:
            return
        records = self._records
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "timestamp","num_messages","latency_ms",
                "status","tokens_in","tokens_out"])
            w.writeheader()
            w.writerows(records)
        messagebox.showinfo("Đã xuất", f"✅ Lưu thành công:\n{path}")
