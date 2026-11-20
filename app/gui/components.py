"""Reusable controls, drag/drop helpers, and UI state utilities."""
from __future__ import annotations
import tkinter as tk
from app.gui.styles import POPUP_THEME

class ComponentsMixin:
    def create_action_button(self, parent, text, command, kind):
        """Create a restrained generate/stop button with distinct interaction states."""
        palettes = {
            "generate": {
                "normal": "#397461",   # muted teal-green
                "hover": "#458770",    # slightly lighter on hover
                "pressed": "#2D5C4D",  # darker while pressed
                "foreground": "#FFFFFF",
            },
            "stop": {
                "normal": "#934F51",   # muted brick red
                "hover": "#A76163",    # slightly lighter on hover
                "pressed": "#753D3F",  # darker while pressed
                "foreground": "#FFFFFF",
            },
            "preview": {
                "normal": "#496270",
                "hover": "#58768B",
                "pressed": "#3E5360",
                "foreground": "#FFFFFF",
            },
        }
        palette = palettes[kind].copy()
        palette["disabled_background"] = "#4A4A4A"
        palette["disabled_foreground"] = "#A6A6A6"
        button = tk.Button(
            parent,
            text=text,
            bg=palette["normal"],
            fg=palette["foreground"],
            font=("Helvetica", 10, "bold"),
            activebackground=palette["hover"],
            activeforeground=palette["foreground"],
            disabledforeground=palette["disabled_foreground"],
            command=command,
        )
        self.action_button_specs[button] = palette
        button.bind("<Enter>", lambda _event, widget=button: self._set_action_button_active_color(widget, "hover"))
        button.bind("<Leave>", lambda _event, widget=button: self._set_action_button_active_color(widget, "normal"))
        button.bind("<ButtonPress-1>", lambda _event, widget=button: self._set_action_button_active_color(widget, "pressed"))
        button.bind("<ButtonRelease-1>", lambda event, widget=button: self._release_action_button(widget, event))
        return button

    def _set_action_button_active_color(self, button, color_state):
        """Set hover/pressed colors without overriding disabled-button styling."""
        palette = getattr(self, "action_button_specs", {}).get(button)
        if not palette or str(button.cget("state")) == "disabled":
            return
        button.configure(activebackground=palette[color_state])

    def _release_action_button(self, button, event):
        """Restore the appropriate hover or normal shade after a click."""
        palette = getattr(self, "action_button_specs", {}).get(button)
        if not palette or str(button.cget("state")) == "disabled":
            return
        inside = 0 <= event.x < button.winfo_width() and 0 <= event.y < button.winfo_height()
        button.configure(activebackground=palette["hover"] if inside else palette["normal"])

    def set_action_button_enabled(self, button, enabled):
        """Use neutral grey for disabled generate buttons, restoring their role color on enable."""
        palette = getattr(self, "action_button_specs", {}).get(button)
        if not palette:
            button.configure(state="normal" if enabled else "disabled")
            return
        if enabled:
            button.configure(
                state="normal",
                bg=palette["normal"],
                fg=palette["foreground"],
                activebackground=palette["hover"],
                activeforeground=palette["foreground"],
                disabledforeground=palette["disabled_foreground"],
            )
        else:
            button.configure(
                state="disabled",
                bg=palette["disabled_background"],
                fg=palette["disabled_foreground"],
                activebackground=palette["disabled_background"],
                activeforeground=palette["disabled_foreground"],
                disabledforeground=palette["disabled_foreground"],
            )

    def write_system_log(self, text_string):
        text_string = str(text_string)
        if not hasattr(self, "process_window_lines"):
            self.process_window_lines = []
        if not hasattr(self, "process_error_lines"):
            self.process_error_lines = []
        self.process_window_lines.append(text_string)
        lowered = text_string.lower()
        if ("❌" in text_string or "traceback" in lowered or "exception" in lowered
                or "error:" in lowered or "failed" in lowered):
            self.process_error_lines.append(text_string)
        self.log_box.config(state="normal")
        self.log_box.insert("end", text_string + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")
        if getattr(self, "process_log_output_directory", None):
            self.save_processing_log(self.process_log_output_directory)

    def clear_system_log(self):
        self.process_window_lines = []
        self.process_error_lines = []
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def record_processing_error(self, message):
        message = str(message)
        if not hasattr(self, "process_error_lines"):
            self.process_error_lines = []
        self.process_error_lines.append(message)
        if getattr(self, "process_log_output_directory", None):
            self.save_processing_log(self.process_log_output_directory)

    def save_processing_log(self, output_directory):
        """Save errors first, followed by the exact process-window text."""
        try:
            from pathlib import Path
            target_dir = Path(output_directory)
            target_dir.mkdir(parents=True, exist_ok=True)
            log_path = target_dir / "Audio-SWARM.log"
            errors = list(getattr(self, "process_error_lines", []))
            window_lines = list(getattr(self, "process_window_lines", []))
            with log_path.open("w", encoding="utf-8") as log_file:
                log_file.write("=== ERRORS ===\n")
                log_file.write("\n".join(errors) if errors else "None")
                log_file.write("\n\n=== PROCESS WINDOW (verbatim) ===\n")
                log_file.write("\n".join(window_lines))
                log_file.write("\n")
            return str(log_path)
        except (OSError, ValueError) as exc:
            import sys
            print(f"Audio-SWARM: could not save Audio-SWARM.log: {exc}", file=sys.stderr)
            return None


        self.log_box.config(state="normal")
        self.log_box.insert("end", text_string + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")


    def toggle_ui_interactivity(self, enable=True):
        self.is_processing = not enable
        self.set_action_button_enabled(self.run_btn_t1, enable)
        self.set_action_button_enabled(self.run_btn_t2, enable)
        if hasattr(self, "run_btn_circular"):
            self.set_action_button_enabled(self.run_btn_circular, enable)
        # Each preview button's enabled state is owned by its tab mixin.
        # The shared processing controller only coordinates the lifecycle.
        if hasattr(self, "set_sound_preview_button_enabled"):
            self.set_sound_preview_button_enabled(enable)
        if hasattr(self, "set_circular_preview_button_enabled"):
            self.set_circular_preview_button_enabled(enable)
        self.browse_btn.config(state="normal" if enable else "disabled")
        self.folder_entry.config(state="normal" if enable else "disabled")

    def show_themed_popup(self, title, message, kind="info", width=500, height=280):
        """Show a localized modal using the shared popup palette for every dialog type."""
        theme = POPUP_THEME
        modal = tk.Toplevel(self.root)
        modal.title(title)
        modal.configure(bg=theme["bg"])
        modal.resizable(False, False)
        modal.transient(self.root)
        modal.geometry(f"{width}x{height}")
        try:
            self.root.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
            modal.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        except tk.TclError:
            pass
        interior = tk.Frame(modal, bg=theme["bg"])
        interior.pack(fill="both", expand=True, padx=20, pady=18)
        label = tk.Label(
            interior, text=message, bg=theme["bg"], fg=theme["fg"],
            font=theme["font_main"], justify="center", wraplength=width - 48,
        )
        label.pack(fill="both", expand=True, pady=(0, 12))

        def dismiss():
            try:
                modal.grab_release()
            except tk.TclError:
                pass
            if modal.winfo_exists():
                modal.destroy()

        button = tk.Button(
            interior, text=self.tr("OK"), bg=theme["btn_bg"], fg=theme["btn_fg"],
            activebackground=theme["btn_active_bg"], activeforeground=theme["btn_active_fg"],
            font=theme["font_btn"], relief="flat", command=dismiss, width=10, pady=4,
        )
        button.pack(side="bottom")
        button.bind("<Enter>", lambda _event: button.configure(bg=theme["btn_hover_bg"], fg=theme["btn_hover_fg"]))
        button.bind("<Leave>", lambda _event: button.configure(bg=theme["btn_bg"], fg=theme["btn_fg"]))
        button.bind("<ButtonPress-1>", lambda _event: button.configure(bg=theme["btn_active_bg"], fg=theme["btn_active_fg"]))
        button.bind("<ButtonRelease-1>", lambda _event: button.configure(bg=theme["btn_hover_bg"], fg=theme["btn_hover_fg"]))
        modal.protocol("WM_DELETE_WINDOW", dismiss)
        modal.bind("<Escape>", lambda _event: dismiss())
        modal.grab_set()
        button.focus_set()
        modal.wait_window()

    def trigger_thread_safe_popup(self, a_count, i_count):
        wait_flag = tk.BooleanVar(value=False)

        def show_modal():
            theme = POPUP_THEME
            modal = tk.Toplevel(self.root)
            modal.title(self.tr("File Count Mismatch"))
            modal.geometry("450x180")
            modal.configure(bg=theme["bg"])
            modal.resizable(False, False)
            modal.transient(self.root)
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 90
            modal.geometry(f"450x180+{max(0, x)}+{max(0, y)}")
            interior_box = tk.Frame(modal, bg=theme["bg"])
            interior_box.pack(fill="both", expand=True, padx=20, pady=20)
            msg_txt = self.tr(
                "Warning: You have {audio_count} audio files but {image_count} image files!\n\n"
                "The studio will only pair the first {limit} matched items to prevent alignment errors."
            ).format(audio_count=a_count, image_count=i_count, limit=min(a_count, i_count))
            msg_lbl = tk.Label(interior_box, text=msg_txt, bg=theme["bg"], fg=theme["fg"],
                               font=theme["font_main"], justify="center", wraplength=400)
            msg_lbl.pack(pady=(0, 15), anchor="w")

            def dismiss_modal():
                wait_flag.set(True)
                try:
                    modal.grab_release()
                except tk.TclError:
                    pass
                if modal.winfo_exists():
                    modal.destroy()

            ok_btn = tk.Button(
                interior_box, text=self.tr("OK"), bg=theme["btn_bg"], fg=theme["btn_fg"],
                activebackground=theme["btn_active_bg"], activeforeground=theme["btn_active_fg"],
                font=theme["font_btn"], relief="flat", command=dismiss_modal, width=10, pady=4,
            )
            ok_btn.pack(side="bottom")
            ok_btn.bind("<Enter>", lambda _event: ok_btn.configure(bg=theme["btn_hover_bg"], fg=theme["btn_hover_fg"]))
            ok_btn.bind("<Leave>", lambda _event: ok_btn.configure(bg=theme["btn_bg"], fg=theme["btn_fg"]))
            ok_btn.bind("<ButtonPress-1>", lambda _event: ok_btn.configure(bg=theme["btn_active_bg"], fg=theme["btn_active_fg"]))
            ok_btn.bind("<ButtonRelease-1>", lambda _event: ok_btn.configure(bg=theme["btn_hover_bg"], fg=theme["btn_hover_fg"]))
            modal.protocol("WM_DELETE_WINDOW", dismiss_modal)
            modal.bind("<Escape>", lambda _event: dismiss_modal())
            modal.grab_set()

        self.root.after(0, show_modal)
        self.root.wait_variable(wait_flag)

    def record_recent_color(self, color):
        """Move a confirmed colour to the front of the 20-colour history."""
        color = str(color).upper()
        self.recent_colors = [color] + [item for item in self.recent_colors if item.upper() != color]
        self.recent_colors = self.recent_colors[:20]
        self.save_settings()

    def pick_flat_backdrop_color(self):
        if self.is_processing:
            return
        from app.gui.color_picker import ColorPickerDialog
        dialog = ColorPickerDialog(self.root, self.bg_solid_color, self.recent_colors,
                                   theme=self.get_theme_palette(), translator=self.tr)
        self.root.wait_window(dialog)
        if dialog.result:
            self.bg_solid_color = dialog.result
            self.bg_solid_color_selected = True
            self.record_recent_color(dialog.result)
            self.sync_transparency_ui_locks()
