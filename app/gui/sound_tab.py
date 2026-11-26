"""Standard waveform tab and asynchronous preview."""
from __future__ import annotations
import os
import queue
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from app.gui.constants import PRESET_DIMENSIONS

class SoundTabMixin:
    def build_tab1_interface(self):
        palette = self.get_theme_palette()
        page_bg = palette["selected"]
        panel_bg = palette["panel"]
        base_bg = palette["base"]
        field_bg = palette["field"]
        # Organize Sound Wave Maker into compact task-oriented sub-tabs.
        self.sound_subnotebook = ttk.Notebook(self.tab1, style="Sub.TNotebook")
        self.sound_subnotebook.pack(fill="x", expand=False, padx=8, pady=(8, 4))
        self.t1_canvas_tab = tk.Frame(self.sound_subnotebook, bg=page_bg)
        self.t1_style_tab = tk.Frame(self.sound_subnotebook, bg=page_bg)
        self.t1_colors_tab = tk.Frame(self.sound_subnotebook, bg=page_bg)
        self.t1_output_tab = tk.Frame(self.sound_subnotebook, bg=page_bg)
        self.sound_subnotebook.add(self.t1_canvas_tab, text=self.tr("Canvas & Resolution"))
        self.sound_subnotebook.add(self.t1_style_tab, text=self.tr("Waveform Style"))
        self.sound_subnotebook.add(self.t1_colors_tab, text=self.tr("Colors"))
        self.sound_subnotebook.add(self.t1_output_tab, text=self.tr("Output Format"))

        # Canvas and resolution controls
        split_columns_box = tk.Frame(self.t1_canvas_tab, bg=page_bg)
        # Extend the gray on the blue Canvas & Resolution tab
        split_columns_box.pack(fill="both", expand=True, padx=10, pady=8)

        # -------------------------------------------------------------
        # 🧱 Column 1 (Left Side): Render Resolution Framework
        # -------------------------------------------------------------
        size_lbl_frame = ttk.LabelFrame(split_columns_box, text=self.tr(" 📐 Render Resolution Framework Configuration "), padding=10)
        size_lbl_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        tk.Label(size_lbl_frame, text=self.tr("Canvas Presets:"), bg=panel_bg, fg="#ffffff").grid(row=0, column=0, sticky="w", pady=5)
        self.t1_preset_menu = ttk.Combobox(
            size_lbl_frame,
            values=[self.tr(label) for label, _width, _height in PRESET_DIMENSIONS]
                  + [self.tr("Custom Mapping Coordinates")],
            state="readonly", width=44
        )
        self.t1_preset_menu.set(self.tr("Landscape 16:9 1920x1080 1080p Full HD"))
        self.t1_preset_menu.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        self.t1_preset_menu.bind("<<ComboboxSelected>>", self.handle_t1_preset_change)

        tk.Label(size_lbl_frame, text=self.tr("Canvas Width Limit:"), bg=panel_bg, fg="#ffffff").grid(row=1, column=0, sticky="w")
        self.w_slider = tk.Scale(size_lbl_frame, from_=10, to=12000, orient="horizontal", variable=self.width_val, bg=panel_bg, fg="#ffffff", highlightthickness=0, command=lambda e: self.force_custom_preset_flag(self.t1_preset_menu))
        self.w_slider.grid(row=1, column=1, sticky="ew", padx=10)

        tk.Label(size_lbl_frame, text=self.tr("Canvas Height Limit:"), bg=panel_bg, fg="#ffffff").grid(row=2, column=0, sticky="w")
        self.h_slider = tk.Scale(size_lbl_frame, from_=10, to=12000, orient="horizontal", variable=self.height_val, bg=panel_bg, fg="#ffffff", highlightthickness=0, command=lambda e: self.force_custom_preset_flag(self.t1_preset_menu))
        self.h_slider.grid(row=2, column=1, sticky="ew", padx=10)

        # -------------------------------------------------------------
        # 🧱 Column 2 (Right Side): Waveform Structural Core Densities
        # -------------------------------------------------------------
        density_lbl_frame = ttk.LabelFrame(split_columns_box, text=self.tr(" 🎛️ Waveform Structural Core Densities "), padding=10)
        density_lbl_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        tk.Label(density_lbl_frame, text=self.tr("Total Grid Bar Count Mapping Layout:"), bg=panel_bg, fg="#ffffff").grid(row=0, column=0, sticky="w")
        self.stem_count_slider = tk.Scale(
            density_lbl_frame, from_=20, to=650, orient="horizontal",
            variable=self.num_bars, bg=panel_bg, fg="#ffffff",
            highlightthickness=0,
            command=lambda _value: self._set_selection_preview_mode("stems"),
        )
        self.stem_count_slider.grid(row=0, column=1, sticky="ew", padx=10)

        self.slice_lbl = tk.Label(density_lbl_frame, text=self.tr("Gradient Processing Slice Resolution:"), bg=panel_bg, fg="#ffffff")
        self.slice_lbl.grid(row=1, column=0, sticky="w")
        self.slice_slider = tk.Scale(
            density_lbl_frame, from_=5, to=200, orient="horizontal",
            variable=self.slices_val, bg=panel_bg, fg="#ffffff",
            highlightthickness=0,
            command=lambda _value: self._set_selection_preview_mode("slices"),
        )
        self.slice_slider.grid(row=1, column=1, sticky="ew", padx=10)

        tk.Label(density_lbl_frame, text=self.tr("DPI (Printing Resolution):"), bg=panel_bg, fg="#ffffff").grid(row=2, column=0, sticky="w", pady=5)
        tk.Entry(density_lbl_frame, textvariable=self.target_dpi, width=10, bg="#2d2d30", fg="#ffffff", insertbackground="white", borderwidth=1).grid(row=2, column=1, sticky="w", padx=10, pady=5)

        
        # 📐 HORIZONTAL SPLIT INFRASTRUCTURE: Establishes column 1 & 2 for Wave Layout Styles
        # Match the surrounding charcoal panel so no darker strip appears between columns.
        style_columns_box = tk.Frame(self.t1_style_tab, bg=page_bg)
        # Expand the gray to the blue on the Waveform Style tab
        style_columns_box.pack(fill="both", expand=True, padx=10, pady=5)

        # -------------------------------------------------------------
        # 🧱 Column 1 (Left Side): Gradient Spectrum Axis Orientation
        # -------------------------------------------------------------
        flow_lbl_frame = ttk.LabelFrame(style_columns_box, text=self.tr(" ↕️↔️ Gradient Spectrum Axis Orientation "), padding=10)
        flow_lbl_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Packed vertically (.pack(anchor="w", pady=2)) so they stack neatly on top of each other!
        tk.Radiobutton(flow_lbl_frame, text=self.tr("Horizontal Flow (Timeline Wave - Color Shifts Left-to-Right)"), variable=self.gradient_direction, value="Horizontal", bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", highlightthickness=0, takefocus=0, command=self.sync_gradient_direction_ui_locks).pack(anchor="w", pady=2)
        tk.Radiobutton(flow_lbl_frame, text=self.tr("Vertical Flow (Peak Meter - Color Shifts with Height)"), variable=self.gradient_direction, value="Vertical", bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", highlightthickness=0, takefocus=0, command=self.sync_gradient_direction_ui_locks).pack(anchor="w", pady=2)

        # -------------------------------------------------------------
        # 🧱 Column 2 (Right Side): NEW Waveform Peak Geometry Choices
        # -------------------------------------------------------------
        geom_lbl_frame = ttk.LabelFrame(style_columns_box, text=self.tr(" 📐 Waveform Bar Peak Contour Geometry Style "), padding=10)
        geom_lbl_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        # Packed vertically to match the height and clean look of Column 1 perfectly
        tk.Radiobutton(geom_lbl_frame, text=self.tr("Standard Classic Bars (Flat Rectangle Tops)"), variable=self.peak_geometry_shape, value="Rectangle", bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", highlightthickness=0, takefocus=0).pack(anchor="w", pady=2)
        tk.Radiobutton(geom_lbl_frame, text=self.tr("Smooth Capsules (Perfect Rounded Pill Contours)"), variable=self.peak_geometry_shape, value="Capsule", bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", highlightthickness=0, takefocus=0).pack(anchor="w", pady=2)
        tk.Radiobutton(geom_lbl_frame, text=self.tr("Lollipop Indicators (Circular Stamp Peaks)"), variable=self.peak_geometry_shape, value="Lollipop", bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", highlightthickness=0, takefocus=0).pack(anchor="w", pady=2)
        tk.Radiobutton(geom_lbl_frame, text=self.tr("Sharp Spikes (Pointy Arrow / Pencil Peaks)"), variable=self.peak_geometry_shape, value="Spike", bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", highlightthickness=0, takefocus=0).pack(anchor="w", pady=2)
        tk.Radiobutton(geom_lbl_frame, text=self.tr("Arrow-Spear (Narrow Stem with Pointed Head)"), variable=self.peak_geometry_shape, value="ArrowSpear", bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", highlightthickness=0, takefocus=0).pack(anchor="w", pady=2)


        # Panel 3: Color Palette Strip Layout Engine
        self.color_lbl_frame = ttk.LabelFrame(self.t1_colors_tab, text=self.tr(" 🎨 Gradient Color Multi-Node Matrix Mixer "), padding=10)
        self.color_lbl_frame.pack(fill="x", padx=10, pady=5)

        self.grad_canvas = tk.Canvas(self.color_lbl_frame, height=35, bg="#111114", highlightthickness=0)
        self.grad_canvas.pack(fill="x", padx=5, pady=5)

        self.node_btn_box = tk.Frame(self.color_lbl_frame, bg=panel_bg)
        self.node_btn_box.pack(fill="x", pady=2)
        
        node_mgmt_box = tk.Frame(self.color_lbl_frame, bg=panel_bg)
        node_mgmt_box.pack(fill="x", pady=5)
        
        ttk.Button(node_mgmt_box, text=self.tr("➕ Add Color Node"), command=self.add_new_gradient_node).pack(side="left", padx=5)
        
        self.solid_mode_check = tk.Checkbutton(node_mgmt_box, text=self.tr("⚡ Enable Solid Flat Color Engine Mode (Ultra Fast / No Slices)"), variable=self.is_solid_color_mode, bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", command=self.toggle_solid_color_processing_locks)
        self.solid_mode_check.pack(side="left", padx=15)

        self.reverse_check = tk.Checkbutton(self.color_lbl_frame, text=self.tr("Invert Layer Core Coordinates Processing Direction (Reverse Vector Flow)"), variable=self.reverse_color_map, bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", command=lambda: (self.redraw_gradient_preview_bar(), self.save_settings()))
        self.reverse_check.pack(anchor="w", pady=2)
        
        self.save_gradient_check = tk.Checkbutton(self.color_lbl_frame, text=self.tr("Save gradient setting"), variable=self.save_gradient_setting, bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", command=self.save_settings)
        self.save_gradient_check.pack(anchor="w", pady=2)

        # Panel 4: File Format Controls
        file_lbl_frame = ttk.LabelFrame(self.t1_output_tab, text=self.tr(" 🖼️ Output Asset Backdrop & Container Rule Matrix "), padding=10)
        # Extend the gray on the blue tab output format
        file_lbl_frame.pack(fill="both", expand=True, padx=10, pady=5)

        tk.Label(file_lbl_frame, text=self.tr("Output Raster Format:"), bg=panel_bg, fg="#ffffff").grid(row=0, column=0, sticky="w", pady=5)
        self.format_menu = ttk.Combobox(file_lbl_frame, values=["PNG", "JPG"], state="readonly", width=10)
        self.format_menu.set("PNG")
        self.format_menu.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        self.format_menu.bind("<<ComboboxSelected>>", self.format_type_interlock_trigger)

        self.trans_check = tk.Checkbutton(file_lbl_frame, text=self.tr("Enable 100% Alpha Channel Canvas Transparency Block"), variable=self.is_transparent, bg=panel_bg, fg="#ffffff", activebackground=panel_bg, activeforeground="white", selectcolor="#2d2d30", command=self.sync_transparency_ui_locks)
        self.trans_check.grid(row=0, column=2, sticky="w", padx=10)
        
        self.bg_color_btn = tk.Button(file_lbl_frame, text=self.tr("Pick Backdrop Solid Color"), bg=self.bg_solid_color, fg="#ffffff", command=self.pick_flat_backdrop_color)
        self.bg_color_btn._preserve_color_swatch = True
        self.bg_color_btn.grid(row=0, column=3, sticky="w", padx=10)
        
        self.node_buttons = []
        self.rebuild_node_button_row()
        
        self.sync_transparency_ui_locks()
        
        tk.Checkbutton(
            file_lbl_frame,
            text=self.tr("Keep images alongside embedded audio"),
            variable=self.keep_standalone_png,
            bg=panel_bg, fg="#ffffff", activebackground=panel_bg,
            activeforeground="white", selectcolor="#2d2d30",
            command=self._on_keep_images_toggle,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=5)

        # Selection preview area: explanatory notice and optional pre-rendered PNG.
        # Keep one PhotoImage reference only so repeated tab changes cannot grow memory.
        self.preview_frame = tk.Frame(self.tab1, bg=base_bg)
        self.preview_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        self.preview_notice = tk.Label(
            self.preview_frame,
            text=self.tr("Note: This preview is for reference only and may differ from the final rendered output."),
            bg=base_bg, fg="#C7C7C7", anchor="w", justify="left", wraplength=1000,
        )
        self.preview_notice.pack(fill="x", padx=5, pady=(0, 3))
        self.preview_image_label = tk.Label(self.preview_frame, bg=base_bg, borderwidth=0)
        self.preview_image_label.pack(fill="both", expand=True)

        # Refresh when the selected page changes, and when relevant values change.
        self.sound_subnotebook.bind("<<NotebookTabChanged>>", self.update_selection_preview)
        for variable in (self.gradient_direction, self.peak_geometry_shape, self.num_bars, self.slices_val):
            variable.trace_add("write", self.update_selection_preview)

        # Primary actions stay visible below the preview, regardless of selected page.
        btn_action_box = tk.Frame(self.tab1, bg=base_bg)
        btn_action_box.pack(fill="x", padx=10, pady=(0, 8))
        
        self.preview_btn_sound = self.create_action_button(btn_action_box, self.tr("👁️ GENERATE A PREVIEW"), self.generate_sound_wave_maker_preview, "preview")
        self.preview_btn_sound.pack(side="left", fill="x", expand=True, padx=5, ipady=8)

        self.run_btn_t1 = self.create_action_button(btn_action_box, self.tr("▶️ RUN GENERATOR ENGINE"), self.launch_tab1_processing_pipeline, "generate")
        self.run_btn_t1.pack(side="left", fill="x", expand=True, padx=5, ipady=8)

        self.cancel_btn_t1 = self.create_action_button(btn_action_box, self.tr("🛑 CANCEL BATCH QUEUE"), self.trigger_abort_sequence, "stop")
        self.cancel_btn_t1.pack(side="left", fill="x", expand=True, padx=5, ipady=8)

    def _selection_preview_filename(self):
        """Return the PNG filename matching the active Sound Wave Maker selection."""
        try:
            sub_index = self.sound_subnotebook.index(self.sound_subnotebook.select())
        except (tk.TclError, AttributeError):
            return None
        if sub_index == 0:  # Canvas & Resolution
            stems = int(self.num_bars.get())
            if stems < 100:
                stem_group = "very-low"
            elif stems < 200:
                stem_group = "medium"
            elif stems < 300:
                stem_group = "high"
            else:
                stem_group = "super-high"
            slices = int(self.slices_val.get())
            if slices < 20:
                slice_group = "low"
            elif slices <= 50:
                slice_group = "medium"
            else:
                slice_group = "high"
            # Remember which control the user last adjusted. Tk focus is unreliable
            # for this purpose (for example, when the slider is dragged with a mouse).
            if getattr(self, "selection_preview_mode", "stems") == "slices":
                return f"canvas-resolution-gradient-slices-{slice_group}.png"
            return f"canvas-resolution-stem-count-{stem_group}.png"
        if sub_index == 1:  # Waveform Style
            direction = "vertical" if self.gradient_direction.get() == "Vertical" else "horizontal"
            geometry = {
                "Rectangle": "standard-classic-bars",
                "Capsule": "smooth-capsules",
                "Lollipop": "lollipop",
                "Spike": "sharp-spikes",
                "ArrowSpear": "arrow-spear",
            }.get(self.peak_geometry_shape.get(), "standard-classic-bars")
            return f"waveform-style-{direction}-{geometry}.png"
        return None

    def _set_selection_preview_mode(self, mode):
        """Show the preview category for the slider the user is adjusting."""
        if mode not in ("stems", "slices"):
            return
        self.selection_preview_mode = mode
        self.update_selection_preview()

    def update_selection_preview(self, *_args):
        """Display the pre-generated preview for current settings without image processing."""
        label = getattr(self, "preview_image_label", None)
        if label is None or not label.winfo_exists():
            return
        if getattr(self, "sound_preview_active", False):
            return
        try:
            sub_index = self.sound_subnotebook.index(self.sound_subnotebook.select())
        except (tk.TclError, AttributeError):
            sub_index = -1
        if sub_index in (0, 1):  # Canvas & Resolution or Waveform Style
            if not self.preview_notice.winfo_manager():
                self.preview_notice.pack(fill="x", padx=5, pady=(0, 3), before=self.preview_image_label)
        else:  # Colors or Output Format
            self.preview_notice.pack_forget()

        filename = self._selection_preview_filename()
        image_path = os.path.join(self.app_dir, "img", self.preview_prefix + filename) if filename else None
        if not image_path or not os.path.isfile(image_path):
            label.configure(image="", text="")
            self.preview_image = None
            self.preview_image_path = None
            return
        if image_path == self.preview_image_path and self.preview_image is not None:
            return
        try:
            # Tk loads PNG directly. No Pillow dependency, resize, or resampling.
            image = tk.PhotoImage(file=image_path, master=self.root)
        except (tk.TclError, OSError) as exc:
            label.configure(image="", text="")
            self.preview_image = None
            self.preview_image_path = None
            print(f"Audio-SWARM: could not load selection preview {image_path}: {exc}", file=sys.stderr)
            return
        label.configure(image=image, text="")
        self.preview_image = image
        self.preview_image_path = image_path

    def _sound_preview_input_queue(self):
        """Return the first audio file in the same deterministic order as batch processing."""
        return self._get_circular_batch_queue()

    def set_sound_preview_button_enabled(self, enabled=True):
        """Set Sound Wave Maker preview-button state from its owning tab.

        The button must stay disabled while either a main processing job or
        this tab's asynchronous preview is active.
        """
        button = getattr(self, "preview_btn_sound", None)
        if button is not None:
            can_enable = bool(enabled) and not self.is_processing and not self.sound_preview_running
            self.set_action_button_enabled(button, can_enable)

    def generate_sound_wave_maker_preview(self):
        """Render a single preview using the canonical engine, without an export pass."""
        if self.is_processing or self.sound_preview_running or self.circular_preview_running:
            return
        queue_items = self._sound_preview_input_queue()
        if not queue_items:
            self._show_sound_preview_failure()
            return
        from app.core.waveform import render_waveform_preview
        audio_path = Path(queue_items[0])
        source_path = self.source_folder.get().strip().strip('{}')
        self._cleanup_active_preview_directories()
        preview_size = (2000, 240) if self.preview_prefix == "4k-" else (1000, 120)
        stops = list(self.color_nodes) or ["#00ff66"]
        if self.reverse_color_map.get() and not self.is_solid_color_mode.get():
            stops.reverse()
        settings = self._build_waveform_settings(preview_size=preview_size)
        from dataclasses import replace
        settings = replace(settings, width=preview_size[0], height=preview_size[1], dpi=100,
                           output_format="PNG", keep_standalone_image=True,
                           gradient_stops=tuple(stops), reverse_gradient=False)
        # Prepared on the Tk thread (it mutates shared GUI state), not in the worker.
        try:
            preview_dir = self._prepare_circular_preview_directory(source_path)
        except OSError as exc:
            self._show_sound_preview_failure()
            self.write_system_log(self.tr("❌ Preview Failed: {error}").format(error=exc))
            return
        self.sound_preview_running = True
        self.set_sound_preview_button_enabled(False)

        def worker():
            try:
                preview_path = Path(preview_dir) / "sound-wave-maker-preview.png"
                result = render_waveform_preview(audio_path, preview_dir, settings, preview_path)
                if result.success and result.output and result.output.is_file():
                    self.sound_preview_result_queue.put(("success", str(result.output), None))
                else:
                    self.sound_preview_result_queue.put(("failure", None, result.message))
            except Exception as exc:
                self.sound_preview_result_queue.put(("failure", None, str(exc)))

        threading.Thread(target=worker, daemon=True, name="AudioSWARM-WaveformPreview").start()
        self.root.after(50, self._poll_sound_wave_maker_preview)

    def _poll_sound_wave_maker_preview(self):
        try:
            result, path, error = self.sound_preview_result_queue.get_nowait()
        except queue.Empty:
            if self.sound_preview_running:
                self.root.after(50, self._poll_sound_wave_maker_preview)
            return
        self.sound_preview_running = False
        self.set_sound_preview_button_enabled(True)
        if self._closing_requested:
            self.on_application_close()
            return
        if result != "success" or not path:
            self._show_sound_preview_failure()
            if error:
                self.write_system_log(self.tr("❌ Preview Failed: {error}").format(error=error))
            return
        try:
            try:
                from PIL import Image, ImageTk
                with Image.open(path) as source_image:
                    image = ImageTk.PhotoImage(source_image.copy(), master=self.root)
            except ImportError:
                image = tk.PhotoImage(file=path, master=self.root)
            self.preview_image_label.configure(image=image, text="")
            self.preview_image = image
            self.preview_image_path = path
            self.sound_preview_active = True
            self._clear_sound_preview_failure()
        except (tk.TclError, OSError) as exc:
            self._show_sound_preview_failure()
            self.write_system_log(self.tr("❌ Preview Failed: {error}").format(error=exc))

    def _show_sound_preview_failure(self):
        if not hasattr(self, "preview_image_label"):
            return
        if self.sound_preview_failure_label is None:
            self.sound_preview_failure_label = tk.Label(
                self.preview_frame, text=self.tr("Preview Failed"),
                bg="#934F51", fg="#FFFFFF", padx=10, pady=5
            )
        self.sound_preview_failure_label.configure(text=self.tr("Preview Failed"))
        self.sound_preview_failure_label.place(relx=0.5, rely=0.5, anchor="center")

    def _clear_sound_preview_failure(self):
        if self.sound_preview_failure_label is not None:
            self.sound_preview_failure_label.place_forget()
            self.sound_preview_failure_label.configure(text="")
    def _on_generate_image_only_toggle(self):
        """Image-only output excludes audio embedding and persists the user's choice."""
        if self.generate_image_only.get() and self.keep_standalone_png.get():
            self.keep_standalone_png.set(False)
        self.save_settings()

    def _on_keep_images_toggle(self):
        """Keep the two output preferences mutually exclusive when enabling either."""
        if self.keep_standalone_png.get() and self.generate_image_only.get():
            self.generate_image_only.set(False)
        self.save_settings()

