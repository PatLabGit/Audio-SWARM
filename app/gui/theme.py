"""Application colour palettes and theme helpers."""
from __future__ import annotations

from copy import deepcopy


THEME_NAMES = ("Dark", "Light", "Gray")

THEMES = {
    "Dark": {
        "base": "#292b2e",
        "panel": "#34373b",
        "field": "#202225",
        "text": "#f1f2f3",
        "muted": "#b9bec4",
        "accent": "#27865f",
        "selected": "#58768b",
        "hover": "#6b899f",
        "tab": "#303438",
        "border": "#555b61",
        "disabled": "#858b91",
        "code": "#303238",
        "code_text": "#ffcf75",
        "separator": "#17191b",
    },
    "Light": {
        "base": "#edf0f2",
        "panel": "#f8fafb",
        "field": "#ffffff",
        "text": "#252a2e",
        "muted": "#68737c",
        "accent": "#27865f",
        "selected": "#dcefe5",
        "hover": "#c5dfd2",
        "tab": "#e3e8eb",
        "border": "#c5cdd2",
        "disabled": "#9aa3aa",
        "code": "#e9edef",
        "code_text": "#895b12",
        "separator": "#cbd2d7",
    },
    "Gray": {
        "base": "#404040",
        "panel": "#383838",
        "field": "#2d2d30",
        "text": "#ffffff",
        "muted": "#a9a9a9",
        "accent": "#27865f",
        "selected": "#58768b",
        "hover": "#6b899f",
        "tab": "#303236",
        "border": "#666666",
        "disabled": "#888888",
        "code": "#303238",
        "code_text": "#ffcf75",
        "separator": "#111114",
    },
}

# Existing widgets created before theme centralisation use these colours.
# Keep the mapping so they can be recoloured without changing their behaviour.
LEGACY_COLOR_ROLES = {
    "#404040": "base",
    "#383838": "panel",
    "#2d2d30": "field",
    "#202124": "field",
    "#202225": "field",
    "#111114": "separator",
    "#ffffff": "text",
    "#eeeeee": "text",
    "#a9a9a9": "muted",
    "#00ff66": "accent",
    "#303236": "tab",
    "#303238": "code",
    "#356b50": "selected",
    # Additional legacy foreground values used by disabled labels and controls.
    "#555555": "muted",
    "#777777": "muted",
    "#a0a0a0": "muted",
    "#bdbdbd": "muted",
    "#c7c7c7": "muted",
    "#000000": "text",
    "white": "text",
    "black": "text",
}


def get_palette(theme_name: str = "Dark") -> dict[str, str]:
    """Return a copy of the requested palette, falling back to Dark."""
    return deepcopy(THEMES.get(theme_name, THEMES["Dark"]))


def get_color_role(
    color: str,
    previous_palette: dict[str, str] | None = None,
    option: str | None = None,
) -> str | None:
    """Resolve a widget colour using its Tk option's semantic role.

    A colour can serve more than one purpose across palettes. In particular,
    Light uses white for input fields while older widgets also use white text.
    Restricting candidate roles by the Tk option prevents a foreground from
    accidentally being interpreted as a field/background colour.
    """
    normalized = str(color).strip().lower()

    foreground_roles = {"text", "muted", "accent", "disabled", "code_text"}
    background_roles = {
        "base", "panel", "field", "selected", "tab", "border", "code", "separator"
    }
    if option in {"foreground", "activeforeground", "insertbackground", "disabledforeground"}:
        allowed_roles = foreground_roles
    elif option in {"background", "activebackground", "selectcolor", "highlightbackground"}:
        allowed_roles = background_roles
    elif option == "highlightcolor":
        allowed_roles = {"accent", "border", "muted"}
    else:
        allowed_roles = set(THEMES["Dark"])

    if previous_palette:
        for role, previous_color in previous_palette.items():
            if role in allowed_roles and normalized == previous_color.lower():
                return role

    legacy_role = LEGACY_COLOR_ROLES.get(normalized)
    if legacy_role in allowed_roles:
        return legacy_role
    return None
