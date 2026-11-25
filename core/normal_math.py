from __future__ import annotations

import numpy as np


def height_to_normal(
    height: np.ndarray,
    strength: float = 4.0,
    y_convention: str = "OpenGL",
    seamless: bool = True,
) -> np.ndarray:
    """Convert a 2D height field to an 8-bit tangent-space RGB normal map."""
    if height.ndim != 2 or min(height.shape) < 2:
        raise ValueError("height must be a 2D array at least 2x2")
    if strength < 0:
        raise ValueError("strength cannot be negative")
    if y_convention not in {"OpenGL", "DirectX"}:
        raise ValueError("y_convention must be 'OpenGL' or 'DirectX'")

    h = np.asarray(height, dtype=np.float32)
    if seamless:
        dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
        dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    else:
        dy, dx = np.gradient(h)

    nx = -dx * strength
    ny = -dy * strength
    if y_convention == "DirectX":
        ny = -ny
    nz = np.ones_like(h)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    normals = np.stack((nx / length, ny / length, nz / length), axis=-1)
    rgb = np.clip((normals * 0.5 + 0.5) * 255.0, 0, 255)
    return np.rint(rgb).astype(np.uint8)
