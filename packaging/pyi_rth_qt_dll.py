"""Prefer the Qt libraries shipped with WinIsland over system-wide Qt DLLs."""

import os
import sys
import ctypes


_qt_dll_directory = None

if getattr(sys, "frozen", False):
    qt_bin = os.path.join(sys._MEIPASS, "PyQt6", "Qt6", "bin")
    if os.path.isdir(qt_bin):
        # Keep the handle alive for the process lifetime; Windows removes the
        # directory from its DLL search list when this handle is closed.
        _qt_dll_directory = os.add_dll_directory(qt_bin)
        os.environ["PATH"] = qt_bin + os.pathsep + os.environ.get("PATH", "")
        # Pin the bundled runtimes and ICU first. Windows may have already
        # loaded older system copies with these same filenames.
        _bundled_native_libraries = []
        for dll_name in (
            "VCRUNTIME140.dll",
            "VCRUNTIME140_1.dll",
            "MSVCP140.dll",
            "MSVCP140_1.dll",
            "MSVCP140_2.dll",
        ):
            dll_path = os.path.join(sys._MEIPASS, dll_name)
            if os.path.isfile(dll_path):
                _bundled_native_libraries.append(ctypes.WinDLL(dll_path))

        # Load the bundled QtCore by absolute path before PyQt6 imports it.
        _qt_core_library = ctypes.WinDLL(os.path.join(qt_bin, "Qt6Core.dll"))
        if sys.platform == "win32":
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
                sys._MEIPASS, "PyQt6", "Qt6", "plugins", "platforms"
            )
