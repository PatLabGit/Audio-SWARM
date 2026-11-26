"""Threaded processing commands wired to the pure-Python core engine."""
from __future__ import annotations
import re
import threading
from dataclasses import replace
from pathlib import Path

from app.core.artwork import prepare_artwork
from app.core.files import IMAGE_EXTENSIONS, discover_audio
from app.core.models import ArtworkSettings, WaveformSettings
from app.core.video import SUPPORTED_VIDEO_SUFFIXES, embed_video_artwork


class ProcessingMixin:
    def _busy(self):
        """True while a batch or any preview render is running (they share Matplotlib state)."""
        return bool(self.is_processing
                    or getattr(self, "sound_preview_running", False)
                    or getattr(self, "circular_preview_running", False))

    def _build_artwork_settings(self):
        """Artwork prep settings shared by the bulk linker and the video poster tab.

        With the Automation Matrix on, the active Sound Wave Maker output format is used.
        JPEG cannot hold alpha, so transparency only applies to PNG output.
        """
        output_format = str(self.format_menu.get()).strip().upper()
        transparency_enabled = bool(self.is_transparent.get())
        background = self.bg_solid_color
        background = str(background.get() if hasattr(background, "get") else background).strip()
        return ArtworkSettings(
            resize=bool(self.tab2_resize_enabled.get()),
            width=max(1, int(self.tab2_width.get())),
            height=max(1, int(self.tab2_height.get())),
            preserve_aspect=bool(self.preserve_aspect.get()),
            output_format=output_format,
            jpeg_quality=95,
            transparent=(transparency_enabled and output_format == "PNG"),
            background_color=background,
        )

    def _build_waveform_settings(self, preview_size=None):
        width, height = preview_size or (int(self.width_val.get()), int(self.height_val.get()))
        stops = tuple(self.color_nodes) if self.color_nodes else ("#00ff66",)
        return WaveformSettings(
            width=max(1, int(width)), height=max(1, int(height)), dpi=max(1, int(self.target_dpi.get())),
            bars=max(1, int(self.num_bars.get())), output_format=self.format_menu.get(),
            transparent=bool(self.is_transparent.get()), background_color=self.bg_solid_color,
            solid_color_mode=bool(self.is_solid_color_mode.get()), solid_color=stops[0],
            gradient_stops=stops, reverse_gradient=bool(self.reverse_color_map.get()),
            geometry=self.peak_geometry_shape.get(), gradient_direction=self.gradient_direction.get().lower(),
            slices=max(1, int(self.slices_val.get())),
            keep_standalone_image=bool(self.keep_standalone_png.get()),
            generate_image_only=bool(self.generate_image_only.get()),
        )

    def _build_circular_settings(self, preview_size=None, preview=False):
        size = int(self.circular_size.get()) if preview_size is None else int(preview_size[0] if isinstance(preview_size, (tuple, list)) else preview_size)
        base = self._build_waveform_settings((size, size))
        extra = {
            "circular_inner_radius": float(self.circular_inner_radius.get()),
            "circular_inward": bool(self.circular_inward.get()),
            "circular_outward": bool(self.circular_outward.get()),
            "radial_spectrum_inner_radius": float(self.radial_spectrum_inner_radius.get()),
            "radial_spectrum_inward": bool(self.radial_spectrum_inward.get()),
            "radial_spectrum_outward": bool(self.radial_spectrum_outward.get()),
            "radial_spectrum_bins": int(self.radial_spectrum_bins.get()),
            "radial_spectrum_sensitivity": float(self.radial_spectrum_sensitivity.get()),
            "minimal_wave_base_radius": float(self.minimal_wave_base_radius.get()),
            "minimal_wave_amplitude": float(self.minimal_wave_amplitude.get()),
            "minimal_wave_line_width": float(self.minimal_wave_line_width.get()),
            "circular_rotation": int(self.circular_rotation.get()),
            "peak_geometry_shape": self.peak_geometry_shape.get(),
        }
        return replace(base, extra=extra, keep_standalone_image=bool(self.keep_standalone_png.get()))

    def _progress_callback(self, message, current, total):
        def update():
            if not hasattr(self, "progress_bar") or not hasattr(self, "status_label"):
                return
            match = re.match(r"(\d+)/(\d+):\s*(.*)", message)
            if match:
                index, batch_total, detail = int(match.group(1)), int(match.group(2)), match.group(3)
                self.progress_bar.configure(maximum=max(1, batch_total), value=current)
                if detail.startswith("Merging Pair ") and " 🔗 " in detail:
                    pair = detail[len("Merging Pair "):]
                    audio_name, image_name = pair.split(" 🔗 ", 1)
                    label = self.tr("🔄 Merging Pair ({current}/{total}): {audio} 🔗 {image}").format(
                        current=index, total=batch_total, audio=audio_name, image=image_name
                    )
                elif detail.startswith("Circular: Rendering "):
                    filename = detail[len("Circular: Rendering "):]
                    label = self.tr("🔵 Circular waveform ({current}/{total}): {filename}").format(
                        current=index, total=batch_total, filename=filename
                    )
                elif detail.startswith("Rendering "):
                    filename = detail[len("Rendering "):]
                    label = self.tr("⏳ Processing Track ({current}/{total}): {filename}").format(
                        current=index, total=batch_total, filename=filename
                    )
                else:
                    label = None
                if label is not None:
                    self.status_label.configure(text=label, fg="#ffff00")
            else:
                self.progress_bar.configure(maximum=max(1, total), value=current)
        self.ui_call(update)

    def _finish_job(self, batch, title, output_directory):
        def update():
            self.toggle_ui_interactivity(True)
            if batch is None:
                self.status_label.configure(text=self.tr("❌ Processing failed."), fg="#ff0033")
                return
            total = len(batch.results)
            self.progress_bar.configure(maximum=max(1, total), value=total)
            if not batch.results and title != "Artwork linking complete":
                self.status_label.configure(text=self.tr("ℹ️ Queue processing halted: no tracks detected."), fg="#ffff00")
                return
            if batch.cancelled:
                if title == "Artwork linking complete":
                    self.write_system_log(self.tr("⚠️ Batch pairing pipeline terminated by user selection request."))
                else:
                    self.write_system_log(self.tr("⚠️ Processing suite queue aborted by operator request."))
                return
            if title == "Waveform rendering complete":
                self.status_label.configure(text=self.tr("🎉 Task Complete! Waveforms processed successfully."), fg="#00ff66")
                popup_title = self.tr("Success")
                popup_message = self.tr("All waveforms created inside:\n{output_directory}").format(output_directory=output_directory)
            elif title == "Circular rendering complete":
                self.status_label.configure(text=self.tr("🎉 Circular waveform generation completed."), fg="#00ff66")
                popup_title = self.tr("Complete")
                popup_message = self.tr("Circular waveforms created inside:\n{output_directory}").format(output_directory=output_directory)
            else:
                self.status_label.configure(text=self.tr("🎉 Bulk embedding pipeline completed successfully!"), fg="#00ff66")
                popup_title = self.tr("Complete")
                popup_message = self.tr("Assets linked safely inside folder:\n{output_dir}").format(output_dir=output_directory)
            if batch.results:
                self.show_themed_popup(popup_title, popup_message, kind="info")
        self.ui_call(update)

    def _run_worker(self, operation, title, output_directory, clear_log=True):
        self.cancel_operation = False
        self.process_log_output_directory = output_directory
        if clear_log:
            self.clear_system_log()
        self.progress_bar.configure(value=0, maximum=1)
        self.toggle_ui_interactivity(False)
        def worker():
            batch = None
            try:
                batch = operation(lambda: self.cancel_operation, self._progress_callback)
            except Exception as exc:
                self.ui_call(lambda m=f"Processing Error: {exc}": self.record_processing_error(m))
                self.ui_call(lambda err=str(exc): self.show_themed_popup(self.tr("Processing Error"), err, kind="error"))
            finally:
                self._finish_job(batch, title, output_directory)
        threading.Thread(target=worker, daemon=True, name="AudioSWARM-Processing").start()

    def launch_tab1_processing_pipeline(self):
        if self._busy():
            return
        self.clear_system_log()
        source = self.source_folder.get().strip().strip('{}')
        settings = self._build_waveform_settings()
        output = str((Path(source).resolve().parent if Path(source).is_file() else Path(source).resolve()) / ("Images_only" if settings.generate_image_only else "Waveform_Outputs"))
        self._run_worker(lambda cancelled, progress: self.engine.render_batch(source, settings, progress=progress, cancelled=cancelled), "Waveform rendering complete", output, clear_log=False)

    def launch_circular_processing_pipeline(self):
        if self._busy():
            return
        self.clear_system_log()
        source = self.source_folder.get().strip().strip('{}')
        mode = self.circular_mode.get()
        settings = self._build_circular_settings()
        output = str((Path(source).resolve().parent if Path(source).is_file() else Path(source).resolve()) / ("Images_only" if settings.generate_image_only else "Circular_Waveform_Outputs"))
        self._run_worker(lambda cancelled, progress: self.engine.render_circular_batch(source, settings, mode=mode, progress=progress, cancelled=cancelled), "Circular rendering complete", output, clear_log=False)

    def launch_tab2_pairing_pipeline(self):
        if self._busy():
            return
        self.clear_system_log()
        source = self.source_folder.get().strip().strip('{}')
        source_path = Path(source).expanduser()
        if not source_path.is_dir():
            self.show_themed_popup(self.tr("Folder Required"), self.tr("Select a folder containing audio tracks and artwork images for bulk artwork linking."), kind="error")
            return

        # Match the original Bulk Artwork Linker: warn gently on count mismatch,
        # then continue with the first one-to-one pairs rather than blocking.
        audio_files = discover_audio(source_path, recursive=False)
        image_files = sorted(
            (item for item in source_path.iterdir()
             if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS),
            key=lambda item: item.name.casefold(),
        )
        audio_count, image_count = len(audio_files), len(image_files)
        self.write_system_log(self.tr(
            "📂 Scanning Directory: {folder}\n🎵 Tracks Found: {audio_count} | 📸 Images Found: {image_count}"
        ).format(folder=str(source_path), audio_count=audio_count, image_count=image_count))
        if audio_count != image_count:
            self.write_system_log(self.tr(
                "⚠️ Warning Mismatch: {audio_count} tracks vs {image_count} images. Limiting run to {limit} items."
            ).format(audio_count=audio_count, image_count=image_count, limit=min(audio_count, image_count)))
            self.trigger_thread_safe_popup(audio_count, image_count)

        settings = self._build_artwork_settings()

        output = str(source_path.resolve() / "Merged_Tracks_Outputs")
        self._run_worker(lambda cancelled, progress: self.engine.merge_artwork_batch(source_path, source_path, settings, progress=progress, cancelled=cancelled), "Artwork linking complete", output, clear_log=False)

    def trigger_abort_sequence(self):
        self.cancel_operation = True
        if hasattr(self, "status_label"):
            self.status_label.configure(text=self.tr("⏹️ Cancellation requested..."), fg="#ff0033")

    def launch_video_poster_pipeline(self):
        """Processes folder batch or single video cover injections on a worker thread."""
        if self._busy():
            return
        self.clear_system_log()

        source = self.source_folder.get().strip().strip('{}')
        source_path = Path(source).expanduser()


        # Determine if handling a single file or a bulk folder directory pass
        if source_path.is_file():
            if source_path.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES:
                self.show_themed_popup(
                    self.tr("Format Mismatch"),
                    self.tr("Dropped file is not a supported video container (MP4, MKV, MOV)."),
                    kind="error"
                )
                return
            video_files = [source_path]
            source_dir = source_path.parent
        elif source_path.is_dir():
            video_files = sorted(
                [item for item in source_path.iterdir()
                 if item.is_file() and item.suffix.lower() in SUPPORTED_VIDEO_SUFFIXES],
                key=lambda item: item.name.casefold()
            )
            source_dir = source_path
        else:
            self.show_themed_popup(
                self.tr("Selection Required"),
                self.tr("Please drag and drop a valid video file or a folder directory to begin."),
                kind="error"
            )
            return

        # Fetch image tracks from the same target folder container paths
        image_files = sorted(
            [item for item in source_dir.iterdir()
             if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS],
            key=lambda item: item.name.casefold()
        )

        video_count, image_count = len(video_files), len(image_files)
        if video_count == 0 or image_count == 0:
            self.show_themed_popup(
                self.tr("Missing Assets"),
                self.tr("The directory requires at least one video track and one companion image file."),
                kind="error"
            )
            return

        # Proactive flexible mismatch parsing logic
        if video_count != image_count:
            self.write_system_log(self.tr(
                "⚠️ Warning Mismatch: {video_count} videos vs {image_count} images. Limiting run to {limit} items."
            ).format(video_count=video_count, image_count=image_count, limit=min(video_count, image_count)))
            self.trigger_thread_safe_popup(video_count, image_count)

        output_dir = source_dir / "Video_Poster_Outputs"
        total_runs = min(video_count, image_count)

        # Lock interface controls after the log has been cleared at request start.
        self.toggle_ui_interactivity(False)
        self.cancel_operation = False
        self.progress_bar.configure(value=0, maximum=total_runs)

        settings = self._build_artwork_settings()

        def worker():
            success_count = 0
            for index in range(total_runs):
                if self.cancel_operation:
                    self.log_threadsafe(self.tr("⚠️ Video batch processing aborted by operator request."))
                    break

                vid = video_files[index]
                img = image_files[index]

                # Interface string step updating routine
                log_msg = self.tr("{current}/{total}: Video Poster -> {video} 🔗 {image}").format(current=index+1, total=total_runs, video=vid.name, image=img.name)
                self.ui_call(lambda m=log_msg, c=index: self._update_video_progress_ui(m, c, total_runs))

                try:
                    # Pass through the artwork matrix processing engine pipeline layout
                    prepared_img = prepare_artwork(img, output_dir, settings)
                    out_file = output_dir / f"{vid.stem}{vid.suffix}"

                    result = embed_video_artwork(vid, prepared_img, out_file)

                    # Clean up temporary resized images if scaling matrix was active
                    if prepared_img != img and prepared_img.is_file():
                        prepared_img.unlink(missing_ok=True)

                    if result.success:
                        success_count += 1
                        self.log_threadsafe(self.tr("✅ Core processing complete: {name}").format(name=vid.name))
                    else:
                        self.log_threadsafe(self.tr("❌ Processing failed for {name}: {err}").format(name=vid.name, err=result.message))
                except Exception as exc:
                    self.log_threadsafe(self.tr("❌ Runtime layout failure on {name}: {msg}").format(name=vid.name, msg=str(exc)))

            # Finalize pipeline loop state pass
            self.ui_call(lambda: self._finalize_video_job(success_count, total_runs, str(output_dir)))

        threading.Thread(target=worker, daemon=True, name="AudioSWARM-VideoPoster").start()

    def _update_video_progress_ui(self, message, current, total):
        self.progress_bar.configure(value=current)
        self.status_label.configure(text=message, fg="#ffff00")

    def _finalize_video_job(self, success, total, out_path):
        self.toggle_ui_interactivity(True)
        self.progress_bar.configure(value=total)
        if self.cancel_operation:
            self.status_label.configure(text=self.tr("❌ Operation cancelled."), fg="#ff0033")
            return

        self.status_label.configure(text=self.tr("🎉 Bulk video poster pipeline completed successfully!"), fg="#00ff66")
        self.show_themed_popup(
            self.tr("Complete"),
            self.tr("Successfully linked {success}/{total} videos inside folder:\n{out}").format(success=success, total=total, out=out_path),
            kind="info"
        )

