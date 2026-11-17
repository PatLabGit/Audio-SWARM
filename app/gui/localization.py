"""Language catalog and translation helpers."""
from __future__ import annotations
import os, sys, json

class LocalizationMixin:
    def discover_languages(self):
        """Discover valid language catalogs directly from the languages directory."""
        languages = {}
        try:
            filenames = os.listdir(self.language_dir)
        except OSError:
            filenames = []

        for filename in filenames:
            if not filename.lower().endswith(".json"):
                continue
            code = filename[:-5]
            catalog_path = os.path.join(self.language_dir, filename)
            try:
                with open(catalog_path, "r", encoding="utf-8") as catalog_file:
                    catalog = json.load(catalog_file)
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(catalog, dict):
                continue
            # Use the catalog's native display name; older catalogs fall back to the code.
            display_name = catalog.get("_language_name", code)
            if isinstance(display_name, str) and display_name.strip():
                languages[code] = display_name.strip()

        # Keep English first, then list the remaining languages alphabetically.
        ordered = {}
        if "en" in languages:
            ordered["en"] = languages.pop("en")
        for code, name in sorted(languages.items(), key=lambda item: item[1].casefold()):
            ordered[code] = name
        return ordered

    def read_saved_language(self):
        """Read the saved language, defaulting to English when unavailable."""
        try:
            with open(self.settings_path, "r", encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
            language_code = settings.get("language", "en") if isinstance(settings, dict) else "en"
        except (OSError, json.JSONDecodeError):
            language_code = "en"

        if language_code not in self.available_languages:
            language_code = "en"
        return language_code

    def read_saved_theme(self):
        """Read the saved interface theme, defaulting to Dark."""
        try:
            with open(self.settings_path, "r", encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
            theme = settings.get("theme", "Dark") if isinstance(settings, dict) else "Dark"
        except (OSError, json.JSONDecodeError):
            theme = "Dark"
        return theme if theme in ("Dark", "Light", "Gray") else "Dark"

    def read_recent_colors(self):
        """Read the most recently used valid HEX colours."""
        try:
            with open(self.settings_path, "r", encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
            colors = settings.get("recent_colors", []) if isinstance(settings, dict) else []
        except (OSError, json.JSONDecodeError):
            colors = []
        if not isinstance(colors, list):
            return []
        return [c.upper() for c in colors if isinstance(c, str) and len(c) == 7
                and c.startswith("#") and all(ch in "0123456789ABCDEFabcdef" for ch in c[1:])][:20]

    def save_settings(self):
        """Persist settings without discarding keys introduced by other features."""
        temporary_path = self.settings_path + ".tmp"
        try:
            try:
                with open(self.settings_path, "r", encoding="utf-8") as settings_file:
                    settings = json.load(settings_file)
                if not isinstance(settings, dict):
                    settings = {}
            except (OSError, json.JSONDecodeError):
                settings = {}
            settings["language"] = self.language_code
            settings["theme"] = getattr(self, "theme_name", "Dark")
            settings["recent_colors"] = list(getattr(self, "recent_colors", []))[:20]
            with open(temporary_path, "w", encoding="utf-8") as settings_file:
                json.dump(settings, settings_file, ensure_ascii=False, indent=4)
                settings_file.write("\n")
            os.replace(temporary_path, self.settings_path)
        except OSError as exc:
            try:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
            except OSError:
                pass
            print(f"Audio-SWARM: could not save settings to {self.settings_path}: {exc}", file=sys.stderr)

    def load_language(self, language_code):
        """Load a JSON language catalog; untranslated strings fall back to English."""
        self.language_code = language_code
        catalog_path = os.path.join(self.language_dir, f"{language_code}.json")
        try:
            with open(catalog_path, "r", encoding="utf-8") as catalog_file:
                catalog = json.load(catalog_file)
            self.translations = catalog if isinstance(catalog, dict) else {}
        except (OSError, json.JSONDecodeError):
            self.translations = {}

    def tr(self, text):
        """Return the translated string, or the original English text as fallback."""
        return self.translations.get(text, text)

    def change_language(self, _event=None):
        """Reload the interface in the selected language while preserving settings."""
        selected_code = self.language_codes_by_name.get(self.language_menu.get(), "en")
        if selected_code == self.language_code:
            return
        self.load_language(selected_code)
        self.save_settings()
        self.root.title(self.tr("Audio-SWARM — Audio Waveform & Artwork Studio"))
        # Keep generated preview PhotoImages and per-mode paths across language rebuilds.
        # Recreated widgets can display the existing image without regenerating it.
        # Recreate root-level widgets so all localized labels and dialogs refresh.
        for child in self.root.winfo_children():
            child.destroy()
        self.setup_ui_layout()
