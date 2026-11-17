"""Presentation layer panel layout for the Video Poster Cover tab."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from app.gui.constants import PRESET_DIMENSIONS


class VideoPosterTab:

    def build_video_poster_interface(self):
        """Builds the visual interface for the Video Poster feature matching your artwork tab style exactly."""
        palette = self.get_theme_palette()
        panel_bg = palette["panel"]
        base_bg = palette["base"]
        # 1. Main Outer Containment LabelFrame matching Tab 2 layout specs
        self.video_resizer_lf = ttk.LabelFrame(
            self.tab_video_poster, 
            text=self.tr(" 🎞️ Automated Parallel Asset Image Pre-Processing (Resizer) "), 
            padding=10
        )
        self.video_resizer_lf.pack(fill="x", padx=10, pady=5)

        # Connect directly to the variables declared in app.py to prevent AttributeErrors
        self.video_preset_selection = tk.StringVar(value=self.tr("Landscape 16:9 1920x1080 1080p Full HD"))

        # Row 0: Automatically resizes checkbox matching tab 2 design rules
        tk.Checkbutton(
            self.video_resizer_lf, 
            text=self.tr("Activate Automation Matrix Scaling Pipeline Before Container Embedding Runs"), 
            variable=self.tab2_resize_enabled, 
            bg=panel_bg, 
            fg="#ffffff", 
            activebackground=panel_bg, 
            activeforeground="white", 
            selectcolor="#2d2d30", 
            command=self.sync_video_resizer_fields_lock
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)

        # Row 1: Canvas Presets Combobox dropdown
        self.lbl_v_preset = tk.Label(self.video_resizer_lf, text=self.tr("Canvas Presets:"), bg=panel_bg, fg="#ffffff")
        self.lbl_v_preset.grid(row=1, column=0, sticky="w", pady=5)
        
        self.video_preset_combo = ttk.Combobox(
            self.video_resizer_lf,
            values=[self.tr(label) for label, _width, _height in PRESET_DIMENSIONS]
                  + [self.tr("Custom Mapping Coordinates")],
            textvariable=self.video_preset_selection,
            state="readonly", 
            width=44
        )
        self.video_preset_combo.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        self.video_preset_combo.bind("<<ComboboxSelected>>", self._on_video_preset_changed)

        # Row 2: Resize Width Slider matching original scale properties
        self.lbl_v_width = tk.Label(self.video_resizer_lf, text=self.tr("Resize Width Target:"), bg=panel_bg, fg="#ffffff")
        self.lbl_v_width.grid(row=2, column=0, sticky="w")
        
        self.video_width_scale = tk.Scale(
            self.video_resizer_lf, 
            from_=10, 
            to=12000, 
            orient="horizontal", 
            variable=self.tab2_width, 
            bg=panel_bg, 
            fg="#ffffff", 
            highlightthickness=0, 
            command=lambda e: self.force_custom_preset_flag(self.video_preset_combo)
        )
        self.video_width_scale.grid(row=2, column=1, sticky="ew", padx=10)

        # Row 3: Resize Height Slider matching original scale properties
        self.lbl_v_height = tk.Label(self.video_resizer_lf, text=self.tr("Resize Height Target:"), bg=panel_bg, fg="#ffffff")
        self.lbl_v_height.grid(row=3, column=0, sticky="w")
        
        self.video_height_scale = tk.Scale(
            self.video_resizer_lf, 
            from_=10, 
            to=12000, 
            orient="horizontal", 
            variable=self.tab2_height, 
            bg=panel_bg, 
            fg="#ffffff", 
            highlightthickness=0, 
            command=lambda e: self.force_custom_preset_flag(self.video_preset_combo)
        )
        self.video_height_scale.grid(row=3, column=1, sticky="ew", padx=10)

        # Row 4: Enforce Asset Letterbox Padding checkbox
        self.video_aspect_check = tk.Checkbutton(
            self.video_resizer_lf, 
            text=self.tr("Enforce Asset Letterbox Padding Rules (Preserve Image Aspect Ratio Profiles)"), 
            variable=self.preserve_aspect, 
            bg=panel_bg, 
            fg="#ffffff", 
            activebackground=panel_bg, 
            activeforeground="white", 
            selectcolor="#2d2d30"
        )
        self.video_aspect_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=5)
        
        # Initialize field lock states
        self.sync_video_resizer_fields_lock()

        # 3. Bottom Button Row Wrapper Panel Frame
        self.video_btn_row = tk.Frame(self.tab_video_poster, bg=base_bg)
        self.video_btn_row.pack(fill="x", padx=10, pady=20)

        # Left Action Launch button built natively through application styles engine factory
        self.start_btn_video = self.create_action_button(
            self.video_btn_row, 
            self.tr("🎬 START BATCH PAIRING PROCESS"), 
            self.launch_video_poster_pipeline, 
            "generate"
        )
        self.start_btn_video.pack(side="left", fill="x", expand=True, padx=5, ipady=8)

        # Right Abort tracking button built natively through application styles engine factory
        self.abort_btn_video = self.create_action_button(
            self.video_btn_row, 
            self.tr("🛑 ABORT PIPELINE STREAM"), 
            self.trigger_abort_sequence, 
            "stop"
        )
        self.abort_btn_video.pack(side="left", fill="x", expand=True, padx=5, ipady=8)

    def _on_video_preset_changed(self, _event=None):
        preset = self.video_preset_selection.get()
        mapping = {self.tr(label): (width, height) for label, width, height in PRESET_DIMENSIONS}
        if preset in mapping:
            width, height = mapping[preset]
            self.tab2_width.set(width)
            self.tab2_height.set(height)

    def sync_video_resizer_fields_lock(self):
        """Synchronizes field visibility and font colors according to resizer checkbox state."""
        state = "normal" if self.tab2_resize_enabled.get() else "disabled"
        self.video_preset_combo.config(state="readonly" if self.tab2_resize_enabled.get() else "disabled")
        self.video_width_scale.config(state=state)
        self.video_height_scale.config(state=state)
        self.video_aspect_check.config(state=state)
        self.lbl_v_width.config(fg="#ffffff" if self.tab2_resize_enabled.get() else "#555555")
        self.lbl_v_height.config(fg="#ffffff" if self.tab2_resize_enabled.get() else "#555555")

