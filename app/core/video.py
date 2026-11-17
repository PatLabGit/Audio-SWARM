"""Pure-Python business logic engine for embedding video artwork posters."""

from __future__ import annotations
import subprocess
from pathlib import Path
from .models import ProcessingResult
from .process import ffmpeg_executable, run_quiet

SUPPORTED_VIDEO_SUFFIXES = frozenset({".mp4", ".m4v", ".mov", ".mkv"})


def embed_video_artwork(
    video_path: str | Path,
    image_path: str | Path,
    output_path: str | Path,
    ffmpeg_path: str | None = None
) -> ProcessingResult:
    """Embeds an image into a video container using lossless stream copying.
    
    Optimized for high compatibility with Linux media players (VLC, Celluloid).
    """
    ffmpeg_path = ffmpeg_path or ffmpeg_executable() or "ffmpeg"
    source_video = Path(video_path).resolve()
    source_image = Path(image_path).resolve()
    dest_video = Path(output_path).resolve()

    if not source_video.is_file() or not source_image.is_file():
        return ProcessingResult(source_video, None, False, "Source video or artwork image file is missing.")

    suffix = source_video.suffix.lower()
    if suffix not in SUPPORTED_VIDEO_SUFFIXES:
        return ProcessingResult(source_video, None, False, f"Unsupported video container format: {suffix}")

    dest_video.parent.mkdir(parents=True, exist_ok=True)
    
    if dest_video.suffix.lower() != suffix:
        dest_video = dest_video.with_suffix(suffix)

    image_ext = source_image.suffix.lower()
    mimetype = "image/jpeg" if image_ext in {".jpg", ".jpeg"} else "image/png"
    filename_attr = f"cover{image_ext}"

    if suffix == ".mkv":
        # Matroska attachment specification rules
        cmd = [
            ffmpeg_path, "-y", "-nostdin", "-i", str(source_video),
            "-attach", str(source_image),
            "-metadata:s:t", f"mimetype={mimetype}",
            "-metadata:s:t", f"filename={filename_attr}",
            "-c", "copy", str(dest_video)
        ]
    else:
        # HIGH COMPATIBILITY MP4/MOV STREAM MAP:
        # Maps Video first, Audio second, Image third. Forcefully declares attached_pic
        # on stream index 1 (the secondary video layout) to ensure VLC/Celluloid display it.
        cmd = [
            ffmpeg_path, "-y", "-nostdin", "-i", str(source_video), "-i", str(source_image),
            "-map", "0:v:0", "-map", "0:a?", "-map", "1:v:0",
            "-c", "copy",
            "-disposition:v:1", "attached_pic",
            "-id3v2_version", "3", str(dest_video)
        ]

    try:
        run_quiet(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=True
        )
        
        if not dest_video.is_file() or dest_video.stat().st_size == 0:
            raise RuntimeError("FFmpeg process completed but failed to output a valid video file.")
            
        return ProcessingResult(source_video, dest_video, True, "Video poster cover embedded successfully.")
        
    except (subprocess.CalledProcessError, RuntimeError, OSError) as error:
        dest_video.unlink(missing_ok=True)
        error_msg = error.stderr.strip() if hasattr(error, "stderr") else str(error)
        return ProcessingResult(source_video, None, False, f"FFmpeg Error: {error_msg}")

