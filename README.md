# AquaForge

A desktop tool for procedural water-surface tangent-space Normal Map generation.

## MVP features
- Procedural multi-directional periodic wave and ripple generation.
- Mathematically normalized tangent-space normals.
- OpenGL (Y+) and DirectX (Y-) channel conventions.
- Seamless periodic generation.
- Adjustable resolution and wave parameters.
- Background generation on a Qt worker thread.
- PNG, TGA and TIFF export with overwrite confirmation.

## Requirements
Python 3.12+ is recommended. Install dependencies:

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

Run:

```bash
python main.py
```

## Tests

```bash
pytest
```

## Current scope
This is the first functional MVP. 3D preview, image-to-normal conversion, presets, tiling comparison and animated preview are planned for subsequent stages.
