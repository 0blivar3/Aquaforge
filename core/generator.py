from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(slots=True)
class GeneratorSettings:
    width: int = 1024
    height: int = 1024
    wave_scale: float = 4.0
    wave_strength: float = 1.0
    frequency: float = 1.0
    direction: float = 35.0
    wind_strength: float = 0.35
    ripple_intensity: float = 0.25
    ripple_scale: float = 18.0
    detail: int = 3
    distortion: float = 0.15
    seed: int = 12345
    seamless: bool = True


def _generate_heightmap_python(settings: GeneratorSettings, progress=None) -> np.ndarray:
    """Generate a periodic multi-directional water height field."""
    s = settings
    if not (16 <= s.width <= 8192 and 16 <= s.height <= 8192):
        raise ValueError("Resolution must be between 16 and 8192 pixels")
    if s.detail < 1 or s.detail > 12:
        raise ValueError("Detail must be between 1 and 12")

    rng = np.random.default_rng(s.seed)
    x = np.arange(s.width, dtype=np.float32)[None, :] / s.width
    y = np.arange(s.height, dtype=np.float32)[:, None] / s.height
    xx, yy = np.broadcast_arrays(x, y)
    height = np.zeros((s.height, s.width), dtype=np.float32)

    base_angle = np.deg2rad(s.direction)
    waves = max(2, s.detail + 1)
    for i in range(waves):
        angle = base_angle + i * (np.pi * (3.0 - np.sqrt(5.0)))
        # Integer lattice frequencies guarantee exact periodicity at the borders.
        magnitude = max(1, int(round(s.wave_scale * s.frequency * (1 + i * 0.22))))
        kx = int(round(np.cos(angle) * magnitude))
        ky = int(round(np.sin(angle) * magnitude))
        if kx == 0 and ky == 0:
            kx = 1
        phase = rng.uniform(0.0, 2.0 * np.pi)
        amplitude = s.wave_strength / (1.0 + i * 0.8)
        wind_bias = 1.0 + s.wind_strength * max(0.0, np.cos(angle - base_angle))
        height += (amplitude * wind_bias / waves) * np.sin(
            2.0 * np.pi * (kx * xx + ky * yy) + phase
        )
        if progress:
            progress(int((i + 1) / (waves + 1) * 75))

    # Fine ripples use higher integer frequencies and remain tileable.
    for i in range(max(1, s.detail)):
        angle = rng.uniform(0.0, 2.0 * np.pi)
        freq = max(2, int(round(s.ripple_scale * (1 + i * 0.12))))
        kx = int(round(np.cos(angle) * freq)) or 1
        ky = int(round(np.sin(angle) * freq))
        phase = rng.uniform(0.0, 2.0 * np.pi)
        height += (s.ripple_intensity / (i + 1) / max(1, s.detail)) * np.sin(
            2.0 * np.pi * (kx * xx + ky * yy) + phase
        )

    if s.distortion:
        # Periodic low-frequency modulation; no non-periodic image noise is introduced.
        modulation = np.sin(2 * np.pi * (2 * xx + yy) + rng.uniform(0, 2*np.pi))
        height *= 1.0 + s.distortion * modulation
    if progress:
        progress(85)
    height -= float(height.mean())
    peak = float(np.max(np.abs(height)))
    if peak > 1e-8:
        height /= peak
    if progress:
        progress(100)
    return height.astype(np.float32)



def generate_heightmap(settings: GeneratorSettings, progress=None) -> np.ndarray:
    """Generate a height field using the native C++ engine when available."""
    from core.native_backend import get_native_backend

    backend = get_native_backend()
    if backend is None:
        return _generate_heightmap_python(settings, progress)

    s = settings
    if not (16 <= s.width <= 8192 and 16 <= s.height <= 8192):
        raise ValueError("Resolution must be between 16 and 8192 pixels")
    if s.detail < 1 or s.detail > 12:
        raise ValueError("Detail must be between 1 and 12")
    if progress:
        progress(5)
    result = backend.generate_heightmap(
        s.width, s.height, s.wave_scale, s.wave_strength, s.frequency,
        s.direction, s.wind_strength, s.ripple_intensity, s.ripple_scale,
        s.detail, s.distortion, s.seed
    )
    if progress:
        progress(100)
    return np.asarray(result, dtype=np.float32)
