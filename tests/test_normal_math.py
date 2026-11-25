import numpy as np
import pytest

from core.normal_math import height_to_normal


def test_flat_surface_is_neutral():
    result = height_to_normal(np.zeros((32, 32), dtype=np.float32))
    assert np.all(result == np.array([128, 128, 255], dtype=np.uint8))


def test_directx_flips_green_channel():
    y, x = np.mgrid[0:32, 0:32].astype(np.float32)
    height = y / 32.0
    gl = height_to_normal(height, strength=3, y_convention="OpenGL", seamless=False)
    dx = height_to_normal(height, strength=3, y_convention="DirectX", seamless=False)
    assert np.array_equal(gl[..., 0], dx[..., 0])
    assert np.array_equal(gl[..., 2], dx[..., 2])
    assert np.all(gl[..., 1] != dx[..., 1])


def test_normals_are_valid_rgb():
    rng = np.random.default_rng(7)
    result = height_to_normal(rng.random((64, 64), dtype=np.float32))
    assert result.dtype == np.uint8
    assert result.shape == (64, 64, 3)
    assert np.isfinite(result).all()


def test_invalid_input_rejected():
    with pytest.raises(ValueError):
        height_to_normal(np.zeros((8, 8, 3)))
