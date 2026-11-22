"""Controller for coordinate slider updates to model state."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from osim_render.api.managers.event_bus import (
    EventBus,
    Event,
    event_handler,
    auto_subscribe_all_events,
)
from osim_render.api.managers.events import EventType
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.logging import get_logger_for

if TYPE_CHECKING:
    from osim_render.api.rendering.scene import SceneManager

logger = get_logger_for(__name__)


class CoordinatePanelController:
    """Update model state and visualization when coordinates change.

    Subscribes to COORDINATE_CHANGED events and:
    1. Sets the coordinate value in the model state
    2. Realizes position (computing forward kinematics)
    3. Updates the scene visualization
    """

    def __init__(self, model_manager: ModelManager, event_bus: EventBus | None = None):
        """Initialize controller.

        Args:
            model_manager: Singleton ModelManager with shared model and state
            event_bus: Application event bus (optional, for testing)
        """
        self.model_manager = model_manager
        self.event_bus = event_bus

        # Auto-subscribe all @event_handler decorated methods if event bus available
        if event_bus:
            auto_subscribe_all_events(self, event_bus)

    @event_handler(EventType.COORDINATE_CHANGED)
    def _on_coordinate_changed(self, event: Event) -> None:
        """Handle coordinate changed event.

        Args:
            event: Event with coordinate_name, value, scene_manager
        """
        logger.info("COORDINATE_CHANGED event received")

        data = event.data
        coord_name = data.get("coordinate_name")
        value = data.get("value")
        scene_manager = data.get("scene_manager")

        logger.info(
            f"Event data: coord_name={coord_name}, value={value}, has_scene_manager={scene_manager is not None}"
        )

        if not all([coord_name, value is not None]):
            logger.warning("Invalid coordinate changed event data")
            return

        logger.info(f"Processing coordinate change: {coord_name} = {value}")
        self._update_coordinate(coord_name, value, scene_manager)

    def _update_coordinate(
        self,
        coord_name: str,
        value: float,
        scene_manager: Optional[SceneManager] = None,
    ) -> None:
        """Update coordinate value and realize position.

        Args:
            coord_name: Name of coordinate to update
            value: New value (in coordinate's native units: radians or meters)
            scene_manager: Optional SceneManager for visualization updates

        Raises:
            ValueError: If model/state not available or coordinate not found
            RuntimeError: If position realization fails
        """
        logger.info(f"Updating coordinate: {coord_name} = {value}")

        opensim_model = self.model_manager.get_opensim_model()
        opensim_state = self.model_manager.get_opensim_state()

        if not opensim_model or not opensim_state:
            raise ValueError("Model or state not available from ModelManager")

        coord = opensim_model.getCoordinateSet().get(coord_name)
        if not coord:
            raise ValueError(f"Coordinate not found: {coord_name}")

        coord.setValue(opensim_state, value)
        logger.info(f"Coordinate value set: {coord_name}")

        # Realize position using SceneManager if available
        # (ensures both position stage is realized AND SceneManager's flag is set)
        if scene_manager:
            scene_manager._realize_position()
            logger.info("Position realized successfully via SceneManager")

            logger.info("Updating scene visualization")
            self._update_scene(scene_manager)
            logger.info("Scene visualization updated")
        else:
            # Fallback: realize position directly if no scene manager
            opensim_model.realizePosition(opensim_state)
            logger.info("Position realized successfully (direct)")

    def _update_scene(self, scene_manager: SceneManager) -> None:
        """Update all actor positions in the 3D scene and trigger a render.

        Args:
            scene_manager: SceneManager instance to update
        """
        scene = scene_manager.get_scene()
        if not scene:
            return

        scene_manager.update_all_actor_positions()

        if scene.render_window:
            scene.render_window.Render()
            logger.debug("VTK render triggered")
