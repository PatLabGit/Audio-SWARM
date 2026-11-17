"""Cross-platform FFmpeg discovery and quiet subprocess helpers."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

_EXE = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
_APP_DIR = Path(__file__).resolve().parents[2]
# GUI launches (macOS .app, Windows .vbs) often inherit a minimal PATH.
_FALLBACK_DIRS = (
    _APP_DIR / "ffmpeg", _APP_DIR / "ffmpeg" / "bin", _APP_DIR / "bin",
    Path("/opt/homebrew/bin"), Path("/usr/local/bin"), Path("/opt/local/bin"), Path("/usr/bin"),
)
# Windows only: stop a console window flashing for every FFmpeg call.
_CREATION_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


@lru_cache(maxsize=1)
def ffmpeg_executable() -> str | None:
    """Return the FFmpeg path, or None when it cannot be found."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    for directory in _FALLBACK_DIRS:
        candidate = directory / _EXE
        if candidate.is_file():
            return str(candidate)
    try:  # optional: pip install imageio-ffmpeg
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - optional dependency, any failure means "not available"
        return None


def ffmpeg_command(*args: str) -> list[str]:
    """Build an FFmpeg command line using the resolved executable."""
    return [ffmpeg_executable() or "ffmpeg", *args]


def run_quiet(command, **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run with no console window, no stdin, and tolerant UTF-8 decoding."""
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    kwargs.setdefault("creationflags", _CREATION_FLAGS)
    if kwargs.get("text") or kwargs.get("universal_newlines"):
        kwargs.setdefault("encoding", "utf-8")
        kwargs.setdefault("errors", "replace")
    return subprocess.run(command, **kwargs)
