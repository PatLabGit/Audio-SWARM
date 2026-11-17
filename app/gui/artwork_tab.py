"""Artwork tab, dimension presets, and shared color controls."""
from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk, filedialog
from matplotlib.colors import LinearSegmentedColormap
from app.gui.constants import PRESET_DIMENSIONS

class ArtworkTabMixin:
    def build_tab2_interface(self):
        palette = self.get_theme_palette()
        panel_bg = palette["panel"]
        base_bg = palette["base"]
        # Panel 1: Image Processing Dimensions Setup
        resizer_lbl_frame = ttk.LabelFrame(self.tab2, text=self.tr(" 📸 Automated Parallel Asset Image Pre-Processing (Resizer) "), padding=10)
        resizer_lbl_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Checkbutton(resizer_lbl_frame, text=self.tr("Activate Automation Matrix Scaling Pipeline Before Container Embedding Runs"), variable=self.tab2_resize_enabled, bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", command=self.sync_tab2_resizer_fields_lock).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
        
        tk.Label(resizer_lbl_frame, text=self.tr("Canvas Presets:"), bg=panel_bg, fg="#ffffff").grid(row=1, column=0, sticky="w", pady=5)
        self.t2_preset_menu = ttk.Combobox(
            resizer_lbl_frame,
            values=[self.tr(label) for label, _width, _height in PRESET_DIMENSIONS]
                  + [self.tr("Custom Mapping Coordinates")],
            state="readonly", width=44
        )
        self.t2_preset_menu.set(self.tr("Landscape 16:9 1920x1080 1080p Full HD"))
        self.t2_preset_menu.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        self.t2_preset_menu.bind("<<ComboboxSelected>>", self.handle_t2_preset_change)
        
        self.t2_w_lbl = tk.Label(resizer_lbl_frame, text=self.tr("Resize Width Target:"), bg=panel_bg, fg="#ffffff")
        self.t2_w_lbl.grid(row=2, column=0, sticky="w")
        self.t2_w_slider = tk.Scale(resizer_lbl_frame, from_=10, to=12000, orient="horizontal", variable=self.tab2_width, bg=panel_bg, fg="#ffffff", highlightthickness=0, command=lambda e: self.force_custom_preset_flag(self.t2_preset_menu))
        self.t2_w_slider.grid(row=2, column=1, sticky="ew", padx=10)
        
        self.t2_h_lbl = tk.Label(resizer_lbl_frame, text=self.tr("Resize Height Target:"), bg=panel_bg, fg="#ffffff")
        self.t2_h_lbl.grid(row=3, column=0, sticky="w")
        self.t2_h_slider = tk.Scale(resizer_lbl_frame, from_=10, to=12000, orient="horizontal", variable=self.tab2_height, bg=panel_bg, fg="#ffffff", highlightthickness=0, command=lambda e: self.force_custom_preset_flag(self.t2_preset_menu))
        self.t2_h_slider.grid(row=3, column=1, sticky="ew", padx=10)
        
        self.t2_aspect_check = tk.Checkbutton(resizer_lbl_frame, text=self.tr("Enforce Asset Letterbox Padding Rules (Preserve Image Aspect Ratio Profiles)"), variable=self.preserve_aspect, bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30")
        self.t2_aspect_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=5)
        self.sync_tab2_resizer_fields_lock()
        
        btn_action_box_t2 = tk.Frame(self.tab2, bg=base_bg)
        btn_action_box_t2.pack(fill="x", padx=10, pady=20)
        
        self.run_btn_t2 = self.create_action_button(btn_action_box_t2, self.tr("🚀 START BATCH PAIRING PROCESS"), self.launch_tab2_pairing_pipeline, "generate")
        self.run_btn_t2.pack(side="left", fill="x", expand=True, padx=5, ipady=8)

        self.cancel_btn_t2 = self.create_action_button(btn_action_box_t2, self.tr("🛑 ABORT PIPELINE STREAM"), self.trigger_abort_sequence, "stop")
        self.cancel_btn_t2.pack(side="left", fill="x", expand=True, padx=5, ipady=8)

    def browse_target_folder(self):
        if self.is_processing: return
        
        # Create a lightweight, stylized drop-down menu pop-up anchored to your mouse cursor coordinates
        popup_choice_menu = tk.Menu(self.root, tearoff=0, bg="#2d2d30", fg="#ffffff", activebackground="#00ff66", activeforeground="#404040")
        
        # Option A: User wants to pick an individual track file where they can see the extensions inline
        def choose_single_file():
            chosen_path = filedialog.askopenfilename(
                parent=self.root,
                initialdir=os.path.dirname(self.source_folder.get()) if os.path.isfile(self.source_folder.get()) else self.source_folder.get(),
                title=self.tr("Select Target Audio Track File"),
                filetypes=[
                    (self.tr("All Supported Audio Tracks"), "*.mp3 *.ogg *.oga *.opus *.wav *.flac *.m4a *.aac *.aiff *.aif"),
                    (self.tr("MP3 Tracks"), "*.mp3"),
                    (self.tr("Ogg Vorbis"), "*.ogg *.oga"),
                    (self.tr("Opus Audio"), "*.opus"),
                    (self.tr("WAV Uncompressed"), "*.wav"),
                    (self.tr("FLAC Audio"), "*.flac"),
                    (self.tr("M4A Audio"), "*.m4a"),
                    (self.tr("AAC Audio"), "*.aac"),
                    (self.tr("AIFF Audio"), "*.aiff *.aif")
                ]
            )
            if chosen_path:
                self.source_folder.set(chosen_path)
                self.clear_system_log()
                self.write_system_log(self.tr("🎵 Active target updated (Single Track):\n   {chosen_path}").format(chosen_path=chosen_path))

        # Option B: User wants to target a complete batch album folder directory
        def choose_entire_folder():
            chosen_path = filedialog.askdirectory(
                parent=self.root,
                initialdir=self.source_folder.get(),
                title=self.tr("Select Target Folder Directory")
            )
            if chosen_path:
                self.source_folder.set(chosen_path)
                self.clear_system_log()
                self.write_system_log(self.tr("📂 Active target updated (Batch Folder):\n   {chosen_path}").format(chosen_path=chosen_path))

        # Add the choices to the menu window element array layers
        popup_choice_menu.add_command(label=self.tr("🎵 Target a Single Audio File"), command=choose_single_file)
        popup_choice_menu.add_command(label=self.tr("📂 Target a Full Batch Folder"), command=choose_entire_folder)
        
        # Pop the choice box open directly under your mouse cursor position smoothly
        try:
            popup_choice_menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery(), 0)
        finally:
            popup_choice_menu.grab_release()

    def force_custom_preset_flag(self, menu_widget):
        menu_widget.set(self.tr("Custom Mapping Coordinates"))

    def handle_t1_preset_change(self, event):
        preset = self.t1_preset_menu.get()
        mapping = {self.tr(label): (width, height) for label, width, height in PRESET_DIMENSIONS}
        if preset in mapping:
            width, height = mapping[preset]
            self.width_val.set(width)
            self.height_val.set(height)

    def handle_t2_preset_change(self, event):
        preset = self.t2_preset_menu.get()
        mapping = {self.tr(label): (width, height) for label, width, height in PRESET_DIMENSIONS}
        if preset in mapping:
            width, height = mapping[preset]
            self.tab2_width.set(width)
            self.tab2_height.set(height)

    def format_type_interlock_trigger(self, event):
        if self.format_menu.get() == "JPG":
            self.is_transparent.set(False)
            self.trans_check.config(state="disabled")
        else:
            self.trans_check.config(state="normal")
        self.sync_transparency_ui_locks()

    def sync_transparency_ui_locks(self):
        # Before a custom color is chosen, use the muted active-sub-tab color to
        # indicate that a solid backdrop can be selected. Keep the workspace's
        # neutral charcoal background unchanged. Once the user picks a color,
        # preserve and display that color across format/transparency changes.
        backdrop_button_color = (
            self.bg_solid_color if self.bg_solid_color_selected else "#496270"
        )
        if self.is_transparent.get():
            self.bg_color_btn.config(
                state="disabled",
                bg=self.bg_solid_color if self.bg_solid_color_selected else "#2d2d30",
                text=self.tr("Locked (Transparent)"),
            )
        else:
            self.bg_color_btn.config(
                state="normal",
                bg=backdrop_button_color,
                text=self.tr("Pick Backdrop Color"),
            )

    def sync_tab2_resizer_fields_lock(self):
        state = "normal" if self.tab2_resize_enabled.get() else "disabled"
        self.t2_preset_menu.config(state="readonly" if self.tab2_resize_enabled.get() else "disabled")
        self.t2_w_slider.config(state=state)
        self.t2_h_slider.config(state=state)
        self.t2_aspect_check.config(state=state)
        self.t2_w_lbl.config(fg="#ffffff" if self.tab2_resize_enabled.get() else "#555555")
        self.t2_h_lbl.config(fg="#ffffff" if self.tab2_resize_enabled.get() else "#555555")

    def sync_gradient_direction_ui_locks(self):
        if self.gradient_direction.get() == "Horizontal":
            self.slice_slider.config(state="disabled")
            self.slice_lbl.config(fg=self.get_theme_palette()["muted"])
        else:
            if not self.is_solid_color_mode.get():
                self.slice_slider.config(state="normal")
                self.slice_lbl.config(fg="#ffffff")

    def toggle_solid_color_processing_locks(self):
        if self.is_solid_color_mode.get():
            self.slice_slider.config(state="disabled")
            self.slice_lbl.config(fg=self.get_theme_palette()["muted"])
            self.reverse_check.config(state="disabled")
            while len(self.color_nodes) > 1:
                self.color_nodes.pop()
        else:
            self.slice_slider.config(state="normal")
            self.slice_lbl.config(fg="#ffffff")
            self.reverse_check.config(state="normal")
            if len(self.color_nodes) == 1:
                self.color_nodes.append("#ffffff")
        self.rebuild_node_button_row()

    def add_new_gradient_node(self):
        if self.is_processing or self.is_solid_color_mode.get():
            return
        # gradient max number of buttons
        if len(self.color_nodes) >= 24:
            return
        self.color_nodes.append("#ffffff")
        self.rebuild_node_button_row()

    def remove_gradient_node(self, index):
        if self.is_processing or self.is_solid_color_mode.get() or len(self.color_nodes) <= 2:
            return
        if 0 <= index < len(self.color_nodes):
            self.color_nodes.pop(index)
            self.rebuild_node_button_row()

    def rebuild_node_button_row(self):
        for child in self.node_btn_box.winfo_children():
            child.destroy()
        self.node_buttons.clear()

        for idx, color in enumerate(self.color_nodes):

            tile = tk.Frame(self.node_btn_box, bg="#404040")
            # gradient max number of buttons per ROW (actual = 5) // 5, column=idx % 5, (idx % 5... change all of them to 8 for 8 buttons per ROW
            tile.grid(row=idx // 8, column=idx % 8, sticky="ew", padx=3, pady=3)
            self.node_btn_box.grid_columnconfigure(idx % 8, weight=1, uniform="color_nodes")

            label = self.tr("Solid Color") if self.is_solid_color_mode.get() else self.tr("Node Color #{index}").format(index=idx+1)
            # button relief . flat > bd=0, remove > relief="raised",
            canvas = tk.Canvas(
                tile,
                bg=color,
                height=40,
                highlightthickness=0,
                bd=1,
                relief="raised",
                cursor="hand2"
            )
            canvas.pack(fill="both", expand=True)

            disabled = len(self.color_nodes) <= 2 or self.is_solid_color_mode.get()
            cross_color = self.get_theme_palette()["muted"] if disabled else "#202020"

            label_id = canvas.create_text(
                0, 0,
                text=label,
                fill="#202020",
                font=("Sans", 10)
            )

            cross_id = canvas.create_text(
                0, 0,
                text="×",
                fill=cross_color,
                font=("Sans", 12, "bold")
            )

            def position_items(event, c=canvas, lbl=label_id, cross=cross_id):
                c.coords(lbl, event.width / 2, event.height / 2)
                c.coords(cross, event.width - 10, 10)

            canvas.bind("<Configure>", position_items)

            def on_swatch_click(event, i=idx, c=canvas):
                if event.x >= c.winfo_width() - 24 and event.y <= 28:
                    if not (len(self.color_nodes) <= 2 or self.is_solid_color_mode.get()):
                        self.remove_gradient_node(i)
                else:
                    self.open_node_color_wheel(i)

            canvas.bind("<Button-1>", on_swatch_click)

            canvas._preserve_color_swatch = True
            self.node_buttons.append(canvas)
        self.redraw_gradient_preview_bar()

    def open_node_color_wheel(self, index):
        if self.is_processing or not (0 <= index < len(self.color_nodes)):
            return
        from app.gui.color_picker import ColorPickerDialog
        dialog = ColorPickerDialog(self.root, self.color_nodes[index], self.recent_colors,
                                   theme=self.get_theme_palette(), translator=self.tr)
        self.root.wait_window(dialog)
        hex_color = dialog.result
        if hex_color:
            self.color_nodes[index] = hex_color
            self.record_recent_color(hex_color)
            self.rebuild_node_button_row()

    def redraw_gradient_preview_bar(self):
        self.grad_canvas.delete("all")
        self.grad_canvas.update()
        w = max(2, self.grad_canvas.winfo_width() if self.grad_canvas.winfo_width() > 1 else 780)
        h = max(2, self.grad_canvas.winfo_height() if self.grad_canvas.winfo_height() > 1 else 35)
        
        if self.is_solid_color_mode.get() or len(self.color_nodes) == 1:
            self.grad_canvas.create_rectangle(0, 0, w, h, fill=self.color_nodes[0], outline="")
        else:
            preview_colors = list(self.color_nodes)

            if self.reverse_color_map.get():
                preview_colors.reverse()

            cmap_mock = LinearSegmentedColormap.from_list('mock', preview_colors)
            for x in range(w):
                factor = x / (w - 1)
                r, g, b, _ = cmap_mock(factor)
                hex_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                self.grad_canvas.create_line(x, 0, x, h, fill=hex_color)
