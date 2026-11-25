import numpy as np
from PIL import Image

from core.image_to_normal import load_height_image, convert_height_image


def test_load_height_image_luminance_and_channels(tmp_path):
    pixels = np.zeros((4, 5, 3), dtype=np.uint8)
    pixels[..., 0] = 255
    pixels[..., 1] = 128
    path = tmp_path / "height.png"
    Image.fromarray(pixels).save(path)

    luminance, source = load_height_image(path)
    red, _ = load_height_image(path, "Red")
    blue, _ = load_height_image(path, "Blue")

    assert luminance.shape == (4, 5)
    assert source.shape == (4, 5, 3)
    assert np.allclose(red, 1.0)
    assert np.allclose(blue, 0.0)
    assert np.all(luminance > 0.2)


def test_convert_height_image_returns_normal_map():
    height = np.tile(np.linspace(0, 1, 32, dtype=np.float32), (16, 1))
    result = convert_height_image(height, strength=4.0)
    assert result.shape == (16, 32, 3)
    assert result.dtype == np.uint8
