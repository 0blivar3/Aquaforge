from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re

from core.generator import GeneratorSettings


BUILTIN_PRESETS: dict[str, dict[str, float | int]] = {
    "Calm Water": {
        "wave_scale": 2.2, "wave_strength": 0.45, "frequency": 0.7,
        "direction": 18, "wind_strength": 0.08, "ripple_intensity": 0.08,
        "ripple_scale": 12, "detail": 2, "distortion": 0.04,
    },
    "Ocean": {
        "wave_scale": 5.5, "wave_strength": 1.35, "frequency": 1.15,
        "direction": 28, "wind_strength": 0.85, "ripple_intensity": 0.3,
        "ripple_scale": 22, "detail": 5, "distortion": 0.24,
    },
    "Lake": {
        "wave_scale": 3.0, "wave_strength": 0.6, "frequency": 0.8,
        "direction": 70, "wind_strength": 0.18, "ripple_intensity": 0.12,
        "ripple_scale": 15, "detail": 3, "distortion": 0.08,
    },
    "River": {
        "wave_scale": 7.0, "wave_strength": 0.85, "frequency": 1.3,
        "direction": 90, "wind_strength": 0.35, "ripple_intensity": 0.38,
        "ripple_scale": 25, "detail": 5, "distortion": 0.18,
    },
    "Storm": {
        "wave_scale": 8.0, "wave_strength": 2.2, "frequency": 1.65,
        "direction": 35, "wind_strength": 1.8, "ripple_intensity": 0.75,
        "ripple_scale": 34, "detail": 8, "distortion": 0.55,
    },
    "Rain": {
        "wave_scale": 2.8, "wave_strength": 0.55, "frequency": 1.0,
        "direction": 15, "wind_strength": 0.2, "ripple_intensity": 1.1,
        "ripple_scale": 42, "detail": 8, "distortion": 0.3,
    },
    "Swamp": {
        "wave_scale": 1.8, "wave_strength": 0.3, "frequency": 0.55,
        "direction": 120, "wind_strength": 0.05, "ripple_intensity": 0.18,
        "ripple_scale": 8, "detail": 2, "distortion": 0.42,
    },
    "Stylized Water": {
        "wave_scale": 4.5, "wave_strength": 1.6, "frequency": 1.0,
        "direction": 45, "wind_strength": 0.45, "ripple_intensity": 0.65,
        "ripple_scale": 16, "detail": 4, "distortion": 0.08,
    },
}

PRESET_FIELDS = set(asdict(GeneratorSettings())) - {"width", "height", "seed", "seamless"}
PRESET_FILE = Path.home() / ".aquaforge" / "presets.json"


def load_custom_presets(path: Path = PRESET_FILE) -> dict[str, dict[str, float | int]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    valid: dict[str, dict[str, float | int]] = {}
    for name, values in data.items():
        if not isinstance(name, str) or not isinstance(values, dict):
            continue
        clean = {key: value for key, value in values.items()
                 if key in PRESET_FIELDS and isinstance(value, (int, float))
                 and not isinstance(value, bool)}
        if clean:
            valid[name] = clean
    return valid


def save_custom_preset(name: str, settings: GeneratorSettings,
                       path: Path = PRESET_FILE) -> None:
    clean_name = re.sub(r"[\\/:*?\"<>|]", "_", name).strip()
    if not clean_name:
        raise ValueError("Preset name cannot be empty")
    if clean_name in BUILTIN_PRESETS:
        raise ValueError("That name is reserved for a built-in preset")
    data = load_custom_presets(path)
    values = asdict(settings)
    data[clean_name] = {key: values[key] for key in PRESET_FIELDS}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
