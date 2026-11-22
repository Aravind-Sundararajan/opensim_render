"""Work around conda ICU DLLs shadowing the Windows system ICU for Qt.

PySide6's Qt6Core.dll imports unversioned ICU symbols (ucnv_open, ...) that
Windows provides via System32's icuuc.dll. conda-forge's icu package (pulled
in transitively by libxml2/libpsl since icu 78) ships an icuuc.dll whose
exports are version-suffixed (ucnv_open_78, ...), and the conda interpreter
registers <env>/Library/bin as a DLL search directory, which Windows searches
BEFORE System32. Qt's import then binds to the wrong icuuc.dll and dies with
"DLL load failed while importing QtCore: The specified procedure could not be
found".

Pre-loading the System32 copies fixes this: modules already loaded into the
process take precedence by name when static imports are resolved, regardless
of search-path order. Call preload_system_icu() before the first PySide6
import; osim_render/__init__.py does this automatically.
"""

import ctypes
import os
import sys
from pathlib import Path

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)

_SYSTEM_ICU_DLLS = ("icuuc.dll", "icuin.dll")


def conda_icu_shadow_path() -> Path | None:
    """Return the conda env's icuuc.dll if one exists to shadow the system's."""
    if sys.platform != "win32":
        return None
    candidate = Path(sys.prefix) / "Library" / "bin" / "icuuc.dll"
    return candidate if candidate.exists() else None


def preload_system_icu() -> None:
    """Load System32's ICU DLLs so Qt binds to them instead of conda's."""
    if sys.platform != "win32":
        return

    system32 = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32"
    for dll_name in _SYSTEM_ICU_DLLS:
        dll_path = system32 / dll_name
        if not dll_path.exists():
            logger.debug(f"System ICU DLL not present, skipping: {dll_path}")
            continue
        try:
            ctypes.WinDLL(str(dll_path))
        except OSError as exc:
            logger.warning(f"Could not pre-load {dll_path}: {exc}")


if __name__ == "__main__":
    """Smoke test: preload, then prove the Qt import works."""
    print("qt_preload smoke test")
    shadow = conda_icu_shadow_path()
    print(f"conda ICU shadow present: {shadow}")
    preload_system_icu()
    from PySide6 import QtCore

    print(f"[OK] QtCore imported, Qt {QtCore.qVersion()}")
