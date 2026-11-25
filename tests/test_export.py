import numpy as np
from PIL import Image

from export.exporter import save_normal_map


def test_png_export_roundtrip(tmp_path):
    pixels = np.zeros((16, 16, 3), dtype=np.uint8)
    pixels[..., 2] = 255
    target = save_normal_map(pixels, tmp_path / "normal.png")
    loaded = np.asarray(Image.open(target).convert("RGB"))
    assert np.array_equal(pixels, loaded)
