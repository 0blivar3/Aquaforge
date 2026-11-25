from core.generator import GeneratorSettings
from core.presets import BUILTIN_PRESETS, load_custom_presets, save_custom_preset


def test_expected_builtin_presets_exist():
    expected = {"Calm Water", "Ocean", "Lake", "River", "Storm", "Rain", "Swamp", "Stylized Water"}
    assert expected.issubset(BUILTIN_PRESETS)


def test_custom_preset_roundtrip(tmp_path):
    target = tmp_path / "presets.json"
    settings = GeneratorSettings(wave_scale=7.5, detail=6, seed=987)
    save_custom_preset("My Water", settings, target)
    loaded = load_custom_presets(target)
    assert loaded["My Water"]["wave_scale"] == 7.5
    assert loaded["My Water"]["detail"] == 6
    assert "seed" not in loaded["My Water"]


def test_builtin_name_is_reserved(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        save_custom_preset("Ocean", GeneratorSettings(), tmp_path / "presets.json")
