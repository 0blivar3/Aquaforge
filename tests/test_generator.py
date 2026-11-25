import numpy as np
from core.generator import GeneratorSettings, generate_heightmap


def test_generator_shape_and_range():
    result = generate_heightmap(GeneratorSettings(width=128, height=64))
    assert result.shape == (64, 128)
    assert result.dtype == np.float32
    assert np.max(np.abs(result)) <= 1.00001


def test_seed_is_reproducible():
    settings = GeneratorSettings(width=64, height=64, seed=99)
    assert np.array_equal(generate_heightmap(settings), generate_heightmap(settings))


def test_seed_changes_result():
    a = generate_heightmap(GeneratorSettings(width=64, height=64, seed=1))
    b = generate_heightmap(GeneratorSettings(width=64, height=64, seed=2))
    assert not np.array_equal(a, b)


def test_resolution_validation():
    import pytest
    with pytest.raises(ValueError):
        generate_heightmap(GeneratorSettings(width=8, height=8))
