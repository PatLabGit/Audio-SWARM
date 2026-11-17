"""Preview rendering wrappers backed by the canonical original engine.

The original 1,520-line implementation is the sole source of waveform geometry,
slice mathematics, circular rendering, and output-image generation. This module
keeps the preview-facing API used by the GUI without maintaining a second renderer.
"""
from __future__ import annotations

from pathlib import Path
from collections.abc import Callable

from .legacy_renderer import LegacyRendererAdapter
from .models import ProcessingResult, WaveformSettings

ProgressCallback = Callable[[str, int, int], None]


def _renderer(settings: WaveformSettings, progress: ProgressCallback | None):
    def report(message: str) -> None:
        if progress is not None:
            progress(message, 0, 1)
    return LegacyRendererAdapter(settings, report if progress is not None else None)


def render_waveform(
    audio_path: str | Path,
    output_dir: str | Path,
    settings: WaveformSettings,
    progress: ProgressCallback | None = None,
) -> ProcessingResult:
    """Render a standard waveform with the canonical original algorithms."""
    source = Path(audio_path).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    result = _renderer(settings, progress).render_waveform(source, destination)
    # Preview callers need the standalone image, even when the original renderer
    # also successfully creates a *_with_art audio file.
    suffix = ".jpg" if settings.output_format == "JPG" else ".png"
    image_path = destination / f"{source.stem}{suffix}"
    if result.success and image_path.is_file():
        return ProcessingResult(source, image_path, True, result.message)
    return result


def render_circular_waveform(
    audio_path: str | Path,
    output_dir: str | Path,
    settings: WaveformSettings,
    mode: str = "waveform",
    progress: ProgressCallback | None = None,
) -> ProcessingResult:
    """Render circular, radial-spectrum, or minimal output via the original engine."""
    source = Path(audio_path).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    mode_key = {"circular": "waveform", "radial": "spectrum"}.get(str(mode).lower(), str(mode).lower())
    if mode_key not in {"waveform", "spectrum", "minimal"}:
        return ProcessingResult(source, None, False, f"Unsupported circular mode: {mode}")
    result = _renderer(settings, progress).render_circular(source, destination, mode_key)
    suffix_name = {
        "waveform": "circular",
        "spectrum": "radial_spectrum",
        "minimal": "minimal_circular",
    }[mode_key]
    suffix = ".jpg" if settings.output_format == "JPG" else ".png"
    image_path = destination / f"{source.stem}_{suffix_name}{suffix}"
    if result.success and image_path.is_file():
        return ProcessingResult(source, image_path, True, result.message)
    return result


def render_waveform_preview(
    audio_path: str | Path, output_dir: str | Path, settings: WaveformSettings, output_image_path: str | Path,
) -> ProcessingResult:
    """Create one preview directly through the canonical original renderer."""
    source = Path(audio_path).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    preview = Path(output_image_path).expanduser().resolve()
    result = _renderer(settings, None).render_waveform_preview(source, destination, preview)
    return ProcessingResult(source, preview if result else None, bool(result),
                            "Original engine preview generated." if result else "Original engine preview failed.")


def render_circular_waveform_preview(
    audio_path: str | Path, output_dir: str | Path, settings: WaveformSettings, mode: str,
    render_size: int, output_image_path: str | Path,
) -> ProcessingResult:
    """Create one circular preview through the canonical original renderer."""
    source = Path(audio_path).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    preview = Path(output_image_path).expanduser().resolve()
    result = _renderer(settings, None).render_circular_preview(source, destination, mode, render_size, preview)
    if result.success and preview.is_file():
        return ProcessingResult(source, preview, True, result.message)
    return ProcessingResult(source, None, False, result.message)
