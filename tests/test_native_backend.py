import numpy as np
import pytest

from core.native_backend import get_native_backend


@pytest.mark.skipif(get_native_backend() is None, reason="optional C++ extension is not built")
def test_native_generator_is_reproducible():
    backend = get_native_backend()
    args = (64, 48, 4.0, 1.0, 1.0, 35.0, 0.35, 0.25, 18.0, 3, 0.15, 1234)
    first = backend.generate_heightmap(*args)
    second = backend.generate_heightmap(*args)
    assert first.shape == (48, 64)
    assert first.dtype == np.float32
    assert np.array_equal(first, second)


@pytest.mark.skipif(get_native_backend() is None, reason="optional C++ extension is not built")
def test_native_normal_conversion_shape_and_format():
    backend = get_native_backend()
    height = np.zeros((32, 48), dtype=np.float32)
    result = backend.height_to_normal(height, 5.0, "OpenGL", True)
    assert result.shape == (32, 48, 3)
    assert result.dtype == np.uint8
    assert np.all(result == np.array([128, 128, 255], dtype=np.uint8))
