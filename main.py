"""OpenSim Renderer application entry point."""

import argparse
import ctypes
import importlib.util
import os
import platform
import sys
from pathlib import Path

from osim_render.api.logging import get_logger_for
from osim_render.qt_preload import conda_icu_shadow_path

logger = get_logger_for(__name__)

_MSVC_RUNTIME_DLLS = ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll")


def _missing_msvc_runtime_dlls() -> list[str]:
    """Return MSVC runtime DLLs that Windows cannot load (PySide6 requires them)."""
    if sys.platform != "win32":
        return []

    missing: list[str] = []
    for dll_name in _MSVC_RUNTIME_DLLS:
        try:
            ctypes.WinDLL(dll_name)
        except OSError:
            missing.append(dll_name)
    return missing


def _qt_dll_directories_on_path() -> list[str]:
    """Return PATH directories carrying foreign Qt DLLs that can shadow PySide6's."""
    pyside_spec = importlib.util.find_spec("PySide6")
    pyside_dir = (
        Path(pyside_spec.origin).parent if pyside_spec and pyside_spec.origin else None
    )

    hits: list[str] = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        directory = Path(entry)
        if not entry or not directory.is_dir() or directory == pyside_dir:
            continue
        if (directory / "Qt6Core.dll").exists() or (directory / "Qt5Core.dll").exists():
            hits.append(str(directory))
    return hits


def _diagnose_qt_import_failure(error: ImportError) -> str:
    """Explain why PySide6 failed to import, with the most likely fix."""
    lines = [
        f"PySide6 (Qt) failed to import: {error}",
        f"Python {platform.python_version()} ({platform.architecture()[0]}) at {sys.executable}",
    ]

    pyside_spec = importlib.util.find_spec("PySide6")
    if pyside_spec is None or pyside_spec.origin is None:
        lines.append("PySide6 is not installed in this interpreter.")
        lines.append(
            "Fix: activate the project environment and run 'poetry install' "
            "(or 'pip install PySide6')."
        )
        return "\n".join(lines)

    lines.append(f"PySide6 package: {Path(pyside_spec.origin).parent}")

    icu_shadow = conda_icu_shadow_path()
    if icu_shadow is not None:
        lines.append(f"A conda ICU DLL shadows the Windows system ICU: {icu_shadow}")
        lines.append(
            "Qt6Core.dll needs the unversioned ICU exports from System32's "
            "icuuc.dll, but the conda copy (version-suffixed exports) wins the "
            "DLL search. osim_render.qt_preload.preload_system_icu() must run "
            "before the first PySide6 import to fix this."
        )

    missing_dlls = _missing_msvc_runtime_dlls()
    if missing_dlls:
        lines.append(
            f"Missing Microsoft Visual C++ runtime DLLs: {', '.join(missing_dlls)}"
        )
        lines.append(
            "Fix: install the Microsoft Visual C++ 2015-2022 Redistributable (x64): "
            "https://aka.ms/vs/17/release/vc_redist.x64.exe"
        )

    shadowing_dirs = _qt_dll_directories_on_path()
    if shadowing_dirs:
        lines.append("Directories on PATH contain other Qt DLLs that can shadow PySide6's:")
        lines.extend(f"  - {directory}" for directory in shadowing_dirs)
        lines.append(
            "Fix: remove these PATH entries before launching (common culprits: an "
            "OpenSim 'bin' directory or another conda environment's 'Library/bin')."
        )

    if not missing_dlls and not shadowing_dirs and icu_shadow is None:
        lines.append(
            "No missing MSVC runtime or PATH Qt conflict detected. Check that the "
            "interpreter is 64-bit Python >=3.11.9,<3.13 to match the PySide6 wheel."
        )
    return "\n".join(lines)


# Import Qt BEFORE VTK: a VTK build that bundles its own Qt (e.g. conda-forge)
# would otherwise load mismatched Qt DLLs into the process first and break the
# PySide6 import with "DLL load failed while importing QtWidgets".
try:
    from PySide6.QtWidgets import QApplication, QMessageBox
