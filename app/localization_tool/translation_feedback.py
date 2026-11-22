"""Status-bar feedback helpers for translation editor actions."""
from __future__ import annotations



SUCCESS_PREFIX = "✓ "
WARNING_PREFIX = "! "
ERROR_PREFIX = "✗ "


def show_feedback(status_widget, palette, message, level="success"):
    """Show one short message in the existing application status label."""
    if status_widget is None or not status_widget.winfo_exists():
        return
    prefix = {"success": SUCCESS_PREFIX, "warning": WARNING_PREFIX,
              "error": ERROR_PREFIX}.get(level, "")
    foreground = {"success": palette["accent"],
                "warning": palette["code_text"],
                "error": "#c65b5b"}.get(level, palette["accent"])
    status_widget.configure(text=prefix + message, fg=foreground)
