"""High-level mesh loading API with C++ backend and VTK fallback."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
import numpy.typing as npt

# Try to import the C++ extension module
try:
    from osim_render import _osim_render_native

    NATIVE_LOADER_AVAILABLE = True
except ImportError:
    NATIVE_LOADER_AVAILABLE = False

# VTK fallback
try:
    import vtkmodules.vtkIOGeometry as vtk_io
    import vtkmodules.vtkIOXML as vtk_xml
    from vtkmodules.vtkCommonDataModel import vtkPolyData

    VTK_AVAILABLE = True
except ImportError:
    VTK_AVAILABLE = False


@dataclass(frozen=True)
class MeshGeometry:
    """Immutable mesh geometry with vertex, normal, and index data.

    Contains 3D mesh data in NumPy arrays suitable for rendering
    with VTK or other graphics engines.

    Attributes:
        vertices: Nx3 array of vertex positions (float32)
        normals: Nx3 array of vertex normals (float32)
        indices: Mx3 array of triangle vertex indices (int32)
        source_path: Path to the source mesh file
    """

    vertices: npt.NDArray[np.float32]
    normals: npt.NDArray[np.float32]
    indices: npt.NDArray[np.int32]
    source_path: Path

    def vertex_count(self) -> int:
        """Get number of vertices.

        Returns:
            Number of vertices in the mesh
        """
        return len(self.vertices)

    def triangle_count(self) -> int:
        """Get number of triangles.

        Returns:
            Number of triangles in the mesh
        """
        return len(self.indices)

    def get_bounds(self) -> tuple[float, float, float, float, float, float]:
        """Get axis-aligned bounding box.

        Returns:
            Tuple (min_x, max_x, min_y, max_y, min_z, max_z)

        Raises:
            ValueError: If mesh has no vertices
        """
        if len(self.vertices) == 0:
            raise ValueError("Cannot compute bounds of empty mesh")

        return (
            float(np.min(self.vertices[:, 0])),
            float(np.max(self.vertices[:, 0])),
            float(np.min(self.vertices[:, 1])),
            float(np.max(self.vertices[:, 1])),
            float(np.min(self.vertices[:, 2])),
            float(np.max(self.vertices[:, 2])),
        )


class MeshLoaderProtocol(Protocol):
    """Abstract protocol for mesh loaders.

    Any object implementing this protocol can load mesh data
    from files and return immutable MeshGeometry objects.
    """

    def load(self, filepath: str | Path) -> MeshGeometry:
        """Load mesh from file.

        Args:
            filepath: Path to mesh file

        Returns:
            Immutable MeshGeometry

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file format is invalid or unsupported
        """
        ...


class NativeMeshLoader:
    """High-performance mesh loader using C++ SWIG extension.

    Wraps the native osim_render C++ module for fast OBJ and VTP
    file loading.

    Raises:
        RuntimeError: If C++ extension is not available
    """

    def __init__(self) -> None:
        """Initialize native loader.

        Raises:
            RuntimeError: If C++ extension module is not available
        """
        if not NATIVE_LOADER_AVAILABLE:
            raise RuntimeError(
                "Native C++ extension not available. "
                "Build the project with CMake and ensure _osim_render.pyd "
                "is in the Python path."
            )

    def load(self, filepath: str | Path) -> MeshGeometry:
        """Load mesh using C++ native code.

        Args:
            filepath: Path to OBJ or VTP file

        Returns:
            Immutable MeshGeometry

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If loading fails or format is invalid
            RuntimeError: If C++ native loader fails
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Mesh file not found: {filepath}")

        loader: Any = _osim_render_native.MeshLoader()
        mesh_data = loader.load(str(filepath))

        if mesh_data is None:
            raise ValueError(f"Failed to load mesh: {loader.get_error()}")

        # Convert C++ vectors to NumPy arrays
        vertices = np.array(mesh_data.vertices, dtype=np.float32)
        vertices = vertices.reshape(-1, 3)

        normals = np.array(mesh_data.normals, dtype=np.float32)
        if len(normals) == 0:
            normals = np.zeros((len(vertices), 3), dtype=np.float32)
        else:
            normals = normals.reshape(-1, 3)

        indices = np.array(mesh_data.indices, dtype=np.int32)
        indices = indices.reshape(-1, 3)

        return MeshGeometry(
            vertices=vertices,
            normals=normals,
            indices=indices,
            source_path=filepath,
        )


