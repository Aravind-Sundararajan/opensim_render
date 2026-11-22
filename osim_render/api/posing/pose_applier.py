"""Push a solved pose into the scene and tell the rest of the app.

Shared by every interactive poser (body dragging, the root gizmo) so they all
realize, redraw and notify in exactly the same way.
"""

from __future__ import annotations

from typing import Any, Optional

from osim_render.api.logging import get_logger_for
from osim_render.api.managers.events import EventType

logger = get_logger_for(__name__)


class PoseApplier:
    """Realize a changed pose, refresh the actors and publish the result."""

    def __init__(self, scene_manager: Any, event_bus: Optional[Any] = None):
        """Initialize the applier.

        Args:
            scene_manager: SceneManager owning the model, state and actors
            event_bus: Optional EventBus for pose notifications
        """
        self.scene_manager = scene_manager
        self.event_bus = event_bus

    def apply(
        self, coordinate_values: dict[str, float], marker_error: float = 0.0
    ) -> None:
        """Refresh the scene for a pose already written into the state.

        Args:
            coordinate_values: Resulting coordinate values, for listeners
            marker_error: Residual IK error, zero when not applicable
        """
        self.scene_manager._realize_position()
        self.scene_manager.update_all_actor_positions()
        self._render()

        if self.event_bus is None:
            return

        self.event_bus.publish_event(
            EventType.POSE_CHANGED,
            data={
                "coordinate_values": coordinate_values,
                "marker_error": marker_error,
            },
        )

    def write_coordinates(self, values: dict[str, float]) -> dict[str, float]:
        """Write coordinate values into the shared state.

        Locked coordinates silently keep their existing value, so the returned
        mapping reflects what the model actually holds.

        Args:
            values: Desired coordinate values

        Returns:
            The values the model accepted
        """
        model = self.scene_manager.opensim_model
        state = self.scene_manager.state
        coordinate_set = model.getCoordinateSet()

        for name, value in values.items():
            coordinate_set.get(name).setValue(state, value, False)

        return {
            name: coordinate_set.get(name).getValue(state) for name in values
        }

    def _render(self) -> None:
        """Redraw the viewport if one is attached."""
        scene = self.scene_manager.scene
        if not scene or not scene.render_window:
            return

        scene.renderer.ResetCameraClippingRange()
        scene.render_window.Render()


if __name__ == "__main__":
    """Smoke test for PoseApplier."""
    import sys
    from pathlib import Path

    import opensim

    from osim_render.api.managers.event_bus import EventBus
    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
    from osim_render.api.rendering.scene import SceneManager

    model_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else str(Path(opensim.__file__).parent / "tests" / "arm26.osim")
    )
    print(f"PoseApplier smoke test on {model_path}")

    opensim.Model.setDebugLevel(-1)
    event_bus = EventBus()
    received: list[dict[str, Any]] = []
    event_bus.subscribe(EventType.POSE_CHANGED, lambda e: received.append(e.data))

    model_manager = ModelManager(event_bus)
    model_manager.load_model(model_path)

    offscreen = OffscreenRenderer(resolution=(320, 240))
    scene_manager = SceneManager(model_manager, model_path)
    scene_manager.create_scene(renderer=offscreen.renderer)

    applier = PoseApplier(scene_manager, event_bus)

    model = model_manager.get_opensim_model()
    assert model is not None, "model manager has no model"
    first = model.getCoordinateSet().get(0).getName()
    accepted = applier.write_coordinates({first: 0.4})
    print(f"[OK] Wrote {first}=0.4, model accepted {accepted[first]:.4f}")

    applier.apply(accepted)
    print(f"[OK] Applied and published {len(received)} event(s)")
    assert received and "coordinate_values" in received[-1]

    print("\nChecking locked coordinates are reported honestly...")
    model.getCoordinateSet().get(first).setLocked(scene_manager.state, True)
    accepted = applier.write_coordinates({first: 1.1})
    print(f"[OK] Locked write returned {accepted[first]:.4f} (not 1.1)")
    assert abs(accepted[first] - 1.1) > 1e-6

    print("\n[OK] Smoke test passed!")
