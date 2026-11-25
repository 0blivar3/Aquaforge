# AquaForge architecture

## Runtime layers

1. **Presentation (`app/`)** — PySide6 windows, widgets, 2D preview, OpenGL material preview and Qt worker orchestration.
2. **Application/core API (`core/`)** — stable Python entry points, settings dataclasses, presets, image conversion and backend selection.
3. **Native compute (`cpp/`)** — optional C++17 implementation for CPU-heavy height-field generation and tangent-space normal conversion.
4. **Rendering (`app/preview_3d.py`)** — OpenGL 2.1 / GLSL 1.20 renderer for interactive material inspection.
5. **I/O (`export/`)** — image export.

## Backend contract

`core.native_backend` is the only module that imports the compiled extension. Core Python modules call it through stable functions and retain NumPy implementations as a fallback. This means source checkouts remain runnable without a C++ compiler.

The C++ extension releases the Python GIL while its pixel loops execute. The Qt worker thread therefore does not block the GUI event loop during native processing.

## Build

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

The editable install compiles `core._aquaforge_native`. On Windows, install Visual Studio Build Tools with the Desktop development with C++ workload first.

If native compilation is unavailable, skip the editable install and run `python main.py`; the application automatically uses the NumPy fallback.

## Current boundaries

- C++ accelerates CPU generation and normal conversion.
- OpenGL currently renders the 3D preview. GPU compute shaders are not yet implemented.
- Export, image loading, preset persistence and GUI orchestration remain Python responsibilities.
- Native and fallback implementations are intentionally interchangeable at the Python API boundary.
