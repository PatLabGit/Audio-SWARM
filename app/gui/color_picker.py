"""Compact, theme-independent colour picker used by Audio-SWARM."""
from __future__ import annotations

import colorsys
import tkinter as tk
from tkinter import ttk


class ColorPickerDialog(tk.Toplevel):
    def __init__(self, parent, initial_color="#ffffff", recent_colors=None, theme=None, translator=None):
        super().__init__(parent)
        self.withdraw()
        self.tr = translator or (lambda text: text)
        self.title(self.tr("Select Color"))
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self.theme = theme or {"base": "#292b2e", "panel": "#34373b", "field": "#202225", "text": "#f1f2f3", "muted": "#b9bec4", "accent": "#35b58a"}
        self.old_color = self._valid_hex(initial_color) or "#ffffff"
        self.current_color = self.old_color
        self.recent_colors = list(dict.fromkeys((recent_colors or [])[:20]))
        self.hue = 0.0
        self.saturation = 1.0
        self.value = 1.0
        self._photo_sv = None
        self._photo_hue = None
        self._build()
        self._set_from_hex(self.current_color, redraw=True)
        self.update_idletasks()
        self.geometry(f"{self.winfo_reqwidth()}x{self.winfo_reqheight()}")
        self.deiconify()
        self.grab_set()
        self.hex_entry.focus_set()

    @staticmethod
    def _valid_hex(value):
        if not isinstance(value, str) or len(value) != 7 or value[0] != "#":
            return None
        try:
            int(value[1:], 16)
        except ValueError:
            return None
        return value.upper()

    def _build(self):
        c = self.theme
        self.configure(bg=c["base"])
        outer = tk.Frame(self, bg=c["base"], padx=12, pady=10)
        outer.pack(fill="both", expand=True)
        top = tk.Frame(outer, bg=c["base"])
        top.pack(fill="x")
        self.sv_canvas = tk.Canvas(top, width=300, height=250, highlightthickness=1,
                                   highlightbackground=c["muted"], cursor="crosshair")
        self.sv_canvas.pack(side="left")
        self.sv_canvas.bind("<Button-1>", self._pick_sv)
        self.sv_canvas.bind("<B1-Motion>", self._pick_sv)
        self.hue_canvas = tk.Canvas(top, width=22, height=250, highlightthickness=1,
                                    highlightbackground=c["muted"], cursor="crosshair")
        self.hue_canvas.pack(side="left", padx=(8, 0))
        self.hue_canvas.bind("<Button-1>", self._pick_hue)
        self.hue_canvas.bind("<B1-Motion>", self._pick_hue)
        self._draw_hue()

        fields = tk.Frame(outer, bg=c["base"])
        fields.pack(fill="x", pady=(10, 7))
        tk.Label(fields, text="HEX", bg=c["base"], fg=c["text"]).pack(side="left")
        self.hex_var = tk.StringVar(value=self.current_color)
        self.hex_entry = tk.Entry(fields, textvariable=self.hex_var, width=10, bg=c["field"],
                                  fg=c["text"], insertbackground=c["text"], relief="flat")
        self.hex_entry.pack(side="left", padx=(7, 14), ipady=4)
        self.hex_entry.bind("<Return>", self._hex_changed)
        self.hex_entry.bind("<FocusOut>", self._hex_changed)
        tk.Label(fields, text="RGB", bg=c["base"], fg=c["muted"]).pack(side="left")
        self.rgb_var = tk.StringVar(value="255, 255, 255")
        tk.Label(fields, textvariable=self.rgb_var, bg=c["base"], fg=c["text"]).pack(side="left", padx=6)
        self.current_swatch = tk.Label(fields, bg=self.current_color, width=5, height=2,
                                       relief="solid", bd=1)
        self.current_swatch.pack(side="right")
        tk.Label(fields, text=self.tr("Current"), bg=c["base"], fg=c["muted"]).pack(side="right", padx=6)

        tk.Label(outer, text=self.tr("Recent colors"), bg=c["base"], fg=c["text"], anchor="w").pack(fill="x", pady=(3, 4))
        self.recent_frame = tk.Frame(outer, bg=c["base"])
        self.recent_frame.pack(fill="x")
        self._draw_recent()

        bottom = tk.Frame(outer, bg=c["base"])
        bottom.pack(fill="x", pady=(12, 0))
        tk.Label(bottom, text=self.tr("Previous"), bg=c["base"], fg=c["muted"]).pack(side="left")
        tk.Label(bottom, bg=self.old_color, width=5, height=1, relief="solid", bd=1).pack(side="left", padx=7)
        ttk.Button(bottom, text=self.tr("Cancel"), command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(bottom, text="OK", command=self._accept).pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())

    def _draw_hue(self):
        self.hue_canvas.delete("all")
        height = 250
        for y in range(height):
            hue = 1.0 - y / max(1, height - 1)
            r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
            color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            self.hue_canvas.create_line(0, y, 22, y, fill=color)
        marker_y = int((1.0 - self.hue) * (height - 1))
        self.hue_canvas.create_rectangle(0, marker_y-2, 21, marker_y+2, outline="#ffffff", width=2)

    def _draw_sv(self):
        width, height = 300, 250
        photo = tk.PhotoImage(width=width, height=height)
        hr, hg, hb = colorsys.hsv_to_rgb(self.hue, 1, 1)
        for y in range(height):
            val = 1.0 - y / (height - 1)
            row = []
            for x in range(width):
                sat = x / (width - 1)
                r = val * (1 - sat + hr * sat)
                g = val * (1 - sat + hg * sat)
                b = val * (1 - sat + hb * sat)
                row.append(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")
            photo.put("{" + " ".join(row) + "}", to=(0, y))
        self._photo_sv = photo
        self.sv_canvas.delete("all")
        self.sv_canvas.create_image(0, 0, image=photo, anchor="nw")
        x = int(self.saturation * (width - 1))
        y = int((1.0 - self.value) * (height - 1))
        self.sv_canvas.create_oval(x-6, y-6, x+6, y+6, outline="#111111", width=3)
        self.sv_canvas.create_oval(x-5, y-5, x+5, y+5, outline="#ffffff", width=1)

    def _pick_sv(self, event):
        self.saturation = min(1.0, max(0.0, event.x / 299))
        self.value = 1.0 - min(1.0, max(0.0, event.y / 249))
        self._update_color()

    def _pick_hue(self, event):
        self.hue = 1.0 - min(1.0, max(0.0, event.y / 249))
        self._draw_hue()
        self._draw_sv()
        self._update_color()

    def _set_from_hex(self, color, redraw=False):
        color = self._valid_hex(color)
        if not color:
            return
        r, g, b = (int(color[i:i+2], 16) / 255 for i in (1, 3, 5))
        self.hue, self.saturation, self.value = colorsys.rgb_to_hsv(r, g, b)
        if redraw:
            self._draw_hue()
            self._draw_sv()
        self._update_color()

    def _update_color(self):
        r, g, b = colorsys.hsv_to_rgb(self.hue, self.saturation, self.value)
        self.current_color = f"#{round(r*255):02X}{round(g*255):02X}{round(b*255):02X}"
        self.hex_var.set(self.current_color)
        self.rgb_var.set(f"{round(r*255)}, {round(g*255)}, {round(b*255)}")
        self.current_swatch.configure(bg=self.current_color)
        self._draw_sv()

    def _hex_changed(self, _event=None):
        color = self._valid_hex(self.hex_var.get().strip())
        if color:
            self._set_from_hex(color, redraw=True)
        else:
            self.hex_var.set(self.current_color)

    def _draw_recent(self):
        for child in self.recent_frame.winfo_children():
            child.destroy()
        colors = self.recent_colors[:20]
        for i in range(20):
            row, col = divmod(i, 10)
            color = colors[i] if i < len(colors) else None
            swatch = tk.Label(self.recent_frame, bg=color or self.theme["panel"],
                              width=4, height=1, relief="solid", bd=1,
                              cursor="hand2" if color else "arrow")
            swatch.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
            if color:
                swatch.bind("<Button-1>", lambda _e, value=color: self._set_from_hex(value, redraw=True))
            self.recent_frame.grid_columnconfigure(col, weight=1)

    def _accept(self):
        self.result = self.current_color
        self.destroy()
