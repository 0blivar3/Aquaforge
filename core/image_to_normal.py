from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

from core.normal_math import height_to_normal


CHANNELS = ("Luminance", "Red", "Green", "Blue")


def load_height_image(path: str | Path, channel: str = "Luminance") -> tuple[np.ndarray, np.ndarray]:
    """Load an image and return (height field, RGB source preview)."""
    if channel not in CHANNELS:
        raise ValueError(f"Channel must be one of: {', '.join(CHANNELS)}")
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    pixels = rgb.astype(np.float32) / 255.0
    if channel == "Red":
        height = pixels[..., 0]
    elif channel == "Green":
        height = pixels[..., 1]
    elif channel == "Blue":
        height = pixels[..., 2]
    else:
        height = (pixels[..., 0] * 0.2126 +
                  pixels[..., 1] * 0.7152 +
                  pixels[..., 2] * 0.0722)
    return height.astype(np.float32), rgb


def convert_height_image(height: np.ndarray, strength: float = 5.0,
                         y_convention: str = "OpenGL",
                         seamless: bool = False) -> np.ndarray:
    """Convert a loaded grayscale height field into an RGB normal map."""
    return height_to_normal(height, strength=strength,
                            y_convention=y_convention, seamless=seamless)
