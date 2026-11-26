"""Tkinter translation editor, kept separate from the application's core UI."""
from __future__ import annotations



import json
import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk


from app.localization_tool.translation_engine import TranslationEngine
from app.localization_tool.translation_languages import LANGUAGES
from app.localization_tool.translation_project import read_registry, register_project
from app.localization_tool.translation_feedback import show_feedback



class TranslationEditorMixin:
    """Translation workspace. Source strings are immutable; target strings are editable."""

    def _translation_ui(self, key):
        """Resolve legacy Translation tab keys through the shared JSON catalog."""
        legacy_keys = {
            "tab": "Translation",
            "project": "Translation project:",
            "new": "New Translation",
            "save": "Save Translation",
            "reload": "Reload GUI",
            "from": "Translate from:",
            "to": "Translate to:",
            "cancel": "Cancel",
            "ok": "OK",
            "choose": "Choose both source and target languages.",
            "different": "Source and target languages must differ.",
            "select_project": "Create or select a translation project first.",
            "select_reload": "Select a translation project first.",
            "created": "Translation project created: {source} → {target}",
            "opened": "Translation project opened: {source} → {target}",
            "saved": "Translation saved: {target}",
            "empty": "Some entries are empty: {count}",
            "reload_ok": "GUI language: {language}",
            "load_error": "Could not load project: {error}",
            "create_error": "Could not create project: {error}",
            "save_error": "Unable to save translation: {error}",
            "invalid": "Translation file is invalid: {error}",
            "not_saved": "Translation file does not exist. Save it first.",
            "source": "Source language",
            "target": "Target language",
        }
        return self.tr(legacy_keys.get(key, key))


    def build_translation_editor_interface(self, parent):
        palette = self.get_theme_palette()
        self.translation_parent = parent
        self.translation_engine = TranslationEngine(self.language_dir)
        self.translation_projects, self.translation_active = read_registry(self.settings_path)
        self.translation_rows = []
        self.translation_source_code = None
        self.translation_target_code = None
        self.translation_editing_index = None
        self.translation_editing_side = None


        frame = tk.Frame(parent, bg=palette["base"])
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        top = tk.Frame(frame, bg=palette["base"])
        top.pack(fill="x", pady=(0, 7))
        tk.Label(top, text=self.tr('Translation project:'), bg=palette["base"],
                fg=palette["text"]).pack(side="left", padx=(2, 6))
        self.translation_project_menu = ttk.Combobox(top, state="readonly", width=30)
        self.translation_project_menu.pack(side="left", fill="x", expand=True)
        self.translation_project_menu.bind("<<ComboboxSelected>>", self._translation_project_selected)


        columns = tk.Frame(frame, bg=palette["base"])
        columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=1, uniform="translation")
        columns.grid_columnconfigure(1, weight=1, uniform="translation")
        columns.grid_rowconfigure(1, weight=1)
        self.translation_columns = columns
        self.translation_source_header = tk.Label(columns, text=self.tr('Source language'),
            bg=palette["selected"], fg=palette["text"], anchor="w", padx=8, pady=5)
        self.translation_target_header = tk.Label(columns, text=self.tr('Target language'),
            bg=palette["selected"], fg=palette["text"], anchor="w", padx=8, pady=5)
        self.translation_source_header.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self.translation_target_header.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        scroller = tk.Frame(columns, bg=palette["base"])
        scroller.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(5, 0))
        self.translation_canvas = tk.Canvas(scroller, bg=palette["field"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroller, orient="vertical", command=self.translation_canvas.yview)
        self.translation_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.translation_canvas.pack(side="left", fill="both", expand=True)
        self.translation_canvas.bind("<Configure>", self._render_translation_rows)
        self.translation_canvas.bind("<Button-1>", self._translation_canvas_click)
        self.translation_canvas.bind("<MouseWheel>", self._translation_mousewheel)
        self.translation_canvas.bind("<Button-4>", lambda e: self._translation_mousewheel(e, -1))
        self.translation_canvas.bind("<Button-5>", lambda e: self._translation_mousewheel(e, 1))

        self.translation_source_editor = tk.Text(self.translation_canvas, wrap="word", padx=6, pady=4,
            borderwidth=0, relief="flat", font=("TkDefaultFont", 10), takefocus=1)
        self.translation_target_editor = tk.Text(self.translation_canvas, wrap="word", padx=6, pady=4,
            borderwidth=0, relief="flat", font=("TkDefaultFont", 10), undo=True, takefocus=1)
        self.translation_source_window = self.translation_canvas.create_window(
            (0, 0), window=self.translation_source_editor, anchor="nw", state="hidden")
        self.translation_target_window = self.translation_canvas.create_window(
            (0, 0), window=self.translation_target_editor, anchor="nw", state="hidden")
        self.translation_source_editor.bind("<FocusOut>", self._close_translation_overlay)
        self.translation_source_editor.bind("<KeyPress>", self._source_editor_key)
        self.translation_source_editor.bind("<Control-a>", self._source_select_all)
        self.translation_target_editor.bind("<FocusOut>", self._close_translation_overlay)
        self.translation_source_editor.bind("<MouseWheel>", self._translation_mousewheel)
        self.translation_target_editor.bind("<MouseWheel>", self._translation_mousewheel)
        self.translation_source_editor.bind("<Button-4>", lambda e: self._translation_mousewheel(e, -1))
        self.translation_source_editor.bind("<Button-5>", lambda e: self._translation_mousewheel(e, 1))
        self.translation_target_editor.bind("<Button-4>", lambda e: self._translation_mousewheel(e, -1))
        self.translation_target_editor.bind("<Button-5>", lambda e: self._translation_mousewheel(e, 1))
        self.translation_target_editor.bind("<KeyRelease>", self._translation_editor_key)
        self.translation_target_editor.bind("<Control-Return>", self._commit_translation_edit)
        self.translation_source_editor.bind("<Control-Return>", self._close_translation_overlay)

        actions = tk.Frame(frame, bg=palette["base"])
        actions.pack(fill="x", pady=(7, 0))
        specs = [("New Translation", self.open_new_translation_dialog, "preview"),
                 ("Save Translation", self.save_translation, "generate"),
                 ("Reload GUI", self.reload_with_translation, "stop")]
        self.translation_buttons = []
        for label, command, role in specs:
            button = self.create_action_button(actions, self.tr(label), command, role)
            button.pack(side="left", fill="x", expand=True, padx=3)
            self.translation_buttons.append(button)
        self._refresh_translation_project_menu()
        self._translation_project_selected()
        self.apply_translation_theme()



    def _translation_mousewheel(self, event, direction=None):
        if direction is None:
            delta = getattr(event, "delta", 0)
            direction = -1 if delta > 0 else 1
        self.translation_canvas.yview_scroll(direction * 3, "units")
        return "break"



    def _refresh_translation_project_menu(self):
        self.translation_project_labels = {}
        labels = []
        for project in self.translation_projects:
            source, target = project.get("source", ""), project.get("target", "")
            source_name = self.available_languages.get(source, source)
            target_name = LANGUAGES.get(target, target)
            label = f"{source_name} → {target_name} ({source} → {target})"
            labels.append(label)
            self.translation_project_labels[label] = (source, target)
        self.translation_project_menu.configure(values=labels)
        active_label = None
        if self.translation_active:
            pair = (self.translation_active.get("source"), self.translation_active.get("target"))
            active_label = next((name for name, value in self.translation_project_labels.items()
                             if value == pair), None)
        active_label = active_label or (labels[-1] if labels else "")
        self.translation_project_menu.set(active_label)



    def _translation_project_selected(self, _event=None):
        pair = self.translation_project_labels.get(self.translation_project_menu.get())
        if not pair:
            self.translation_source_code = self.translation_target_code = None
            self._clear_translation_rows()
            return
        source_code, target_code = pair
        self.translation_source_code, self.translation_target_code = source_code, target_code
        self.translation_source_header.configure(
            text=f"{self.available_languages.get(source_code, source_code)} ({source_code})")
        self.translation_target_header.configure(
            text=f"{LANGUAGES.get(target_code, target_code)} ({target_code})")
        try:
            rows = self.translation_engine.build_rows(source_code, target_code)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self._clear_translation_rows()
            self._translation_feedback(self.tr('Could not load project: {error}').format(error=exc), "error")
            return
        self._populate_translation_rows(rows)
        self.translation_active = {"source": source_code, "target": target_code}



    def _clear_translation_rows(self):
        self.translation_rows = []
        if hasattr(self, "translation_canvas") and self.translation_canvas.winfo_exists():
            self.translation_canvas.delete("row_item")
            self.translation_canvas.configure(scrollregion=(0, 0, 0, 0))
            self.translation_canvas.yview_moveto(0)
            self._hide_translation_overlays()
        self.translation_editing_index = None
        self.translation_editing_side = None



    def _populate_translation_rows(self, rows):
        self._commit_translation_edit()
        self.translation_rows = [{"key": key, "source": source, "target": target,
                                "y": 0, "height": 0, "source_lines": 1, "target_lines": 1}
                               for key, source, target in rows]
        self._render_translation_rows()
        self.translation_canvas.yview_moveto(0)



    @staticmethod
    def _translation_wrapped_lines(text, font, max_width):
        """Estimate wrapped visual lines using Tk font measurements, not character counts."""
        result = 0
        for raw_line in str(text).split("\n"):
            if not raw_line:
                result += 1
                continue
            words = raw_line.split(" ")
            current = ""
            for word in words:
                candidate = word if not current else current + " " + word
                if current and font.measure(candidate) > max_width:
                    result += 1
                    current = word
                else:
                    current = candidate
            result += 1
        return max(1, result)



    @staticmethod
    def _translation_adjust_color(color, amount):
        """Change field luminosity slightly while keeping the same hue."""
        color = color.lstrip("#")
        try:
            rgb = [int(color[i:i + 2], 16) for i in (0, 2, 4)]
        except (ValueError, IndexError):
            return "#333333"
        rgb = [max(0, min(255, component + amount)) for component in rgb]
        return "#" + "".join(f"{component:02x}" for component in rgb)



    def _render_translation_rows(self, _event=None):
        canvas = getattr(self, "translation_canvas", None)
        if canvas is None or not canvas.winfo_exists():
            return
        canvas.delete("row_item")
        palette = self.get_theme_palette()
        width = max(240, canvas.winfo_width())
        column_width = max(100, (width - 8) // 2)
        text_width = max(60, column_width - 20)
        font = tkfont.Font(font=("TkDefaultFont", 10))
        line_height = font.metrics("linespace") + 8
        target_bg = self._translation_adjust_color(palette["field"],
            9 if self.theme_name in ("Dark", "Gray") else -7)
        y = 0
        for row in self.translation_rows:
            heading = bool(row["key"] and (row["key"].startswith(" ") or row["key"].endswith(" ")))
            if heading:
                y += 7
            source_lines = self._translation_wrapped_lines(row["source"], font, text_width)
            target_lines = self._translation_wrapped_lines(row["target"], font, text_width)
            height = max(source_lines, target_lines, 2) * line_height + 8
            row.update(y=y, height=height, source_lines=source_lines, target_lines=target_lines)
            canvas.create_rectangle(2, y, column_width - 2, y + height,
                fill=palette["field"], outline=palette["border"], width=1, tags=("row_item",))
            canvas.create_rectangle(column_width + 2, y, width - 2, y + height,
                fill=target_bg, outline=palette["border"], width=1, tags=("row_item",))
            canvas.create_text(9, y + 4, anchor="nw", text=row["source"], width=text_width,
                fill=palette["text"], font=font, tags=("row_item",))
            canvas.create_text(column_width + 9, y + 4, anchor="nw", text=row["target"], width=text_width,
                fill=palette["text"], font=font, tags=("row_item",))
            y += height + (5 if heading else 2)
        canvas.configure(scrollregion=(0, 0, width, max(y, canvas.winfo_height())))
        if self.translation_editing_index is not None:
            self._position_translation_overlay(self.translation_editing_index,
                                            self.translation_editing_side)



    def _translation_canvas_click(self, event):
        if not self.translation_rows:
            return
        x = self.translation_canvas.canvasx(event.x)
        y = self.translation_canvas.canvasy(event.y)
        width = max(240, self.translation_canvas.winfo_width())
        side = "source" if x < width / 2 else "target"
        for index, row in enumerate(self.translation_rows):
            if row["y"] <= y <= row["y"] + row["height"]:
                self._open_translation_overlay(index, side)
                return



    def _hide_translation_overlays(self):
        for item in (getattr(self, "translation_source_window", None),
                    getattr(self, "translation_target_window", None)):
            if item is not None:
                try:
                    self.translation_canvas.itemconfigure(item, state="hidden")
                except tk.TclError:
                    pass



    def _open_translation_overlay(self, index, side):
        self._commit_translation_edit()
        if not (0 <= index < len(self.translation_rows)):
            return
        self.translation_editing_index = index
        self.translation_editing_side = side
        editor = self.translation_source_editor if side == "source" else self.translation_target_editor
        value = self.translation_rows[index][side]
        editor.configure(state="normal", wrap="word")
        editor.delete("1.0", "end")
        editor.insert("1.0", value)
        self._position_translation_overlay(index, side)
        editor.focus_set()
        if side == "target":
            editor.mark_set("insert", "end-1c")



    def _position_translation_overlay(self, index, side):
        if side not in ("source", "target") or index >= len(self.translation_rows):
            return
        row = self.translation_rows[index]
        canvas_width = max(240, self.translation_canvas.winfo_width())
        col_width = max(100, (canvas_width - 8) // 2)
        window = self.translation_source_window if side == "source" else self.translation_target_window
        widget = self.translation_source_editor if side == "source" else self.translation_target_editor
        x = 4 if side == "source" else col_width + 4
        widget_bg = self.get_theme_palette()["field"]
        if side == "target":
            widget_bg = self._translation_adjust_color(widget_bg,
                9 if self.theme_name in ("Dark", "Gray") else -7)
        widget.configure(bg=widget_bg, fg=self.get_theme_palette()["text"],
            insertbackground=self.get_theme_palette()["text"])
        self.translation_canvas.coords(window, x, row["y"] + 2)
        self.translation_canvas.itemconfigure(window, width=col_width - 8,
            height=max(30, row["height"] - 4), state="normal")
        widget.lift()



    def _source_editor_key(self, event):
        """Keep the source overlay selectable/copyable but prevent text edits."""
        control_pressed = bool(event.state & 0x4)
        if control_pressed and event.keysym.lower() in ("c", "a"):
            return None
        return "break"



    def _source_select_all(self, _event=None):
        self.translation_source_editor.tag_add("sel", "1.0", "end-1c")
        self.translation_source_editor.mark_set("insert", "end-1c")
        return "break"



    def _translation_editor_key(self, _event=None):
        index = self.translation_editing_index
        if index is None or self.translation_editing_side != "target":
            return
        self.translation_rows[index]["target"] = self.translation_target_editor.get("1.0", "end-1c")
        self._render_translation_rows()
        self._position_translation_overlay(index, "target")



    def _commit_translation_edit(self, _event=None):
        index = getattr(self, "translation_editing_index", None)
        side = getattr(self, "translation_editing_side", None)
        if index is not None and side == "target" and index < len(self.translation_rows):
            self.translation_rows[index]["target"] = self.translation_target_editor.get("1.0", "end-1c")
        self._hide_translation_overlays()
        self.translation_editing_index = None
        self.translation_editing_side = None
        self._render_translation_rows()
        return "break"



    def _close_translation_overlay(self, _event=None):
        self._commit_translation_edit()
        return "break"



    def open_new_translation_dialog(self):
        palette = self.get_theme_palette()
        dialog = tk.Toplevel(self.root)
        dialog.title(self.tr('New Translation'))
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.configure(bg=palette["base"])
        dialog.grab_set()
        frame = tk.Frame(dialog, bg=palette["base"], padx=14, pady=12)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=self.tr('Translate from:'), bg=palette["base"],
                fg=palette["text"]).grid(row=0, column=0, sticky="w", pady=(0, 4))
        source_by_display = {name: code for code, name in self.available_languages.items()}
        source_combo = ttk.Combobox(frame, state="readonly", width=36,
            values=list(self.available_languages.values()))
        source_combo.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        source_combo.set(self.available_languages.get("en", "English"))
        tk.Label(frame, text=self.tr('Translate to:'), bg=palette["base"],
                fg=palette["text"]).grid(row=2, column=0, sticky="w", pady=(0, 4))
        target_values = [f"{name} ({code})" for code, name in sorted(
            LANGUAGES.items(), key=lambda item: item[1].casefold())]
        target_combo = ttk.Combobox(frame, state="readonly", width=36, values=target_values)
        target_combo.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        target_combo.set("")
        buttons = tk.Frame(frame, bg=palette["base"])
        buttons.grid(row=4, column=0, sticky="e")
        result = {"source": None, "target": None}

        def confirm():
            source = source_by_display.get(source_combo.get())
            selected = target_combo.get()
            target = selected.rsplit("(", 1)[-1].rstrip(")") if selected else None
            if not source or not target:
                self._translation_feedback(self.tr('Choose both source and target languages.'), "warning")
                return
            if source == target:
                self._translation_feedback(self.tr('Source and target languages must differ.'), "warning")
                return
            result.update(source=source, target=target)
            dialog.destroy()

        cancel = tk.Button(buttons, text=self.tr('Cancel'), command=dialog.destroy,
            bg=palette["panel"], fg=palette["text"], activebackground=palette["hover"],
            relief="flat", padx=12, pady=6)
        ok = tk.Button(buttons, text=self.tr('OK'), command=confirm,
            bg=palette["accent"], fg="#ffffff", activebackground=palette["hover"],
            relief="flat", padx=12, pady=6)
        cancel.pack(side="left", padx=(0, 6))
        ok.pack(side="left")
        dialog.bind("<Return>", lambda _e: confirm())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.root.wait_window(dialog)
        if result["source"] and result["target"]:
            self._create_translation_project(result["source"], result["target"])



    def _create_translation_project(self, source_code, target_code):
        source_name = self.available_languages.get(source_code, source_code)
        target_name = LANGUAGES.get(target_code, target_code)
        target_path = self.translation_engine.catalog_path(target_code)
        catalog_created = False
        registry_saved = False
        try:
            catalog, catalog_created = self.translation_engine.create_target_catalog(
                target_code, target_name, source_code)
            register_project(self.settings_path, source_code, target_code)
            registry_saved = True
            self.available_languages[target_code] = target_name
            self.translation_projects, self.translation_active = read_registry(self.settings_path)
            self._refresh_translation_project_menu()
            label = next((name for name, pair in self.translation_project_labels.items()
                         if pair == (source_code, target_code)), "")
            if label:
                self.translation_project_menu.set(label)
            self._translation_project_selected()
            status_text = "Translation project created: {source} → {target}" if catalog_created else "Translation project opened: {source} → {target}"
            message = self.tr(status_text).format(source=source_name, target=target_name)
            self._translation_feedback(message, "success")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            if catalog_created and not registry_saved and os.path.isfile(target_path):
                try:
                    os.remove(target_path)
                except OSError:
                    pass
            self._translation_feedback(self.tr('Could not create project: {error}').format(error=exc), "error")



    def save_translation(self):
        if not self.translation_source_code or not self.translation_target_code:
            self._translation_feedback(self.tr('Create or select a translation project first.'), "warning")
            return
        try:
            self._commit_translation_edit()
            catalog = self.translation_engine.target_catalog(self.translation_target_code)
            if not catalog:
                self._translation_feedback(self.tr('Translation file does not exist. Save it first.'), "warning")
                return
            empty_count = 0
            for row in self.translation_rows:
                catalog[row["key"]] = row["target"]
                empty_count += int(not row["target"].strip())
            self.translation_engine.write_catalog(self.translation_target_code, catalog)
            message = self.tr('Translation saved: {target}').format(target=f"{self.translation_target_code}.json")
            level = "success"
            if empty_count:
                message += " · " + self.tr('Some entries are empty: {count}').format(count=empty_count)
                level = "warning"
            self._translation_feedback(message, level)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self._translation_feedback(self.tr('Unable to save translation: {error}').format(error=exc), "error")



    def reload_with_translation(self):
        target_code = self.translation_target_code
        if not target_code:
            self._translation_feedback(self.tr('Select a translation project first.'), "warning")
            return
        try:
            self.translation_engine.read_catalog(target_code)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self._translation_feedback(self.tr('Translation file is invalid: {error}').format(error=exc), "error")
            return
        self.available_languages = self.discover_languages()
        self.load_language(target_code)
        self.save_settings()
        self.root.title(self.tr("Audio-SWARM — Audio Waveform & Artwork Studio"))
        for child in self.root.winfo_children():
            child.destroy()
        self.setup_ui_layout()
        self._translation_feedback(self.tr('GUI language: {language}').format(
            language=LANGUAGES.get(target_code, target_code)), "success")



    def _translation_feedback(self, message, level="success"):
        show_feedback(getattr(self, "status_label", None), self.get_theme_palette(), message, level)



    def apply_translation_theme(self):
        if not hasattr(self, "translation_columns") or not self.translation_columns.winfo_exists():
            return
        palette = self.get_theme_palette()
        self.translation_columns.configure(bg=palette["base"])
        target_bg = self._translation_adjust_color(palette["field"],
            9 if self.theme_name in ("Dark", "Gray") else -7)
        self.translation_canvas.configure(bg=palette["field"])
        self.translation_source_header.configure(bg=palette["selected"], fg=palette["text"])
        self.translation_target_header.configure(bg=palette["selected"], fg=palette["text"])
        self.translation_source_editor.configure(bg=palette["field"], fg=palette["text"],
            insertbackground=palette["text"])
        self.translation_target_editor.configure(bg=target_bg, fg=palette["text"],
            insertbackground=palette["text"])
        self._render_translation_rows()
