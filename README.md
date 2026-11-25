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

### Advanced 2D preview
- Single texture preview and 3x3 tiling mode for checking repeat seams.
- Mouse-wheel zoom and click-and-drag panning.
- Isolated R, G and B channel inspection in grayscale.
- Source, result and side-by-side comparison.
- Reset View control.
- Animated texture playback with direction, speed and motion controls.
- Animation affects only the preview; exported Normal Maps remain static.

### Real-time 3D material preview
- OpenGL preview with Plane, Cube, Sphere and Cylinder meshes.
- Tangent-space Normal Map shader with diffuse and specular lighting.
- Adjustable UV tiling and normal intensity.
- Drag the viewport to rotate the preview object.
- The latest generated or converted Normal Map is uploaded to the 3D material preview.

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
