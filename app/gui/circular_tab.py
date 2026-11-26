"""Circular waveform controls and asynchronous preview."""
from __future__ import annotations
import os
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk

class CircularTabMixin:
    def build_circular_tab_interface(self):
        """Build compact circular visualizer tabs with shared output controls."""
        palette = self.get_theme_palette()
        page_bg = palette["selected"]
        panel_bg = palette["panel"]
        base_bg = palette["base"]
        shared = ttk.LabelFrame(self.tab_circular, text=self.tr("Shared Settings"), padding=8)
        shared.pack(fill="x", padx=8, pady=(6, 3))
        shared.columnconfigure(1, weight=1)
        tk.Label(shared, text=self.tr("Output Size (square pixels):"), bg=panel_bg, fg="#ffffff").grid(row=0, column=0, sticky="w", pady=2)
        self.circular_size_slider = tk.Scale(shared, from_=256, to=12000, resolution=1, orient="horizontal", variable=self.circular_size, bg=panel_bg, fg="#ffffff", highlightthickness=0, length=520)
        self.circular_size_slider.grid(row=0, column=1, sticky="ew", padx=10, pady=2)
        tk.Label(shared, text=self.tr("Rotation (degrees):"), bg=panel_bg, fg="#ffffff").grid(row=1, column=0, sticky="w", pady=2)
        self.circular_rotation_slider = tk.Scale(shared, from_=0, to=359, resolution=1, orient="horizontal", variable=self.circular_rotation, bg=panel_bg, fg="#ffffff", highlightthickness=0, length=520)
        self.circular_rotation_slider.grid(row=1, column=1, sticky="ew", padx=10, pady=2)

        self.circular_mode_panels = {}
        circular_workspace = tk.Frame(self.tab_circular, bg=base_bg)
        circular_workspace.pack(fill="both", expand=True, padx=8, pady=3)
        circular_workspace.columnconfigure(0, weight=3)
        circular_workspace.columnconfigure(1, weight=2, minsize=300)
        circular_workspace.rowconfigure(0, weight=1)

        circular_settings_area = tk.Frame(circular_workspace, bg=base_bg)
        circular_settings_area.grid(row=0, column=0, sticky="nsew")
        circular_preview_area = tk.Frame(circular_workspace, bg=base_bg)
        circular_preview_area.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        circular_preview_area.rowconfigure(1, weight=1)
        circular_preview_area.columnconfigure(0, weight=1)

        self.circular_subnotebook = ttk.Notebook(circular_settings_area, style="Sub.TNotebook")
        self.circular_subnotebook.pack(fill="both", expand=True)

        self.circular_preview_frame = tk.Frame(circular_preview_area, bg=base_bg)
        self.circular_preview_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.circular_preview_image_frame = tk.Frame(self.circular_preview_frame, bg=base_bg)
        self.circular_preview_image_frame.pack(expand=True, fill="both")
        self.circular_preview_image_label = tk.Label(
            self.circular_preview_image_frame, bg=panel_bg, borderwidth=0,
            highlightthickness=0, compound="center"
        )
        self.circular_preview_image_label.place(relx=0.5, rely=0.5, anchor="center")
        self.circular_preview_failure_label = tk.Label(
            self.circular_preview_image_frame, text="", bg="#934F51", fg="#ffffff",
            font=("Helvetica", 10, "bold"), padx=8, pady=4
        )
        self.circular_preview_failure_label.place_forget()
        self._load_circular_placeholder()
        waveform_tab = tk.Frame(self.circular_subnotebook, bg=page_bg)
        spectrum_tab = tk.Frame(self.circular_subnotebook, bg=page_bg)
        minimal_tab = tk.Frame(self.circular_subnotebook, bg=page_bg)
        self.circular_subnotebook.add(waveform_tab, text=self.tr("Mode: Circular Waveform"))
        self.circular_subnotebook.add(spectrum_tab, text=self.tr("Mode: Radial Spectrum"))
        self.circular_subnotebook.add(minimal_tab, text=self.tr("Mode: Minimal Circular Waveform"))

        panel_text_color = self.get_theme_palette()["text"]
        waveform_panel = tk.LabelFrame(waveform_tab, text=self.tr("Circular Waveform Settings"), bg=panel_bg, fg=panel_text_color, padx=10, pady=6, bd=0, relief="flat", highlightthickness=0)
        #expand the gray over the blur in Circular waveform tab
        waveform_panel.pack(fill="both", expand=True, padx=8, pady=6)
        waveform_panel.columnconfigure(1, weight=1)
        tk.Label(waveform_panel, text=self.tr("Inner Radius:"), bg=panel_bg, fg="#ffffff").grid(row=0, column=0, sticky="w", pady=2)
        self.circular_radius_slider = tk.Scale(waveform_panel, from_=0.10, to=0.90, resolution=0.01, orient="horizontal", variable=self.circular_inner_radius, bg=panel_bg, fg="#ffffff", highlightthickness=0, length=520)
        self.circular_radius_slider.grid(row=0, column=1, sticky="ew", padx=10, pady=2)
        direction_frame = tk.Frame(waveform_panel, bg=panel_bg)
        direction_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 0))
        tk.Checkbutton(direction_frame, text=self.tr("Outward"), variable=self.circular_outward, command=lambda: self.ensure_circular_direction_selected("waveform", "outward"), bg=panel_bg, fg="#ffffff", activebackground="#404040", activeforeground="white", selectcolor="#2d2d30").pack(side="left")
        tk.Label(direction_frame, text="|", bg=panel_bg, fg="#a0a0a0").pack(side="left", padx=7)
        tk.Checkbutton(direction_frame, text=self.tr("Inward"), variable=self.circular_inward, command=lambda: self.ensure_circular_direction_selected("waveform", "inward"), bg=panel_bg, fg="#ffffff", activebackground="#404040", activeforeground="white", selectcolor="#2d2d30").pack(side="left")
        tk.Label(waveform_panel, text=self.tr("Waveform geometry uses the selection in the Sound Wave Maker tab."), bg=panel_bg, fg="#bdbdbd", anchor="w", wraplength=850).grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=(3, 0))
        self.circular_mode_panels["waveform"] = waveform_panel

        spectrum_panel = tk.LabelFrame(spectrum_tab, text=self.tr("Radial Spectrum Settings"), bg=panel_bg, fg=panel_text_color, padx=10, pady=6, bd=0, relief="flat", highlightthickness=0)
        # Expand the gray over the blue in radial spectrum tab
        spectrum_panel.pack(fill="both", expand=True, padx=8, pady=6)
        spectrum_panel.columnconfigure(1, weight=1)
        tk.Label(spectrum_panel, text=self.tr("Inner Radius:"), bg=panel_bg, fg="#ffffff").grid(row=0, column=0, sticky="w", pady=2)
        self.radial_spectrum_radius_slider = tk.Scale(spectrum_panel, from_=0.10, to=0.90, resolution=0.01, orient="horizontal", variable=self.radial_spectrum_inner_radius, bg=panel_bg, fg="#ffffff", highlightthickness=0, length=520)
        self.radial_spectrum_radius_slider.grid(row=0, column=1, sticky="ew", padx=10, pady=2)
        tk.Label(spectrum_panel, text=self.tr("Frequency Bands:"), bg=panel_bg, fg="#ffffff").grid(row=1, column=0, sticky="w", pady=2)
        self.radial_spectrum_bins_slider = tk.Scale(spectrum_panel, from_=32, to=512, resolution=8, orient="horizontal", variable=self.radial_spectrum_bins, bg=panel_bg, fg="#ffffff", highlightthickness=0, length=520)
        self.radial_spectrum_bins_slider.grid(row=1, column=1, sticky="ew", padx=10, pady=2)
        tk.Label(spectrum_panel, text=self.tr("Sensitivity:"), bg=panel_bg, fg="#ffffff").grid(row=2, column=0, sticky="w", pady=2)
        self.radial_spectrum_sensitivity_slider = tk.Scale(spectrum_panel, from_=0.25, to=9.0, resolution=0.05, orient="horizontal", variable=self.radial_spectrum_sensitivity, bg=panel_bg, fg="#ffffff", highlightthickness=0, length=520)
        self.radial_spectrum_sensitivity_slider.grid(row=2, column=1, sticky="ew", padx=10, pady=2)
        direction_frame = tk.Frame(spectrum_panel, bg=panel_bg)
        direction_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=(3, 0))
        tk.Checkbutton(direction_frame, text=self.tr("Outward"), variable=self.radial_spectrum_outward, command=lambda: self.ensure_circular_direction_selected("spectrum", "outward"), bg=panel_bg, fg="#ffffff", activebackground="#404040", activeforeground="white", selectcolor="#2d2d30").pack(side="left")
        tk.Label(direction_frame, text="|", bg=panel_bg, fg="#a0a0a0").pack(side="left", padx=7)
        tk.Checkbutton(direction_frame, text=self.tr("Inward"), variable=self.radial_spectrum_inward, command=lambda: self.ensure_circular_direction_selected("spectrum", "inward"), bg=panel_bg, fg="#ffffff", activebackground="#404040", activeforeground="white", selectcolor="#2d2d30").pack(side="left")
        self.circular_mode_panels["spectrum"] = spectrum_panel

        minimal_panel = tk.LabelFrame(minimal_tab, text=self.tr("Minimal Circular Waveform Settings"), bg=panel_bg, fg=panel_text_color, padx=10, pady=6, bd=0, relief="flat", highlightthickness=0)
        # Expand the gray over the blue in minimal circular tab
        minimal_panel.pack(fill="both", expand=True, padx=8, pady=6)
        minimal_panel.columnconfigure(1, weight=1)
        tk.Label(minimal_panel, text=self.tr("Base Radius:"), bg=panel_bg, fg="#ffffff").grid(row=0, column=0, sticky="w", pady=2)
        self.minimal_wave_radius_slider = tk.Scale(minimal_panel, from_=0.20, to=0.80, resolution=0.01, orient="horizontal", variable=self.minimal_wave_base_radius, bg=panel_bg, fg="#ffffff", highlightthickness=0, length=520)
        self.minimal_wave_radius_slider.grid(row=0, column=1, sticky="ew", padx=10, pady=2)
        tk.Label(minimal_panel, text=self.tr("Wave Amplitude:"), bg=panel_bg, fg="#ffffff").grid(row=1, column=0, sticky="w", pady=2)
        self.minimal_wave_amplitude_slider = tk.Scale(minimal_panel, from_=0.01, to=0.90, resolution=0.01, orient="horizontal", variable=self.minimal_wave_amplitude, bg=panel_bg, fg="#ffffff", highlightthickness=0, length=520)
        self.minimal_wave_amplitude_slider.grid(row=1, column=1, sticky="ew", padx=10, pady=2)
        tk.Label(minimal_panel, text=self.tr("Line Width:"), bg=panel_bg, fg="#ffffff").grid(row=2, column=0, sticky="w", pady=2)
        self.minimal_wave_line_width_slider = tk.Scale(minimal_panel, from_=0.5, to=16.0, resolution=0.5, orient="horizontal", variable=self.minimal_wave_line_width, bg=panel_bg, fg="#ffffff", highlightthickness=0, length=520)
        self.minimal_wave_line_width_slider.grid(row=2, column=1, sticky="ew", padx=10, pady=2)
        self.circular_mode_panels["minimal"] = minimal_panel

        def mode_tab_changed(_event=None):
            selected_tab = self.circular_subnotebook.index(self.circular_subnotebook.select())
            self.circular_mode.set(("waveform", "spectrum", "minimal")[selected_tab])
            self.update_circular_mode_controls()
        self.circular_subnotebook.bind("<<NotebookTabChanged>>", mode_tab_changed)

        action_box = tk.Frame(self.tab_circular, bg=base_bg)
        action_box.pack(fill="x", padx=8, pady=(3, 6))
        self.preview_btn_circular = self.create_action_button(
            action_box, self.tr("👁️ GENERATE A PREVIEW"), self.generate_circular_preview, "preview"
        )
        self.preview_btn_circular.pack(side="left", fill="x", expand=True, padx=4, ipady=6)
        self.run_btn_circular = self.create_action_button(action_box, self.tr("▶️ GENERATE CIRCULAR WAVEFORMS"), self.launch_circular_processing_pipeline, "generate")
        self.run_btn_circular.pack(side="left", fill="x", expand=True, padx=4, ipady=6)
        self.cancel_btn_circular = self.create_action_button(action_box, self.tr("🛑 CANCEL BATCH QUEUE"), self.trigger_abort_sequence, "stop")
        self.cancel_btn_circular.pack(side="left", fill="x", expand=True, padx=4, ipady=6)
        self.update_circular_mode_controls()
        self.circular_mode.trace_add("write", lambda *_args: self._load_circular_placeholder())

    def _circular_preview_size(self):
        return 400 if self.preview_prefix == "4k-" else 200

    def _circular_preview_placeholder_path(self, mode=None):
        mode = mode or self.circular_mode.get()
        name = {"waveform": "circular-waveform.png", "spectrum": "circular-radial.png", "minimal": "circular-minimal.png"}.get(mode, "circular-waveform.png")
        return os.path.join(self.app_dir, "img", self.preview_prefix + name)

    def _show_circular_preview_photo(self, image, image_path=None):
        old_image = self.circular_preview_image
        self.circular_preview_image_label.configure(image=image, text="")
        self.circular_preview_image = image
        self.circular_preview_image_path = image_path
        if old_image is not None and old_image is not image and old_image not in self.circular_preview_images.values():
            del old_image
        if self.circular_preview_failure_label is not None:
            self.circular_preview_failure_label.place_forget()
            self.circular_preview_failure_label.configure(text="")

    def _load_circular_placeholder(self):
        if not hasattr(self, "circular_preview_image_label"):
            return
        mode = self.circular_mode.get()
        stored = self.circular_preview_images.get(mode)
        if stored is not None:
            self._show_circular_preview_photo(stored, self.circular_preview_real_modes.get(mode))
            return
        path = self._circular_preview_placeholder_path(mode)
        try:
            from PIL import Image, ImageTk
            with Image.open(path) as source_image:
                source_image.load()
                image = ImageTk.PhotoImage(source_image.copy(), master=self.root)
        except ImportError:
            try:
                image = tk.PhotoImage(file=path, master=self.root)
            except (tk.TclError, OSError) as exc:
                self._show_circular_preview_failure()
                self.write_system_log(self.tr("❌ Preview Failed: {error}").format(error=exc))
                return
        except (tk.TclError, OSError, ValueError) as exc:
            self._show_circular_preview_failure()
            self.write_system_log(self.tr("❌ Preview Failed: {error}").format(error=exc))
            return
        self._show_circular_preview_photo(image, path)

    def _show_circular_preview_failure(self):
        if self.circular_preview_failure_label is not None:
            self.circular_preview_failure_label.configure(text=self.tr("Preview Failed"))
            self.circular_preview_failure_label.place(relx=0.5, rely=0.5, anchor="center")

    def _get_circular_batch_queue(self):
        folder = self.source_folder.get().strip().strip('{}')
        valid_extensions = self.DROP_AUDIO_EXTENSIONS
        queue = []
        if os.path.isfile(folder):
            if folder.lower().endswith(valid_extensions):
                queue.append(folder)
        elif os.path.isdir(folder):
            for walk_root, dirs, files in os.walk(folder):
                dirs[:] = [d for d in dirs if d not in ("Waveform_Outputs", "Merged_Tracks_Outputs", "Circular_Waveform_Outputs", "circular-preview")]
                for filename in files:
                    if filename.lower().endswith(valid_extensions) and "_with_art" not in filename.lower():
                        queue.append(os.path.join(walk_root, filename))
            queue.sort()
        return queue

    def _capture_circular_preview_settings(self):
        return {
            "format": self.format_menu.get(),
            "target_dpi": int(self.target_dpi.get()),
            "is_transparent": bool(self.is_transparent.get()),
            "bg_solid_color": self.bg_solid_color,
            "is_solid_color_mode": bool(self.is_solid_color_mode.get()),
            "color_nodes": self.color_nodes.copy(),
            "reverse_color_map": bool(self.reverse_color_map.get()),
            "gradient_direction": self.gradient_direction.get(),
            "peak_geometry_shape": self.peak_geometry_shape.get(),
            "num_bars": int(self.num_bars.get()),
            "circular_mode": self.circular_mode.get(),
            "circular_rotation": int(self.circular_rotation.get()),
            "circular_inner_radius": float(self.circular_inner_radius.get()),
            "circular_inward": bool(self.circular_inward.get()),
            "circular_outward": bool(self.circular_outward.get()),
            "radial_spectrum_inner_radius": float(self.radial_spectrum_inner_radius.get()),
            "radial_spectrum_inward": bool(self.radial_spectrum_inward.get()),
            "radial_spectrum_outward": bool(self.radial_spectrum_outward.get()),
            "radial_spectrum_bins": int(self.radial_spectrum_bins.get()),
            "radial_spectrum_sensitivity": float(self.radial_spectrum_sensitivity.get()),
            "minimal_wave_base_radius": float(self.minimal_wave_base_radius.get()),
            "minimal_wave_amplitude": float(self.minimal_wave_amplitude.get()),
            "minimal_wave_line_width": float(self.minimal_wave_line_width.get()),
        }

    def _prepare_circular_preview_directory(self, source=None):
        source = (source if source is not None else self.source_folder.get()).strip().strip('{}')
        base = os.path.dirname(source) if os.path.isfile(source) else source
        preview_dir = os.path.join(base, "circular-preview")
        existed = os.path.isdir(preview_dir)
        os.makedirs(preview_dir, exist_ok=True)
        marker = os.path.join(preview_dir, ".swarm-preview-owned")
        if not existed:
            Path(marker).write_text("Audio-SWARM circular preview session\n", encoding="utf-8")
            self.circular_preview_owned = True
        else:
            self.circular_preview_owned = os.path.isfile(marker)
        self.circular_preview_dir = os.path.abspath(preview_dir)
        tracked = getattr(self, "active_preview_directories", None)
        if tracked is None:
            self.active_preview_directories = []
            tracked = self.active_preview_directories
        absolute_preview_dir = os.path.abspath(preview_dir)
        if absolute_preview_dir not in tracked:
            tracked.append(absolute_preview_dir)
        return preview_dir

    def _poll_circular_preview_result(self):
        try:
            result, mode, preview_path, error = self.circular_preview_result_queue.get_nowait()
        except queue.Empty:
            if self.circular_preview_running:
                self.root.after(50, self._poll_circular_preview_result)
            return
        if self._closing_requested:
            self.circular_preview_running = False
            self.on_application_close()
            return
        if result == "success":
            self._finish_circular_preview(mode, preview_path)
        else:
            self._fail_circular_preview(error)

    def _finish_circular_preview(self, mode, preview_path):
        try:
            try:
                from PIL import Image, ImageTk
                with Image.open(preview_path) as source_image:
                    image = ImageTk.PhotoImage(source_image.copy(), master=self.root)
            except ImportError:
                image = tk.PhotoImage(file=preview_path, master=self.root)
            # A newly generated preview replaces the previous cached preview.
            # Keep the currently displayed image alive until _show_circular_preview_photo
            # switches the label to the new image.
            self.circular_preview_images.clear()
            self.circular_preview_real_modes.clear()
            self.circular_preview_images[mode] = image
            self.circular_preview_real_modes[mode] = preview_path
            if self.circular_mode.get() == mode:
                self._show_circular_preview_photo(image, preview_path)
            self.circular_preview_running = False
            self.set_circular_preview_button_enabled(True)
        except (tk.TclError, OSError) as exc:
            self._fail_circular_preview(exc)

    def _fail_circular_preview(self, error=None):
        self.circular_preview_running = False
        self.set_circular_preview_button_enabled(True)
        self._show_circular_preview_failure()
        if error is not None:
            self.write_system_log(self.tr("❌ Preview Failed: {error}").format(error=error))

    def ensure_circular_direction_selected(self, mode, clicked_direction=None):
        """Keep one direction enabled; clicking the sole selected box switches direction."""
        if mode == "waveform":
            inward_var = self.circular_inward
            outward_var = self.circular_outward
        else:
            inward_var = self.radial_spectrum_inward
            outward_var = self.radial_spectrum_outward
        if not inward_var.get() and not outward_var.get():
            # The clicked checkbox has just toggled off. Select the other direction
            # so a user can switch modes with one click rather than two.
            if clicked_direction == "outward":
                inward_var.set(True)
            else:
                outward_var.set(True)

    def update_circular_mode_controls(self):
        """Enable only the settings belonging to the selected circular mode."""
        selected = self.circular_mode.get()
        palette = self.get_theme_palette()
        for mode, panel in self.circular_mode_panels.items():
            enabled = mode == selected
            panel.configure(fg=palette["text"] if enabled else palette["muted"])
            self._set_widget_tree_enabled(panel, enabled)

    def _set_widget_tree_enabled(self, parent, enabled):
        """Recursively enable/disable controls without disabling the container."""
        state = "normal" if enabled else "disabled"
        for child in parent.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                try:
                    child.state(["!disabled"] if enabled else ["disabled"])
                except (tk.TclError, AttributeError):
                    pass
            self._set_widget_tree_enabled(child, enabled)

    def set_circular_preview_button_enabled(self, enabled=True):
        """Set Circular Waveform preview-button state from its owning tab."""
        button = getattr(self, "preview_btn_circular", None)
        if button is not None:
            can_enable = bool(enabled) and not self.is_processing and not self.circular_preview_running
            self.set_action_button_enabled(button, can_enable)

    def generate_circular_preview(self):
        """Render the selected circular preview through the original engine."""
        if self.is_processing or self.circular_preview_running or self.sound_preview_running:
            return
        queue_items = self._get_circular_batch_queue()
        if not queue_items:
            self._show_circular_preview_failure()
            return
        from app.core.waveform import render_circular_waveform_preview
        from dataclasses import replace
        audio_path = Path(queue_items[0])
        mode = self.circular_mode.get()
        preview_size = self._circular_preview_size()
        settings = self._build_circular_settings(preview_size=(preview_size, preview_size), preview=True)
        settings = replace(settings, width=preview_size, height=preview_size, dpi=100,
                           output_format="PNG", keep_standalone_image=True)
        source_path = self.source_folder.get().strip().strip('{}')
        self._cleanup_active_preview_directories()
        # Prepared on the Tk thread: this mutates shared GUI state that the close
        # handler and cleanup code read, so it must not run inside the worker.
        try:
            preview_dir = self._prepare_circular_preview_directory(source_path)
        except OSError as exc:
            self._show_circular_preview_failure()
            self.write_system_log(self.tr("❌ Preview Failed: {error}").format(error=exc))
            return
        self.circular_preview_running = True
        self.set_circular_preview_button_enabled(False)

        def worker():
            try:
                preview_path = Path(preview_dir) / f"circular-{mode}-preview.png"
                result = render_circular_waveform_preview(
                    audio_path, preview_dir, settings, mode, preview_size, preview_path
                )
                if result.success and result.output and result.output.is_file():
                    self.circular_preview_result_queue.put(("success", mode, str(result.output), None))
                else:
                    self.circular_preview_result_queue.put(("failure", mode, None, result.message))
            except Exception as exc:
                self.circular_preview_result_queue.put(("failure", mode, None, str(exc)))

        threading.Thread(target=worker, daemon=True, name="AudioSWARM-CircularPreview").start()
        self.root.after(50, self._poll_circular_preview_result)

