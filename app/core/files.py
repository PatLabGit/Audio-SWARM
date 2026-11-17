"""Filesystem discovery and safe output path helpers."""
from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable

AUDIO_EXTENSIONS = frozenset({".mp3", ".ogg", ".oga", ".opus", ".wav", ".flac", ".m4a", ".aac", ".aiff", ".aif"})
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg"})
GENERATED_DIRECTORIES = frozenset({"Waveform_Outputs", "Merged_Tracks_Outputs", "Circular_Waveform_Outputs", "circular-preview"})


def discover_audio(source: str | Path, recursive: bool = True) -> list[Path]:
    """Discover supported audio files in a file or directory, deterministically."""
    root = Path(source).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Source path does not exist: {root}")
    if root.is_file():
        if root.suffix.lower() not in AUDIO_EXTENSIONS:
            raise ValueError(f"Unsupported audio format: {root.suffix}")
        return [root]
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    iterator: Iterable[Path] = root.rglob("*") if recursive else root.iterdir()
    found = []
    for path in iterator:
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        if "_with_art" in path.stem.lower():
            continue
        if any(part in GENERATED_DIRECTORIES for part in path.relative_to(root).parts[:-1]):
            continue
        found.append(path)
    return sorted(found, key=lambda item: str(item).casefold())


def mirrored_output_directory(source_root: Path, audio_path: Path, output_root: Path) -> Path:
    """Return a destination mirroring the source's relative parent directory."""
    if source_root.is_file():
        destination = output_root
    else:
        destination = output_root / audio_path.parent.relative_to(source_root)
    destination.mkdir(parents=True, exist_ok=True)
    return destination
