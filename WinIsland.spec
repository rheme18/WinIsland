# -*- mode: python ; coding: utf-8 -*-

import os
import sys

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['packaging/pyi_rth_qt_dll.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# PyInstaller collects the Python installation's VCRUNTIME140.dll beside the
# application. That older copy may already be loaded before PyQt6 imports its
# Qt 6.12 binaries, which require the newer MSVC runtime shipped with PyQt6.
# Keep the shared runtime at the version used to build the bundled Qt DLLs.
qt_runtime_dir = os.path.join(
    sys.prefix, 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'bin'
)
for index, (destination, source, kind) in enumerate(a.binaries):
    runtime_name = os.path.basename(destination).lower()
    if runtime_name in {'vcruntime140.dll', 'vcruntime140_1.dll'}:
        qt_runtime = os.path.join(qt_runtime_dir, os.path.basename(destination))
        if os.path.isfile(qt_runtime):
            a.binaries[index] = (destination, qt_runtime, kind)

# PyInstaller may collect ICU from an unrelated PATH entry (for example,
# Poppler). Qt's DLLs expect the Windows system ICU ABI; never ship that
# unrelated, version-suffixed ICU build beside Qt.
a.binaries[:] = [
    entry for entry in a.binaries
    if os.path.basename(entry[0]).lower() not in {'icuuc.dll', 'icudt78.dll'}
]

# Make the matching C++ runtime available beside the executable. The Windows
# loader resolves these DLLs before PyInstaller can initialize its private
# library directory, so keeping them only under _internal is too late.
for runtime_name in ('MSVCP140.dll', 'MSVCP140_1.dll', 'MSVCP140_2.dll'):
    qt_runtime = os.path.join(qt_runtime_dir, runtime_name)
    if os.path.isfile(qt_runtime) and not any(
        entry[0].lower() == runtime_name.lower() for entry in a.binaries
    ):
        a.binaries.append((runtime_name, qt_runtime, 'BINARY'))
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WinIsland',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/WinIsland.ico'],
    contents_directory='.',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='WinIsland',
)
