#!/usr/bin/env python3
"""Audio-SWARM desktop application entry point."""
from __future__ import annotations
import os
import queue
import threading
import traceback
import tkinter as tk
from app.gui.localization import LocalizationMixin
from app.gui.help_about import HelpAboutMixin
from app.gui.components import ComponentsMixin
from app.gui.main_window import MainWindowMixin
from app.gui.sound_tab import SoundTabMixin
from app.gui.circular_tab import CircularTabMixin
from app.gui.artwork_tab import ArtworkTabMixin
from app.gui.processing import ProcessingMixin
from app.core.process import ffmpeg_executable

from app.gui.video_tab import VideoPosterTab


class AudioSWARMApp(LocalizationMixin, HelpAboutMixin, ComponentsMixin, MainWindowMixin,
                    SoundTabMixin, CircularTabMixin, ArtworkTabMixin, VideoPosterTab, ProcessingMixin):
    # Ensure this variable name is correct and no duplicate assignments happen here:
    DROP_AUDIO_EXTENSIONS = (".mp3", ".ogg", ".oga", ".opus", ".wav", ".flac", ".m4a", ".aac", ".aiff", ".aif")

    def __init__(self, root):
        self.root = root
        # Expose Tk's native Tcl list parser for safe drag-and-drop path parsing.
        self.tk = root.tk
        self.app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        # Preview assets are selected by the physical screen resolution. Images are
        # displayed at native size; no runtime resizing or resampling is performed.
        try:
            screen_width = root.winfo_screenwidth()
        except tk.TclError:
            screen_width = 1920
        self.preview_prefix = "4k-" if screen_width >= 3840 else ""
        self.preview_image = None  # Retain only the currently displayed image.
        self.preview_image_path = None
        self.sound_preview_running = False
        self.sound_preview_result_queue = queue.Queue()
        self.sound_preview_owned_dir = False
        self.sound_preview_failure_label = None
        self.sound_preview_active = False
        self.selection_preview_mode = "stems"
        self.language_dir = os.path.join(self.app_dir, "languages")
        self.help_dir = os.path.join(self.app_dir, "help")
        self.about_dir = os.path.join(self.app_dir, "about")
        self.settings_path = os.path.join(self.app_dir, "settings.json")
        self.available_languages = self.discover_languages()
        self.language_code = self.read_saved_language()
        self.theme_name = self.read_saved_theme()
        self.recent_colors = self.read_recent_colors()
        self.translations = {}
        self.load_language(self.language_code)
        self.root.title(self.tr("Audio-SWARM — Audio Waveform & Artwork Studio"))
        self.root.geometry("1280x720")
        self.root.configure(bg=self.get_theme_palette()["base"])

        # -------------------------------------------------------------
        # Core Architecture Variable Blocks
        # -------------------------------------------------------------
        # Default to the user's Music folder (or home) instead of the working
        # directory, which is SWARM's own install folder when launched via a launcher.
        home_dir = os.path.expanduser("~")
        music_dir = os.path.join(home_dir, "Music")
        self.source_folder = tk.StringVar(value=music_dir if os.path.isdir(music_dir) else home_dir)

        # Tab 1 State Variables
        self.width_val = tk.IntVar(value=1920)
        self.height_val = tk.IntVar(value=1080)
        self.num_bars = tk.IntVar(value=135)
        self.slices_val = tk.IntVar(value=25)
        self.target_dpi = tk.IntVar(value=100)
        self.file_format = tk.StringVar(value="PNG")
        self.is_transparent = tk.BooleanVar(value=True)
        self.bg_solid_color = "#404040"
        # True after the user explicitly chooses a backdrop color. Until then,
        # the enabled backdrop button uses the muted active-sub-tab color.
        self.bg_solid_color_selected = False
        self.keep_standalone_png = tk.BooleanVar(value=True)
        self.generate_image_only = tk.BooleanVar(value=False)
        self.gradient_direction = tk.StringVar(value="Horizontal")
        self.peak_geometry_shape = tk.StringVar(value="Rectangle")

        # Gradient State Control Setup (Dynamic Node Storage Array)
        self.color_nodes = ["#00ff66", "#ffff00", "#ff9900", "#ff0033"]
        self.is_solid_color_mode = tk.BooleanVar(value=False)
        self.reverse_color_map = tk.BooleanVar(value=False)

        # Tab 2 State Variables
        self.tab2_resize_enabled = tk.BooleanVar(value=True)
        self.tab2_width = tk.IntVar(value=1920)
        self.tab2_height = tk.IntVar(value=1080)
        self.preserve_aspect = tk.BooleanVar(value=False)

        # Circular waveform tab state. Shared colors, output format, transparency,
        # backdrop color, DPI, and standalone-image preference reuse existing controls.
        self.circular_size = tk.IntVar(value=2000)
        self.circular_mode = tk.StringVar(value="waveform")
        self.circular_inner_radius = tk.DoubleVar(value=0.38)
        self.circular_inward = tk.BooleanVar(value=False)
        self.circular_outward = tk.BooleanVar(value=True)
        self.circular_rotation = tk.IntVar(value=0)
        self.radial_spectrum_inner_radius = tk.DoubleVar(value=0.38)
        self.radial_spectrum_inward = tk.BooleanVar(value=False)
        self.radial_spectrum_outward = tk.BooleanVar(value=True)
        self.radial_spectrum_bins = tk.IntVar(value=180)
        self.radial_spectrum_sensitivity = tk.DoubleVar(value=2.0)
        self.minimal_wave_base_radius = tk.DoubleVar(value=0.58)
        self.minimal_wave_amplitude = tk.DoubleVar(value=0.25)
        self.minimal_wave_line_width = tk.DoubleVar(value=2.0)

        # Circular preview state. Only the current displayed image is retained.
        self.circular_preview_image = None
        self.circular_preview_image_path = None
        self.circular_preview_failure_label = None
        self.circular_preview_dir = None
        self.circular_preview_owned = False
        # Absolute preview directories created during this application session.
        self.active_preview_directories = []
        self.circular_preview_real_modes = {}
        self.circular_preview_images = {}
        self.circular_preview_running = False
        self._closing_requested = False
        self.circular_preview_result_queue = queue.Queue()

        # Thread / Processing Guard Flags
        self._cancel_event = threading.Event()
        self.cancel_operation = False
        self.is_processing = False
        # Worker threads never touch Tk: they queue callables that the main thread runs.
        self.ui_queue = queue.Queue()
        self._shutting_down = False

        from app.core.engine import ProcessingEngine
        self.engine = ProcessingEngine(
            logger=self.log_threadsafe,
            popup=lambda title, message, kind="info": self.ui_call(
                lambda: self.show_themed_popup(title, message, kind)
            ),
            translator=self.tr,
        )

        self.setup_ui_layout()
        self.root.protocol("WM_DELETE_WINDOW", self.on_application_close)
        self._drain_ui_queue()
        self.root.after(600, self._warn_if_ffmpeg_missing)

    # -- thread-safe UI plumbing -------------------------------------------------
    @property
    def cancel_operation(self):
        return self._cancel_event.is_set()

    @cancel_operation.setter
    def cancel_operation(self, value):
        if value:
            self._cancel_event.set()
        else:
            self._cancel_event.clear()

    def ui_call(self, callback):
        """Run ``callback`` on the Tk main thread. Safe to call from any thread."""
        self.ui_queue.put(callback)

    def log_threadsafe(self, message):
        self.ui_call(lambda: self.write_system_log(message) if hasattr(self, "log_box") else None)

    def _drain_ui_queue(self):
        try:
            while True:
                callback = self.ui_queue.get_nowait()
                try:
                    callback()
                except tk.TclError:
                    pass  # widget destroyed while the callback was queued
                except Exception:  # noqa: BLE001 - one bad callback must not stop the UI pump
                    traceback.print_exc()
        except queue.Empty:
            pass
        if not self._shutting_down:
            self.root.after(50, self._drain_ui_queue)

    def _warn_if_ffmpeg_missing(self):
        if ffmpeg_executable() is None:
            message = self.tr(
                "FFmpeg was not found. Install it (https://ffmpeg.org) and make sure it is on your PATH, "
                "or place it in an 'ffmpeg' folder next to main.py. Rendering and embedding need it."
            )
            self.write_system_log("⚠️ " + message)
            self.show_themed_popup(self.tr("FFmpeg Required"), message, kind="error")

def main():
    root = tk.Tk()
    AudioSWARMApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
