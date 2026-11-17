"""Compatibility bridge that executes the original Audio-SWARM render/embedding code.

The rendering formulas, slice loops, geometry paths and metadata-writing helpers are
kept verbatim in ``LegacyRenderCore`` (see ``engine.py``). This adapter supplies the settings and safe
logging callbacks expected by that original implementation without importing Tk UI
objects into the core package.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import shutil
import tempfile
from matplotlib.colors import LinearSegmentedColormap

from .models import ProcessingResult


def _core():
    """Return LegacyRenderCore lazily: engine.py imports this module, so a
    top-level import here would be circular."""
    from .engine import LegacyRenderCore
    return LegacyRenderCore


class _Value:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value


class LegacyRendererAdapter:
    def __init__(self, settings, logger=None, single_file=False, popup=None, translator=None):
        self.settings = settings
        self.single_file = bool(single_file)
        self.logger = logger or (lambda _message: None)
        self.popup = popup
        self.translator = translator or (lambda text: text)
        extra = dict(getattr(settings, "extra", {}) or {})
        stops = list(getattr(settings, "gradient_stops", ()) or (getattr(settings, "solid_color", "#ffffff"),))
        if getattr(settings, "reverse_gradient", False) and not getattr(settings, "solid_color_mode", False):
            stops.reverse()
        self.color_nodes = stops
        self.bg_solid_color = getattr(settings, "background_color", "#000000")
        self.root = SimpleNamespace(after=self._after)
        self._values = {
            "format_menu": getattr(settings, "output_format", "PNG"),
            "width_val": getattr(settings, "width", 1920),
            "height_val": getattr(settings, "height", 1080),
            "target_dpi": getattr(settings, "dpi", 100),
            "num_bars": getattr(settings, "bars", 160),
            "slices_val": getattr(settings, "slices", 64),
            "is_transparent": getattr(settings, "transparent", False),
            "is_solid_color_mode": getattr(settings, "solid_color_mode", False),
            "keep_standalone_png": getattr(settings, "keep_standalone_image", True),
            "generate_image_only": getattr(settings, "generate_image_only", False),
            "gradient_direction": self._direction(getattr(settings, "gradient_direction", "Vertical")),
            "peak_geometry_shape": getattr(settings, "geometry", "Standard Classic Bars"),
            "reverse_color_map": getattr(settings, "reverse_gradient", False),
            "circular_size": extra.get("circular_size", getattr(settings, "width", 2000)),
            "circular_mode": extra.get("circular_mode", "waveform"),
            "circular_rotation": extra.get("circular_rotation", 0),
            "circular_inner_radius": extra.get("circular_inner_radius", 0.38),
            "circular_inward": extra.get("circular_inward", False),
            "circular_outward": extra.get("circular_outward", True),
            "radial_spectrum_inner_radius": extra.get("radial_spectrum_inner_radius", 0.38),
            "radial_spectrum_inward": extra.get("radial_spectrum_inward", False),
            "radial_spectrum_outward": extra.get("radial_spectrum_outward", True),
            "radial_spectrum_bins": extra.get("radial_spectrum_bins", 180),
            "radial_spectrum_sensitivity": extra.get("radial_spectrum_sensitivity", 2.0),
            "minimal_wave_base_radius": extra.get("minimal_wave_base_radius", 0.58),
            "minimal_wave_amplitude": extra.get("minimal_wave_amplitude", 0.25),
            "minimal_wave_line_width": extra.get("minimal_wave_line_width", 2.0),
        }
        self._values["color_nodes"] = self.color_nodes
        for key, value in self._values.items():
            setattr(self, key, value if key == "color_nodes" else _Value(value))

    @staticmethod
    def _direction(value):
        value = str(value).strip().lower()
        return "Horizontal" if value.startswith("h") else "Vertical"

    def _after(self, _delay, callback=None):
        # Never touch Tk from a worker thread. The supplied logger is thread-safe by
        # contract; defer scheduling semantics to the host engine's callback.
        if callback is not None:
            callback()

    def tr(self, text):
        return self.translator(text)

    def write_system_log(self, message):
        self.logger(str(message))

    def show_themed_popup(self, title, message, kind="info"):
        if self.popup is not None:
            self.popup(title, message, kind)
        else:
            self.logger(f"{title}: {message}")

    def _embed_ogg_waveform_artwork(self, *args, **kwargs):
        return _core()._embed_ogg_waveform_artwork(self, *args, **kwargs)

    def _embed_aiff_waveform_artwork(self, *args, **kwargs):
        return _core()._embed_aiff_waveform_artwork(self, *args, **kwargs)

    def _embed_waveform_artwork_with_ffmpeg(self, *args, **kwargs):
        return _core()._embed_waveform_artwork_with_ffmpeg(self, *args, **kwargs)

    def render_waveform(self, audio_path: str | Path, output_dir: str | Path):
        from matplotlib import pyplot as plt

        audio_path, output_dir = Path(audio_path), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        settings = self.settings
        stops = list(self.color_nodes)
        cmap = LinearSegmentedColormap.from_list("user_grad", stops)
        scratch_dir = Path(tempfile.mkdtemp(prefix=".swarm_single_", dir=output_dir)) if self.single_file else output_dir
        try:
            _core().execute_single_waveform_render(
                self, str(audio_path), str(scratch_dir), cmap
            )
        except Exception as exc:
            if self.single_file:
                shutil.rmtree(scratch_dir, ignore_errors=True)
            return ProcessingResult(audio_path, None, False, str(exc))
        finally:
            plt.close("all")

        suffix = ".jpg" if getattr(settings, "output_format", "PNG") == "JPG" else ".png"
        image_path = scratch_dir / f"{audio_path.stem}{suffix}"
        embedded = scratch_dir / f"{audio_path.stem}_with_art{audio_path.suffix.lower()}"
        if audio_path.suffix.lower() == ".aac":
            embedded = scratch_dir / f"{audio_path.stem}_with_art.m4a"

        if self.single_file:
            # Render into a private scratch directory first so a same-named image
            # beside the source can never be overwritten by a single-file run.
            final_image = output_dir / f"{audio_path.stem}_with_art{suffix}"
            final_embedded = output_dir / f"{audio_path.stem}_with_art{embedded.suffix}"
            if image_path.is_file():
                image_path.replace(final_image)
                image_path = final_image
            else:
                image_path = final_image if final_image.is_file() else image_path
            if embedded.is_file():
                embedded.replace(final_embedded)
                embedded = final_embedded
            else:
                embedded = final_embedded if final_embedded.is_file() else embedded
            if audio_path.suffix.lower() == ".wav" and not getattr(settings, "generate_image_only", False):
                wav_copy = output_dir / f"{audio_path.stem}_with_art.wav"
                shutil.copy2(audio_path, wav_copy)
                embedded = wav_copy
            shutil.rmtree(scratch_dir, ignore_errors=True)
        else:
            # Bulk output is isolated in a generated folder: retain source stems.
            bulk_embedded = output_dir / f"{audio_path.stem}{embedded.suffix}"
            if embedded.is_file() and embedded != bulk_embedded:
                embedded.replace(bulk_embedded)
                embedded = bulk_embedded

        if embedded.is_file():
            output = embedded
            message = "Original renderer completed; artwork embedding output created."
        elif image_path.is_file():
            output = image_path
            message = "Original renderer completed; standalone waveform image created."
        else:
            if self.single_file:
                shutil.rmtree(scratch_dir, ignore_errors=True)
            return ProcessingResult(audio_path, None, False, "Original renderer did not create an output file; see processing log.")
        if self.single_file:
            shutil.rmtree(scratch_dir, ignore_errors=True)
        return ProcessingResult(audio_path, output, True, message)


    def render_waveform_preview(self, audio_path: str | Path, output_dir: str | Path, output_image_path: str | Path):
        """Render one preview through the original engine's drawing pipeline only."""
        audio_path, output_dir, output_image_path = Path(audio_path), Path(output_dir), Path(output_image_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        stops = list(self.color_nodes)
        cmap = LinearSegmentedColormap.from_list("user_grad", stops)
        settings = {
            "format_menu": getattr(self.settings, "output_format", "PNG"),
            "width_val": getattr(self.settings, "width", 1000),
            "height_val": getattr(self.settings, "height", 120),
            "target_dpi": getattr(self.settings, "dpi", 100),
            "num_bars": getattr(self.settings, "bars", 135),
            "slices_val": getattr(self.settings, "slices", 25),
            "is_transparent": getattr(self.settings, "transparent", True),
            "bg_solid_color": getattr(self.settings, "background_color", "#404040"),
            "is_solid_color_mode": getattr(self.settings, "solid_color_mode", False),
            "color_nodes": list(self.color_nodes),
            "keep_standalone_png": True,
            "gradient_direction": self._direction(getattr(self.settings, "gradient_direction", "Vertical")),
            "peak_geometry_shape": getattr(self.settings, "geometry", "Rectangle"),
            "reverse_color_map": getattr(self.settings, "reverse_gradient", False),
        }
        try:
            success = _core().execute_single_waveform_render(
                self, str(audio_path), str(output_dir), cmap,
                preview_only=True,
                render_size=(int(self.settings.width), int(self.settings.height)),
                output_image_path=str(output_image_path),
                preview_settings=settings,
            )
            return bool(success and output_image_path.is_file() and output_image_path.stat().st_size > 0)
        finally:
            from matplotlib import pyplot as plt
            plt.close("all")

    def render_circular_preview(self, audio_path: str | Path, output_dir: str | Path, mode: str, render_size: int, output_image_path: str | Path):
        """Render a circular preview through the original engine's preview-only branch."""
        audio_path, output_dir, output_image_path = Path(audio_path), Path(output_dir), Path(output_image_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.circular_mode = _Value(mode)
        settings = {
            "format": getattr(self.settings, "output_format", "PNG"),
            "target_dpi": getattr(self.settings, "dpi", 100),
            "is_transparent": getattr(self.settings, "transparent", True),
            "bg_solid_color": getattr(self.settings, "background_color", "#404040"),
            "is_solid_color_mode": getattr(self.settings, "solid_color_mode", False),
            "color_nodes": list(self.color_nodes),
            "reverse_color_map": getattr(self.settings, "reverse_gradient", False),
            "gradient_direction": self._direction(getattr(self.settings, "gradient_direction", "Vertical")),
            "peak_geometry_shape": getattr(self.settings, "geometry", "Rectangle"),
            "num_bars": getattr(self.settings, "bars", 135),
            "circular_mode": mode,
            **dict(getattr(self.settings, "extra", {}) or {}),
        }
        try:
            success = _core().execute_single_circular_waveform(
                self, str(audio_path), str(output_dir),
                LinearSegmentedColormap.from_list("user_grad", list(self.color_nodes)),
                mode=mode, render_size=int(render_size), output_image_path=str(output_image_path),
                preview_only=True, preview_settings=settings,
            )
            if success and output_image_path.is_file() and output_image_path.stat().st_size > 0:
                return ProcessingResult(audio_path, output_image_path, True, "Original engine preview generated.")
            return ProcessingResult(audio_path, None, False, "Original engine did not create a preview image.")
        except Exception as exc:
            return ProcessingResult(audio_path, None, False, str(exc))
        finally:
            from matplotlib import pyplot as plt
            plt.close("all")

    def render_circular(self, audio_path: str | Path, output_dir: str | Path, mode: str):
        from matplotlib import pyplot as plt
        audio_path, output_dir = Path(audio_path), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.circular_mode = _Value(mode)
        scratch_dir = Path(tempfile.mkdtemp(prefix=".swarm_single_", dir=output_dir)) if self.single_file else output_dir
        try:
            _core().execute_single_circular_waveform(
                self, str(audio_path), str(scratch_dir), None, mode=mode
            )
        except Exception as exc:
            if self.single_file:
                shutil.rmtree(scratch_dir, ignore_errors=True)
            return ProcessingResult(audio_path, None, False, str(exc))
        finally:
            plt.close("all")
        suffix_name = {"waveform": "circular", "spectrum": "radial_spectrum", "minimal": "minimal_circular"}.get(mode, "circular")
        suffix = ".jpg" if getattr(self.settings, "output_format", "PNG") == "JPG" else ".png"
        image_path = scratch_dir / f"{audio_path.stem}_{suffix_name}{suffix}"
        embedded = scratch_dir / f"{audio_path.stem}_with_art{audio_path.suffix.lower()}"
        if audio_path.suffix.lower() == ".aac":
            embedded = scratch_dir / f"{audio_path.stem}_with_art.m4a"

        if self.single_file:
            final_image = output_dir / f"{audio_path.stem}_{suffix_name}{suffix}"
            final_embedded = output_dir / f"{audio_path.stem}_with_art{embedded.suffix}"
            if image_path.is_file():
                image_path.replace(final_image)
                image_path = final_image
            else:
                image_path = final_image if final_image.is_file() else image_path
            if embedded.is_file():
                embedded.replace(final_embedded)
                embedded = final_embedded
            else:
                embedded = final_embedded if final_embedded.is_file() else embedded
            if audio_path.suffix.lower() == ".wav" and not getattr(self.settings, "generate_image_only", False):
                wav_copy = output_dir / f"{audio_path.stem}_with_art.wav"
                shutil.copy2(audio_path, wav_copy)
                embedded = wav_copy
            shutil.rmtree(scratch_dir, ignore_errors=True)
        else:
            bulk_image = output_dir / f"{audio_path.stem}{suffix}"
            if image_path.is_file() and image_path != bulk_image:
                image_path.replace(bulk_image)
                image_path = bulk_image
            bulk_embedded = output_dir / f"{audio_path.stem}{embedded.suffix}"
            if embedded.is_file() and embedded != bulk_embedded:
                embedded.replace(bulk_embedded)
                embedded = bulk_embedded

        if embedded.is_file():
            result = ProcessingResult(audio_path, embedded, True, "Original circular renderer completed and artwork was embedded.")
        elif image_path.is_file():
            result = ProcessingResult(audio_path, image_path, True, "Original circular renderer completed.")
        else:
            result = ProcessingResult(audio_path, None, False, "Original circular renderer did not create an output file; see processing log.")
        if self.single_file:
            shutil.rmtree(scratch_dir, ignore_errors=True)
        return result
