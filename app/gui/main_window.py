"""Top-level window layout and application lifecycle."""
from __future__ import annotations

import os
import shutil
import sys
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import ttk
from tkinter.ttk import Progressbar
from app.gui.styles import configure_styles
from app.gui.theme import THEME_NAMES, get_color_role, get_palette


class MainWindowMixin:
    def setup_ui_layout(self):
        self.action_button_specs = {}
        self.theme_name = getattr(self, "theme_name", "Dark")
        configure_styles(ttk.Style(), self.theme_name)
        palette = self.get_theme_palette()

        master_container = tk.Frame(self.root, bg=palette["base"])
        master_container.pack(fill="both", expand=True)
        v_scrollbar = ttk.Scrollbar(master_container, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        self.scroll_canvas = tk.Canvas(master_container, bg=palette["base"], highlightthickness=0,
                                       yscrollcommand=v_scrollbar.set)
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        v_scrollbar.config(command=self.scroll_canvas.yview)
        content_frame = tk.Frame(self.scroll_canvas, bg=palette["base"])
        self.scroll_window_id = self.scroll_canvas.create_window((0, 0), window=content_frame, anchor="nw")

        def update_workspace_geometry(_event=None):
            canvas_width = max(1, self.scroll_canvas.winfo_width())
            canvas_height = max(1, self.scroll_canvas.winfo_height())
            requested_height = content_frame.winfo_reqheight()
            self.scroll_canvas.itemconfigure(self.scroll_window_id, width=canvas_width,
                                             height=max(canvas_height, requested_height))
            self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

        content_frame.bind("<Configure>", lambda _e: self.scroll_canvas.after_idle(update_workspace_geometry))
        self.scroll_canvas.bind("<Configure>", update_workspace_geometry)

        def on_main_wheel(event):
            if isinstance(event.widget, tk.Text):
                return
            if getattr(event, "num", None) == 4:
                step = -1
            elif getattr(event, "num", None) == 5:
                step = 1
            else:
                step = -1 if event.delta > 0 else 1
            self.scroll_canvas.yview_scroll(step, "units")

        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.root.bind(sequence, on_main_wheel)

        # Global header: source selection remains outside individual workspaces.
        header = tk.Frame(content_frame, bg=palette["panel"], padx=10, pady=8)
        header.pack(fill="x", padx=10, pady=(10, 6))
        # Application logo
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "img",
            "audio-swarm-logo-2.png"
        )

        logo_image = Image.open(logo_path)
        logo_image.thumbnail((42, 42), Image.Resampling.LANCZOS)

        self.header_logo = ImageTk.PhotoImage(logo_image)

        tk.Label(
            header,
            image=self.header_logo,
            bg=palette["panel"]
        ).pack(side="left", padx=(2, 8))

        # Application title
        tk.Label(
            header,
            text="Audio-SWARM",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Sans", 14, "bold")
        ).pack(side="left", padx=(0, 14))

        self.global_source_frame = tk.Frame(header, bg=palette["panel"])
        self.global_source_frame.pack(side="left", fill="x", expand=True)
        self.source_label = tk.Label(self.global_source_frame, text=self.tr("Audio source:"),
                                     bg=palette["panel"], fg=palette["muted"])
        self.source_label.pack(side="left", padx=(0, 5))
        self.folder_entry = tk.Entry(self.global_source_frame, textvariable=self.source_folder, bg=palette["field"],
                                     fg=palette["text"], insertbackground=palette["text"], borderwidth=1)
        self.folder_entry.pack(side="left", padx=4, fill="x", expand=True)
        self.browse_btn = ttk.Button(self.global_source_frame, text=self.tr("Browse"), command=self.browse_workspace_source)
        self.browse_btn.pack(side="left", padx=4)

        self.language_label = ttk.Label(header, text=self.tr("Language:"))
        self.language_label.pack(side="left", padx=(12, 3))
        self.language_codes_by_name = {name: code for code, name in self.available_languages.items()}
        self.language_menu = ttk.Combobox(header, state="readonly", width=11,
                                          values=list(self.available_languages.values()))
        self.language_menu.set(self.available_languages.get(self.language_code, "English"))
        self.language_menu.pack(side="left", padx=3)
        self.language_menu.bind("<<ComboboxSelected>>", self.change_language)

        self.theme_label = ttk.Label(header, text=self.tr("Theme:"))
        self.theme_label.pack(side="left", padx=(10, 3))
        self.theme_display_names = {self.tr(name): name for name in THEME_NAMES}
        self.theme_menu = ttk.Combobox(header, state="readonly", width=9,
                                       values=list(self.theme_display_names))
        self.theme_menu.set(self.tr(self.theme_name))
        self.theme_menu.pack(side="left", padx=3)
        self.theme_menu.bind("<<ComboboxSelected>>", self.change_theme)

        # Left navigation and a single active workspace.
        body = tk.Frame(content_frame, bg=palette["base"])
        body.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        self.sidebar = tk.Frame(body, bg=palette["panel"], width=190, padx=7, pady=8)
        self.sidebar.pack(side="left", fill="y", padx=(0, 8))
        self.sidebar.pack_propagate(False)

        # Responsive sidebar width: 18%, minimum 180px, maximum 260px.
        body.bind(
            "<Configure>",
            lambda event: self.sidebar.configure(
                width=max(180, min(260, int(event.width * 0.18)))
            )
        )
        self.workspace_host = tk.Frame(body, bg=palette["base"])
        self.workspace_host.pack(side="left", fill="both", expand=True)

        self.tab1 = tk.Frame(self.workspace_host, bg=palette["base"])
        self.tab_circular = tk.Frame(self.workspace_host, bg=palette["base"])
        self.tab2 = tk.Frame(self.workspace_host, bg=palette["base"])
        self.tab_video_poster = tk.Frame(self.workspace_host, bg=palette["base"])
        self.tab_help_about = tk.Frame(self.workspace_host, bg=palette["base"])
        self.workspace_frames = {
            "sound": self.tab1, "circular": self.tab_circular, "artwork": self.tab2,
            "video": self.tab_video_poster, "help": self.tab_help_about,
        }
        self.workspace_buttons = {}
        # Keep navigation labels aligned with the established language-catalog keys.
        navigation = [
            ("sound", " 🎨 Sound Wave Maker "),
            ("circular", " 🔵 Circular Waveform "),
            ("artwork", " 🖼️ Bulk Artwork Linker "),
            ("video", " 🎬 Video Poster "),
            ("help", " 📘 Help / About "),
        ]
        for key, label in navigation:
            button = tk.Button(self.sidebar, text=self.tr(label).strip(), anchor="w", relief="flat",
                               bd=0, highlightthickness=0,
                               padx=10, pady=9, bg=palette["panel"], fg=palette["text"],
                               activebackground=palette["accent"], activeforeground="#ffffff",
                               command=lambda item=key: self.show_workspace(item))
            button.pack(fill="x", pady=2)
            self.workspace_buttons[key] = button

        self.build_tab1_interface()
        self.build_circular_tab_interface()
        self.build_tab2_interface()
        self.build_video_poster_interface()
        self.build_help_about_interface()
        self.show_workspace("sound")

        bottom_frame = ttk.Frame(content_frame, padding=6)
        bottom_frame.pack(fill="x", padx=10, pady=(0, 6))
        self.progress_bar = Progressbar(bottom_frame, orient="horizontal", mode="determinate",
                                        style="Green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=5)
        self.status_label = tk.Label(bottom_frame,
            text=self.tr("System Core Idle. Awaiting execution path instructions..."),
            bg=palette["base"], fg=palette["accent"], anchor="w")
        self.status_label.pack(fill="x")
        self.log_box = tk.Text(bottom_frame, height=3, bg=palette["field"], fg=palette["text"],
                               borderwidth=1, insertbackground=palette["text"])
        self.log_box.pack(fill="x", pady=(3, 0))
        self.log_box.config(state="disabled")

        self.root.after(200, self.redraw_gradient_preview_bar)
        self.root.after_idle(self.update_selection_preview)
        self.grad_canvas.bind("<Configure>", lambda _event: self.redraw_gradient_preview_bar())
        self.register_drop_targets()
        self.apply_theme_to_widgets()

    def show_workspace(self, key):
        """Show one workspace without rebuilding its controls or losing state."""
        for frame in self.workspace_frames.values():
            frame.pack_forget()
        self.workspace_frames[key].pack(fill="both", expand=True)
        self.active_workspace = key
        # The source selector is part of the global header and stays visible
        # in every workspace, including Help / About.
        source_labels = {
            "sound": "Audio source (file or folder):",
            "circular": "Audio source (file or folder):",
            "artwork": "Folder containing audio + artwork:",
            "video": "Video / poster source:",
            "help": "Source (not required here):",
        }
        self.source_label.configure(text=self.tr(source_labels.get(key, "Source:")))
        palette = self.get_theme_palette()
        for name, button in self.workspace_buttons.items():
            selected = name == key
            button.configure(bg=palette["selected"] if selected else palette["panel"],
                             fg=palette["text"])
        if key == "help":
            self.root.after_idle(self._render_visible_help_document)

    def browse_workspace_source(self):
        """Open a source chooser appropriate to the active workspace."""
        if self.is_processing:
            return
        from tkinter import filedialog
        import os
        current = self.source_folder.get().strip().strip("{}")
        initial_dir = os.path.dirname(current) if os.path.isfile(current) else current
        if not os.path.isdir(initial_dir):
            initial_dir = os.path.expanduser("~")
        selected = ""
        if self.active_workspace in ("sound", "circular"):
            self.browse_target_folder()
            return
        if self.active_workspace == "artwork":
            selected = filedialog.askdirectory(parent=self.root, initialdir=initial_dir,
                                               title=self.tr("Select folder containing audio and artwork"))
        elif self.active_workspace == "video":
            choice = tk.Menu(self.root, tearoff=0)
            choice.add_command(label=self.tr("Select a video file"), command=lambda: self._choose_video_source_file(initial_dir))
            choice.add_command(label=self.tr("Select a folder"), command=lambda: self._choose_source_folder(initial_dir))
            try:
                choice.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
            finally:
                choice.grab_release()
            return
        if selected:
            self._set_source_path(selected)

    def _choose_video_source_file(self, initial_dir):
        from tkinter import filedialog
        selected = filedialog.askopenfilename(parent=self.root, initialdir=initial_dir,
            title=self.tr("Select video file"),
            filetypes=[(self.tr("Supported videos"), "*.mp4 *.m4v *.mov *.mkv"),
                       (self.tr("All files"), "*.*")])
        if selected:
            self._set_source_path(selected)

    def _choose_source_folder(self, initial_dir):
        from tkinter import filedialog
        selected = filedialog.askdirectory(parent=self.root, initialdir=initial_dir,
                                           title=self.tr("Select source folder"))
        if selected:
            self._set_source_path(selected)

    def _set_source_path(self, selected):
        self._cleanup_active_preview_directories()
        self.source_folder.set(selected)
        self.clear_system_log()
        self.write_system_log(self.tr("Source updated:\n   {path}").format(path=selected))

    def get_theme_palette(self):
        """Return the centralized palette for the active theme."""
        return get_palette(getattr(self, "theme_name", "Dark"))

    def change_theme(self, _event=None):
        """Persist and apply the newly selected application theme."""
        selected = self.theme_display_names.get(self.theme_menu.get(), self.theme_menu.get())
        if selected not in THEME_NAMES or selected == self.theme_name:
            return
        self.theme_name = selected
        self.save_settings()
        configure_styles(ttk.Style(), self.theme_name)
        self.apply_theme_to_widgets()

    def apply_theme_to_widgets(self):
        """Recolour themed widgets while retaining user-selected artwork colours."""
        palette = self.get_theme_palette()
        previous_palette = getattr(self, "_applied_theme_palette", None)
        # Use canonical Tk option names only. "bg"/"background" and
        # "fg"/"foreground" are aliases; processing both would remap twice.
        color_options = (
            "background", "foreground", "activebackground",
            "activeforeground", "insertbackground", "selectcolor",
            "highlightbackground", "highlightcolor", "disabledforeground",
        )

        def visit(widget):
            try:
                if (
                    widget in getattr(self, "node_buttons", [])
                    or getattr(widget, "_preserve_color_swatch", False)
                ):
                    return

                options = widget.configure()
                # Tk's classic check/radio controls draw a rectangular focus
                # highlight around the whole control by default. Remove that
                # decoration so their surface blends into the settings panel.
                if isinstance(widget, (tk.Checkbutton, tk.Radiobutton)):
                    widget.configure(bd=0, highlightthickness=0, relief="flat")
                is_action_button = widget in getattr(self, "action_button_specs", {})
                for option in color_options:
                    if option not in options:
                        continue
                    if is_action_button and option in ("foreground", "disabledforeground"):
                        continue
                    current = widget.cget(option)
                    role = get_color_role(current, previous_palette, option)
                    if role in palette:
                        widget.configure(**{option: palette[role]})

                # Tk widgets do not all inherit ttk's disabled-state colours.
                # Explicitly theme their disabled foregrounds to avoid dark text
                # on dark panels or pale text on the Light theme.
                if "disabledforeground" in options:
                    widget.configure(disabledforeground=palette["muted"])

                if isinstance(widget, tk.Button):
                    button_key = next(
                        (key for key, button in self.workspace_buttons.items() if button is widget),
                        None,
                    )
                    if button_key is not None:
                        is_active = button_key == getattr(self, "active_workspace", None)
                        widget.configure(
                            bg=palette["selected"] if is_active else palette["panel"],
                            fg=palette["text"],
                            activebackground=palette["accent"],
                            activeforeground="#ffffff",
                        )
            except (tk.TclError, TypeError):
                pass

            for child in widget.winfo_children():
                visit(child)

        visit(self.root)
        self._applied_theme_palette = dict(palette)
        if hasattr(self, "apply_help_theme"):
            self.apply_help_theme()
        if hasattr(self, "theme_menu"):
            self.theme_menu.set(self.tr(self.theme_name))
        self.redraw_gradient_preview_bar()

    def register_drop_targets(self):
        try:
            from tkinterdnd2 import DND_FILES
        except ImportError:
            return
        if not hasattr(self.root, "TkdndVersion"):
            return  # the window was created as a plain tk.Tk(): drag and drop is unavailable

        def register(widget):
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self.handle_dropped_paths)
            except (tk.TclError, AttributeError):
                pass  # a widget type that cannot be a drop target is simply skipped
            for child in widget.winfo_children():
                register(child)

        register(self.root)

    def _cleanup_active_preview_directories(self):
        """Remove preview directories without changing the preview currently displayed."""
        tracked = list(getattr(self, "active_preview_directories", []))
        for preview_dir in tracked:
            try:
                absolute_dir = os.path.abspath(os.fspath(preview_dir))
                if os.path.isdir(absolute_dir):
                    shutil.rmtree(absolute_dir)
            except (OSError, PermissionError, TypeError, ValueError) as exc:
                print(f"Audio-SWARM: could not clean preview directory {preview_dir!r}: {exc}", file=sys.stderr)
        # Forget removed directories, but retain the in-memory preview image.
        self.active_preview_directories = []
        self.circular_preview_dir = None
        self.circular_preview_owned = False

    def handle_dropped_paths(self, event):
        """Place the first dropped file or folder into the target path entry."""
        if self.is_processing:
            self.write_system_log(self.tr("⚠️ Drop ignored: a batch is currently running."))
            return "refuse_drop"

        try:
            paths = self.tk.splitlist(event.data)
        except (tk.TclError, TypeError):
            return "refuse_drop"

        if paths:
            target_path = paths[0]
            self._cleanup_active_preview_directories()
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, target_path)
            self.source_folder.set(target_path)
            self.folder_entry.update_idletasks()
            return getattr(event, "action", "copy")

        return "refuse_drop"

    def on_application_close(self):
        busy = self.is_processing or self.circular_preview_running or self.sound_preview_running
        attempts = getattr(self, "_close_attempts", 0)
        if busy and attempts < 25:
            # Ask the worker to stop and retry for up to ~5 s so temp files are cleaned up.
            self._close_attempts = attempts + 1
            self._closing_requested = True
            self.cancel_operation = True
            self.root.after(200, self.on_application_close)
            return
        self._shutting_down = True
        try:
            self.circular_preview_image = None
            self.circular_preview_image_path = None
            self.circular_preview_images.clear()
            self.circular_preview_real_modes.clear()
            if self.circular_preview_owned and self.circular_preview_dir and os.path.isdir(self.circular_preview_dir):
                import shutil
                shutil.rmtree(self.circular_preview_dir, ignore_errors=False)
        except (OSError, PermissionError) as exc:
            print(f"Audio-SWARM: could not clean circular preview directory: {exc}", file=sys.stderr)
        finally:
            self.root.destroy()
