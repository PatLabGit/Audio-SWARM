"""Typed data models and configuration for Audio-SWARM processing."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

ProgressCallback = Callable[[str, int, int], None]
LogCallback = Callable[[str], None]
CancelCallback = Callable[[], bool]
AudioFormat = Literal["PNG", "JPG"]


@dataclass(frozen=True)
class WaveformSettings:
    """Options required to render a waveform without any GUI dependencies."""
    width: int = 1920
    height: int = 1080
    dpi: int = 100
    bars: int = 160
    output_format: AudioFormat = "PNG"
    transparent: bool = False
    background_color: str = "#000000"
    solid_color_mode: bool = False
    solid_color: str = "#ffffff"
    gradient_stops: tuple[str, ...] = ("#00d4ff", "#7b2cff", "#ff2d95")
    reverse_gradient: bool = False
    geometry: str = "Standard Classic Bars"
    gradient_direction: str = "vertical"
    slices: int = 64
    keep_standalone_image: bool = True
    generate_image_only: bool = False
    extra: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1 or self.dpi < 1:
            raise ValueError("Width, height, and DPI must be positive integers.")
        if self.bars < 1:
            raise ValueError("bars must be a positive integer.")
        if self.slices < 1:
            raise ValueError("slices must be a positive integer.")
        if self.output_format not in ("PNG", "JPG"):
            raise ValueError("output_format must be 'PNG' or 'JPG'.")


@dataclass(frozen=True)
class ArtworkSettings:
    """Options for artwork preparation and audio metadata embedding."""
    resize: bool = False
    width: int = 1000
    height: int = 1000
    preserve_aspect: bool = True
    output_format: AudioFormat = "PNG"
    jpeg_quality: int = 95
    transparent: bool = False
    background_color: str = "#404040"

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("Artwork dimensions must be positive integers.")
        if self.output_format not in ("PNG", "JPG"):
            raise ValueError("output_format must be 'PNG' or 'JPG'.")
        if not 1 <= self.jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100.")


@dataclass(frozen=True)
class ProcessingResult:
    """Outcome for one processed file."""
    source: Path
    output: Path | None
    success: bool
    message: str


@dataclass(frozen=True)
class BatchResult:
    """Summary of a batch processing operation."""
    results: tuple[ProcessingResult, ...]
    cancelled: bool = False

    @property
    def succeeded(self) -> int:
        """Return the number of successful files."""
        return sum(result.success for result in self.results)

    @property
    def failed(self) -> int:
        """Return the number of failed files."""
        return sum(not result.success for result in self.results)
