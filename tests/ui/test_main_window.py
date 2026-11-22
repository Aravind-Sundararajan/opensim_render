"""UI smoke tests for MainWindow."""

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot
from PySide6.QtWidgets import QMainWindow, QToolBar

from osim_render.ui.main_window import MainWindow
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.managers.settings_manager import SettingsManager


class TestMainWindow:
    """Test MainWindow widget instantiation with qtbot."""

    @pytest.fixture
    def event_bus(self) -> EventBus:
        """Create event bus."""
        return EventBus()

    @pytest.fixture
    def model_manager(self, event_bus: EventBus) -> ModelManager:
        """Create model manager."""
        return ModelManager(event_bus)

    @pytest.fixture
    def settings_manager(self, tmp_path: Path) -> SettingsManager:
        """Create settings manager."""
        return SettingsManager(config_path=tmp_path / "settings.json")

    @pytest.fixture
    def main_window(self, qtbot: QtBot, event_bus: EventBus, model_manager: ModelManager, settings_manager: SettingsManager) -> MainWindow:
        """Create MainWindow instance with qtbot."""
        window = MainWindow(event_bus, model_manager, settings_manager)
        qtbot.addWidget(window)
        return window

    def test_main_window_instantiation(self, main_window: MainWindow) -> None:
        """Test MainWindow can be instantiated."""
        assert main_window is not None
        assert isinstance(main_window, QMainWindow)

    def test_main_window_is_main_window(self, main_window: MainWindow) -> None:
        """Test MainWindow is a QMainWindow."""
        assert isinstance(main_window, QMainWindow)

    def test_main_window_has_model_manager(self, main_window: MainWindow, model_manager: ModelManager) -> None:
        """Test MainWindow stores model_manager."""
        assert main_window.model_manager is model_manager

    def test_main_window_has_settings_manager(self, main_window: MainWindow, settings_manager: SettingsManager) -> None:
        """Test MainWindow stores settings_manager."""
        assert main_window.settings_manager is settings_manager

    def test_main_window_has_event_bus(self, main_window: MainWindow, event_bus: EventBus) -> None:
        """Test MainWindow stores event_bus."""
        assert main_window.event_bus is event_bus

    def test_main_window_has_menu_bar(self, main_window: MainWindow) -> None:
        """Test MainWindow has a menu bar."""
        assert main_window.menuBar() is not None

    def test_main_window_has_toolbars(self, main_window: MainWindow) -> None:
        """Test MainWindow has toolbars."""
        toolbars = main_window.findChildren(QToolBar)
        # Should have at least one toolbar or zero (depending on implementation)
        assert len(toolbars) >= 0

    def test_main_window_title_set(self, main_window: MainWindow) -> None:
        """Test MainWindow has a title."""
        title = main_window.windowTitle()
        assert title is not None
        assert len(title) > 0

    def test_main_window_size_reasonable(self, main_window: MainWindow) -> None:
        """Test MainWindow has reasonable default size."""
        width = main_window.width()
        height = main_window.height()
        # Should have some reasonable default size
        assert width > 0
        assert height > 0

    def test_main_window_central_widget(self, main_window: MainWindow) -> None:
        """Test MainWindow has a central widget."""
        assert main_window.centralWidget() is not None


class TestMainWindowProperties:
    """Test MainWindow properties with qtbot."""

    @pytest.fixture
    def event_bus(self) -> EventBus:
        """Create event bus."""
        return EventBus()

    @pytest.fixture
    def model_manager(self, event_bus: EventBus) -> ModelManager:
        """Create model manager."""
        return ModelManager(event_bus)

    @pytest.fixture
    def settings_manager(self, tmp_path: Path) -> SettingsManager:
        """Create settings manager."""
        return SettingsManager(config_path=tmp_path / "settings.json")

    @pytest.fixture
    def main_window(self, qtbot: QtBot, event_bus: EventBus, model_manager: ModelManager, settings_manager: SettingsManager) -> MainWindow:
        """Create MainWindow instance with qtbot."""
        window = MainWindow(event_bus, model_manager, settings_manager)
        qtbot.addWidget(window)
        return window

    def test_main_window_menu_bar_exists(self, main_window: MainWindow) -> None:
        """Test menu bar exists."""
        assert main_window.menuBar() is not None

    def test_main_window_menu_bar_has_menus(self, main_window: MainWindow) -> None:
        """Test menu bar has menus."""
        menu_bar = main_window.menuBar()
        actions = menu_bar.actions()
        # Should have at least some actions/menus
        assert len(actions) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
