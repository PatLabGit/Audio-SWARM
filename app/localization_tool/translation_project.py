"""Translation project registry helpers for settings.json."""
from __future__ import annotations



import json
import os
import tempfile

PROJECTS_KEY = "translation_projects"
ACTIVE_KEY = "translation_active_project"



def _read_settings(settings_path):
    try:
        with open(settings_path, "r", encoding="utf-8") as handle:
            settings = json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise ValueError("settings.json contains invalid JSON; it was not changed.") from exc
    if not isinstance(settings, dict):
        raise ValueError("settings.json must contain a JSON object; it was not changed.")
    return settings



def read_registry(settings_path):
    try:
        settings = _read_settings(settings_path)
    except ValueError:
        # Invalid settings should not prevent the app from opening.
        # Registry writes still refuse to overwrite the invalid file.
        settings = {}
    projects = settings.get(PROJECTS_KEY, [])
    if not isinstance(projects, list):
        projects = []
    projects = [item for item in projects
                if isinstance(item, dict)
                and isinstance(item.get("source"), str)
                and isinstance(item.get("target"), str)]
    active = settings.get(ACTIVE_KEY)
    if not isinstance(active, dict):
        active = None
    return projects, active



def write_registry(settings_path, projects, active):
    """Update translation keys only, preserving every other setting."""
    settings_path = os.path.abspath(settings_path)
    directory = os.path.dirname(settings_path)
    os.makedirs(directory, exist_ok=True)
    settings = _read_settings(settings_path)
    settings[PROJECTS_KEY] = projects
    settings[ACTIVE_KEY] = active
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=directory,
            prefix=".settings_", suffix=".tmp", delete=False,
        ) as handle:
            temp_path = handle.name
            json.dump(settings, handle, ensure_ascii=False, indent=4)
            handle.write("\n")
        os.replace(temp_path, settings_path)
    except OSError:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise



def register_project(settings_path, source_code, target_code):
    projects, _active = read_registry(settings_path)
    pair = {"source": source_code, "target": target_code}
    if pair not in projects:
        projects.append(pair)
    write_registry(settings_path, projects, pair)
    return projects
