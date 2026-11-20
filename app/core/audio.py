"""Audio decoding utilities used by Audio-SWARM renderers."""
from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np


def decode_mono_samples(audio_path: str | Path, sample_rate: int = 11025) -> np.ndarray:
    """Decode the first audio stream to mono float samples using FFmpeg.

    Raises RuntimeError when FFmpeg is unavailable or decoding fails.
    """
    source = Path(audio_path)
    with tempfile.TemporaryDirectory(prefix="audio_swarm_") as temporary_directory:
        decoded_path = Path(temporary_directory) / "decoded.wav"
        command = [
            "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-i", str(source), "-map", "0:a:0", "-vn", "-ac", "1", "-ar",
            str(sample_rate), "-c:a", "pcm_s16le", str(decoded_path),
        ]
        try:
            process = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError as error:
            raise RuntimeError("FFmpeg could not be started.") from error
        if process.returncode != 0 or not decoded_path.is_file():
            detail = process.stderr.strip()[-500:]
            raise RuntimeError(f"Audio decoding failed: {detail or 'no decoded output'}")
        try:
            with wave.open(str(decoded_path), "rb") as wav_file:
                if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
                    raise RuntimeError("FFmpeg produced an unexpected WAV format.")
                samples = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype="<i2")
        except (OSError, wave.Error) as error:
            raise RuntimeError("Decoded audio file is invalid.") from error
    if samples.size == 0:
        raise RuntimeError("The audio file contains no samples.")
    return samples.astype(np.float32)
