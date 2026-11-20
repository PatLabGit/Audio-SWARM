"""Pure-Python orchestration for Audio-SWARM processing jobs."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .artwork import embed_artwork, prepare_artwork
from .files import IMAGE_EXTENSIONS, discover_audio, mirrored_output_directory
from .models import (
    ArtworkSettings,
    BatchResult,
    CancelCallback,
    LogCallback,
    ProcessingResult,
    ProgressCallback,
    WaveformSettings,
)
from .legacy_renderer import LegacyRendererAdapter
import os
import wave
import base64
import shutil
import subprocess
import tempfile
import gc

import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless backend: no Tk canvases/windows created from worker threads
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon, Rectangle


class ProcessingEngine:
    """Coordinate audio rendering and artwork tasks without UI dependencies.

    Callbacks are ordinary Python callables. A GUI may adapt them to its own
    event loop, but this package never imports or manipulates GUI objects.
    """

    def __init__(self, logger: LogCallback | None = None, popup=None, translator=None) -> None:
        self._logger = logger or (lambda _message: None)
        self._popup = popup
        self._translator = translator or (lambda text: text)

    def _log(self, message: str) -> None:
        """Send a log message to the optional injected callback."""
        self._logger(message)

    def render_batch(
        self,
        source: str | Path,
        settings: WaveformSettings,
        output_directory: str = "Waveform_Outputs",
        progress: ProgressCallback | None = None,
        cancelled: CancelCallback | None = None,
    ) -> BatchResult:
        """Render using the original Audio-SWARM renderer without changing its math."""
        source_path = Path(source).expanduser().resolve()
        audio_files = discover_audio(source_path)
        # Original behavior: a single file writes beside that file; a folder writes
        # into its Waveform_Outputs tree, preserving relative subdirectories.
        output_root = (source_path.parent if source_path.is_file() else source_path) / ("Images_only" if settings.generate_image_only else ("" if source_path.is_file() else output_directory))
        output_root.mkdir(parents=True, exist_ok=True)
        renderer = LegacyRendererAdapter(settings, self._log, single_file=source_path.is_file(), popup=self._popup, translator=self._translator)
        results: list[ProcessingResult] = []
        was_cancelled = False
        for index, audio_path in enumerate(audio_files, start=1):
            if cancelled is not None and cancelled():
                was_cancelled = True
                break
            destination_dir = mirrored_output_directory(source_path, audio_path, output_root)
            if progress is not None:
                progress(f"{index}/{len(audio_files)}: Rendering {audio_path.name}", index - 1, len(audio_files))
            # Folder drops copy WAV audio into the output tree as requested. For a
            # single-file drop output_root is the source folder, so no redundant copy.
            if source_path.is_dir() and audio_path.suffix.lower() == ".wav" and not settings.generate_image_only:
                try:
                    shutil.copy2(audio_path, destination_dir / audio_path.name)
                except OSError as error:
                    results.append(ProcessingResult(audio_path, None, False, str(error)))
                    continue
            renderer.set_batch_log_context(source_path, audio_path)
            result = renderer.render_waveform(audio_path, destination_dir)
            results.append(result)
            if progress is not None:
                progress(f"{index}/{len(audio_files)}: Rendering {audio_path.name}", index, len(audio_files))
        return BatchResult(tuple(results), was_cancelled)

    def render_circular_batch(
        self,
        source: str | Path,
        settings: WaveformSettings,
        mode: str = "radial",
        output_directory: str = "Circular_Waveform_Outputs",
        progress: ProgressCallback | None = None,
        cancelled: CancelCallback | None = None,
    ) -> BatchResult:
        """Render circular output with the original circular rendering algorithm."""
        source_path = Path(source).expanduser().resolve()
        audio_files = discover_audio(source_path)
        output_root = (source_path.parent if source_path.is_file() else source_path) / ("Images_only" if settings.generate_image_only else ("" if source_path.is_file() else output_directory))
        output_root.mkdir(parents=True, exist_ok=True)
        renderer = LegacyRendererAdapter(settings, self._log, single_file=source_path.is_file(), popup=self._popup, translator=self._translator)
        results: list[ProcessingResult] = []
        was_cancelled = False
        normalized_mode = {"radial": "waveform", "waveform": "waveform", "spectrum": "spectrum", "minimal": "minimal"}.get(mode, mode)
        for index, audio_path in enumerate(audio_files, start=1):
            if cancelled is not None and cancelled():
                was_cancelled = True
                break
            destination_dir = mirrored_output_directory(source_path, audio_path, output_root)
            if progress is not None:
                progress(f"{index}/{len(audio_files)}: Circular: Rendering {audio_path.name}", index - 1, len(audio_files))
            if source_path.is_dir() and audio_path.suffix.lower() == ".wav" and not settings.generate_image_only:
                try:
                    shutil.copy2(audio_path, destination_dir / audio_path.name)
                except OSError as error:
                    results.append(ProcessingResult(audio_path, None, False, str(error)))
                    continue
            renderer.set_batch_log_context(source_path, audio_path, normalized_mode)
            result = renderer.render_circular(audio_path, destination_dir, normalized_mode)
            results.append(result)
            if progress is not None:
                progress(f"{index}/{len(audio_files)}: Circular: Rendering {audio_path.name}", index, len(audio_files))
        return BatchResult(tuple(results), was_cancelled)

    def merge_artwork_batch(
        self,
        source: str | Path,
        artwork_source: str | Path | None,
        settings: ArtworkSettings | None = None,
        output_directory: str = "Merged_Tracks_Outputs",
        progress: ProgressCallback | None = None,
        cancelled: CancelCallback | None = None,
    ) -> BatchResult:
        """Embed a corresponding image into each audio file in a source folder.

        Images and audio files are paired by case-insensitive sorted order. If
        ``artwork_source`` is a directory, its supported images are used; if it
        is a single image, that image is reused for every input track.
        """
        source_path = Path(source).expanduser().resolve()
        audio_files = discover_audio(source_path, recursive=False)
        if artwork_source is None:
            image_files: list[Path] = []
        else:
            image_path = Path(artwork_source).expanduser().resolve()
            if image_path.is_file():
                if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
                    raise ValueError(f"Unsupported artwork format: {image_path.suffix}")
                image_files = [image_path]
            elif image_path.is_dir():
                image_files = sorted(
                    (item for item in image_path.iterdir()
                     if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS),
                    key=lambda item: item.name.casefold(),
                )
            else:
                raise FileNotFoundError(f"Artwork path does not exist: {image_path}")
        if not audio_files:
            return BatchResult(())
        # Deliberately do not reject count mismatches: the legacy linker warns
        # and processes only the available one-to-one pairs.
        pair_count = min(len(audio_files), len(image_files))
        if pair_count == 0:
            return BatchResult(())
        output_root = source_path.parent / output_directory if source_path.is_file() else source_path / output_directory
        output_root.mkdir(parents=True, exist_ok=True)
        artwork_settings = settings or ArtworkSettings()
        results: list[ProcessingResult] = []
        was_cancelled = False
        for index, audio_path in enumerate(audio_files[:pair_count], start=1):
            if cancelled is not None and cancelled():
                was_cancelled = True
                break
            image_path = image_files[index - 1]
            if progress is not None:
                progress(f"{index}/{pair_count}: Merging Pair {audio_path.name} 🔗 {image_path.name}", index - 1, pair_count)
            destination_dir = mirrored_output_directory(source_path, audio_path, output_root)
            prepared_path: Path | None = None
            try:
                prepared_path = prepare_artwork(image_path, destination_dir, artwork_settings)
                # Bulk/folder operations live in a dedicated output directory, so
                # preserve the source basename without the single-file safety suffix.
                output_path = destination_dir / audio_path.name
                if audio_path.suffix.lower() == ".aac":
                    output_path = output_path.with_suffix(".m4a")
                result = embed_artwork(audio_path, prepared_path, output_path)
            except (OSError, RuntimeError, ValueError) as error:
                result = ProcessingResult(audio_path, None, False, str(error))
            finally:
                if prepared_path is not None and prepared_path != image_path.resolve():
                    prepared_path.unlink(missing_ok=True)
            results.append(result)
            if result.success and result.output is not None:
                self._log(self._translator("✅ Embedded artwork in audio -> {filename}").format(filename=result.output.name))
            elif not result.success:
                self._log(self._translator("❌ Could not embed artwork for '{filename}': {error}. The standalone image was kept.").format(filename=audio_path.name, error=result.message))
            if progress is not None:
                progress(f"{index}/{pair_count}: Merging Pair {audio_path.name} 🔗 {image_path.name}", index, pair_count)
        return BatchResult(tuple(results), was_cancelled)


# ---------------------------------------------------------------------------
# Canonical render/embedding routines (formerly original_engine.py).
#
# These are deliberately kept verbatim. They are *not* methods of the
# ProcessingEngine above: they are called as ``LegacyRenderCore.method(adapter, ...)``
# with a duck-typed ``self`` (LegacyRendererAdapter, or a bare object for the
# embedding helpers) that supplies .root, .tr, .write_system_log and the setting
# attributes. Keeping them in their own class also avoids clobbering the name
# ProcessingEngine, which the GUI imports from this module.
# ---------------------------------------------------------------------------
class LegacyRenderCore:
    """Verbatim waveform-render and metadata-embedding routines."""

    def _embed_ogg_waveform_artwork(self, audio_path, image_path, output_path, width, height, image_is_jpg):
        """Copy an OGG/OGA file and replace its Vorbis-comment picture without remuxing the image as video."""
        temp_path = None
        try:
            # Mutagen stores OGG cover images as METADATA_BLOCK_PICTURE comments.
            # The audio stream is copied byte-for-byte; no audio re-encoding occurs.
            from mutagen import File as MutagenFile
            from mutagen.flac import Picture

            fd, temp_path = tempfile.mkstemp(
                prefix=".swarm_ogg_cover_", suffix=".ogg", dir=os.path.dirname(output_path) or "."
            )
            os.close(fd)
            shutil.copy2(audio_path, temp_path)

            audio = MutagenFile(temp_path)
            if audio is None or getattr(audio, "tags", None) is None:
                raise RuntimeError("Mutagen could not read this OGG/OGA container's tags")

            picture = Picture()
            picture.type = 3  # Cover (front)
            picture.mime = "image/jpeg" if image_is_jpg else "image/png"
            picture.desc = "Cover (front)"
            picture.width = max(1, int(width))
            picture.height = max(1, int(height))
            picture.depth = 24 if image_is_jpg else 32
            picture.colors = 0
            with open(image_path, "rb") as image_file:
                picture.data = image_file.read()
            if not picture.data:
                raise RuntimeError("the generated cover image is empty")

            # Replace older cover-picture comments instead of accumulating multiple covers.
            for old_key in ("metadata_block_picture", "coverart", "coverartmime"):
                try:
                    audio.tags.pop(old_key, None)
                except (AttributeError, TypeError):
                    pass
            encoded_picture = base64.b64encode(picture.write()).decode("ascii")
            audio["metadata_block_picture"] = [encoded_picture]
            audio.save()

            # Reload and verify that the output actually contains the picture metadata.
            verify = MutagenFile(temp_path)
            if (not os.path.isfile(temp_path) or os.path.getsize(temp_path) == 0 or
                    verify is None or not getattr(verify, "tags", None) or
                    not verify.tags.get("metadata_block_picture")):
                raise RuntimeError("the OGG cover artwork could not be verified after saving")

            os.replace(temp_path, output_path)
            temp_path = None
            return True, ""
        except ImportError:
            return False, "OGG/OGA artwork embedding requires the Python 'mutagen' package"
        except Exception as exc:
            return False, str(exc)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _embed_aiff_waveform_artwork(self, audio_path, image_path, output_path, image_is_jpg):
        """Embed an AIFF cover as an ID3 APIC frame while preserving the audio data."""
        temp_path = None
        try:
            from mutagen.aiff import AIFF
            from mutagen.id3 import APIC

            fd, temp_path = tempfile.mkstemp(
                prefix=".swarm_aiff_cover_", suffix=os.path.splitext(output_path)[1],
                dir=os.path.dirname(output_path) or "."
            )
            os.close(fd)
            shutil.copy2(audio_path, temp_path)

            audio = AIFF(temp_path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall("APIC")
            with open(image_path, "rb") as image_file:
                picture_data = image_file.read()
            if not picture_data:
                raise RuntimeError("the generated cover image is empty")
            audio.tags.add(APIC(
                encoding=3,
                mime="image/jpeg" if image_is_jpg else "image/png",
                type=3,
                desc="Cover (front)",
                data=picture_data,
            ))
            audio.save()

            verify = AIFF(temp_path)
            if (not os.path.isfile(temp_path) or os.path.getsize(temp_path) == 0 or
                    verify.tags is None or not any(frame.FrameID == "APIC" for frame in verify.tags.values())):
                raise RuntimeError("the AIFF cover artwork could not be verified after saving")

            os.replace(temp_path, output_path)
            temp_path = None
            return True, ""
        except ImportError:
            return False, "AIFF artwork embedding requires the Python 'mutagen' package"
        except Exception as exc:
            return False, str(exc)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _embed_waveform_artwork_with_ffmpeg(self, audio_path, image_path, output_path, video_codec):
        """Embed a cover image in MP3/FLAC/M4A/AIFF via a checked, audio-only input map."""
        fd, temp_path = tempfile.mkstemp(
            prefix=".swarm_embed_", suffix=os.path.splitext(output_path)[1],
            dir=os.path.dirname(output_path) or "."
        )
        os.close(fd)
        try:
            command = [
                "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-i", audio_path, "-i", image_path,
                # Explicit audio mapping excludes any existing attached-picture stream in the input.
                "-map", "0:a:0", "-map", "1:v:0", "-map_metadata", "0",
                "-c:a", "copy", "-c:v", video_codec, "-disposition:v:0", "attached_pic",
                temp_path,
            ]
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                    text=True, check=False)
            if result.returncode != 0 or not os.path.isfile(temp_path) or os.path.getsize(temp_path) == 0:
                details = (result.stderr or "FFmpeg did not produce a valid output file").strip()
                return False, details[-700:]
            os.replace(temp_path, output_path)
            temp_path = None
            return True, ""
        except OSError as exc:
            return False, str(exc)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


    def execute_single_waveform_render(self, audio_path, output_dir, cmap_engine, preview_only=False, render_size=None, output_image_path=None, preview_settings=None):
        """Render with the canonical waveform math; preview mode only changes output handling."""
        def setting(name, widget_name):
            if preview_settings is not None:
                return preview_settings[name]
            value = getattr(self, widget_name)
            return value.get() if callable(getattr(value, "get", None)) else value

        file_name = os.path.basename(audio_path)
        file_base, file_ext = os.path.splitext(file_name)
        ext = file_ext.lower()

        is_jpg = (setting("format_menu", "format_menu") == "JPG" and not preview_only)
        out_img_ext = "jpg" if is_jpg else "png"
        if output_image_path is None:
            output_image_path = os.path.join(output_dir, f"{file_base}.{out_img_ext}")
        temp_wav_name = ".swarm_temp_preview.wav" if preview_only else f".swarm_temp_core_{file_base}.wav"
        temp_wav = os.path.join(output_dir, temp_wav_name)
        # Decode only the first audio stream. In particular, ignore attached album-art
        # video streams that may already exist inside an MP3 or another audio container.
        try:
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
            decode = subprocess.run(
                ["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
                 "-i", audio_path, "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "11025",
                 "-c:a", "pcm_s16le", temp_wav],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False,
            )
            if decode.returncode != 0 or not os.path.isfile(temp_wav) or os.path.getsize(temp_wav) <= 44:
                details = (decode.stderr or "FFmpeg did not produce decoded audio").strip()
                self.root.after(0, lambda fn=file_name: self.write_system_log(
                    self.tr("❌ Error: Core engine codec failure decoding '{filename}'.").format(filename=fn)
                ))
                self.root.after(0, lambda fn=file_name, err=details[-400:]: self.write_system_log(
                    self.tr("Audio decoding details for '{filename}': {error}").format(filename=fn, error=err)
                ))
                return

            with wave.open(temp_wav, 'rb') as w:
                num_frames = w.getnframes()
                raw_bytes = w.readframes(num_frames)
        except (OSError, wave.Error, ValueError) as exc:
            self.root.after(0, lambda fn=file_name, err=str(exc): self.write_system_log(
                self.tr("❌ Error: Core engine codec failure decoding '{filename}'.").format(filename=fn)
            ))
            return
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except OSError:
                    pass

        if not raw_bytes:
            self.root.after(0, lambda fn=file_name: self.write_system_log(
                self.tr("⚠️ Track '{filename}' contains no audio samples.").format(filename=fn)
            ))
            return
        audio_samples = np.frombuffer(raw_bytes, dtype='<i2').astype(np.float32)
        bars = setting("num_bars", "num_bars")
        samples_per_bar = len(audio_samples) // bars
        
        if samples_per_bar == 0:
            self.root.after(0, lambda: self.write_system_log(self.tr("⚠️ Track '{filename}' is too short for the selected bar count.").format(filename=file_name)))
            return

        raw_heights = [np.max(np.abs(audio_samples[i*samples_per_bar : (i+1)*samples_per_bar])) for i in range(bars)]
        max_peak = max(raw_heights) if max(raw_heights) > 0 else 1
        normalized_heights = [(h / max_peak) * 0.9 + 0.1 for h in raw_heights]

        render_dpi = 100 if preview_only else max(1, int(setting("target_dpi", "target_dpi")))
        if render_size is not None:
            w_in = int(render_size[0]) / render_dpi
            h_in = int(render_size[1]) / render_dpi
        else:
            w_in = setting("width_val", "width_val") / render_dpi
            h_in = setting("height_val", "height_val") / render_dpi

        canvas_bg = 'none' if (setting("is_transparent", "is_transparent") and not is_jpg) else setting("bg_solid_color", "bg_solid_color")
        fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=render_dpi, facecolor=canvas_bg)
        ax.set_facecolor(canvas_bg)

        x_positions = np.arange(bars)



        # THE UNIFIED MULTI-GEOMETRY WAVE RENDERING ENGINE PIPELINE
        geom_type = setting("peak_geometry_shape", "peak_geometry_shape")
        is_solid = setting("is_solid_color_mode", "is_solid_color_mode")
        
        # Calculate a highly responsive vector border thickness based on your total bar counts
        calculated_edge_width = 0.75 if bars > 180 else 1.2
        # Lollipop stems stay thin, while the endpoint dots remain clearly
        # distinguishable and scale with the spacing between bars.
        bar_spacing_pt = (w_in * 72.0) / max(1, bars)
        lollipop_stem_width_pt = max(0.65, bar_spacing_pt * 0.24)
        lollipop_marker_size = max(2.0, bar_spacing_pt * 0.70)

        def draw_sliced_pointed_bar(x, height, y0, y1, color, shape, overlap=0.0):
            """Draw a color slice while preserving the exact pointed silhouette."""
            h = max(float(height), 1e-9)
            # Slight overlap prevents antialiased black hairlines between adjacent slices.
            a = max(0.0, y0 - overlap)
            b = min(h, y1 + overlap)
            if shape == "Spike":
                # A single continuous triangular silhouette from centerline to peak.
                w0 = 0.375 * max(0.0, 1.0 - a / h)
                w1 = 0.375 * max(0.0, 1.0 - b / h)
                ax.fill([x-w0, x+w0, x+w1, x-w1], [a, a, b, b],
                        color=color, edgecolor='none', linewidth=0, antialiased=False)
                ax.fill([x-w0, x+w0, x+w1, x-w1], [-a, -a, -b, -b],
                        color=color, edgecolor='none', linewidth=0, antialiased=False)

        def draw_arrow_spear(x, height, color, stem_width=0.13, head_half_width=0.22):
            """Draw a clear arrowhead on a slightly thicker stem."""
            h = max(float(height), 1e-9)
            # Keep the arrowhead visibly triangular at both high and low bar counts.
            head_h = min(h * 0.16, 0.16, h * 0.35)
            stem_end = max(0.0, h - head_h)
            ax.bar(x, stem_end, width=stem_width, color=color, bottom=0,
                   edgecolor='none', linewidth=0)
            ax.bar(x, stem_end, width=stem_width, color=color, bottom=-stem_end,
                   edgecolor='none', linewidth=0)
            ax.fill([x-head_half_width, x, x+head_half_width],
                    [stem_end, h, stem_end], color=color, edgecolor='none', linewidth=0)
            ax.fill([x-head_half_width, x, x+head_half_width],
                    [-stem_end, -h, -stem_end], color=color, edgecolor='none', linewidth=0)

        if is_solid:
            # Solid mode has exactly one active node; pass a single color to Matplotlib.
            target_color = setting("color_nodes", "color_nodes")[0]
            if geom_type == "Capsule":
                # Rectangles do not support rounded bar ends reliably. Draw each
                # symmetric bar as a round-capped vertical stroke instead.
                capsule_width_pt = max(1.0, (w_in * 72.0 / max(1, bars)) * 0.75)
                for i, height in enumerate(normalized_heights):
                    ax.plot([x_positions[i], x_positions[i]], [-height, height],
                            color=target_color, linewidth=capsule_width_pt,
                            solid_capstyle="round", antialiased=True)
            elif geom_type == "Lollipop":
                for i, height in enumerate(normalized_heights):
                    ax.plot([x_positions[i], x_positions[i]], [-height, height],
                            color=target_color, linewidth=lollipop_stem_width_pt,
                            solid_capstyle="butt", antialiased=True)
                    ax.plot([x_positions[i], x_positions[i]], [height, -height],
                            marker='o', markersize=lollipop_marker_size,
                            color=target_color, markeredgecolor='none', linestyle='None')
            elif geom_type == "Spike":
                for i, height in enumerate(normalized_heights):
                    ax.fill([x_positions[i]-0.375, x_positions[i], x_positions[i]+0.375], [0, height, 0], color=target_color, edgecolor='none')
                    ax.fill([x_positions[i]-0.375, x_positions[i], x_positions[i]+0.375], [0, -height, 0], color=target_color, edgecolor='none')
            elif geom_type == "ArrowSpear":
                for i, height in enumerate(normalized_heights):
                    draw_arrow_spear(x_positions[i], height, target_color)
            else:
                ax.bar(x_positions, normalized_heights, width=0.75, color=target_color, bottom=0, edgecolor='none')
                ax.bar(x_positions, normalized_heights, width=0.75, color=target_color, bottom=-np.array(normalized_heights), edgecolor='none')
            
        elif setting("gradient_direction", "gradient_direction") == "Horizontal":
            for i, height in enumerate(normalized_heights):
                position_ratio = i / (bars - 1) if bars > 1 else 0
                bar_color = cmap_engine(position_ratio)
                
                if geom_type == "Capsule":
                    # Round-capped strokes create genuine rounded tips in horizontal flow.
                    capsule_width_pt = max(1.0, (w_in * 72.0 / max(1, bars)) * 0.75)
                    ax.plot([x_positions[i], x_positions[i]], [-height, height],
                            color=bar_color, linewidth=capsule_width_pt,
                            solid_capstyle="round", antialiased=True)
                elif geom_type == "Lollipop":
                    ax.plot([x_positions[i], x_positions[i]], [-height, height],
                            color=bar_color, linewidth=lollipop_stem_width_pt,
                            solid_capstyle="butt", antialiased=True)
                    ax.plot([x_positions[i], x_positions[i]], [height, -height],
                            marker='o', markersize=lollipop_marker_size,
                            color=bar_color, markeredgecolor='none', linestyle='None')
                elif geom_type == "Spike":
                    ax.fill([x_positions[i]-0.375, x_positions[i], x_positions[i]+0.375], [0, height, 0], color=bar_color, edgecolor='none')
                    ax.fill([x_positions[i]-0.375, x_positions[i], x_positions[i]+0.375], [0, -height, 0], color=bar_color, edgecolor='none')
                elif geom_type == "ArrowSpear":
                    draw_arrow_spear(x_positions[i], height, bar_color)
                else:
                    ax.bar(x_positions[i], height, width=0.75, color=bar_color, bottom=0, edgecolor='none')
                    ax.bar(x_positions[i], height, width=0.75, color=bar_color, bottom=-height, edgecolor='none')
                

        else:
            # Option C: Vertical Slices Peak Meter Flow Mode
            slices = setting("slices_val", "slices_val")
            
            if geom_type == "Capsule":
                #  TRUE CAPSULE FIX: Uses native coordinate grid widths instead of pixel blocks
                # This guarantees bars never smash together, leaving clean, distinct pill gaps!
                for i, height in enumerate(normalized_heights):
                    y_coords = np.linspace(0, height, slices)
                    
                    # Calculate a precise relative width that exactly mimics a 0.75 bar width setting
                    native_scale_width = (fig.get_size_inches()[0] * fig.dpi) / bars * 0.55
                    native_scale_width = max(1.0, native_scale_width) # Protect low-res runs from vanishing
                    
                    for s in range(len(y_coords) - 1):
                        b_val = y_coords[s]
                        t_val = y_coords[s + 1]
                        slice_color = cmap_engine(b_val)
                        
                        # Draw top track pill components cleanly
                        ax.plot([x_positions[i], x_positions[i]], [b_val, t_val], 
                                color=slice_color, solid_capstyle='round', linewidth=native_scale_width)
                        # Draw bottom mirroring pill components cleanly
                        ax.plot([x_positions[i], x_positions[i]], [-b_val, -t_val], 
                                color=slice_color, solid_capstyle='round', linewidth=native_scale_width)


            else:
                # Lollipop follows the user's slice-resolution setting below 200,
                # preserving visible color bands. At 200, switch to a dense gradient
                # for smooth stems while keeping the same lollipop geometry.
                if geom_type == "Lollipop":
                    configured_slices = max(2, int(slices))
                    for i, height in enumerate(normalized_heights):
                        if configured_slices < 200:
                            segment_count = configured_slices - 1
                        else:
                            segment_count = min(768, max(256, int(h_in * setting("target_dpi", "target_dpi") * height)))
                        y_steps = np.linspace(0.0, height, segment_count + 1)
                        upper_segments = [[(x_positions[i], y_steps[j]),
                                           (x_positions[i], y_steps[j + 1])]
                                          for j in range(segment_count)]
                        lower_segments = [[(x_positions[i], -y_steps[j]),
                                           (x_positions[i], -y_steps[j + 1])]
                                          for j in range(segment_count)]
                        segment_colors = [cmap_engine((y_steps[j] + y_steps[j + 1]) / 2.0)
                                          for j in range(segment_count)]
                        ax.add_collection(LineCollection(
                            upper_segments, colors=segment_colors,
                            linewidths=lollipop_stem_width_pt, antialiaseds=True))
                        ax.add_collection(LineCollection(
                            lower_segments, colors=segment_colors,
                            linewidths=lollipop_stem_width_pt, antialiaseds=True))
                        peak_color = cmap_engine(height)
                        ax.plot([x_positions[i]], [height], marker='o', linestyle='None',
                                markersize=lollipop_marker_size, color=peak_color,
                                markeredgecolor='none')
                        ax.plot([x_positions[i]], [-height], marker='o', linestyle='None',
                                markersize=lollipop_marker_size, color=peak_color,
                                markeredgecolor='none')
                else:
                    # Other geometry styles retain their existing slice-based rendering.
                    for i, height in enumerate(normalized_heights):
                        y_steps = np.linspace(0, height, slices)

                        # For vertical-flow Sharp Spikes, keep the existing horizontal
                        # gradient bands but clip them to one continuous triangular path.
                        # This prevents the outer edges from becoming stair-stepped when
                        # the gradient slice resolution is low, without changing the colors.
                        if geom_type == "Spike":
                            x = x_positions[i]
                            half_width = 0.375
                            upper_triangle = Polygon(
                                [(x - half_width, 0), (x, height), (x + half_width, 0)],
                                closed=True, facecolor='none', edgecolor='none',
                                transform=ax.transData)
                            lower_triangle = Polygon(
                                [(x - half_width, 0), (x, -height), (x + half_width, 0)],
                                closed=True, facecolor='none', edgecolor='none',
                                transform=ax.transData)
                            ax.add_patch(upper_triangle)
                            ax.add_patch(lower_triangle)
                            for s in range(len(y_steps) - 1):
                                b_val = y_steps[s]
                                t_val = y_steps[s + 1]
                                slice_color = cmap_engine(b_val)
                                upper_band = Rectangle(
                                    (x - half_width, b_val), 2 * half_width,
                                    t_val - b_val, facecolor=slice_color,
                                    edgecolor='none', linewidth=0, antialiased=False)
                                lower_band = Rectangle(
                                    (x - half_width, -t_val), 2 * half_width,
                                    t_val - b_val, facecolor=slice_color,
                                    edgecolor='none', linewidth=0, antialiased=False)
                                ax.add_patch(upper_band)
                                ax.add_patch(lower_band)
                                upper_band.set_clip_path(upper_triangle)
                                lower_band.set_clip_path(lower_triangle)
                            continue

                        for s in range(len(y_steps) - 1):
                            b_val = y_steps[s]
                            t_val = y_steps[s + 1]
                            slice_color = cmap_engine(b_val)

                            if geom_type == "ArrowSpear":
                                # Gradient stem slices stay narrow; only the outer peak gets
                                # the small arrowhead, matching the original reference design.
                                stem_width = 0.13
                                head_half_width = 0.22
                                # Match the solid/horizontal arrowhead proportions.
                                head_h = min(height * 0.16, 0.16, height * 0.35)
                                stem_end = max(0.0, height - head_h)
                                if b_val < stem_end:
                                    sb = b_val
                                    st = min(t_val, stem_end)
                                    if st > sb:
                                        ax.bar(x_positions[i], st - sb, width=stem_width,
                                               color=slice_color, bottom=sb, edgecolor='none', linewidth=0)
                                        ax.bar(x_positions[i], st - sb, width=stem_width,
                                               color=slice_color, bottom=-st, edgecolor='none', linewidth=0)
                                # Draw each tip once after all stem slices (last slice only).
                                if s == len(y_steps) - 2:
                                    tip_color = cmap_engine(height)
                                    ax.fill([x_positions[i]-head_half_width, x_positions[i],
                                             x_positions[i]+head_half_width],
                                            [stem_end, height, stem_end],
                                            color=tip_color, edgecolor='none', linewidth=0)
                                    ax.fill([x_positions[i]-head_half_width, x_positions[i],
                                             x_positions[i]+head_half_width],
                                            [-stem_end, -height, -stem_end],
                                            color=tip_color, edgecolor='none', linewidth=0)
                            else:
                                ax.bar(x_positions[i], t_val - b_val, width=0.75, color=slice_color, bottom=b_val, edgecolor='none')
                                ax.bar(x_positions[i], t_val - b_val, width=0.75, color=slice_color, bottom=-t_val, edgecolor='none')


   
        ax.set_ylim(-1.1, 1.1)
        ax.set_xlim(-1, bars)
        ax.axis('off')
        fig.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)

        try:
            fig.savefig(output_image_path, dpi=render_dpi, pad_inches=0, transparent=(setting("is_transparent", "is_transparent") and not is_jpg))
        finally:
            fig.clear()
            plt.close(fig)
            del fig, ax
            # Release the decoded audio buffers for this track before the next one.
            audio_samples = raw_bytes = raw_heights = normalized_heights = None
            gc.collect()
        if preview_only:
            return os.path.isfile(output_image_path) and os.path.getsize(output_image_path) > 0

        self.root.after(0, lambda: self.write_system_log(self.tr("📸 Image generated: {filename}").format(filename=os.path.basename(output_image_path))))

        v_codec = "mjpeg" if is_jpg else "png"

        # Image-only mode deliberately stops after rendering and never invokes
        # Mutagen or FFmpeg artwork embedding.
        if setting("generate_image_only", "generate_image_only"):
            return True

        # Embed artwork only in containers that can represent it. WAV stays image-only;
        # raw AAC has no artwork metadata container, so its output is packaged as M4A.
        embedded_output = None
        if ext == '.mp3':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.mp3")
        elif ext in ('.ogg', '.oga', '.opus'):
            embedded_extension = ".opus" if ext == ".opus" else ".ogg"
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art{embedded_extension}")
        elif ext == '.flac':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.flac")
        elif ext == '.m4a':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.m4a")
        elif ext == '.aac':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.m4a")
        elif ext == '.aiff':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.aiff")
        elif ext == '.aif':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.aif")

        if embedded_output:
            if ext in ('.ogg', '.oga', '.opus'):
                success, error = self._embed_ogg_waveform_artwork(
                    audio_path, output_image_path, embedded_output,
                    setting("width_val", "width_val"), setting("height_val", "height_val"), is_jpg,
                )
            elif ext in ('.aiff', '.aif'):
                success, error = self._embed_aiff_waveform_artwork(
                    audio_path, output_image_path, embedded_output, is_jpg,
                )
            else:
                success, error = self._embed_waveform_artwork_with_ffmpeg(
                    audio_path, output_image_path, embedded_output, v_codec,
                )

            if success:
                self.root.after(0, lambda fn=os.path.basename(embedded_output): self.write_system_log(
                    self.tr("✅ Embedded artwork in audio -> {filename}").format(filename=fn)
                ))
                if ext == '.aac':
                    self.root.after(0, lambda fn=os.path.basename(embedded_output): self.write_system_log(
                        self.tr("Raw AAC has no standard cover-art container; created an M4A file -> {filename}").format(filename=fn)
                    ))
                if not setting("keep_standalone_png", "keep_standalone_png"):
                    try:
                        os.remove(output_image_path)
                    except OSError:
                        pass
            else:
                # Never leave a zero-byte/broken *_with_art file. Keep the standalone image.
                self.root.after(0, lambda fn=file_name, err=error: self.write_system_log(
                    self.tr("❌ Could not embed artwork for '{filename}': {error}. The standalone image was kept.").format(
                        filename=fn, error=err
                    )
                ))


    def execute_single_circular_waveform(self, audio_path, output_dir, cmap_engine, mode=None, render_size=None, output_image_path=None, preview_only=False, preview_settings=None):
        """Render one selected circular visualization and optionally embed it as cover art."""
        import subprocess
        import matplotlib.pyplot as plt

        def setting(name, widget_name):
            if preview_settings is not None:
                return preview_settings[name]
            value = getattr(self, widget_name)
            # Most settings are Tk variables; color_nodes is already a Python list.
            # Calling .get() on that list breaks every non-preview circular render.
            return value.get() if callable(getattr(value, "get", None)) else value

        def log_ui(callback):
            if preview_settings is None:
                self.root.after(0, callback)

        file_name = os.path.basename(audio_path)
        file_base, file_ext = os.path.splitext(file_name)
        ext = file_ext.lower()
        is_jpg = setting("format", "format_menu") == "JPG" and not preview_only
        image_ext = "jpg" if is_jpg else "png"
        mode = mode or setting("circular_mode", "circular_mode")
        suffix = {
            "waveform": "circular",
            "spectrum": "radial_spectrum",
            "minimal": "minimal_circular",
        }.get(mode, "circular")
        if output_image_path is None:
            output_image_path = os.path.join(output_dir, f"{file_base}_{suffix}.{image_ext}")
        temp_wav = os.path.join(output_dir, f".swarm_temp_{file_base}_{suffix}.wav")

        try:
            # Decode only the first audio stream and explicitly discard video/artwork
            # streams. Some MP3/M4A files contain an attached cover image that FFmpeg
            # otherwise may treat as a video stream during WAV conversion.
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
            decode = subprocess.run(
                ["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
                 "-i", audio_path, "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "11025",
                 "-c:a", "pcm_s16le", temp_wav],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False,
            )
            if decode.returncode != 0 or not os.path.isfile(temp_wav) or os.path.getsize(temp_wav) <= 44:
                details = (decode.stderr or "FFmpeg did not produce decoded audio").strip()
                log_ui( lambda fn=file_name: self.write_system_log(
                    self.tr("❌ Error: Core engine codec failure decoding '{filename}'.").format(filename=fn)
                ))
                log_ui( lambda fn=file_name, err=details[-400:]: self.write_system_log(
                    self.tr("Audio decoding details for '{filename}': {error}").format(filename=fn, error=err)
                ))
                return

            with wave.open(temp_wav, 'rb') as wav_file:
                frame_count = wav_file.getnframes()
                raw_bytes = wav_file.readframes(frame_count)
            if not raw_bytes:
                log_ui( lambda fn=file_name: self.write_system_log(
                    self.tr("⚠️ Track '{filename}' contains no audio samples.").format(filename=fn)
                ))
                return
            audio_samples = np.frombuffer(raw_bytes, dtype='<i2').astype(np.float32)
        except (OSError, wave.Error, ValueError) as exc:
            log_ui( lambda fn=file_name, err=str(exc): self.write_system_log(
                self.tr("❌ Circular waveform failed for '{filename}': {error}").format(filename=fn, error=err)
            ))
            return
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except OSError:
                    pass

        size_px = int(render_size) if render_size is not None else max(256, min(12000, int(self.circular_size.get())))
        if size_px < 1:
            raise ValueError("Invalid circular render size")
        dpi = max(1, int(setting("target_dpi", "target_dpi")))
        rotation = np.deg2rad(int(setting("circular_rotation", "circular_rotation")))
        canvas_bg = 'none' if (setting("is_transparent", "is_transparent") and not is_jpg) else setting("bg_solid_color", "bg_solid_color")
        fig = None
        try:
            fig = plt.figure(figsize=(size_px / dpi, size_px / dpi), dpi=dpi, facecolor=canvas_bg)

            # Colors are shared across all circular modes.
            if setting("is_solid_color_mode", "is_solid_color_mode"):
                color_map = None
                solid_color = setting("color_nodes", "color_nodes")[0]
            else:
                stops = setting("color_nodes", "color_nodes").copy()
                if setting("reverse_color_map", "reverse_color_map"):
                    stops.reverse()
                color_map = LinearSegmentedColormap.from_list('swarm_circular_grad', stops)
                solid_color = setting("color_nodes", "color_nodes")[0]

            def draw_radial_arrow_spear(axis, angle, base_radius, outer_radius, color, bar_width):
                """Draw one outward-facing Arrow-Spear for a polar visualizer."""
                bar_height = max(0.0, float(outer_radius) - float(base_radius))
                if bar_height <= 0.0:
                    return

                # Keep the arrowhead proportional to each bar, capped so long bars
                # do not get oversized heads. This only affects circular rendering.
                head_height = min(bar_height * 0.28, 0.10)
                stem_end = max(base_radius, outer_radius - head_height)

                # Size the stem in output pixels, then convert to points. Using a
                # line rather than a data-coordinate rectangle avoids irregular
                # apparent widths caused by fractional-pixel alignment.
                mean_radius = (base_radius + stem_end) / 2.0
                stem_width_px = max(
                    1.0, bar_width * max(mean_radius, 0.12) * size_px * 0.5 * 0.24
                )
                stem_width_pt = stem_width_px * 72.0 / dpi
                if stem_end > base_radius:
                    axis.plot(
                        [angle, angle], [base_radius, stem_end], color=color,
                        linewidth=stem_width_pt, solid_capstyle="butt",
                        antialiased=True, clip_on=True,
                    )

                head_half_angle = bar_width * 0.44
                axis.fill(
                    [angle - head_half_angle, angle, angle + head_half_angle],
                    [stem_end, outer_radius, stem_end],
                    facecolor=color, edgecolor='none', linewidth=0, antialiased=True,
                )

            def draw_radial_arrow_spear_inward(
                axis, angle, anchor_radius, tip_radius, color, bar_width,
                match_outward_stem_width=False,
            ):
                """Draw one Arrow-Spear pointing toward the center.

                In combined mode, use the mirrored outward stem's width so the
                two sides meet with a consistent diameter at the baseline.
                """
                bar_height = max(0.0, float(anchor_radius) - float(tip_radius))
                if bar_height <= 0.0:
                    return
                head_height = min(bar_height * 0.28, 0.10)
                head_base_radius = min(anchor_radius, tip_radius + head_height)
                mean_radius = (anchor_radius + head_base_radius) / 2.0
                if match_outward_stem_width:
                    # Match the stem width to the existing outward-facing stem.
                    mean_radius = anchor_radius + (bar_height - head_height) / 2.0
                stem_width_px = max(
                    1.0, bar_width * max(mean_radius, 0.12) * size_px * 0.5 * 0.24
                )
                stem_width_pt = stem_width_px * 72.0 / dpi

                head_half_angle = bar_width * 0.44
                stem_start_radius = head_base_radius
                if match_outward_stem_width:
                    # Polar angular widths shrink toward the center. Enforce a
                    # minimum physical arrowhead base width equal to the stem,
                    # even for arrows close to the center. A small minimum base
                    # radius keeps the angle calculation well-defined; adjacent
                    # arrowheads may overlap near the center, which is intentional.
                    min_half_width_radius = stem_width_px / max(1.0, float(size_px))
                    head_base_radius = min(
                        anchor_radius,
                        max(head_base_radius, min_half_width_radius),
                    )
                    if head_base_radius > 0.0:
                        min_head_half_angle = np.arcsin(min(
                            1.0, min_half_width_radius / head_base_radius
                        ))
                        head_half_angle = max(head_half_angle, float(min_head_half_angle))


                # Extend the stem about two output pixels underneath the
                # arrowhead in every inward Arrow-Spear mode. Drawing the head
                # afterward covers the overlap, preventing antialiasing from
                # leaving a hairline seam. This does not alter the stem width,
                # arrowhead shape, or the existing outward-only rendering.
                stem_start_radius = max(
                    tip_radius, head_base_radius - 4.0 / max(1.0, float(size_px))
                )

                if anchor_radius > stem_start_radius:
                    axis.plot(
                        [angle, angle], [stem_start_radius, anchor_radius], color=color,
                        linewidth=stem_width_pt, solid_capstyle="butt",
                        antialiased=True, clip_on=True,
                    )
                axis.fill(
                    [angle - head_half_angle, angle, angle + head_half_angle],
                    [head_base_radius, tip_radius, head_base_radius],
                    facecolor=color, edgecolor='none', linewidth=0, antialiased=True,
                )

            if mode == "minimal":
                # Minimal mode is a true signed-sample waveform, drawn as a clean
                # continuous line in Cartesian coordinates to support gradient colors.
                from matplotlib.collections import LineCollection
                ax = fig.add_axes([0, 0, 1, 1])
                ax.set_xlim(-1.0, 1.0)
                ax.set_ylim(-1.0, 1.0)
                ax.set_aspect('equal', adjustable='box')
                ax.set_axis_off()
                ax.set_facecolor(canvas_bg)
                point_count = min(1200, max(360, int(setting("num_bars", "num_bars")) * 2))
                sample_indexes = np.linspace(0, len(audio_samples) - 1, point_count, dtype=int)
                signed_samples = audio_samples[sample_indexes].astype(np.float32)
                sample_peak = float(np.max(np.abs(signed_samples))) if signed_samples.size else 0.0
                if sample_peak > 0:
                    signed_samples = signed_samples / sample_peak
                base_radius = float(setting("minimal_wave_base_radius", "minimal_wave_base_radius"))
                amplitude = float(setting("minimal_wave_amplitude", "minimal_wave_amplitude"))
                radii = np.clip(base_radius + signed_samples * amplitude, 0.08, 0.94)
                angles = np.linspace(0, 2 * np.pi, point_count, endpoint=False) + rotation - np.pi / 2
                points = np.column_stack((radii * np.cos(angles), radii * np.sin(angles)))
                points = np.vstack((points, points[0]))
                segments = np.stack((points[:-1], points[1:]), axis=1)
                if color_map is None:
                    segment_colors = [solid_color] * len(segments)
                elif setting("gradient_direction", "gradient_direction") == "Horizontal":
                    segment_colors = [color_map(i / max(1, len(segments) - 1)) for i in range(len(segments))]
                else:
                    amplitude_values = np.clip((signed_samples + 1.0) / 2.0, 0.0, 1.0)
                    segment_colors = [color_map(float(value)) for value in amplitude_values]
                    segment_colors.append(segment_colors[0])
                collection = LineCollection(
                    segments, colors=segment_colors,
                    linewidths=float(setting("minimal_wave_line_width", "minimal_wave_line_width")),
                    capstyle='round', joinstyle='round', antialiased=True,
                )
                ax.add_collection(collection)
            else:
                ax = fig.add_axes([0, 0, 1, 1], projection='polar')
                ax.set_facecolor(canvas_bg)
                ax.set_theta_offset(np.pi / 2)
                ax.set_theta_direction(-1)
                ax.set_ylim(0, 1.0)
                ax.set_axis_off()

                if mode == "spectrum":
                    # Average short-window FFT magnitudes across the track to build
                    # a stable frequency profile rather than a single whole-file FFT.
                    band_count = max(32, min(512, int(setting("radial_spectrum_bins", "radial_spectrum_bins"))))
                    frame_size = 2048
                    hop_size = 1024
                    if len(audio_samples) < frame_size:
                        padded = np.pad(audio_samples, (0, frame_size - len(audio_samples)))
                        frame_starts = [0]
                        samples_for_fft = padded
                    else:
                        frame_starts = list(range(0, len(audio_samples) - frame_size + 1, hop_size))
                        if len(frame_starts) > 160:
                            chosen = np.linspace(0, len(frame_starts) - 1, 160, dtype=int)
                            frame_starts = [frame_starts[i] for i in chosen]
                        samples_for_fft = audio_samples
                    window = np.hanning(frame_size).astype(np.float32)
                    spectra = []
                    for frame_start in frame_starts:
                        frame = samples_for_fft[frame_start:frame_start + frame_size]
                        if len(frame) < frame_size:
                            frame = np.pad(frame, (0, frame_size - len(frame)))
                        spectra.append(np.abs(np.fft.rfft(frame * window))[1:])
                    average_spectrum = np.mean(spectra, axis=0) if spectra else np.ones(frame_size // 2)
                    bands = [part for part in np.array_split(average_spectrum, band_count)]
                    magnitudes = np.array([float(np.mean(part)) if len(part) else 0.0 for part in bands], dtype=np.float32)
                    max_magnitude = float(magnitudes.max()) if magnitudes.size else 0.0
                    normalized = magnitudes / max_magnitude if max_magnitude > 0 else np.zeros_like(magnitudes)
                    normalized = np.sqrt(normalized)
                    sensitivity = float(setting("radial_spectrum_sensitivity", "radial_spectrum_sensitivity"))
                    inner_radius = float(setting("radial_spectrum_inner_radius", "radial_spectrum_inner_radius"))
                    inward = bool(setting("radial_spectrum_inward", "radial_spectrum_inward"))
                    outward = bool(setting("radial_spectrum_outward", "radial_spectrum_outward"))
                    if not inward and not outward:
                        outward = True
                    combined_mode = inward and outward
                    seam_overlap = 3.0 / max(1, size_px) if combined_mode else 0.0
                    if combined_mode:
                        # Combined mode mirrors the same band magnitude in both directions.
                        # Keep each bar within the existing inward and outward limits.
                        max_height = max(0.008, min(inner_radius, 0.82 - inner_radius, 0.50))
                    elif inward:
                        max_height = max(0.008, min(inner_radius, 0.50))
                    else:
                        max_height = max(0.02, min(0.82 - inner_radius, 0.50))
                    heights = np.clip(normalized * sensitivity * 0.28, 0.008, max_height)
                    count = len(heights)
                    theta = np.linspace(0, 2 * np.pi, count, endpoint=False) + rotation
                    bar_width = (2 * np.pi / count) * 0.72
                    if color_map is None:
                        colors = [solid_color] * count
                    elif setting("gradient_direction", "gradient_direction") == "Horizontal":
                        colors = [color_map(i / max(1, count - 1)) for i in range(count)]
                    else:
                        colors = [color_map(float(value)) for value in normalized]
                    # Apply the same geometry selector used by Circular Waveform.
                    # Radial Spectrum changes the source data (FFT bands), not the
                    # available visual shapes.
                    geom_type = setting("peak_geometry_shape", "peak_geometry_shape")
                    if inward:
                        tip_radii = np.maximum(0.0, inner_radius - heights)
                        if geom_type == "Capsule":
                            for angle, tip_radius, color in zip(theta, tip_radii, colors):
                                mean_radius = (
                                    inner_radius + (inner_radius - tip_radius) / 2.0
                                    if combined_mode else (inner_radius + tip_radius) / 2.0
                                )
                                width_px = max(1.0, bar_width * mean_radius * size_px * 0.5 * 0.82)
                                width_pt = width_px * 72.0 / dpi
                                ax.plot([angle, angle], [tip_radius, inner_radius], color=color,
                                        linewidth=width_pt, solid_capstyle='round', antialiased=True, clip_on=True)
                        elif geom_type == "Lollipop":
                            for angle, tip_radius, color in zip(theta, tip_radii, colors):
                                mean_radius = (inner_radius + tip_radius) / 2.0
                                stem_radius = inner_radius if combined_mode else mean_radius
                                stem_px = max(1.0, bar_width * stem_radius * size_px * 0.5 * 0.18)
                                stem_pt = stem_px * 72.0 / dpi
                                dot_px = max(2.0, bar_width * max(tip_radius, 0.02) * size_px * 0.5 * 0.90)
                                dot_pt = dot_px * 72.0 / dpi
                                ax.plot([angle, angle], [tip_radius, inner_radius], color=color,
                                        linewidth=stem_pt, solid_capstyle='round', antialiased=True, clip_on=True)
                                ax.plot([angle], [tip_radius], marker='o', linestyle='None', markersize=dot_pt,
                                        markerfacecolor=color, markeredgecolor=color, markeredgewidth=0,
                                        antialiased=True, clip_on=True)
                        elif geom_type == "ArrowSpear":
                            for angle, tip_radius, color in zip(theta, tip_radii, colors):
                                draw_radial_arrow_spear_inward(
                                    ax, angle, inner_radius, tip_radius, color, bar_width,
                                    match_outward_stem_width=combined_mode,
                                )
                        elif geom_type == "Spike":
                            half_width = bar_width / 2.0
                            for angle, tip_radius, color in zip(theta, tip_radii, colors):
                                join_radius = inner_radius + seam_overlap if combined_mode else inner_radius
                                ax.fill([angle - half_width, angle, angle + half_width],
                                        [join_radius, tip_radius, join_radius],
                                        facecolor=color, edgecolor='none', linewidth=0, antialiased=True)
                        else:
                            inward_bar_heights = heights + seam_overlap if combined_mode else heights
                            ax.bar(
                                theta, inward_bar_heights, width=bar_width, bottom=tip_radii,
                                color=colors, edgecolor='none', align='center', linewidth=0,
                            )
                    if outward:
                        geom_type = setting("peak_geometry_shape", "peak_geometry_shape")
                        outer_radii = inner_radius + heights
                        if geom_type == "Capsule":
                            for angle, outer_radius, color in zip(theta, outer_radii, colors):
                                mean_radius = (inner_radius + outer_radius) / 2.0
                                width_px = max(1.0, bar_width * mean_radius * size_px * 0.5 * 0.82)
                                width_pt = width_px * 72.0 / dpi
                                ax.plot([angle, angle], [inner_radius, outer_radius], color=color,
                                        linewidth=width_pt, solid_capstyle='round', antialiased=True, clip_on=True)
                        elif geom_type == "Lollipop":
                            for angle, outer_radius, color in zip(theta, outer_radii, colors):
                                stem_px = max(1.0, bar_width * inner_radius * size_px * 0.5 * 0.18)
                                stem_pt = stem_px * 72.0 / dpi
                                dot_px = max(2.0, bar_width * outer_radius * size_px * 0.5 * 0.90)
                                dot_pt = dot_px * 72.0 / dpi
                                ax.plot([angle, angle], [inner_radius, outer_radius], color=color,
                                        linewidth=stem_pt, solid_capstyle='round', antialiased=True, clip_on=True)
                                ax.plot([angle], [outer_radius], marker='o', linestyle='None', markersize=dot_pt,
                                        markerfacecolor=color, markeredgecolor=color, markeredgewidth=0,
                                        antialiased=True, clip_on=True)
                        elif geom_type == "ArrowSpear":
                            for angle, outer_radius, color in zip(theta, outer_radii, colors):
                                draw_radial_arrow_spear(
                                    ax, angle, inner_radius, outer_radius, color, bar_width
                                )
                        elif geom_type == "Spike":
                            half_width = bar_width / 2.0
                            for angle, outer_radius, color in zip(theta, outer_radii, colors):
                                ax.fill([angle - half_width, angle, angle + half_width],
                                        [inner_radius, outer_radius, inner_radius],
                                        facecolor=color, edgecolor='none', linewidth=0, antialiased=True)
                        else:
                            ax.bar(
                                theta, heights, width=bar_width, bottom=inner_radius,
                                color=colors, edgecolor='none', align='center', linewidth=0,
                            )
                else:
                    # Existing circular amplitude waveform; preserve its geometry setting.
                    bars = max(40, int(setting("num_bars", "num_bars")))
                    chunks = np.array_split(audio_samples, min(bars, len(audio_samples)))
                    peaks = np.array([np.max(np.abs(chunk)) if len(chunk) else 0 for chunk in chunks], dtype=np.float32)
                    peak_max = float(peaks.max()) if peaks.size and peaks.max() > 0 else 1.0
                    normalized = peaks / peak_max
                    normalized = 0.08 + normalized * 0.92
                    count = len(normalized)
                    theta = np.linspace(0, 2 * np.pi, count, endpoint=False) + rotation
                    bar_width = (2 * np.pi / count) * 0.78
                    inner_radius = float(setting("circular_inner_radius", "circular_inner_radius"))
                    inward = bool(setting("circular_inward", "circular_inward"))
                    outward = bool(setting("circular_outward", "circular_outward"))
                    if not inward and not outward:
                        outward = True
                    combined_mode = inward and outward
                    seam_overlap = 3.0 / max(1, size_px) if combined_mode else 0.0
                    if combined_mode:
                        # Use identical heights on both sides of the baseline.
                        # The smaller of the existing limits governs combined mode.
                        heights = normalized * min(inner_radius, 0.92 - inner_radius, 0.45)
                    elif inward:
                        heights = normalized * min(inner_radius, 0.45)
                    else:
                        heights = normalized * min(0.92 - inner_radius, 0.45)
                    if color_map is None:
                        colors = [solid_color] * count
                    elif setting("gradient_direction", "gradient_direction") == "Horizontal":
                        colors = [color_map(i / max(1, count - 1)) for i in range(count)]
                    else:
                        colors = [color_map(float(value)) for value in normalized]
                    geom_type = setting("peak_geometry_shape", "peak_geometry_shape")
                    if inward:
                        tip_radii = np.maximum(0.0, inner_radius - heights)
                        if geom_type == "Capsule":
                            for angle, tip_radius, color in zip(theta, tip_radii, colors):
                                mean_radius = (
                                    inner_radius + (inner_radius - tip_radius) / 2.0
                                    if combined_mode else (inner_radius + tip_radius) / 2.0
                                )
                                width_px = max(1.0, bar_width * mean_radius * size_px * 0.5 * 0.82)
                                width_pt = width_px * 72.0 / dpi
                                ax.plot([angle, angle], [tip_radius, inner_radius], color=color,
                                        linewidth=width_pt, solid_capstyle='round', antialiased=True, clip_on=True)
                        elif geom_type == "Lollipop":
                            for angle, tip_radius, color in zip(theta, tip_radii, colors):
                                mean_radius = (inner_radius + tip_radius) / 2.0
                                stem_radius = inner_radius if combined_mode else mean_radius
                                stem_px = max(1.0, bar_width * stem_radius * size_px * 0.5 * 0.18)
                                stem_pt = stem_px * 72.0 / dpi
                                dot_px = max(2.0, bar_width * max(tip_radius, 0.02) * size_px * 0.5 * 0.90)
                                dot_pt = dot_px * 72.0 / dpi
                                ax.plot([angle, angle], [tip_radius, inner_radius], color=color,
                                        linewidth=stem_pt, solid_capstyle='round', antialiased=True, clip_on=True)
                                ax.plot([angle], [tip_radius], marker='o', linestyle='None', markersize=dot_pt,
                                        markerfacecolor=color, markeredgecolor=color, markeredgewidth=0,
                                        antialiased=True, clip_on=True)
                        elif geom_type == "ArrowSpear":
                            for angle, tip_radius, color in zip(theta, tip_radii, colors):
                                draw_radial_arrow_spear_inward(
                                    ax, angle, inner_radius, tip_radius, color, bar_width,
                                    match_outward_stem_width=combined_mode,
                                )
                        elif geom_type == "Spike":
                            half_width = bar_width / 2.0
                            for angle, tip_radius, color in zip(theta, tip_radii, colors):
                                join_radius = inner_radius + seam_overlap if combined_mode else inner_radius
                                ax.fill([angle - half_width, angle, angle + half_width],
                                        [join_radius, tip_radius, join_radius],
                                        facecolor=color, edgecolor='none', linewidth=0, antialiased=True)
                        else:
                            inward_bar_heights = heights + seam_overlap if combined_mode else heights
                            ax.bar(theta, inward_bar_heights, width=bar_width, bottom=tip_radii,
                                   color=colors, edgecolor='none', align='center', linewidth=0)
                    if outward:
                        geom_type = setting("peak_geometry_shape", "peak_geometry_shape")
                        outer_radii = inner_radius + heights
                        if geom_type == "Capsule":
                            for angle, outer_radius, color in zip(theta, outer_radii, colors):
                                mean_radius = (inner_radius + outer_radius) / 2.0
                                width_px = max(1.0, bar_width * mean_radius * size_px * 0.5 * 0.82)
                                width_pt = width_px * 72.0 / dpi
                                ax.plot([angle, angle], [inner_radius, outer_radius], color=color,
                                        linewidth=width_pt, solid_capstyle='round', antialiased=True, clip_on=True)
                        elif geom_type == "Lollipop":
                            for angle, outer_radius, color in zip(theta, outer_radii, colors):
                                stem_px = max(1.0, bar_width * inner_radius * size_px * 0.5 * 0.18)
                                stem_pt = stem_px * 72.0 / dpi
                                dot_px = max(2.0, bar_width * outer_radius * size_px * 0.5 * 0.90)
                                dot_pt = dot_px * 72.0 / dpi
                                ax.plot([angle, angle], [inner_radius, outer_radius], color=color,
                                        linewidth=stem_pt, solid_capstyle='round', antialiased=True, clip_on=True)
                                ax.plot([angle], [outer_radius], marker='o', linestyle='None', markersize=dot_pt,
                                        markerfacecolor=color, markeredgecolor=color, markeredgewidth=0,
                                        antialiased=True, clip_on=True)
                        elif geom_type == "ArrowSpear":
                            for angle, outer_radius, color in zip(theta, outer_radii, colors):
                                draw_radial_arrow_spear(
                                    ax, angle, inner_radius, outer_radius, color, bar_width
                                )
                        elif geom_type == "Spike":
                            half_width = bar_width / 2.0
                            for angle, outer_radius, color in zip(theta, outer_radii, colors):
                                ax.fill([angle - half_width, angle, angle + half_width],
                                        [inner_radius, outer_radius, inner_radius],
                                        facecolor=color, edgecolor='none', linewidth=0, antialiased=True)
                        else:
                            ax.bar(theta, heights, width=bar_width, bottom=inner_radius,
                                   color=colors, edgecolor='none', align='center', linewidth=0)
            fig.savefig(
                output_image_path, dpi=dpi, format=image_ext,
                facecolor=canvas_bg, transparent=(setting("is_transparent", "is_transparent") and not is_jpg),
                pad_inches=0,
            )
        except Exception as exc:
            log_ui( lambda fn=file_name, err=str(exc): self.write_system_log(
                self.tr("❌ Circular waveform failed for '{filename}': {error}").format(filename=fn, error=err)
            ))
            return
        finally:
            if fig is not None:
                fig.clear()
                plt.close(fig)
            fig = None
            audio_samples = raw_bytes = None
            gc.collect()

        log_ui( lambda fn=os.path.basename(output_image_path): self.write_system_log(
            self.tr("📸 Circular image generated: {filename}").format(filename=fn)
        ))

        if preview_only:
            return True

        # Image-only mode deliberately stops after rendering and never invokes
        # Mutagen or FFmpeg artwork embedding.
        if setting("generate_image_only", "generate_image_only"):
            return True

        # Use the same verified, container-specific artwork embedding helpers as
        # Sound Wave Maker. WAV remains image-only; raw AAC is packaged as M4A,
        # because the raw AAC/ADTS stream has no standard cover-art container.
        video_codec = "mjpeg" if is_jpg else "png"
        embedded_output = None
        if ext == '.mp3':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.mp3")
        elif ext in ('.ogg', '.oga', '.opus'):
            embedded_extension = ".opus" if ext == ".opus" else ".ogg"
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art{embedded_extension}")
        elif ext == '.flac':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.flac")
        elif ext == '.m4a':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.m4a")
        elif ext == '.aac':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.m4a")
        elif ext == '.aiff':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.aiff")
        elif ext == '.aif':
            embedded_output = os.path.join(output_dir, f"{file_base}_with_art.aif")

        if embedded_output:
            if ext in ('.ogg', '.oga', '.opus'):
                success, error = self._embed_ogg_waveform_artwork(
                    audio_path, output_image_path, embedded_output,
                    size_px, size_px, is_jpg,
                )
            elif ext in ('.aiff', '.aif'):
                success, error = self._embed_aiff_waveform_artwork(
                    audio_path, output_image_path, embedded_output, is_jpg,
                )
            else:
                success, error = self._embed_waveform_artwork_with_ffmpeg(
                    audio_path, output_image_path, embedded_output, video_codec,
                )

            if success:
                self.root.after(0, lambda fn=os.path.basename(embedded_output): self.write_system_log(
                    self.tr("✅ Embedded artwork in audio -> {filename}").format(filename=fn)
                ))
                if ext == '.aac':
                    self.root.after(0, lambda fn=os.path.basename(embedded_output): self.write_system_log(
                        self.tr("Raw AAC has no standard cover-art container; created an M4A file -> {filename}").format(filename=fn)
                    ))
                if not self.keep_standalone_png.get():
                    try:
                        os.remove(output_image_path)
                    except OSError:
                        pass
            else:
                self.root.after(0, lambda fn=file_name, err=error: self.write_system_log(
                    self.tr("❌ Could not embed artwork for '{filename}': {error}. The standalone image was kept.").format(
                        filename=fn, error=err
                    )
                ))
        return True
