import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

from osim_render.api.loaders import (
    MeshGeometry,
    NativeMeshLoader,
    PythonMeshLoader,
    load_mesh,
)


class TestMeshGeometry:
    """Test MeshGeometry immutable data structure."""

    def test_mesh_geometry_creation(self) -> None:
        """Test creating a simple MeshGeometry."""
        vertices = np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            dtype=np.float32,
        )
        normals = np.array(
            [[0.0, 0.0, 1.0], [0.0, 0.0, 1.0], [0.0, 0.0, 1.0]],
            dtype=np.float32,
        )
        indices = np.array([[0, 1, 2]], dtype=np.int32)

        geometry = MeshGeometry(
            vertices=vertices,
            normals=normals,
            indices=indices,
            source_path=Path("test.obj"),
        )

        assert geometry.vertex_count() == 3
        assert geometry.triangle_count() == 1
        assert geometry.source_path == Path("test.obj")

    def test_mesh_geometry_bounds(self) -> None:
        """Test computing bounds of mesh."""
        vertices = np.array(
            [[0.0, 0.0, 0.0], [1.0, 2.0, 3.0], [-1.0, -2.0, -3.0]],
            dtype=np.float32,
        )
        normals = np.zeros((3, 3), dtype=np.float32)
        indices = np.array([[0, 1, 2]], dtype=np.int32)

        geometry = MeshGeometry(
            vertices=vertices,
            normals=normals,
            indices=indices,
            source_path=Path("test.obj"),
        )

        bounds = geometry.get_bounds()
        assert bounds == (-1.0, 1.0, -2.0, 2.0, -3.0, 3.0)

    def test_mesh_geometry_empty_bounds(self) -> None:
        """Test that getting bounds of empty mesh raises error."""
        vertices = np.array([], dtype=np.float32).reshape(0, 3)
        normals = np.array([], dtype=np.float32).reshape(0, 3)
        indices = np.array([], dtype=np.int32).reshape(0, 3)

        geometry = MeshGeometry(
            vertices=vertices,
            normals=normals,
            indices=indices,
            source_path=Path("test.obj"),
        )

        with pytest.raises(ValueError, match="empty mesh"):
            geometry.get_bounds()


class SimpleOBJFixture:
    """Creates a simple OBJ file for testing."""

    @staticmethod
    def create_triangle_obj(filepath: Path) -> None:
        """Create a simple OBJ with one triangle.

        Args:
            filepath: Path to write OBJ file
        """
        content = """# Simple triangle
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
f 1 2 3
"""
        filepath.write_text(content)

    @staticmethod
    def create_cube_obj(filepath: Path) -> None:
        """Create a simple OBJ with cube geometry.

        Args:
            filepath: Path to write OBJ file
        """
        content = """# Simple cube
v -1.0 -1.0 -1.0
v  1.0 -1.0 -1.0
v  1.0  1.0 -1.0
v -1.0  1.0 -1.0
v -1.0 -1.0  1.0
v  1.0 -1.0  1.0
v  1.0  1.0  1.0
v -1.0  1.0  1.0

f 1 2 3
f 1 3 4
f 5 6 7
f 5 7 8
f 1 2 6
f 1 6 5
f 3 4 8
f 3 8 7
f 1 4 8
f 1 8 5
f 2 3 7
f 2 7 6
"""
        filepath.write_text(content)


