"""UI smoke tests for all panels."""

import pytest
from pytestqt.qtbot import QtBot
from PySide6.QtWidgets import QDockWidget, QWidget

from osim_render.ui.panels.outliner_panel import OutlinerPanel
from osim_render.ui.panels.scripting_panel import ScriptingPanel
from osim_render.ui.panels.coordinate_slider_panel import CoordinateSliderPanel
from osim_render.api.animation.script_executor import ScriptExecutor
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager


class TestOutlinerPanel:
    """Test OutlinerPanel widget instantiation."""

    def test_outliner_panel_instantiation(self, qtbot: QtBot) -> None:
        """Test OutlinerPanel can be instantiated."""
        panel = OutlinerPanel()
        qtbot.addWidget(panel)
        assert panel is not None
        assert isinstance(panel, QWidget)

    def test_outliner_panel_is_widget(self, qtbot: QtBot) -> None:
        """Test OutlinerPanel is a QWidget."""
        panel = OutlinerPanel()
        qtbot.addWidget(panel)
        assert isinstance(panel, QWidget)


class TestScriptingPanel:
    """Test ScriptingPanel widget instantiation."""

    @pytest.fixture
    def script_executor(self) -> ScriptExecutor:
        """Create script executor with real ModelManager."""
        model_manager = ModelManager(EventBus())
        event_bus = EventBus()
        return ScriptExecutor(
            model_manager,
            None,
            event_bus,
        )

    def test_scripting_panel_instantiation(self, qtbot: QtBot, script_executor: ScriptExecutor) -> None:
        """Test ScriptingPanel can be instantiated."""
        panel = ScriptingPanel(script_executor)
        qtbot.addWidget(panel)
        assert panel is not None
        assert isinstance(panel, QDockWidget)

    def test_scripting_panel_is_dock_widget(self, qtbot: QtBot, script_executor: ScriptExecutor) -> None:
        """Test ScriptingPanel is a QDockWidget."""
        panel = ScriptingPanel(script_executor)
        qtbot.addWidget(panel)
        assert isinstance(panel, QDockWidget)


class TestCoordinateSliderPanel:
    """Test CoordinateSliderPanel widget instantiation."""

    @pytest.fixture
    def event_bus(self) -> EventBus:
        """Create event bus."""
        return EventBus()

    @pytest.fixture
    def model_manager(self, event_bus: EventBus) -> ModelManager:
        """Create model manager."""
        return ModelManager(event_bus)

    def test_coordinate_slider_panel_instantiation(self, qtbot: QtBot, event_bus: EventBus, model_manager: ModelManager) -> None:
        """Test CoordinateSliderPanel can be instantiated."""
        panel = CoordinateSliderPanel(event_bus, model_manager)
        qtbot.addWidget(panel)
        assert panel is not None
        assert isinstance(panel, QDockWidget)

    def test_coordinate_slider_panel_is_dock_widget(self, qtbot: QtBot, event_bus: EventBus, model_manager: ModelManager) -> None:
        """Test CoordinateSliderPanel is a QDockWidget."""
        panel = CoordinateSliderPanel(event_bus, model_manager)
        qtbot.addWidget(panel)
        assert isinstance(panel, QDockWidget)

    def test_coordinate_slider_panel_title(self, qtbot: QtBot, event_bus: EventBus, model_manager: ModelManager) -> None:
        """Test CoordinateSliderPanel has a title."""
        panel = CoordinateSliderPanel(event_bus, model_manager)
        qtbot.addWidget(panel)
        assert panel.windowTitle() is not None


class TestPanelInstantiationAll:
    """Test all panels instantiate together."""

    @pytest.fixture
    def event_bus(self) -> EventBus:
        """Create event bus."""
        return EventBus()

    @pytest.fixture
    def model_manager(self, event_bus: EventBus) -> ModelManager:
        """Create model manager."""
        return ModelManager(event_bus)

    def test_all_panels_instantiate(self, qtbot: QtBot, event_bus: EventBus, model_manager: ModelManager) -> None:
        """Test all panels can be instantiated together."""
        outliner = OutlinerPanel()
        qtbot.addWidget(outliner)

        script_executor = ScriptExecutor(
            model_manager,
            None,
            event_bus,
        )
        scripting = ScriptingPanel(script_executor)
        qtbot.addWidget(scripting)

        coordinate_slider = CoordinateSliderPanel(event_bus, model_manager)
        qtbot.addWidget(coordinate_slider)

        assert outliner is not None
        assert scripting is not None
        assert coordinate_slider is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
