from setuptools import Extension, setup
import pybind11

extension = Extension(
    "core._aquaforge_native",
    ["cpp/aquaforge_core.cpp"],
    include_dirs=[pybind11.get_include()],
    language="c++",
    extra_compile_args=["/std:c++17"] if __import__("sys").platform == "win32" else ["-std=c++17"],
)

setup(ext_modules=[extension])
