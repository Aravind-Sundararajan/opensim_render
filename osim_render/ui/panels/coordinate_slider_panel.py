"""Dock panel for manipulating model coordinates with sliders."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Qt

import opensim

from osim_render.api.logging import get_logger_for
from osim_render.api.managers.event_bus import (
    EventBus,
    Event,
    event_handler,
    auto_subscribe_all_events,
)
from osim_render.api.managers.events import EventType
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.ui.coordinate_panel.state import (
    CoordinateInfo,
    CoordinatePanelState,
)
from osim_render.api.ui.coordinate_panel.slider_factory import CoordinateSliderRow

logger = get_logger_for(__name__)


class CoordinateSliderPanel(QDockWidget):
    """Dock panel for coordinate manipulation.

    Displays sliders for all model coordinates.
    Updates model state and visualization when sliders move.
    """

    def __init__(self, event_bus: EventBus, model_manager: ModelManager, parent: Optional[QWidget] = None):
        """Initialize coordinate slider panel.

        Args:
            event_bus: Application event bus for model load/unload events
            model_manager: Singleton ModelManager with shared model and state
            parent: Parent widget
        """
        super().__init__("Model Coordinates", parent)

        self.event_bus = event_bus
        self.model_manager = model_manager
        self.slider_rows: dict[str, CoordinateSliderRow] = {}
        self.state = CoordinatePanelState(
            model_loaded=False, model_path=None, coordinates=()
        )

        self.scene_manager: Any | None = None
        self.coordinates: tuple[CoordinateInfo, ...] = ()

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self._on_reset_to_default)
        self.reset_button.setEnabled(False)  # Disabled until model loads
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_content.setLayout(self.scroll_layout)

        self.placeholder_label = QLabel("Load a model to adjust coordinates")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_layout.addWidget(self.placeholder_label)
        self.scroll_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        self.setWidget(main_widget)

        # Auto-subscribe all @event_handler decorated methods
        auto_subscribe_all_events(self, event_bus)

    def set_scene_manager(self, scene_manager: Any) -> None:
        """Set the scene manager for visualization updates.

        Args:
            scene_manager: SceneManager instance
        """
        self.scene_manager = scene_manager

    def update_sliders_from_motion_frame(self, frame: Any) -> None:
        """Update all sliders to match motion frame data without triggering events.

        Args:
            frame: MotionFrame with coordinate_values dict

        Raises:
            AttributeError: If frame or slider_row lacks required attributes
            KeyError: If coordinate name not found in expected locations
        """
        for coord_name, slider_row in self.slider_rows.items():
            if coord_name in frame.coordinate_values:
                value = frame.coordinate_values[coord_name]
                slider_row.set_value(value)
                self.state.current_values[coord_name] = value

    @event_handler(EventType.MODEL_LOADED)
    def _on_model_loaded(self, event: Event) -> None:
        """Handle model loaded event.

        Model and state are now managed by ModelManager singleton.

        Raises:
            ValueError: If event data missing required fields
            AttributeError: If model or state lacks required methods
            RuntimeError: If coordinate extraction fails
        """
        filepath = event.data.get("filepath", "")
        if not filepath:
            raise ValueError("Model loaded event missing filepath")

        logger.info(f"Setting up coordinate sliders for model: {filepath}")
        model_path = Path(filepath)

        model = self.model_manager.get_opensim_model()
        if not model:
            raise RuntimeError("Model not available from ModelManager")

        opensim.Model.setDebugLevel(0)

        state = self.model_manager.get_opensim_state()
        coordinates = self._extract_coordinates(model, state)
        if not coordinates:
            raise ValueError("Model has no coordinates")

        logger.info(f"Found {len(coordinates)} coordinates, populating sliders")
        self.coordinates = coordinates

        # Populate panel with sliders
        self._populate_sliders(coordinates)
        logger.info("Slider panel populated successfully")

        # Enable reset button
        self.reset_button.setEnabled(True)

        current_values = {coord.name: coord.default_value for coord in coordinates}
        self.state = CoordinatePanelState(
            model_loaded=True,
            model_path=model_path,
            coordinates=coordinates,
            current_values=current_values,
        )

    @event_handler(EventType.MODEL_LOADING_FAILED)
    def _on_model_unloaded(self, event: Event) -> None:
        """Handle model unloaded event."""
        self._clear_panel()

    def _extract_coordinates(
        self, model: Any, state: Any
    ) -> tuple[CoordinateInfo, ...]:
        """Extract coordinate information from model.

        Args:
            model: OpenSim Model instance
            state: Current model state

        Returns:
            Tuple of CoordinateInfo for all coordinates

        Raises:
            AttributeError: If model or coordinate lacks required methods
            RuntimeError: If coordinate extraction fails
        """
        coordinates = []

        coord_set = model.getCoordinateSet()
        for i in range(coord_set.getSize()):
            coord = coord_set.get(i)
            name = coord.getName()

            min_val = coord.getRangeMin()
            max_val = coord.getRangeMax()
            default_val = coord.getDefaultValue()

            # Clamp default to range
            default_val = max(min_val, min(max_val, default_val))

            coordinates.append(
                CoordinateInfo(
                    name=name,
                    min_value=min_val,
                    max_value=max_val,
                    default_value=default_val,
                )
            )

        return tuple(coordinates)

    def _populate_sliders(self, coordinates: tuple[CoordinateInfo, ...]) -> None:
        """Create and layout sliders for coordinates.

        Args:
            coordinates: Tuple of CoordinateInfo
        """
        self._clear_sliders()

        while self.scroll_layout.count() > 0:
            item = self.scroll_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()

        for coord_info in coordinates:
            row = CoordinateSliderRow(coord_info, self)
            logger.debug(f"Created slider for {coord_info.name}")

            # Connect to valueChanged to catch all changes
            def make_callback(name: str) -> Callable[[int], None]:
                def callback(val: int) -> None:
                    logger.info(f"Slider moved: {name} = {val}")
                    self._on_slider_moved(name, val)

                return callback

            row.slider.valueChanged.connect(make_callback(coord_info.name))
            row.lockToggled.connect(self._on_lock_toggled)
            row.clampToggled.connect(self._on_clamp_toggled)
            self.slider_rows[coord_info.name] = row
            self.scroll_layout.addWidget(row)

        self._sync_constraints_from_model()

        logger.info(f"Created and connected {len(self.slider_rows)} coordinate sliders")
        self.scroll_layout.addStretch()

    def _clear_sliders(self) -> None:
        """Remove all slider rows."""
        for row in self.slider_rows.values():
            row.deleteLater()
        self.slider_rows.clear()

    def _clear_panel(self) -> None:
        """Clear the panel and show placeholder."""
        self._clear_sliders()

        while self.scroll_layout.count() > 0:
            item = self.scroll_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget and widget != self.placeholder_label:
                widget.deleteLater()

        self.controller = None
        self.coordinates = ()
        self.reset_button.setEnabled(False)
        self.state = CoordinatePanelState(
            model_loaded=False, model_path=None, coordinates=()
        )

        self.scroll_layout.addWidget(self.placeholder_label)
        self.scroll_layout.addStretch()

    def _sync_constraints_from_model(self) -> None:
        """Show each coordinate's current lock and clamp flags."""
        model = self.model_manager.get_opensim_model()
        state = self.model_manager.get_opensim_state()
        if model is None or state is None:
            return

        coordinate_set = model.getCoordinateSet()
        for name, row in self.slider_rows.items():
            coordinate = coordinate_set.get(name)
            row.set_constraints(
                locked=coordinate.getLocked(state),
                clamped=coordinate.getClamped(state),
            )

    def _on_lock_toggled(self, coord_name: str, locked: bool) -> None:
        """Hold a coordinate fixed, or release it.

        Args:
            coord_name: Coordinate the user toggled
            locked: True to hold the coordinate fixed
        """
        self._set_coordinate_flag(coord_name, locked, lock=True)

    def _on_clamp_toggled(self, coord_name: str, clamped: bool) -> None:
        """Enforce or release a coordinate's range during IK.

        Args:
            coord_name: Coordinate the user toggled
            clamped: True to keep the coordinate inside its range
        """
        self._set_coordinate_flag(coord_name, clamped, lock=False)

    def _set_coordinate_flag(self, coord_name: str, value: bool, lock: bool) -> None:
        """Apply a lock or clamp flag to the shared model state.

        Args:
            coord_name: Coordinate to modify
            value: New flag value
            lock: True to set the lock flag, False for the clamp flag
        """
        model = self.model_manager.get_opensim_model()
        state = self.model_manager.get_opensim_state()
        if model is None or state is None:
            raise RuntimeError("Cannot constrain coordinates before a model loads")

        coordinate = model.getCoordinateSet().get(coord_name)
        if lock:
            coordinate.setLocked(state, value)
        else:
            coordinate.setClamped(state, value)

        logger.info(
            f"{'Locked' if lock else 'Clamped'} {coord_name} -> {value}"
        )
        self.event_bus.publish_event(
            EventType.COORDINATE_CONSTRAINT_CHANGED,
            data={
                "coordinate_name": coord_name,
                "locked": coordinate.getLocked(state),
                "clamped": coordinate.getClamped(state),
            },
        )

    @event_handler(EventType.POSE_CHANGED)
    def _on_pose_changed(self, event: Event) -> None:
        """Follow an interactive IK drag without re-driving the model.

        The pose already lives in the model state, so sliders are set
        silently; emitting here would fight the solver mid-drag.

        Args:
            event: Event carrying the solved coordinate_values
        """
        coordinate_values = event.data.get("coordinate_values", {})

        for coord_name, value in coordinate_values.items():
            if coord_name not in self.slider_rows:
                continue
            self.slider_rows[coord_name].set_value(value)
            self.state.current_values[coord_name] = value

    def _on_slider_moved(self, coord_name: str, slider_value: int) -> None:
        """Handle slider movement - publish COORDINATE_CHANGED event.

        Args:
            coord_name: Name of coordinate that was moved
            slider_value: Slider position (integer)

        Raises:
            KeyError: If coordinate not found in slider_rows
            AttributeError: If slider_row lacks required methods
            RuntimeError: If event publishing fails
        """
        logger.debug(f"_on_slider_moved called: {coord_name} = {slider_value}")

        if coord_name not in self.slider_rows:
            raise KeyError(f"Coordinate {coord_name} not in slider_rows")

        slider_row = self.slider_rows[coord_name]
        value = slider_row.get_current_value()
        logger.debug(f"Got current value: {coord_name} = {value}")

        self.state.current_values[coord_name] = value

        logger.debug(f"Publishing COORDINATE_CHANGED event for {coord_name}")
        self.event_bus.publish_event(
            EventType.COORDINATE_CHANGED,
            data={
                "coordinate_name": coord_name,
                "value": value,
                "scene_manager": self.scene_manager,
            },
        )
        logger.debug("Event published successfully")

    def _on_reset_to_default(self) -> None:
        """Reset all coordinates to their default values.

        Raises:
            ValueError: If no coordinates available
            KeyError: If slider not found for coordinate
            AttributeError: If slider_row lacks required methods
        """
        logger.info("Resetting all coordinates to default values")

        if not self.coordinates:
            raise ValueError("No coordinates available to reset")

        for coord_info in self.coordinates:
            if coord_info.name not in self.slider_rows:
                raise KeyError(f"No slider found for {coord_info.name}")

            slider_row = self.slider_rows[coord_info.name]

            # The slider is mapped from min/max to 0/1000
            min_val = coord_info.min_value
            max_val = coord_info.max_value
            default_val = coord_info.default_value

            # Clamp to range
            default_val = max(min_val, min(max_val, default_val))

            # Map to slider range (0-1000)
            if max_val > min_val:
                slider_pos = int(((default_val - min_val) / (max_val - min_val)) * 1000)
            else:
                slider_pos = 500

            slider_row.slider.setValue(slider_pos)
            logger.debug(f"Reset {coord_info.name} to default: {default_val}")

        logger.info("All coordinates reset to default values")
