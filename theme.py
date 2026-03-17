"""
theme.py — Màu sắc & styled widget helpers dùng chung
"""
import tkinter as tk
from tkinter import ttk

# ── Catppuccin Mocha palette ─────────────────────────────────────────────────
C = {
    "base":     "#1e1e2e",
    "mantle":   "#181825",
    "crust":    "#11111b",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "overlay":  "#6c7086",
    "text":     "#cdd6f4",
    "subtext":  "#a6adc8",
    "blue":     "#89b4fa",
    "green":    "#a6e3a1",
    "red":      "#f38ba8",
    "yellow":   "#f9e2af",
    "mauve":    "#cba6f7",
    "peach":    "#fab387",
    "teal":     "#94e2d5",
    "sky":      "#89dceb",
    "lavender": "#b4befe",
}

FONT_UI      = ("Segoe UI",  10)
FONT_UI_B    = ("Segoe UI",  10, "bold")
FONT_TITLE   = ("Segoe UI",  14, "bold")
FONT_H2      = ("Segoe UI",  11, "bold")
FONT_MONO    = ("Consolas",  10)
FONT_MONO_SM = ("Consolas",   9)
FONT_SMALL   = ("Segoe UI",   9)


# ── Helpers ──────────────────────────────────────────────────────────────────

def lbl(parent, text, size=10, bold=False, color=None, bg=None, **kw):
    weight = "bold" if bold else "normal"
    return tk.Label(
        parent, text=text,
        font=("Segoe UI", size, weight),
        bg=bg or C["base"], fg=color or C["text"],
        **kw,
    )

def entry(parent, textvariable=None, width=28, show="", readonly=False):
    state = "readonly" if readonly else "normal"
    return tk.Entry(
        parent,
        textvariable=textvariable,
        font=FONT_MONO,
        bg=C["surface0"], fg=C["text"],
        insertbackground=C["text"],
        disabledbackground=C["surface0"],
        disabledforeground=C["subtext"],
        readonlybackground=C["surface0"],
        relief="flat", bd=6,
        width=width, show=show,
        state=state,
    )

def btn(parent, text, command, color=None, fg=None, width=12, **kw):
    return tk.Button(
        parent, text=text,
        font=FONT_UI_B,
        bg=color or C["blue"],
        fg=fg or C["crust"],
        activebackground=color or C["blue"],
        activeforeground=fg or C["crust"],
        relief="flat", bd=0,
        padx=16, pady=7,
        cursor="hand2",
        width=width,
        command=command,
        **kw,
    )

def card(parent, **kw):
    return tk.Frame(parent, bg=C["surface0"], **kw)

def divider(parent, color=None):
    return tk.Frame(parent, bg=color or C["surface1"], height=1)

def section_header(parent, text, bg=None):
    bg = bg or C["base"]
    f = tk.Frame(parent, bg=bg)
    lbl(f, text, 11, bold=True, bg=bg).pack(side="left")
    return f

def badge(parent, text, color, **kw):
    return tk.Label(
        parent, text=f" {text} ",
        font=("Segoe UI", 8, "bold"),
        bg=color, fg=C["crust"],
        relief="flat", padx=4, pady=2,
        **kw,
    )


# ── Treeview style ────────────────────────────────────────────────────────────

def apply_treeview_style():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Dark.Treeview",
        background=C["surface0"],
        foreground=C["text"],
        fieldbackground=C["surface0"],
        rowheight=28,
        font=FONT_MONO_SM,
        borderwidth=0,
    )
    style.configure(
        "Dark.Treeview.Heading",
        background=C["surface1"],
        foreground=C["blue"],
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        borderwidth=0,
    )
    style.map("Dark.Treeview",
        background=[("selected", C["blue"])],
        foreground=[("selected", C["crust"])],
    )
    style.configure(
        "Dark.Scrollbar",
        background=C["surface1"],
        troughcolor=C["surface0"],
        bordercolor=C["surface0"],
        arrowcolor=C["overlay"],
    )
    return style