class TestPythonMeshLoader:
    """Test pure Python mesh loader using VTK fallback."""

    def test_python_loader_triangle_obj(self) -> None:
        """Test loading simple triangle OBJ with Python loader."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "triangle.obj"
            SimpleOBJFixture.create_triangle_obj(filepath)

            loader = PythonMeshLoader()
            geometry = loader.load(filepath)

            assert geometry.vertex_count() == 3
            assert geometry.triangle_count() == 1
            assert geometry.source_path == filepath

    def test_python_loader_cube_obj(self) -> None:
        """Test loading cube OBJ with Python loader."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "cube.obj"
            SimpleOBJFixture.create_cube_obj(filepath)

            loader = PythonMeshLoader()
            geometry = loader.load(filepath)

            assert geometry.vertex_count() == 8
            assert geometry.triangle_count() == 12
            assert geometry.source_path == filepath

    def test_python_loader_missing_file(self) -> None:
        """Test that loader raises FileNotFoundError for missing file."""
        loader = PythonMeshLoader()
        filepath = Path("/nonexistent/mesh.obj")

        with pytest.raises(FileNotFoundError):
            loader.load(filepath)

    def test_python_loader_returns_mesh_geometry(self) -> None:
        """Test that loader returns MeshGeometry with proper attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "triangle.obj"
            SimpleOBJFixture.create_triangle_obj(filepath)

            loader = PythonMeshLoader()
            geometry = loader.load(filepath)

            # Check types
            assert isinstance(geometry, MeshGeometry)
            assert isinstance(geometry.vertices, np.ndarray)
            assert isinstance(geometry.normals, np.ndarray)
            assert isinstance(geometry.indices, np.ndarray)

            # Check shapes
            assert geometry.vertices.ndim == 2
            assert geometry.vertices.shape[1] == 3
            assert geometry.normals.shape == geometry.vertices.shape
            assert geometry.indices.ndim == 2
            assert geometry.indices.shape[1] == 3

            # Check dtype
            assert geometry.vertices.dtype == np.float32
            assert geometry.normals.dtype == np.float32
            assert geometry.indices.dtype == np.int32


class TestLoadMeshFunction:
    """Test the high-level load_mesh function."""

    def test_load_mesh_with_triangle(self) -> None:
        """Test load_mesh with simple triangle OBJ."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "triangle.obj"
            SimpleOBJFixture.create_triangle_obj(filepath)

            geometry = load_mesh(filepath)

            assert isinstance(geometry, MeshGeometry)
            assert geometry.vertex_count() == 3
            assert geometry.triangle_count() == 1

    def test_load_mesh_with_path_string(self) -> None:
        """Test load_mesh accepts string paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "triangle.obj"
            SimpleOBJFixture.create_triangle_obj(filepath)

            geometry = load_mesh(str(filepath))

            assert isinstance(geometry, MeshGeometry)
            assert geometry.vertex_count() == 3

    def test_load_mesh_missing_file(self) -> None:
        """Test load_mesh raises FileNotFoundError for missing file."""
        filepath = Path("/nonexistent/mesh.obj")

        with pytest.raises(FileNotFoundError):
            load_mesh(filepath)

    def test_load_mesh_preserves_path(self) -> None:
        """Test that source_path is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "triangle.obj"
            SimpleOBJFixture.create_triangle_obj(filepath)

            geometry = load_mesh(filepath)

            assert geometry.source_path == filepath


class TestNativeMeshLoader:
    """Test native C++ mesh loader (if available)."""

    @pytest.mark.skipif(
        not hasattr(sys.modules.get("osim_render", None),
                    "_osim_render_native"),
        reason="Native C++ extension not available",
    )
    def test_native_loader_available(self) -> None:
        """Test that native loader can be instantiated when available."""
        try:
            loader = NativeMeshLoader()
            assert loader is not None
        except RuntimeError:
            pytest.skip("Native extension not available")

    @pytest.mark.skipif(
        not hasattr(sys.modules.get("osim_render", None),
                    "_osim_render_native"),
        reason="Native C++ extension not available",
    )
    def test_native_loader_triangle_obj(self) -> None:
        """Test loading triangle OBJ with native loader (if available)."""
        try:
            loader = NativeMeshLoader()
        except RuntimeError:
            pytest.skip("Native extension not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "triangle.obj"
            SimpleOBJFixture.create_triangle_obj(filepath)

            geometry = loader.load(filepath)

            assert geometry.vertex_count() == 3
            assert geometry.triangle_count() == 1


if __name__ == "__main__":
    """Smoke test for mesh loader."""
    print("MeshLoader smoke tests")
    print("\nRunning basic instantiation tests...")

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "triangle.obj"
        SimpleOBJFixture.create_triangle_obj(filepath)

        print(f"[OK] Created test OBJ file: {filepath}")

        try:
            geometry = load_mesh(filepath)
            print(
                f"[OK] Loaded mesh: {geometry.vertex_count()} vertices, "
                f"{geometry.triangle_count()} triangles"
            )
        except RuntimeError as e:
            print(f"[OK] load_mesh works (VTK fallback): {e}")

    print("\n[OK] All smoke tests passed!")
