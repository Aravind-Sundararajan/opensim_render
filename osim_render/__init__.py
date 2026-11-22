"""OpenSim model and simulation renderer with C++/VTK integration.

A high-performance 3D visualization tool for OpenSim biomechanical models.
Provides fast mesh loading via C++ SWIG bindings with Python fallback to VTK.
"""

__version__ = "0.1.0"
__author__ = "Aravind Sundararajan"

# Must run before anything imports PySide6: binds Qt's ICU imports to the
# Windows system ICU before a conda-provided icuuc.dll can shadow it.
from osim_render.qt_preload import preload_system_icu

preload_system_icu()

# Import public API (below the preload call by design: loaders may pull in Qt)
from osim_render.api.loaders import (  # noqa: E402
    MeshGeometry,
    MeshLoaderProtocol,
    NativeMeshLoader,
    PythonMeshLoader,
    load_mesh,
)

__all__ = [
    "MeshGeometry",
    "MeshLoaderProtocol",
    "NativeMeshLoader",
    "PythonMeshLoader",
    "load_mesh",
]


if __name__ == "__main__":
    """Package smoke test."""
    print(f"osim_render {__version__}")
    print(f"Author: {__author__}")
    print("\n[OK] Package initialized successfully")
