# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

qt_datas, qt_binaries, qt_hiddenimports = collect_all("PySide6")
opengl_hiddenimports = collect_submodules("OpenGL")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=qt_binaries,
    datas=qt_datas,
    hiddenimports=qt_hiddenimports + opengl_hiddenimports + ["core._aquaforge_native"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="AquaForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=False,
    name="AquaForge",
)
