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
- Adjustable UV tiling, normal intensity and light intensity.
- Drag the viewport to rotate the preview object.
- The latest generated or converted Normal Map is uploaded to the 3D material preview.

### Export
- PNG, TGA and TIFF export with overwrite confirmation.

## Architecture

- Python + PySide6 owns the application UI, task orchestration, presets and file workflows.
- The optional C++17 compute engine is exposed through pybind11 and accelerates procedural height-field generation and height-to-normal conversion.
- NumPy implementations remain available as a compatible fallback when the native extension has not been built.
- OpenGL/GLSL remains responsible for interactive 3D material rendering; this is currently a renderer, not yet a compute-shader backend.

### Easy installation (Windows)

Download `AquaForge-Windows-x64.zip` from the project's GitHub Releases, extract the archive, then launch:

```text
AquaForge/AquaForge.exe
```

No Python installation, pip commands or C++ compiler are required. The portable package already contains the Python runtime, Qt dependencies and the compiled C++ engine.

Windows builds are produced automatically by GitHub Actions. Every version tag beginning with `v` publishes a GitHub Release with the ZIP package attached.

### Run from source

Developers can still run the application from source:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
python main.py
```

The editable install compiles the optional C++ engine. If it is not built, AquaForge falls back to NumPy.

## Tests

```bash
pytest
```

## Roadmap

- Advanced wave models (including Gerstner-style waves and circular ripple emitters).