except ImportError as qt_error:
    logger.error(_diagnose_qt_import_failure(qt_error))
    sys.exit(1)

# Suppress VTK warnings early
try:
    import vtk

    vtk.vtkObject.GlobalWarningDisplayOff()
    vtk.vtkOutputWindow.SetGlobalWarningDisplay(0)

    if hasattr(vtk, "vtkOpenGLRenderWindow"):
        vtk.vtkOpenGLRenderWindow.SetGlobalMaximumNumberOfMultiSamples(0)
except ImportError:
    pass

# These imports pull in PySide6 (via MainWindow), so they must stay below the
# Qt import guard above.
from osim_render.api.managers.event_bus import EventBus  # noqa: E402
from osim_render.api.managers.model_manager import ModelManager  # noqa: E402
from osim_render.api.managers.settings_manager import SettingsManager  # noqa: E402
from osim_render.ui.main_window import MainWindow  # noqa: E402


def create_application() -> MainWindow:
    """Create and initialize the application.

    Returns:
        MainWindow instance ready for display

    Raises:
        RuntimeError: If application initialization fails
    """
    # Create managers
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    settings_manager = SettingsManager()

    # Create main window
    window = MainWindow(event_bus, model_manager, settings_manager)

    return window


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="OpenSim Renderer - 3D visualization of OpenSim biomechanical models",
        epilog="Examples:\n"
        "  poetry run python main.py                      # Launch with empty scene\n"
        "  poetry run python main.py model.osim           # Launch and load model\n"
        "  poetry run python main.py /path/to/model.osim  # Load from absolute path\n"
        "  poetry run python main.py models/ -g /OpenSim  # Add geometry search path",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "model",
        nargs="?",
        type=Path,
        default=None,
        help="Path to OpenSim model file (.osim) to load on startup",
    )

    parser.add_argument(
        "-g",
        "--geometry-path",
        type=Path,
        dest="geometry_paths",
        action="append",
        default=[],
        help="Add directory to search for geometry files (.vtp, .obj, .stl). "
        "Can be used multiple times for multiple paths.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output for debugging",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main application entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Application exit code
    """
    logger.info("OpenSim Renderer starting")

    args = parse_arguments(argv)

    if args.verbose:
        logger.info("Verbose mode enabled")
        if args.model:
            logger.info(f"Model: {args.model}")
        if args.geometry_paths:
            logger.info(f"Geometry paths: {args.geometry_paths}")

    print("OpenSim Renderer starting...")

    app = QApplication(sys.argv)

    try:
        window = create_application()
        window.show()

        # Add geometry search paths if provided
        if args.geometry_paths:
            settings = window.settings_manager.get_settings()
            for geom_path in args.geometry_paths:
                settings = settings.add_geometry_search_path(geom_path)
                if args.verbose:
                    print(f"[OK] Added geometry path: {geom_path}")
            window.settings_manager.update_settings(settings)

        # Load model if provided
        if args.model is not None:
            model_path = args.model

            if args.verbose:
                print(f"Loading model: {model_path}")

            if not model_path.exists():
                error_msg = f"Model file not found: {model_path}"
                print(f"[ERROR] {error_msg}")
                QMessageBox.critical(window, "File Not Found", error_msg)
            else:
                try:
                    window.model_manager.load_model(model_path)
                    print(f"[OK] Loaded model: {model_path}")
                except Exception as e:
                    error_msg = f"Failed to load model: {e}"
                    print(f"[ERROR] {error_msg}")
                    QMessageBox.critical(window, "Load Failed", error_msg)

        logger.info("Application ready")
        print("[OK] Application ready")
        return app.exec()

    except Exception as e:
        print(f"[ERROR] Failed to initialize application: {e}")
        raise


if __name__ == "__main__":
    """Entry point when run as script."""
    sys.exit(main())
