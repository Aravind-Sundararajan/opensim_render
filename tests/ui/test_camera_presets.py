"""Tests for camera preset functionality."""

import tempfile
from pathlib import Path
from collections.abc import Generator

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.managers.settings_manager import (
    SettingsManager,
    CameraPreset,
    ApplicationSettings,
)
from osim_render.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def app() -> QCoreApplication:
    """Create QApplication for tests."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def temp_settings_dir() -> Generator[Path, None, None]:
    """Create temporary settings directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestCameraPresetSettings:
    """Test camera preset settings storage and retrieval."""

    def test_camera_preset_creation(self) -> None:
        """Test creating a camera preset."""
        preset = CameraPreset(
            name="Front",
            position=(0, 0, 1),
            focal_point=(0, 0, 0),
            up_vector=(0, 1, 0),
        )
        assert preset.name == "Front"
        assert preset.position == (0, 0, 1)
        assert preset.parallel_projection is False

    def test_camera_preset_with_orthographic(self) -> None:
        """Test camera preset with orthographic projection."""
        preset = CameraPreset(
            name="Top",
            position=(0, 1, 0),
            focal_point=(0, 0, 0),
            up_vector=(0, 0, -1),
            parallel_projection=True,
        )
        assert preset.parallel_projection is True

    def test_add_camera_preset_to_settings(self) -> None:
        """Test adding camera preset to settings."""
        settings = ApplicationSettings()
        preset = CameraPreset(
            name="Front", position=(0, 0, 1), focal_point=(0, 0, 0), up_vector=(0, 1, 0)
        )
        settings = settings.with_camera_preset(preset)
        assert len(settings.camera_presets) == 1
        assert settings.camera_presets[0].name == "Front"

    def test_get_camera_preset(self) -> None:
        """Test retrieving camera preset from settings."""
        settings = ApplicationSettings()
        preset = CameraPreset(
            name="Front", position=(0, 0, 1), focal_point=(0, 0, 0), up_vector=(0, 1, 0)
        )
        settings = settings.with_camera_preset(preset)
        retrieved = settings.get_camera_preset("Front")
        assert retrieved is not None
        assert retrieved.name == "Front"
        assert retrieved.position == (0, 0, 1)

    def test_get_nonexistent_preset(self) -> None:
        """Test getting non-existent preset returns None."""
        settings = ApplicationSettings()
        retrieved = settings.get_camera_preset("NonExistent")
        assert retrieved is None

    def test_replace_camera_preset(self) -> None:
        """Test replacing camera preset with same name."""
        settings = ApplicationSettings()
        preset1 = CameraPreset(
            name="Front", position=(0, 0, 1), focal_point=(0, 0, 0), up_vector=(0, 1, 0)
        )
        settings = settings.with_camera_preset(preset1)
        preset2 = CameraPreset(
            name="Front", position=(0, 0, 2), focal_point=(0, 0, 0), up_vector=(0, 1, 0)
        )
        settings = settings.with_camera_preset(preset2)
        assert len(settings.camera_presets) == 1
        assert settings.camera_presets[0].position == (0, 0, 2)

    def test_save_load_presets(self, temp_settings_dir: Path) -> None:
        """Test saving and loading presets from file."""
        config_path = temp_settings_dir / "settings.json"
        manager = SettingsManager(config_path)
        settings = manager.get_settings()

        preset = CameraPreset(
            name="Front", position=(0, 0, 1), focal_point=(0, 0, 0), up_vector=(0, 1, 0)
        )
        settings = settings.with_camera_preset(preset)
        manager.update_settings(settings)

        # Create new manager and load settings
        manager2 = SettingsManager(config_path)
        loaded_settings = manager2.get_settings()
        assert len(loaded_settings.camera_presets) == 1
        assert loaded_settings.camera_presets[0].name == "Front"

    def test_multiple_presets(self, temp_settings_dir: Path) -> None:
        """Test storing multiple presets."""
        config_path = temp_settings_dir / "settings.json"
        manager = SettingsManager(config_path)
        settings = manager.get_settings()

        views = [
            ("Front", (0, 0, 1), (0, 1, 0)),
            ("Top", (0, 1, 0), (0, 0, -1)),
            ("Right", (1, 0, 0), (0, 1, 0)),
        ]

        for name, position, up_vector in views:
            preset = CameraPreset(
                name=name,
                position=position,
                focal_point=(0, 0, 0),
                up_vector=up_vector,
            )
            settings = settings.with_camera_preset(preset)

        manager.update_settings(settings)

        # Load and verify
        manager2 = SettingsManager(config_path)
        loaded = manager2.get_settings()
        assert len(loaded.camera_presets) == 3
        assert loaded.get_camera_preset("Front") is not None
        assert loaded.get_camera_preset("Top") is not None
        assert loaded.get_camera_preset("Right") is not None


class TestCameraPresetUI:
    """Test camera preset UI functionality."""

    def test_main_window_loads_presets(self, app: QCoreApplication, temp_settings_dir: Path) -> None:
        """Test main window loads presets from settings."""
        config_path = temp_settings_dir / "settings.json"
        settings_manager = SettingsManager(config_path)
        settings = settings_manager.get_settings()

        preset = CameraPreset(
            name="Front", position=(0, 0, 1), focal_point=(0, 0, 0), up_vector=(0, 1, 0)
        )
        settings = settings.with_camera_preset(preset)
        settings_manager.update_settings(settings)

        # Create window
        event_bus = EventBus()
        model_manager = ModelManager(event_bus)
        window = MainWindow(event_bus, model_manager, settings_manager)

        # Check that preset was added to combo
        preset_items = [
            window.presets_combo.itemText(i)
            for i in range(window.presets_combo.count())
        ]
        assert "Front" in preset_items

    def test_get_current_camera_state(self, app: QCoreApplication, temp_settings_dir: Path) -> None:
        """Test retrieving current camera state."""
        config_path = temp_settings_dir / "settings.json"
        settings_manager = SettingsManager(config_path)

        event_bus = EventBus()
        model_manager = ModelManager(event_bus)
        window = MainWindow(event_bus, model_manager, settings_manager)

        # Get initial camera state
        (
            position,
            focal_point,
            up_vector,
            is_parallel,
        ) = window._get_current_camera_state()
        assert position is not None
        assert focal_point is not None
        assert up_vector is not None
        assert isinstance(is_parallel, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
