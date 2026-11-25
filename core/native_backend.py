"""Optional compiled backend loader for AquaForge's C++ engine."""
from __future__ import annotations

try:
    from core import _aquaforge_native as _native
except ImportError:
    _native = None


def get_native_backend():
    """Return the compiled backend module, or None when it is not installed."""
    return _native


def backend_name() -> str:
    return "C++17 / pybind11" if _native is not None else "Python / NumPy"


def is_native_available() -> bool:
    return _native is not None
