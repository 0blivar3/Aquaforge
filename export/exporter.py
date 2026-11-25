from __future__ import annotations

from pathlib import Path
from PIL import Image
import numpy as np


SUPPORTED_FORMATS = {".png", ".tga", ".tif", ".tiff"}


def save_normal_map(image: np.ndarray, path: str | Path) -> Path:
    target = Path(path)
    if target.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError("Supported formats: PNG, TGA and TIFF")
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Expected an 8-bit RGB normal map")
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image, mode="RGB").save(target)
    return target
