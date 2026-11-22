"""Read mesh geometry files into VTK PolyData.

Provides a single, format-dispatching entry point used by the body and
contact visualizers so the extension-to-reader mapping lives in one place.
"""

from pathlib import Path
from typing import Protocol

import vtkmodules.all as vtk


class PolyDataReader(Protocol):
    """Structural type for VTK readers that produce PolyData from a file."""

    def SetFileName(self, name: str) -> None:
        """Set the source file path."""
        ...

    def Update(self) -> None:
        """Execute the reader."""
        ...

    def GetOutput(self) -> vtk.vtkPolyData:
        """Return the read PolyData."""
        ...


def create_reader(file_ext: str) -> PolyDataReader | None:
    """Create a VTK reader for a mesh file extension.

    Args:
        file_ext: Lowercase file extension including the dot (e.g. ".stl")

    Returns:
        A reader for the format, or None if the extension is unsupported
    """
    if file_ext == ".vtp":
        return vtk.vtkXMLPolyDataReader()
    if file_ext == ".obj":
        return vtk.vtkOBJReader()
    if file_ext == ".stl":
        return vtk.vtkSTLReader()
    return None


def read_polydata(file_path: Path) -> vtk.vtkPolyData | None:
    """Read a mesh file into VTK PolyData based on its extension.

    Args:
        file_path: Path to a VTP, OBJ, or STL geometry file

    Returns:
        The read PolyData, or None if the format is unsupported
    """
    reader = create_reader(file_path.suffix.lower())
    if reader is None:
        return None
    reader.SetFileName(str(file_path))
    reader.Update()
    return reader.GetOutput()


if __name__ == "__main__":
    print("Testing mesh_reader module...")

    assert create_reader(".vtp") is not None
    assert create_reader(".obj") is not None
    assert create_reader(".stl") is not None
    assert create_reader(".xyz") is None
    print("[PASS] create_reader dispatches by extension")

    assert read_polydata(Path("does_not_exist.xyz")) is None
    print("[PASS] read_polydata returns None for unsupported format")

    print("\n[PASS] All mesh_reader tests passed!")
