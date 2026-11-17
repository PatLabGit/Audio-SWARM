"""Shared ttk styles for Audio-SWARM."""
from __future__ import annotations

import sys
from tkinter import ttk

from app.gui.theme import get_palette


# "Sans" and "Monospace" are X11 aliases; use platform-native families elsewhere.
if sys.platform == "win32":
    SANS_FONT, MONO_FONT = "Segoe UI", "Consolas"
elif sys.platform == "darwin":
    SANS_FONT, MONO_FONT = "Helvetica Neue", "Menlo"
else:
    SANS_FONT, MONO_FONT = "Sans", "Monospace"


POPUP_THEME = {
    "bg": "#8f6d38",
    "fg": "#ffffff",
    "btn_bg": "#cc5e5e",
    "btn_fg": "#2e2e2e",
    "btn_hover_bg": "#e07474",
    "btn_hover_fg": "#2e2e2e",
    "btn_active_bg": "#00cc55",
    "btn_active_fg": "#ffffff",
    "font_main": (SANS_FONT, 12),
    "font_btn": (SANS_FONT, 10, "bold"),
}


def configure_styles(style: ttk.Style, theme_name: str = "Dark") -> None:
    """Apply the selected application palette to shared ttk widgets."""
    colors = get_palette(theme_name)
    base = colors["base"]
    panel = colors["panel"]
    field = colors["field"]
    text = colors["text"]
    accent = colors["accent"]
    tab = colors["tab"]
    selected = colors["selected"]
    hover = colors["hover"]
    disabled = colors["disabled"]

    style.theme_use("clam")
    style.configure(".", background=base, foreground=text, fieldbackground=field)
    style.configure("TFrame", background=base)
    style.configure("TLabel", background=panel, foreground=text)
    # Settings groups use the same surface as the main sidebar. Keep the
    # LabelFrame border the same colour as its surface so no pale outline is drawn.
    style.configure(
        "TLabelframe",
        background=panel,
        foreground=text,
        borderwidth=0,
        relief="flat",
        bordercolor=panel,
        lightcolor=panel,
        darkcolor=panel,
    )
    style.configure("TLabelframe.Label", background=panel, foreground=text)
    style.configure("TButton", background=panel, foreground=text, bordercolor=colors["border"])
    style.map(
        "TButton",
        background=[("disabled", base), ("active", selected)],
        foreground=[("disabled", disabled), ("!disabled", text)],
    )
    notebook_options = {
        "background": base,
        "borderwidth": 0,
        "relief": "flat",
        # The notebook client edge is painted in the page colour so it
        # disappears into the selected page instead of forming a white frame.
        "bordercolor": selected,
        "lightcolor": selected,
        "darkcolor": selected,
        "tabmargins": [0, 2, 0, 0],
    }
    style.configure("TNotebook", **notebook_options)
    style.configure("Main.TNotebook", **notebook_options)
    style.configure(
        "Main.TNotebook.Tab", background=tab, foreground=text,
        padding=[13, 4], borderwidth=0, relief="flat",
        bordercolor=tab, lightcolor=tab, darkcolor=tab,
    )
    style.map(
        "Main.TNotebook.Tab",
        background=[("selected", selected), ("active", hover), ("!selected", tab)],
        foreground=[("selected", text), ("!selected", text)],
        padding=[("selected", [14, 7]), ("!selected", [12, 4])],
        bordercolor=[("selected", selected), ("!selected", tab)],
        lightcolor=[("selected", selected), ("!selected", tab)],
        darkcolor=[("selected", selected), ("!selected", tab)],
    )
    style.configure("Sub.TNotebook", **notebook_options)
    style.configure(
        "Sub.TNotebook.Tab", background=tab, foreground=text,
        padding=[11, 4], borderwidth=0, relief="flat",
        bordercolor=tab, lightcolor=tab, darkcolor=tab,
    )
    style.map(
        "Sub.TNotebook.Tab",
        background=[("selected", selected), ("active", hover), ("!selected", tab)],
        foreground=[("selected", text), ("!selected", text)],
        padding=[("selected", [13, 7]), ("!selected", [11, 4])],
        bordercolor=[("selected", selected), ("!selected", tab)],
        lightcolor=[("selected", selected), ("!selected", tab)],
        darkcolor=[("selected", selected), ("!selected", tab)],
    )
    style.configure(
        "TCombobox",
        fieldbackground=field,
        background=panel,
        foreground=text,
        arrowcolor=text,
        bordercolor=colors["border"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", field), ("disabled", base)],
        foreground=[("readonly", text), ("disabled", disabled)],
        selectbackground=[("readonly", selected)],
        selectforeground=[("readonly", text)],
    )
    style.configure(
        "Green.Horizontal.TProgressbar",
        thickness=15,
        troughcolor=colors["separator"],
        background=accent,
        bordercolor=base,
    )
