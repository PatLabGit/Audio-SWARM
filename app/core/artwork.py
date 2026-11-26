"""Artwork preparation and canonical original metadata embedding routines."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from .models import ArtworkSettings, ProcessingResult

SUPPORTED_AUDIO_SUFFIXES = frozenset({
    ".mp3", ".ogg", ".oga", ".opus", ".flac", ".m4a", ".aac", ".aiff", ".aif", ".wav"
})


def prepare_artwork(image_path: str | Path, output_dir: str | Path,
                    settings: ArtworkSettings) -> Path:
    """Prepare bulk-linker artwork using the active format, alpha, and backdrop settings.

    When matrix resizing/conversion is disabled, the original image is returned unchanged.
    The caller is responsible for removing a generated temporary image.
    """
    source = Path(image_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Artwork image does not exist: {source}")
    if not settings.resize:
        return source
    try:
        from PIL import Image, ImageColor
    except ImportError as error:
        raise RuntimeError("Pillow is required when artwork resizing or format conversion is enabled.") from error

    output_format = str(settings.output_format).upper()
    output_suffix = ".jpg" if output_format == "JPG" else ".png"
    output_image_format = "JPEG" if output_format == "JPG" else "PNG"
    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".audio_swarm_resized_", suffix=output_suffix,
                                        dir=destination_dir)
    os.close(descriptor)
    destination = Path(name)
    try:
        # STRIP CLEANING: Extract the color code safely and strip spaces
        color_str = str(settings.background_color).strip()
        if color_str.startswith(".") or not color_str:
            color_str = "#404040" # Protection fallback if object name leaked
            
        color = ImageColor.getrgb(color_str)
        if len(color) == 4:
            color = color[:3]
            
        output_format = output_format if output_format in {"PNG", "JPG"} else "PNG"
        
        # Suffix and transparency evaluations
        keep_alpha = (output_format == "PNG" and bool(settings.transparent))
        canvas_size = (int(settings.width), int(settings.height))

        with Image.open(source) as image:
            image.load()
            source_rgba = image.convert("RGBA")
            try:
                if settings.preserve_aspect:
                    artwork = source_rgba.copy()
                    artwork.thumbnail(canvas_size, Image.Resampling.LANCZOS)
                    position = ((canvas_size[0] - artwork.width) // 2,
                                (canvas_size[1] - artwork.height) // 2)
                else:
                    artwork = source_rgba.resize(canvas_size, Image.Resampling.LANCZOS)
                    position = (0, 0)

                try:
                    if keep_alpha:
                        # PNG with Transparency Enabled
                        prepared = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
                        prepared.alpha_composite(artwork, dest=position)
                        try:
                            prepared.save(destination, format="PNG", optimize=True)
                        finally:
                            prepared.close()
                    else:
                        # Solid Opaque Background: Force solid backdrop generation
                        # for both JPG and non-transparent PNG
                        backdrop = Image.new("RGB", canvas_size, color)
                        try:
                            # Build explicit canvas to paste the foreground image onto
                            canvas_rgba = Image.new("RGBA", canvas_size, color + (255,))
                            canvas_rgba.alpha_composite(artwork, dest=position)
                            flattened = canvas_rgba.convert("RGB")
                            try:
                                if output_format == "JPG":
                                    flattened.save(destination, format="JPEG",
                                                   quality=settings.jpeg_quality, optimize=True)
                                else:
                                    flattened.save(destination, format="PNG", optimize=True)
                            finally:
                                flattened.close()
                        finally:
                            backdrop.close()
                finally:
                    artwork.close()
            finally:
                source_rgba.close()
    except BaseException:  # clean up the half-written file on any failure, then re-raise
        destination.unlink(missing_ok=True)
        raise
    return destination



def embed_artwork(audio_path: str | Path, image_path: str | Path,
                  output_path: str | Path) -> ProcessingResult:
    """Embed generated artwork using the application's original format handlers.

    The original Mutagen paths for OGG/OGA and AIFF, and the original FFmpeg
    attached-picture path for other supported containers, are preserved verbatim.
    WAV has no portable embedded-cover convention and is copied beside its image.
    """
    source = Path(audio_path).resolve()
    image = Path(image_path).resolve()
    destination = Path(output_path).resolve()
    if not source.is_file() or not image.is_file():
        return ProcessingResult(source, None, False, "Audio or artwork file is missing.")
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_AUDIO_SUFFIXES:
        return ProcessingResult(source, None, False, f"Unsupported audio format: {suffix}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".wav":
        try:
            audio_target = destination if destination.suffix.lower() == ".wav" else destination / source.name
            audio_target.parent.mkdir(parents=True, exist_ok=True)
            image_target = audio_target.parent / f"{source.stem}{image.suffix.lower()}"
            if source.resolve() != audio_target.resolve():
                shutil.copy2(source, audio_target)
            if image.resolve() != image_target.resolve():
                shutil.copy2(image, image_target)
            return ProcessingResult(source, audio_target, True,
                                    f"WAV does not support portable embedded cover art; copied audio and image side by side ({image_target.name}).")
        except OSError as error:
            return ProcessingResult(source, None, False, str(error))
    output_suffix = ".m4a" if suffix == ".aac" else suffix
    if destination.suffix.lower() != output_suffix:
        destination = destination.with_suffix(output_suffix)
    image_is_jpg = image.suffix.lower() in {".jpg", ".jpeg"}
    codec = "mjpeg" if image_is_jpg else "png"
    try:
        try:
            from PIL import Image
            with Image.open(image) as artwork:
                image_width, image_height = artwork.size
        except ImportError:
            image_width = image_height = 1
        # Invoke the exact original implementations; these verify the written
        # metadata before atomically publishing the destination.
        # Imported here (not at module top) because engine.py imports this module.
        from .engine import LegacyRenderCore
        adapter = type("OriginalEmbeddingAdapter", (), {})()
        if suffix in {".ogg", ".oga", ".opus"}:
            success, error = LegacyRenderCore._embed_ogg_waveform_artwork(
                adapter, str(source), str(image), str(destination),
                image_width, image_height, image_is_jpg
            )
        elif suffix in {".aiff", ".aif"}:
            success, error = LegacyRenderCore._embed_aiff_waveform_artwork(
                adapter, str(source), str(image), str(destination), image_is_jpg
            )
        else:
            success, error = LegacyRenderCore._embed_waveform_artwork_with_ffmpeg(
                adapter, str(source), str(image), str(destination), codec
            )
        if not success:
            raise RuntimeError(error or "The original artwork embedding routine failed.")
        if not destination.is_file() or destination.stat().st_size == 0:
            raise RuntimeError("Artwork embedding did not produce a valid output file.")
        return ProcessingResult(source, destination, True, "Original artwork embedding completed and was verified.")
    except (OSError, RuntimeError, ValueError, TypeError) as error:
        return ProcessingResult(source, None, False, str(error))
