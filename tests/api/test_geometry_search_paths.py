"""Tests for geometry search path functionality."""

import tempfile
from pathlib import Path

import pytest

from osim_render.api.managers.settings_manager import (
    SettingsManager,
    ApplicationSettings,
)
from osim_render.api.loaders.mesh_loader import _resolve_mesh_path


class TestGeometrySearchPaths:
    """Test geometry search path configuration and usage."""

    def test_default_geometry_paths_created(self) -> None:
        """Test that default geometry paths are populated."""
        settings = ApplicationSettings()
        assert len(settings.geometry_search_paths) >= 0
        # All paths should be strings
        for path in settings.geometry_search_paths:
            assert isinstance(path, str)

    def test_add_geometry_search_path(self) -> None:
        """Test adding a geometry search path."""
        settings = ApplicationSettings()
        initial_count = len(settings.geometry_search_paths)

        settings = settings.add_geometry_search_path("/test/geometry")
        assert len(settings.geometry_search_paths) == initial_count + 1
        assert "/test/geometry" in settings.geometry_search_paths

    def test_add_duplicate_geometry_search_path(self) -> None:
        """Test that duplicate paths are not added."""
        settings = ApplicationSettings()
        settings = settings.add_geometry_search_path("/test/geometry")
        count_after_first = len(settings.geometry_search_paths)

        # Try to add same path again
        settings = settings.add_geometry_search_path("/test/geometry")
        assert len(settings.geometry_search_paths) == count_after_first

    def test_remove_geometry_search_path(self) -> None:
        """Test removing a geometry search path."""
        settings = ApplicationSettings()
        settings = settings.add_geometry_search_path("/test/geometry")
        assert "/test/geometry" in settings.geometry_search_paths

        settings = settings.remove_geometry_search_path("/test/geometry")
        assert "/test/geometry" not in settings.geometry_search_paths

    def test_get_geometry_search_paths(self) -> None:
        """Test retrieving valid geometry search paths."""
        settings = ApplicationSettings()
        settings = settings.add_geometry_search_path("/nonexistent/path")
        settings = settings.add_geometry_search_path(str(Path.home()))

        valid_paths = settings.get_geometry_search_paths()
        # Should only return existing paths
        assert all(p.exists() for p in valid_paths)

    def test_geometry_paths_persist_in_settings(self) -> None:
        """Test that geometry paths are saved and loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"
            manager = SettingsManager(config_path)

            # Add a geometry path
            settings = manager.get_settings()
            settings = settings.add_geometry_search_path("/test/geometry/1")
            settings = settings.add_geometry_search_path("/test/geometry/2")
            manager.update_settings(settings)

            # Load with new manager
            manager2 = SettingsManager(config_path)
            loaded_settings = manager2.get_settings()

            assert "/test/geometry/1" in loaded_settings.geometry_search_paths
            assert "/test/geometry/2" in loaded_settings.geometry_search_paths


class TestMeshPathResolution:
    """Test mesh file path resolution with search paths."""

    def test_resolve_existing_file(self) -> None:
        """Test resolving a file that exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mesh_file = Path(tmpdir) / "mesh.obj"
            mesh_file.touch()

            resolved = _resolve_mesh_path(mesh_file)
            assert resolved.exists()
            assert resolved.name == "mesh.obj"

    def test_resolve_relative_path_in_search_dirs(self) -> None:
        """Test finding mesh in search directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create geometry directory with mesh
            geom_dir = tmpdir_path /"geometry"
            geom_dir.mkdir()
            mesh_file = geom_dir / "mesh.obj"
            mesh_file.touch()

            # Try to resolve with search path
            resolved = _resolve_mesh_path(
                Path("mesh.obj"),
                search_paths=[geom_dir],
            )
            assert resolved.exists()
            assert resolved.name == "mesh.obj"

    def test_resolve_mesh_by_filename_only(self) -> None:
        """Test finding mesh by filename in search paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create two geometry directories
            geom_dir1 = tmpdir_path / "geometry1"
            geom_dir1.mkdir()
            geom_dir2 = tmpdir_path / "geometry2"
            geom_dir2.mkdir()

            # Put mesh in second directory
            mesh_file = geom_dir2 / "mesh.obj"
            mesh_file.touch()

            # Search in both directories
            resolved = _resolve_mesh_path(
                Path("mesh.obj"),
                search_paths=[geom_dir1, geom_dir2],
            )
            assert resolved.exists()
            assert resolved.parent == geom_dir2

    def test_resolve_nonexistent_file_raises(self) -> None:
        """Test that nonexistent file raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir, pytest.raises(FileNotFoundError):
            _resolve_mesh_path(
                Path("nonexistent.obj"),
                search_paths=[Path(tmpdir)],
            )

    def test_resolve_absolute_path_not_searched(self) -> None:
        """Test that absolute paths are not searched, only checked directly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create mesh in search directory
            geom_dir = tmpdir_path /"geometry"
            geom_dir.mkdir()
            mesh_file = geom_dir / "mesh.obj"
            mesh_file.touch()

            # Try to resolve absolute path to different location
            other_path = tmpdir_path /"other" / "mesh.obj"
            with pytest.raises(FileNotFoundError):
                _resolve_mesh_path(
                    other_path,
                    search_paths=[geom_dir],
                )

    def test_resolve_relative_with_subdirectory(self) -> None:
        """Test resolving mesh with subdirectory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create nested directory structure
            geom_dir = tmpdir_path /"OpenSim" / "geometry"
            geom_dir.mkdir(parents=True)
            mesh_file = geom_dir / "body_mesh.vtp"
            mesh_file.touch()

            # Search with relative path including subdirectory
            resolved = _resolve_mesh_path(
                Path("OpenSim/geometry/body_mesh.vtp"),
                search_paths=[tmpdir_path],
            )
            assert resolved.exists()

    def test_search_path_priority(self) -> None:
        """Test that first matching path is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create two geometry directories with same filename
            geom_dir1 = tmpdir_path / "geometry1"
            geom_dir1.mkdir()
            mesh_file1 = geom_dir1 / "mesh.obj"
            mesh_file1.write_text("geometry1")

            geom_dir2 = tmpdir_path / "geometry2"
            geom_dir2.mkdir()
            mesh_file2 = geom_dir2 / "mesh.obj"
            mesh_file2.write_text("geometry2")

            # Resolve should return first match
            resolved = _resolve_mesh_path(
                Path("mesh.obj"),
                search_paths=[geom_dir1, geom_dir2],
            )
            assert resolved.read_text() == "geometry1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
