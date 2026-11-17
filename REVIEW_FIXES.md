# Review fixes applied

- Race: all launchers use `_busy()` (batch + both previews); batches render in separate worker processes (max 4, 2 for huge images).
- Tk is never called from worker threads: `ui_call()` queue drained on the main thread; `cancel_operation` is backed by `threading.Event`.
- FFmpeg: resolved once (`app/core/process.py`), no console flash on Windows, UTF-8 safe stderr, `-nostdin`, startup warning if missing.
- Mouse wheel on the main canvas works on Windows/macOS/Linux; platform-appropriate fonts.
- Figure always closed on drawing errors; vectorised bar heights; unique preview temp WAV; clean shutdown while a job runs.
- Removed unused imports, duplicate code, inline imports, 12-space indents, broad `except Exception` in help_about.
- Added requirements.txt.
Not changed (architectural, would risk altering renders): duck-typed `LegacyRenderCore` adapter, splitting the 500-line circular render function.
