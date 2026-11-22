"""JSON catalog operations for the Translation workspace."""
from __future__ import annotations


import json
import os
import shutil
import tempfile


class TranslationEngine:
    """Read and save catalogs; initialize new translations from source copies."""
    def __init__(self, language_dir):
        self.language_dir = os.path.abspath(language_dir)

    def catalog_path(self, code):
        if not isinstance(code, str) or len(code) != 2 or not code.isalpha():
            raise ValueError("Language code must be a two-letter code.")
        return os.path.join(self.language_dir, f"{code.lower()}.json")



    def read_catalog(self, code):
        with open(self.catalog_path(code), "r", encoding="utf-8") as handle:
            catalog = json.load(handle)
        if not isinstance(catalog, dict):
            raise ValueError(f"Catalog {code!r} is not a JSON object.")
        return catalog



    def source_entries(self, source_code):
        catalog = self.read_catalog(source_code)
        return [(key, value) for key, value in catalog.items()
                if not key.startswith("_") and isinstance(value, str)]



    def target_catalog(self, target_code):
        path = self.catalog_path(target_code)
        return self.read_catalog(target_code) if os.path.isfile(path) else {}



    def create_target_catalog(self, target_code, target_name, source_code):
        """Copy the selected source catalog; only target metadata is renamed."""
        if source_code.lower() == target_code.lower():
            raise ValueError("Source and target languages must differ.")
        os.makedirs(self.language_dir, exist_ok=True)
        source_path = self.catalog_path(source_code)
        target_path = self.catalog_path(target_code)
        if os.path.exists(target_path):
            return self.read_catalog(target_code), False
        if not os.path.isfile(source_path):
            raise FileNotFoundError(source_path)
        shutil.copy2(source_path, target_path)
        try:
            catalog = self.read_catalog(target_code)
            catalog["_language_name"] = target_name
            self.write_catalog(target_code, catalog)
        except Exception:
            try:
                os.remove(target_path)
            except OSError:
                pass
            raise
        return catalog, True



    def write_catalog(self, target_code, catalog):
        """Atomically save a UTF-8 catalog while preserving string values."""
        path = self.catalog_path(target_code)
        os.makedirs(self.language_dir, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                dir=self.language_dir, prefix=f".{target_code}_", suffix=".tmp",
                delete=False) as handle:
                temp_path = handle.name
                json.dump(catalog, handle, ensure_ascii=False, indent=4)
                handle.write("\n")
            os.replace(temp_path, path)
        except OSError:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise



    def build_rows(self, source_code, target_code):
        source_entries = self.source_entries(source_code)
        target_catalog = self.target_catalog(target_code)
        rows = []
        for key, source_value in source_entries:
            target_value = target_catalog.get(key, source_value)
            # Old Translation projects may have been initialized with empty values.
            # Treat those as untranslated and display the original source text.
            if not isinstance(target_value, str) or not target_value:
                target_value = source_value
            rows.append((key, source_value, target_value))
        return rows
