"""
dashboard.py — Cửa sổ Dashboard chính
=======================================
Sidebar trái  +  Content area phải
4 tabs: Profile | API History | License | Account

Cách dùng trong app.py:
    from dashboard import Dashboard
    dash = Dashboard(license_info=license_manager.info(), on_logout=lambda: sys.exit(0))
    dash.run()
"""

import sys
import tkinter as tk
from pathlib import Path

# Thêm project root vào sys.path
sys.path.insert(0, str(Path(__file__).parent))

from theme import C, lbl, divider

# Lazy imports — chỉ load khi user click tab
from tabs.tab_profile     import ProfileTab
from tabs.tab_api_history import ApiHistoryTab
from tabs.tab_license     import LicenseTab
from tabs.tab_account     import AccountTab


# ── Sidebar button ────────────────────────────────────────────────────────────

class SidebarBtn(tk.Frame):
    def __init__(self, parent, icon, label, command, **kw):
        super().__init__(parent, bg=C["mantle"], cursor="hand2", **kw)
        self._active  = False
        self._command = command

        self._indicator = tk.Frame(self, bg=C["mantle"], width=3)
        self._indicator.pack(side="left", fill="y")

        inner = tk.Frame(self, bg=C["mantle"], padx=16, pady=14)
        inner.pack(side="left", fill="x", expand=True)

        self._icon_lbl = tk.Label(inner, text=icon,
                                  font=("Segoe UI", 14),
                                  bg=C["mantle"], fg=C["overlay"])
        self._icon_lbl.pack(side="left")

        self._text_lbl = tk.Label(inner, text=label,
                                  font=("Segoe UI", 10),
                                  bg=C["mantle"], fg=C["subtext"])
        self._text_lbl.pack(side="left", padx=10)

        for w in [self, inner, self._icon_lbl, self._text_lbl]:
            w.bind("<Button-1>", lambda e: self._command())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def set_active(self, active: bool):
        self._active = active
        if active:
            self._indicator.config(bg=C["blue"])
            self._icon_lbl.config(fg=C["blue"])
            self._text_lbl.config(fg=C["text"],
                                  font=("Segoe UI", 10, "bold"))
            self.config(bg=C["surface0"])
            for w in self.winfo_children():
                self._set_bg_deep(w, C["surface0"])
            self._indicator.config(bg=C["blue"])
        else:
            self._indicator.config(bg=C["mantle"])
            self._icon_lbl.config(fg=C["overlay"])
            self._text_lbl.config(fg=C["subtext"],
                                  font=("Segoe UI", 10))
            self.config(bg=C["mantle"])
            for w in self.winfo_children():
                self._set_bg_deep(w, C["mantle"])
            self._indicator.config(bg=C["mantle"])

    def _set_bg_deep(self, widget, color):
        try:
            widget.config(bg=color)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._set_bg_deep(child, color)

    def _on_enter(self, e):
        if not self._active:
            self.config(bg=C["surface0"])

    def _on_leave(self, e):
        if not self._active:
            self.config(bg=C["mantle"])


# ── Main Dashboard ────────────────────────────────────────────────────────────

class Dashboard:
    def __init__(self, license_info: dict, on_logout=None):
        self.license_info = license_info
        self.on_logout    = on_logout
        self._current_tab = None
        self._tab_cache   = {}

        self.root = tk.Tk()
        self.root.title("Claude via Browser — Dashboard")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.configure(bg=C["base"])
        self._center_window()
        self._build()

    def _center_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - 1100) // 2
        y  = (sh - 700)  // 2
        self.root.geometry(f"1100x700+{x}+{y}")

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # Root = sidebar | content
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()

        # Show default tab
        self._switch_tab("profile")

    def _build_sidebar(self):
        sidebar = tk.Frame(self.root, bg=C["mantle"], width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # App branding
        brand = tk.Frame(sidebar, bg=C["crust"], pady=22, padx=20)
        brand.pack(fill="x")

        tk.Label(brand, text="⚡ Claude via Browser",
                 font=("Segoe UI", 11, "bold"),
                 bg=C["crust"], fg=C["blue"]).pack(anchor="w")

        email = self.license_info.get("email", "")
        if email:
            tk.Label(brand, text=email,
                     font=("Segoe UI", 8),
                     bg=C["crust"], fg=C["subtext"]).pack(anchor="w", pady=2)

        tk.Frame(sidebar, bg=C["surface0"], height=1).pack(fill="x")

        # Nav label
        tk.Label(sidebar, text="MENU",
                 font=("Segoe UI", 7, "bold"),
                 bg=C["mantle"], fg=C["overlay"],
                 padx=20).pack(anchor="w", pady=(16, 4))

        # Nav buttons
        nav_items = [
            ("profile",    "👤", "Hồ sơ"),
            ("history",    "📊", "Lịch sử API"),
            ("license",    "⏳", "License"),
            ("account",    "🧑‍💻", "Tài khoản"),
        ]

        self._nav_btns = {}
        for key, icon, label in nav_items:
            b = SidebarBtn(sidebar, icon, label,
                           command=lambda k=key: self._switch_tab(k))
            b.pack(fill="x")
            self._nav_btns[key] = b

        # Spacer
        tk.Frame(sidebar, bg=C["mantle"]).pack(fill="both", expand=True)

        # Footer
        tk.Frame(sidebar, bg=C["surface0"], height=1).pack(fill="x")
        footer = tk.Frame(sidebar, bg=C["mantle"], pady=16, padx=20)
        footer.pack(fill="x")

        expires = self.license_info.get("expires", "")
        if expires:
            tk.Label(footer, text=f"Hết hạn: {expires}",
                     font=("Segoe UI", 8),
                     bg=C["mantle"], fg=C["subtext"]).pack(anchor="w")

    def _build_content_area(self):
        self._content = tk.Frame(self.root, bg=C["base"])
        self._content.pack(side="left", fill="both", expand=True)

    # ── Tab switching ─────────────────────────────────────────────────────────

    def _switch_tab(self, key: str):
        if self._current_tab == key:
            return

        # Hide current
        if self._current_tab and self._current_tab in self._tab_cache:
            self._tab_cache[self._current_tab].pack_forget()

        # Update nav buttons
        for k, btn in self._nav_btns.items():
            btn.set_active(k == key)

        # Build tab if not cached
        if key not in self._tab_cache:
            self._tab_cache[key] = self._build_tab(key)

        # Show
        self._tab_cache[key].pack(fill="both", expand=True)
        self._current_tab = key

        # Refresh API history when switching to it
        if key == "history":
            self._tab_cache[key].refresh()

    def _build_tab(self, key: str) -> tk.Frame:
        if key == "profile":
            return ProfileTab(self._content, self.license_info)
        if key == "history":
            return ApiHistoryTab(self._content)
        if key == "license":
            return LicenseTab(self._content, self.license_info)
        if key == "account":
            return AccountTab(self._content, self.license_info,
                              on_logout=self._do_logout)
        raise ValueError(f"Unknown tab: {key}")

    def _do_logout(self):
        self.root.destroy()
        if self.on_logout:
            self.on_logout()

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Demo — thay bằng license_manager.info() thật khi tích hợp
    demo_info = {
        "key":     "ABCDE-12345-FGHIJ-67890-XY12",
        "email":   "demo@example.com",
        "expires": "2025-12-31",
        "valid":   True,
    }
    dash = Dashboard(license_info=demo_info, on_logout=lambda: print("Logged out"))
    dash.run()
