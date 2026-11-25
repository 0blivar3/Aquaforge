from __future__ import annotations

import numpy as np


def _height_to_normal_python(
    height: np.ndarray,
    strength: float = 4.0,
    y_convention: str = "OpenGL",
    seamless: bool = True,
    progress=None,
) -> np.ndarray:
    """Convert a 2D height field to an 8-bit tangent-space RGB normal map.

    Rows are processed in chunks to keep peak memory use manageable for
    large textures (2K/4K), rather than allocating several full-size float
    and three-channel intermediate arrays.
    """
    if height.ndim != 2 or min(height.shape) < 2:
        raise ValueError("height must be a 2D array at least 2x2")
    if strength < 0:
        raise ValueError("strength cannot be negative")
    if y_convention not in {"OpenGL", "DirectX"}:
        raise ValueError("y_convention must be 'OpenGL' or 'DirectX'")

    h = np.asarray(height, dtype=np.float32)
    height_px, width_px = h.shape
    result = np.empty((height_px, width_px, 3), dtype=np.uint8)
    chunk_rows = max(16, min(256, 1_048_576 // max(1, width_px)))

    if not seamless:
        # np.gradient preserves the original one-sided edge behavior.
        grad_y, grad_x = np.gradient(h)
    else:
        grad_y = grad_x = None

    for start in range(0, height_px, chunk_rows):
        end = min(height_px, start + chunk_rows)
        if seamless:
            rows = np.arange(start, end)
            above = h[(rows - 1) % height_px]
            below = h[(rows + 1) % height_px]
            current = h[start:end]
            dx = (np.roll(current, -1, axis=1) - np.roll(current, 1, axis=1)) * 0.5
            dy = (below - above) * 0.5
        else:
            dx = grad_x[start:end]
            dy = grad_y[start:end]

        nx = -dx * strength
        ny = -dy * strength
        if y_convention == "DirectX":
            ny *= -1.0
        length = np.sqrt(nx * nx + ny * ny + 1.0)
        nx /= length
        ny /= length
        nz = 1.0 / length

        chunk = result[start:end]
        chunk[..., 0] = np.rint(np.clip((nx * 0.5 + 0.5) * 255.0, 0, 255)).astype(np.uint8)
        chunk[..., 1] = np.rint(np.clip((ny * 0.5 + 0.5) * 255.0, 0, 255)).astype(np.uint8)
        chunk[..., 2] = np.rint(np.clip((nz * 0.5 + 0.5) * 255.0, 0, 255)).astype(np.uint8)

        if progress:
            progress(int(end / height_px * 100))

    return result



def height_to_normal(
    height: np.ndarray,
    strength: float = 4.0,
    y_convention: str = "OpenGL",
    seamless: bool = True,
    progress=None,
) -> np.ndarray:
    """Convert a height field using the native engine, falling back to NumPy."""
    from core.native_backend import get_native_backend

    if y_convention not in {"OpenGL", "DirectX"}:
        raise ValueError("y_convention must be 'OpenGL' or 'DirectX'")
    if strength < 0:
        raise ValueError("strength cannot be negative")
    array = np.asarray(height, dtype=np.float32)
    if array.ndim != 2 or min(array.shape) < 2:
        raise ValueError("height must be a 2D array at least 2x2")

    backend = get_native_backend()
    if backend is None:
        return _height_to_normal_python(
            array, strength, y_convention, seamless, progress
        )
    if progress:
        progress(5)
    result = backend.height_to_normal(array, strength, y_convention, seamless)
    if progress:
        progress(100)
    return np.asarray(result, dtype=np.uint8)
