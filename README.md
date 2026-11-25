# AquaForge

A desktop tool for procedural water-surface tangent-space Normal Map generation and image-to-normal conversion.

## Features

### Procedural generation
- Procedural multi-directional periodic wave and ripple generation.
- Adjustable resolution, wave scale, strength, frequency, direction, wind, ripple detail and distortion.
- Built-in presets: Calm Water, Ocean, Lake, River, Storm, Rain, Swamp and Stylized Water.
- Save and reuse custom presets (stored in the user's `.aquaforge/presets.json` folder).
- Mathematically normalized tangent-space normals.
- OpenGL (Y+) and DirectX (Y-) channel conventions.
- Seamless mode for tileable procedural textures.
- Background generation on a Qt worker thread.

### Image to Normal
- Load common image formats and use luminance or the Red, Green or Blue channel as a height source.
- Adjust normal strength and Y-channel convention.
- Preview the source image and the generated Normal Map.
- Convert images in a background worker thread.

### Export
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

## Roadmap

- Advanced wave models (including Gerstner-style waves and circular ripple emitters).
- 2D tiling/zoom comparison tools and channel inspection.
- Animated preview.
- Real-time 3D preview with PyOpenGL and GLSL.