class PythonMeshLoader:
    """Pure Python mesh loader using VTK.

    Provides fallback mesh loading when C++ extension is unavailable.
    Supports OBJ and VTP formats via VTK.

    Raises:
        RuntimeError: If VTK is not available
    """

    def __init__(self) -> None:
        """Initialize Python loader.

        Raises:
            RuntimeError: If VTK is not available
        """
        if not VTK_AVAILABLE:
            raise RuntimeError(
                "VTK not available. Install vtk package: pip install vtk"
            )

    def load(self, filepath: str | Path) -> MeshGeometry:
        """Load mesh using VTK.

        Args:
            filepath: Path to OBJ or VTP file

        Returns:
            Immutable MeshGeometry

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If loading fails or format is invalid
            RuntimeError: If VTK operations fail
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Mesh file not found: {filepath}")

        poly_data = self._load_polydata(filepath)
        return self._polydata_to_geometry(poly_data, filepath)

    def _load_polydata(self, filepath: Path) -> vtkPolyData:
        """Load VTK PolyData from file.

        Args:
            filepath: Path to file

        Returns:
            vtkPolyData object

        Raises:
            ValueError: If file cannot be read
        """
        suffix = filepath.suffix.lower()

        reader: Any
        if suffix == ".obj":
            reader = vtk_io.vtkOBJReader()
        elif suffix == ".vtp":
            reader = vtk_xml.vtkXMLPolyDataReader()
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        reader.SetFileName(str(filepath))
        reader.Update()
        return cast(vtkPolyData, reader.GetOutput())

    def _polydata_to_geometry(
        self, poly_data: vtkPolyData, source_path: Path
    ) -> MeshGeometry:
        """Convert VTK PolyData to MeshGeometry.

        Args:
            poly_data: VTK PolyData object
            source_path: Path to source file

        Returns:
            MeshGeometry with vertex, normal, and index data
        """
        # Extract vertices
        points = poly_data.GetPoints()
        if points is None or points.GetNumberOfPoints() == 0:
            raise ValueError("PolyData has no points")

        num_points = points.GetNumberOfPoints()
        vertices = np.zeros((num_points, 3), dtype=np.float32)
        for i in range(num_points):
            point = points.GetPoint(i)
            vertices[i] = point[:3]

        # Extract normals if available
        normals_data = poly_data.GetPointData().GetNormals()
        if normals_data is not None:
            num_normals = normals_data.GetNumberOfTuples()
            normals = np.zeros((num_normals, 3), dtype=np.float32)
            for i in range(num_normals):
                normal = normals_data.GetTuple3(i)
                normals[i] = normal[:3]
        else:
            normals = np.zeros((num_points, 3), dtype=np.float32)

        # Extract triangles using safer method
        from vtkmodules.vtkCommonCore import vtkIdList

        polys = poly_data.GetPolys()
        if polys is None or polys.GetNumberOfCells() == 0:
            raise ValueError("PolyData has no polygons")

        indices = []
        num_cells = polys.GetNumberOfCells()

        for cell_id in range(num_cells):
            id_list = vtkIdList()
            polys.GetCellAtId(cell_id, id_list)

            num_ids = id_list.GetNumberOfIds()
            if num_ids >= 3:
                for i in range(1, num_ids - 1):
                    indices.append(
                        [
                            id_list.GetId(0),
                            id_list.GetId(i),
                            id_list.GetId(i + 1),
                        ]
                    )

        if not indices:
            raise ValueError("PolyData has no triangles")

        indices_array = np.array(indices, dtype=np.int32)

        return MeshGeometry(
            vertices=vertices,
            normals=normals,
            indices=indices_array,
            source_path=source_path,
        )


def _resolve_mesh_path(
    filepath: str | Path, search_paths: list[Path] | None = None
) -> Path:
    """Resolve mesh file path with fallback search.

    Searches for mesh file in the following order:
    1. Direct path (absolute or relative)
    2. Same directory as file (if subdirectory specified)
    3. User-configured geometry search paths

    Args:
        filepath: Path to mesh file
        search_paths: Optional list of paths to search for geometry files

    Returns:
        Resolved Path to mesh file

    Raises:
        FileNotFoundError: If file cannot be found in any search path
    """
    filepath = Path(filepath)

    # Try direct path first
    if filepath.exists():
        return filepath

    # If path is absolute and doesn't exist, fail
    if filepath.is_absolute():
        raise FileNotFoundError(f"Mesh file not found: {filepath}")

    # Search in provided search paths
    if search_paths:
        for search_dir in search_paths:
            candidate = search_dir / filepath.name
            if candidate.exists():
                return candidate

            # Also try with relative path structure
            candidate = search_dir / filepath
            if candidate.exists():
                return candidate

    # Not found anywhere
    raise FileNotFoundError(
        f"Mesh file not found: {filepath} (searched in {len(search_paths or [])} locations)"
    )


def load_mesh(
    filepath: str | Path, search_paths: list[Path] | None = None
) -> MeshGeometry:
    """Load a mesh file with automatic loader selection.

    Tries to use fast C++ native loader if available,
    falls back to VTK-based Python loader.

    Searches for mesh files in configured geometry search paths
    if the direct path doesn't exist.

    Args:
        filepath: Path to mesh file (OBJ or VTP)
        search_paths: Optional list of paths to search for geometry files

    Returns:
        Immutable MeshGeometry

    Raises:
        FileNotFoundError: If file does not exist in any search path
        ValueError: If file format is invalid or all loaders fail
        RuntimeError: If no suitable loader is available
    """
    filepath = Path(filepath)

    # Resolve path with search paths, or use as-is if absolute
    if filepath.exists():
        resolved_path = filepath
    elif filepath.is_absolute():
        resolved_path = filepath  # Will fail in loader with FileNotFoundError
    else:
        # Try search paths
        resolved_path = _resolve_mesh_path(filepath, search_paths)

    # Try native loader first if available
    if NATIVE_LOADER_AVAILABLE:
        loader = NativeMeshLoader()
        return loader.load(resolved_path)

    # Fall back to VTK loader if available
    if VTK_AVAILABLE:
        vtk_loader = PythonMeshLoader()
        return vtk_loader.load(resolved_path)

    # No loader available
    raise RuntimeError(
        "No mesh loader available. Install VTK or build C++ extension: "
        "pip install vtk or cmake --build build"
    )


if __name__ == "__main__":
    """Smoke test for mesh loading."""
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        print(f"Loading mesh: {filepath}")
        geometry = load_mesh(filepath)
        print(
            f"[OK] Loaded {geometry.vertex_count()} vertices, "
            f"{geometry.triangle_count()} triangles"
        )
        bounds = geometry.get_bounds()
        print(f"[OK] Bounds: {bounds}")
    else:
        print("MeshLoader smoke test")
        print(f"Usage: python {Path(__file__).name} <mesh_file>")
        print(f"\nNative loader available: {NATIVE_LOADER_AVAILABLE}")
        print(f"VTK loader available: {VTK_AVAILABLE}")
        print("\n[OK] Smoke test passed!")
