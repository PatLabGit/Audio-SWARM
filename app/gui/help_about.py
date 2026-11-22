"""Help, about, and markdown rendering widgets."""
from __future__ import annotations
import os, struct, re, webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from app.gui.styles import MONO_FONT, SANS_FONT

class HelpAboutMixin:
    def build_help_about_interface(self):
        palette = self.get_theme_palette()
        page_bg = palette["selected"]
        base_bg = palette["base"]
        outer = tk.Frame(self.tab_help_about, bg=base_bg)
        outer.pack(fill="both", expand=True, padx=8, pady=8)

        self.help_about_notebook = ttk.Notebook(outer, style="Sub.TNotebook")
        self.help_about_notebook.pack(fill="both", expand=True)
        help_tab = tk.Frame(self.help_about_notebook, bg=page_bg)
        about_tab = tk.Frame(self.help_about_notebook, bg=page_bg)
        translation_tab = tk.Frame(self.help_about_notebook, bg=base_bg)
        self.help_about_notebook.add(help_tab, text=self.tr("Help"))
        self.help_about_notebook.add(about_tab, text=self.tr("About"))
        self.help_about_notebook.add(translation_tab, text=self._translation_ui("tab"))

        self.help_text = self._create_markdown_view(help_tab, "help")
        self.about_text = self._create_markdown_view(about_tab, "about")
        self.translation_tab = translation_tab
        self._translation_editor_initialized = False
        # Render each document only when it is first shown (not at startup or after a
        # language change), so images are not decoded for pages nobody opens.
        self._help_documents_rendered = {"help": False, "about": False}
        self.apply_translation_theme()
        self.help_about_notebook.bind("<<NotebookTabChanged>>", self._render_visible_help_document, add="+")

        # Keep mouse-wheel scrolling inside the active document rather than
        # moving the application's outer canvas.
        for text_widget in (self.help_text, self.about_text):
            text_widget.bind("<Button-4>", lambda _e, widget=text_widget: self._scroll_markdown(widget, -3))
            text_widget.bind("<Button-5>", lambda _e, widget=text_widget: self._scroll_markdown(widget, 3))
            text_widget.bind("<MouseWheel>", lambda event, widget=text_widget: self._on_markdown_mousewheel(event, widget))

        self.help_about_notebook.select(help_tab)

    def _render_visible_help_document(self, _event=None):
        """Render the Help or About document the first time its tab is actually visible."""
        try:
            if getattr(self, "active_workspace", None) != "help":
                return
            rendered = self._help_documents_rendered
            sub_index = self.help_about_notebook.index(self.help_about_notebook.select())
            if sub_index == 2:
                # Build the translation editor only when its tab is opened.
                # Avoid creating hundreds of Text widgets during normal startup or
                # every global-language rebuild.
                if not getattr(self, "_translation_editor_initialized", False):
                    self.build_translation_editor_interface(self.translation_tab)
                    self._translation_editor_initialized = True
                return
            key = "help" if sub_index == 0 else "about"
            if rendered.get(key):
                return
            rendered[key] = True
            # Let Tk finish laying out the tab so the real widget width is known for image sizing.
            self.root.update_idletasks()
            if key == "help":
                self._load_and_render_help()
            else:
                self._load_and_render_about()
        except tk.TclError:
            pass

    def _create_markdown_view(self, parent, document_name):
        frame = tk.Frame(parent, bg=parent.cget("background"))
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        text_widget = tk.Text(
            frame, wrap="word", height=1, undo=False, padx=14, pady=12,
            bg="#202124", fg="#eeeeee", insertbackground="#ffffff",
            selectbackground="#356b50", relief="flat", borderwidth=0,
            font=(SANS_FONT, 12), spacing1=1, spacing3=3,
        )
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text_widget.pack(side="left", fill="both", expand=True)
        self._apply_markdown_theme_to_widget(text_widget)
        return text_widget

    def _apply_markdown_theme_to_widget(self, text_widget):
        """Apply semantic text colours to Markdown tags for the active theme."""
        palette = self.get_theme_palette()
        text_widget.tag_configure("h1", font=(SANS_FONT, 26, "bold"), foreground=palette["accent"], spacing1=8, spacing3=8)
        text_widget.tag_configure("h2", font=(SANS_FONT, 22, "bold"), foreground=palette["accent"], spacing1=12, spacing3=5)
        text_widget.tag_configure("h3", font=(SANS_FONT, 18, "bold"), foreground=palette["text"], spacing1=8, spacing3=3)
        text_widget.tag_configure("h4", font=(SANS_FONT, 15, "bold"), foreground=palette["text"], spacing1=8, spacing3=3)
        text_widget.tag_configure("h5", font=(SANS_FONT, 13, "bold"), foreground=palette["text"], spacing1=8, spacing3=3)
        text_widget.tag_configure("bold", font=(SANS_FONT, 12, "bold"), foreground=palette["text"])
        text_widget.tag_configure("italic", font=(SANS_FONT, 12, "italic"))
        text_widget.tag_configure("inline_code", font=(MONO_FONT, 10), foreground=palette["code_text"], background=palette["code"])
        text_widget.tag_configure("bullet", foreground=palette["accent"])
        text_widget.tag_configure("hr", foreground=palette["muted"])
        text_widget.tag_configure("md_link", foreground=palette["accent"], underline=True)
        text_widget.tag_configure("fallback_notice", foreground=palette["code_text"], font=(SANS_FONT, 10, "italic"))
        text_widget.tag_configure("md_caption", foreground=palette["muted"], font=(SANS_FONT, 10, "italic"))
        text_widget.tag_configure("align_center", justify="center")
        text_widget.tag_configure("align_right", justify="right")

    def apply_help_theme(self):
        """Refresh Help, About, and translation-editor styling after a theme change."""
        for widget_name in ("help_text", "about_text"):
            text_widget = getattr(self, widget_name, None)
            if text_widget is not None and text_widget.winfo_exists():
                self._apply_markdown_theme_to_widget(text_widget)
        if hasattr(self, "apply_translation_theme"):
            self.apply_translation_theme()

    def _scroll_markdown(self, text_widget, units):
        text_widget.yview_scroll(units, "units")
        return "break"

    def _on_markdown_mousewheel(self, event, text_widget):
        delta = getattr(event, "delta", 0)
        if delta:
            units = -int(delta / 120)
            if units == 0:
                units = -1 if delta > 0 else 1
            text_widget.yview_scroll(units * 3, "units")
        return "break"

    def _load_and_render_help(self):
        self._load_and_render_markdown(self.help_text, self.help_dir, "Help", "help")

    def _load_and_render_about(self):
        self._load_and_render_markdown(self.about_text, self.about_dir, "About", "about")

    def _load_and_render_markdown(self, text_widget, document_dir, document_name, document_key):
        path = os.path.abspath(os.path.join(document_dir, f"{self.language_code}.md"))
        used_fallback = False
        try:
            with open(path, "r", encoding="utf-8") as document_file:
                markdown = document_file.read()
        except (OSError, UnicodeError):
            used_fallback = self.language_code != "en"
            path = os.path.abspath(os.path.join(document_dir, "en.md"))
            try:
                with open(path, "r", encoding="utf-8") as document_file:
                    markdown = document_file.read()
            except (OSError, UnicodeError):
                markdown = f"# Audio-SWARM {document_name}\n\nThe {document_name.lower()} document could not be loaded."

        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        if used_fallback:
            notice = f"The {document_name.lower()} file for this language is not available; English {document_name.lower()} is shown.\n\n"
            text_widget.insert("end", notice, ("fallback_notice",))

        # FIX: Standardize a persistent global class dictionary reference for holding images
        if not hasattr(self, "global_help_image_cache"):
            self.global_help_image_cache = {}
        if document_key not in self.global_help_image_cache:
            self.global_help_image_cache[document_key] = []
        
        # Clear old references for this tab to prevent memory leaks on language reload
        self.global_help_image_cache[document_key].clear()

        link_counter = 0
        for raw_line in markdown.splitlines():
            anchor_match = re.search(r"\s*<!--\s*anchor:\s*([A-Za-z0-9_-]+)\s*-->\s*$", raw_line)
            line = re.sub(r"\s*<!--\s*anchor:\s*[A-Za-z0-9_-]+\s*-->\s*$", "", raw_line).rstrip()
            image_match = re.match(r"^\s*!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)\s*$", line)
            heading = re.match(r"^(#{1,5})\s+(.*)$", line)
            if image_match:
                self._insert_markdown_image(
                    text_widget, os.path.dirname(path), document_key,
                    image_match.group(1), image_match.group(2), image_match.group(3) or "",
                )
            elif heading:
                level = len(heading.group(1))
                heading_text = heading.group(2).strip()
                if anchor_match:
                    anchor_name = anchor_match.group(1)
                    text_widget.mark_set(f"section_{anchor_name}", "end-1c" if text_widget.compare("end", ">", "1.0") else "1.0")
                    text_widget.mark_gravity(f"section_{anchor_name}", "left")
                link_counter = self._insert_markdown_inline(text_widget, heading_text, document_key, link_counter)
                text_widget.insert("end", "\n", (f"h{level}",))
                heading_start = text_widget.index("end-2c linestart")
                heading_end = text_widget.index("end-1c")
                text_widget.tag_add(f"h{level}", heading_start, heading_end)
            elif not line.strip():
                text_widget.insert("end", "\n")
            elif re.match(r"^\s*(---+|\*\*\*+|___+)\s*$", line):
                text_widget.insert("end", "────────────────────────────────────────────────────\n", ("hr",))
            elif re.match(r"^\s*[-*]\s+", line):
                text_widget.insert("end", "  • ", ("bullet",))
                link_counter = self._insert_markdown_inline(text_widget, re.sub(r"^\s*[-*]\s+", "", line), document_key, link_counter)
                text_widget.insert("end", "\n")
            elif re.match(r"^\s*\d+\.\s+", line):
                prefix = re.match(r"^\s*(\d+\.\s+)(.*)$", line)
                text_widget.insert("end", "  " + prefix.group(1))
                link_counter = self._insert_markdown_inline(text_widget, prefix.group(2), document_key, link_counter)
                text_widget.insert("end", "\n")
            else:
                link_counter = self._insert_markdown_inline(text_widget, line, document_key, link_counter)
                text_widget.insert("end", "\n")
        text_widget.configure(state="disabled")
        text_widget.yview_moveto(0)

    def _resolve_markdown_image_path(self, document_dir, target):
        """Resolve images from the project root beside main.py and the loaded document.

        This module lives in <project-root>/app/gui, so parents[2] is the root
        containing main.py and the sibling help/images directory. The path is
        independent of the process working directory and the currently loaded GUI
        submodule.
        """
        from urllib.parse import unquote

        target = unquote(target.strip().strip("<>"))
        if not target or re.match(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)", target):
            return None

        # Absolute local paths are allowed, but remote URLs are intentionally not loaded.
        if os.path.isabs(target):
            candidate = os.path.abspath(os.path.normpath(target))
            return candidate if os.path.isfile(candidate) else None

        # Anchor resolution to the project root containing main.py, never to
        # the process working directory. In a normal source checkout this is
        # two levels above app/gui/help_about.py; walk upward as a fallback so
        # the same code also works if the package layout is nested differently.
        module_root = Path(__file__).resolve().parent
        app_root = next((parent for parent in (module_root, *module_root.parents)
                         if (parent / "main.py").is_file()),
                        Path(__file__).resolve().parents[2])
        app_root = str(app_root)
        help_root = os.path.join(app_root, "help")
        help_images_root = os.path.join(help_root, "images")
        document_dir = os.path.abspath(document_dir)

        # Markdown currently uses paths such as images/example.png. Also support
        # a bare filename that lives directly in help/images/.
        normalized_target = target.replace("\\", os.sep).replace("/", os.sep)
        candidates = []
        if normalized_target.lower().startswith(f"images{os.sep}".lower()):
            candidates.append(os.path.join(help_root, normalized_target))
            candidates.append(os.path.join(help_images_root, normalized_target[len("images" + os.sep):]))
        else:
            candidates.append(os.path.join(help_images_root, normalized_target))
            candidates.append(os.path.join(document_dir, normalized_target))
        candidates.extend((
            os.path.join(help_root, normalized_target),
            os.path.join(app_root, normalized_target),
            os.path.join(app_root, "img", normalized_target),
        ))
        seen = set()
        for candidate_path in candidates:
            candidate = os.path.abspath(os.path.normpath(candidate_path))
            if candidate in seen:
                continue
            seen.add(candidate)
            if os.path.isfile(candidate):
                return candidate
        return None

    def _parse_markdown_image_options(self, option_text, alt_text):
        """Read the quoted title of an image line: width=, height=, align=, caption[=text].

        Example: ![Main window](main.png "width=50% height=300 align=center caption=The main window")
        'caption' must be last; everything after 'caption=' is the caption text. A bare
        'caption' (or 'caption=alt') uses the alt text as the caption.
        """
        options = {"width": None, "height": None, "align": "left", "caption": ""}
        text = option_text.strip()
        caption_match = re.search(r"(?:^|\s)caption(?:\s*=\s*(.*))?$", text, re.IGNORECASE | re.DOTALL)
        if caption_match:
            caption = (caption_match.group(1) or "").strip()
            options["caption"] = alt_text.strip() if caption.lower() in ("", "alt") else caption
            text = text[:caption_match.start()].strip()
        for key, value in re.findall(r"(\w+)\s*=\s*(\S+)", text):
            key = key.lower()
            if key in ("width", "height"):
                number = re.match(r"^(\d+(?:\.\d+)?)(%|px)?$", value.lower())
                if number:
                    options[key] = (float(number.group(1)), number.group(2) == "%")
            elif key == "align" and value.lower() in ("left", "center", "right"):
                options["align"] = value.lower()
        return options

    def _markdown_image_scale(self, native_width, native_height, max_width, width=None, height=None):
        """Scale factor for an image (None = keep its size). Explicit sizes may enlarge; the window width caps it."""
        scale = None
        if width or height:
            candidates = []
            if width:
                candidates.append(width / native_width)
            if height:
                candidates.append(height / native_height)
            scale = min(candidates)
        if native_width * (scale or 1.0) > max_width:
            scale = max_width / native_width
        return scale

    def _png_native_size(image_path):
        """Read a PNG's width and height from its header without decoding it; None if not a PNG."""
        try:
            with open(image_path, "rb") as image_file:
                header = image_file.read(24)
            if len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR":
                return struct.unpack(">II", header[16:24])
        except OSError:
            pass
        return None

    def _prepare_markdown_image_data(self, image_path, max_width, width=None, height=None):
        """Process help images using raw PIL pipeline references to bypass format crashes."""
        try:
            from PIL import Image, ImageTk
            with Image.open(image_path) as source:
                prepared = source.convert("RGBA")
                try:
                    # FIX: Added required self routing parameter check context
                    scale = self._markdown_image_scale(prepared.width, prepared.height, max_width, width, height)
                    if scale is not None and abs(scale - 1.0) > 1e-6:
                        new_size = (max(1, round(prepared.width * scale)), max(1, round(prepared.height * scale)))
                        resized = prepared.resize(new_size, Image.Resampling.LANCZOS)
                        prepared.close()
                        prepared = resized
                    return ImageTk.PhotoImage(prepared)
                finally:
                    if 'prepared' in locals() and prepared is not source:
                        prepared.close()
        except (OSError, ValueError, tk.TclError):
            return None

    def _insert_markdown_image(self, text_widget, document_dir, document_key, alt_text, target, option_text=""):
        options = self._parse_markdown_image_options(option_text, alt_text)
        try:
            image_path = self._resolve_markdown_image_path(document_dir, target)
            if image_path is None:
                raise FileNotFoundError(target)
            widget_width = text_widget.winfo_width()
            max_width = max(240, min(1200, widget_width - 50)) if widget_width > 120 else 640

            def to_pixels(spec, reference):
                if spec is None:
                    return None
                amount, is_percent = spec
                return max(1, round(reference * amount / 100.0 if is_percent else amount))

            width_px = to_pixels(options["width"], max_width)
            height_px = to_pixels(options["height"], max_width)
            
            # FIX: Force load via Pillow pipeline to prevent Tkinter image formatting errors
            photo = self._prepare_markdown_image_data(image_path, max_width, width_px, height_px)
            if photo is None:
                raise ValueError("unsupported image configuration")
        except (OSError, ValueError, tk.TclError):
            label = alt_text.strip() or target
            text_widget.insert("end", f"[image not available: {label}]\n", ("fallback_notice",))
            return

        # Pinned instance dictionary cache mapping
        self.global_help_image_cache[document_key].append(photo)
        
        align_tag = {"center": "align_center", "right": "align_right"}.get(options["align"])
        text_widget.insert("end", "\n")
        line_start = text_widget.index("end-1c linestart")
        text_widget.image_create("end", image=photo, padx=4, pady=4)
        text_widget.insert("end", "\n")
        if align_tag:
            text_widget.tag_add(align_tag, line_start, "end-1c")
        if options["caption"]:
            caption_start = text_widget.index("end-1c linestart")
            tags = ("md_caption", align_tag) if align_tag else ("md_caption",)
            text_widget.insert("end", options["caption"] + "\n", tags)

    def _insert_markdown_inline(self, text_widget, text, document_key, link_counter):
        token_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|(?<!\*)\*([^*]+)\*(?!\*)|`([^`]+)`")
        pos = 0
        for match in token_pattern.finditer(text):
            if match.start() > pos:
                text_widget.insert("end", text[pos:match.start()])
            if match.group(1) is not None:
                label, target = match.group(1), match.group(2).strip()
                link_counter += 1
                tag = f"{document_key}_link_{link_counter}"
                text_widget.insert("end", label, ("md_link", tag))
                text_widget.tag_bind(tag, "<Button-1>", lambda _event, widget=text_widget, destination=target: self._activate_markdown_link(widget, destination))
                text_widget.tag_bind(tag, "<Enter>", lambda _event, widget=text_widget: widget.configure(cursor="hand2"))
                text_widget.tag_bind(tag, "<Leave>", lambda _event, widget=text_widget: widget.configure(cursor="xterm"))
            elif match.group(3) is not None:
                text_widget.insert("end", match.group(3), ("bold",))
            elif match.group(4) is not None:
                text_widget.insert("end", match.group(4), ("italic",))
            elif match.group(5) is not None:
                text_widget.insert("end", match.group(5), ("inline_code",))
            pos = match.end()
        if pos < len(text):
            text_widget.insert("end", text[pos:])
        return link_counter

    def _activate_markdown_link(self, text_widget, target):
        if target.startswith("#"):
            anchor = target[1:]
            mark = f"section_{anchor}"
            try:
                index = text_widget.index(mark)
                text_widget.see(index)
                text_widget.mark_set("insert", index)
                return "break"
            except tk.TclError:
                return "break"
        if target.startswith(("https://", "http://", "mailto:")):
            webbrowser.open(target)
        return "break"

    def _scroll_help(self, units):
        return self._scroll_markdown(self.help_text, units)

    def _on_help_mousewheel(self, event):
        return self._on_markdown_mousewheel(event, self.help_text)

    def _activate_help_link(self, target):
        return self._activate_markdown_link(self.help_text, target)
