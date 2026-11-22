"""Coordinate an interactive drag-to-pose gesture.

Owns the lifecycle of a drag: pick a body, pin a drag plane through the grab
point, then solve and redraw on every mouse move until the button is released.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for
from osim_render.api.managers.events import EventType
from osim_render.api.posing.body_picker import BodyPicker
from osim_render.api.posing.drag_marker_rig import DragMarkerRig
from osim_render.api.posing.drag_plane import DragPlane, Point3D
from osim_render.api.posing.jacobian_pose_solver import JacobianPoseSolver
from osim_render.api.posing.model_root import find_model_root
from osim_render.api.posing.pose_applier import PoseApplier
from osim_render.api.posing.pose_solver import PoseSolution, PoseSolver

logger = get_logger_for(__name__)


@dataclass(frozen=True)
class DragSession:
    """State captured when a drag begins and held until it ends."""

    body_name: str
    marker_name: str
    plane: DragPlane
    grab_point: Point3D


class DragPoseController:
    """Pose a model by dragging its bodies, solved by OpenSim IK."""

    def __init__(
        self,
        scene_manager: Any,
        rig: DragMarkerRig,
        event_bus: Optional[Any] = None,
        solver: Optional[Union[PoseSolver, JacobianPoseSolver]] = None,
    ):
        """Initialize the drag-to-pose controller.

        Args:
            scene_manager: SceneManager owning the model, state and actors
            rig: DragMarkerRig installed on the same model
            event_bus: Optional EventBus for pose notifications
            solver: Optional solver. Defaults to JacobianPoseSolver; pass a
                PoseSolver to fall back to the assemble-based path.
        """
        self.scene_manager = scene_manager
        self.rig = rig
        self.event_bus = event_bus
        # JacobianPoseSolver steps the pose from Simbody's exact station
        # Jacobian instead of re-assembling every mouse-move. On the 198-
        # coordinate spine model a pinned hand drag goes 60 -> 19 ms/step, and
        # the drag stops spraying into joints that cannot affect the target.
        # Swap PoseSolver back in here to compare.
        self.solver = solver or JacobianPoseSolver(scene_manager.opensim_model)
        self.applier = PoseApplier(scene_manager, event_bus)
        self.session: Optional[DragSession] = None
        self._picker: Optional[BodyPicker] = None

        self.root = find_model_root(scene_manager.opensim_model)
        # Only a floating base is worth pinning. Pinning a one-axis root such
        # as arm26's shoulder would just freeze the arm.
        self.pin_root = bool(self.root and self.root.is_floating_base)

    @property
    def can_pin_root(self) -> bool:
        """Whether this model has a floating base that pinning would affect."""
        return bool(self.root and self.root.is_floating_base)

    def set_pin_root(self, pinned: bool) -> None:
        """Choose whether drags hold the floating base still.

        Args:
            pinned: True to articulate joints instead of moving the whole model
        """
        self.pin_root = pinned
        logger.info(f"Root pinning {'enabled' if pinned else 'disabled'}")

    def _pinned_coordinates(self) -> frozenset[str]:
        """Root coordinates to hold fixed for the current drag.

        Returns:
            Coordinate names to pin, empty when pinning is off
        """
        if not self.pin_root or self.root is None:
            return frozenset()
        return frozenset(self.root.coordinate_names)

    @property
    def is_dragging(self) -> bool:
        """Whether a drag is currently in progress."""
        return self.session is not None

    def begin_drag(
        self, renderer: vtk.vtkRenderer, display_x: int, display_y: int
    ) -> bool:
        """Start a drag if a body lies under the cursor.

        Args:
            renderer: Renderer showing the model
            display_x: Viewport x coordinate
            display_y: Viewport y coordinate

        Returns:
            True if a body was grabbed and the drag started
        """
        pick = self._picker_for_scene().pick(renderer, display_x, display_y)
        if pick is None:
            return False

        if not self.rig.has_marker_for(pick.body_name):
            logger.warning(f"Body has no drag marker, ignoring: {pick.body_name}")
            return False

        marker_name = self.rig.set_grab_point(pick.body_name, pick.local_point)
        self.session = DragSession(
            body_name=pick.body_name,
            marker_name=marker_name,
            plane=DragPlane.facing_camera(renderer.GetActiveCamera(), pick.world_point),
            grab_point=pick.world_point,
        )

        logger.info(f"Drag started on body: {pick.body_name}")
        self._publish(EventType.POSE_DRAG_STARTED, {"body_name": pick.body_name})
        return True

    def update_drag(
        self, renderer: vtk.vtkRenderer, display_x: int, display_y: int
    ) -> bool:
        """Solve and redraw for a new cursor position.

        Args:
            renderer: Renderer showing the model
            display_x: Viewport x coordinate
            display_y: Viewport y coordinate

        Returns:
            True if the pose was updated
        """
        if self.session is None:
            return False

        target = self.session.plane.project_display_point(
            renderer, display_x, display_y
        )
        if target is None:
            return False

        solution = self.solver.solve(
            self.scene_manager.state,
            self.session.marker_name,
            target,
            pinned_coordinates=self._pinned_coordinates(),
        )
        self._apply(solution)
        return True

    def end_drag(self) -> None:
        """Finish the current drag, if any."""
        if self.session is None:
            return

        logger.info(f"Drag ended on body: {self.session.body_name}")
        body_name = self.session.body_name
        self.session = None
        self._publish(EventType.POSE_DRAG_ENDED, {"body_name": body_name})

    def invalidate_scene(self) -> None:
        """Drop cached actors so the next pick rebuilds against a new scene."""
        self._picker = None

    def _apply(self, solution: PoseSolution) -> None:
        """Push a solved pose into the scene and notify listeners.

        Args:
            solution: Result of the IK solve
        """
        self.applier.apply(solution.coordinate_values, solution.marker_error)

    def _picker_for_scene(self) -> BodyPicker:
        """Get a picker bound to the current scene's body actors.

        Returns:
            BodyPicker for the active scene

        Raises:
            RuntimeError: If no scene has been created yet
        """
        if self._picker is not None:
            return self._picker

        scene = self.scene_manager.scene
        if scene is None:
            raise RuntimeError("Cannot pick bodies before a scene is created")

        self._picker = BodyPicker(scene.actors)
        return self._picker

    def _publish(self, event_type: EventType, data: dict[str, Any]) -> None:
        """Publish an event if a bus is attached.

        Args:
            event_type: Event to publish
            data: Event payload
        """
        if self.event_bus is None:
            return
        self.event_bus.publish_event(event_type, data=data)


if __name__ == "__main__":
    """Smoke test for DragPoseController."""
    import sys

    import opensim

    from osim_render.api.managers.event_bus import EventBus
    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.rendering.scene import SceneManager

    model_path = (
        sys.argv[1] if len(sys.argv) > 1 else "resources/Models/Arm26/arm26.osim"
    )
    print(f"DragPoseController smoke test on {model_path}")

    opensim.Model.setDebugLevel(-1)

    event_bus = EventBus()
    received: list[str] = []
    event_bus.subscribe(
        EventType.POSE_CHANGED, lambda event: received.append("changed")
    )

    model_manager = ModelManager(event_bus)
    model_manager.load_model(model_path)
    print("[OK] Model loaded with drag rig installed")

    scene_manager = SceneManager(model_manager, model_path)

    render_window = vtk.vtkRenderWindow()
    render_window.SetOffScreenRendering(1)
    render_window.SetSize(600, 600)
    renderer = vtk.vtkRenderer()
    render_window.AddRenderer(renderer)

    scene = scene_manager.create_scene(renderer=renderer)
    renderer.ResetCamera()
    render_window.Render()
    print(f"[OK] Scene created with {len(scene.actors)} body actors")

    posed_model = model_manager.get_opensim_model()
    assert posed_model is not None, "model manager has no model"

    rig = DragMarkerRig(posed_model)
    controller = DragPoseController(scene_manager, rig, event_bus)

    # The first body is typically welded to ground, so hunt for a body that
    # actually carries degrees of freedom.
    movable_body = [b.getName() for b in posed_model.getBodySet()][-1]
    probes = [(x, y) for x in range(60, 560, 12) for y in range(60, 560, 12)]

    grabbed = None
    for probe in probes:
        if not controller.begin_drag(renderer, probe[0], probe[1]):
            continue
        session = controller.session
        assert session is not None
        if session.body_name == movable_body:
            grabbed = probe
            break
        controller.end_drag()

    assert grabbed is not None, f"never picked movable body {movable_body}"
    print(f"[OK] Grabbed {movable_body} at pixel {grabbed}")
    assert controller.is_dragging

    coordinates = posed_model.getCoordinateSet()
    before = {c.getName(): c.getValue(scene_manager.state) for c in coordinates}

    for offset in range(1, 40):
        controller.update_drag(renderer, grabbed[0] + offset * 2, grabbed[1] + offset)

    after = {c.getName(): c.getValue(scene_manager.state) for c in coordinates}
    changed = {k: round(after[k] - before[k], 4) for k in before if abs(after[k] - before[k]) > 1e-6}
    print(f"[OK] Dragged 39 steps, coordinates changed: {changed}")
    assert changed, "drag did not move any coordinate"
    assert received, "no POSE_CHANGED events published"
    print(f"[OK] Published {len(received)} POSE_CHANGED events")

    controller.end_drag()
    assert not controller.is_dragging
    print("[OK] Drag ended cleanly")

    missed = controller.begin_drag(renderer, 2, 2)
    print(f"[OK] Click on empty space returned {missed}")
    assert missed is False

    print("\n[OK] Smoke test passed!")
