"""Interactor style that routes left-drags to either posing or the camera.

Left-dragging a body poses the model when pose mode is active (or while Ctrl
is held); every other drag falls through to the usual trackball camera, so
navigation is unchanged when nothing is grabbed.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


class PoseControllerProtocol(Protocol):
    """Contract the interactor style needs from a drag-to-pose controller."""

    @property
    def is_dragging(self) -> bool:
        """Whether a drag is currently in progress."""
        ...

    def begin_drag(
        self, renderer: vtk.vtkRenderer, display_x: int, display_y: int
    ) -> bool:
        """Start a drag at a viewport position."""
        ...

    def update_drag(
        self, renderer: vtk.vtkRenderer, display_x: int, display_y: int
    ) -> bool:
        """Continue a drag at a viewport position."""
        ...

    def end_drag(self) -> None:
        """Finish the active drag."""
        ...


class PoseInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    """Trackball camera style with drag-to-pose layered on top."""

    def __init__(self, renderer: vtk.vtkRenderer):
        """Initialize the style.

        Args:
            renderer: Renderer whose bodies can be posed
        """
        super().__init__()
        self.renderer = renderer
        self.controller: Optional[PoseControllerProtocol] = None
        self.pose_mode_enabled = False

        self.AddObserver(vtk.vtkCommand.LeftButtonPressEvent, self._on_left_button_press)
        self.AddObserver(vtk.vtkCommand.MouseMoveEvent, self._on_mouse_move)
        self.AddObserver(
            vtk.vtkCommand.LeftButtonReleaseEvent, self._on_left_button_release
        )

    def set_controller(self, controller: Optional[PoseControllerProtocol]) -> None:
        """Attach the drag-to-pose controller.

        Args:
            controller: DragPoseController, or None to disable posing
        """
        self.controller = controller

    def set_pose_mode_enabled(self, enabled: bool) -> None:
        """Turn pose mode on or off.

        Args:
            enabled: True to pose on plain left-drag
        """
        self.pose_mode_enabled = enabled
        logger.info(f"Pose mode {'enabled' if enabled else 'disabled'}")

    def _on_left_button_press(self, obj: Any, event: str) -> None:
        """Begin a pose drag, or fall back to camera rotation.

        Args:
            obj: Emitting VTK object
            event: VTK event name
        """
        controller = self.controller
        if controller is None or not self._posing_requested():
            self.OnLeftButtonDown()
            return

        position = self.GetInteractor().GetEventPosition()
        if not controller.begin_drag(self.renderer, position[0], position[1]):
            self.OnLeftButtonDown()

    def _on_mouse_move(self, obj: Any, event: str) -> None:
        """Update an active pose drag, or let the camera handle the move.

        Args:
            obj: Emitting VTK object
            event: VTK event name
        """
        controller = self.controller
        if controller is None or not controller.is_dragging:
            self.OnMouseMove()
            return

        position = self.GetInteractor().GetEventPosition()
        controller.update_drag(self.renderer, position[0], position[1])

    def _on_left_button_release(self, obj: Any, event: str) -> None:
        """End an active pose drag, or release the camera.

        Args:
            obj: Emitting VTK object
            event: VTK event name
        """
        controller = self.controller
        if controller is None or not controller.is_dragging:
            self.OnLeftButtonUp()
            return

        controller.end_drag()

    def _posing_requested(self) -> bool:
        """Whether this click should attempt to pose rather than orbit.

        Returns:
            True if a pose drag should be attempted
        """
        if self.controller is None:
            return False
        return self.pose_mode_enabled or bool(self.GetInteractor().GetControlKey())


if __name__ == "__main__":
    """Smoke test for PoseInteractorStyle."""

    class RecordingController:
        """Real stand-in controller that records drag calls."""

        def __init__(self) -> None:
            self.calls: list[str] = []
            self.is_dragging = False

        def begin_drag(self, renderer: Any, x: int, y: int) -> bool:
            self.calls.append(f"begin({x},{y})")
            self.is_dragging = True
            return True

        def update_drag(self, renderer: Any, x: int, y: int) -> bool:
            self.calls.append(f"update({x},{y})")
            return True

        def end_drag(self) -> None:
            self.calls.append("end")
            self.is_dragging = False

    print("PoseInteractorStyle smoke test")

    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.SetOffScreenRendering(1)
    render_window.SetSize(300, 300)
    render_window.AddRenderer(renderer)

    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)

    style = PoseInteractorStyle(renderer)
    interactor.SetInteractorStyle(style)
    render_window.Render()
    print("[OK] Style attached to interactor")

    assert not style._posing_requested(), "no controller means no posing"
    print("[OK] Without a controller, posing is off")

    controller = RecordingController()
    style.set_controller(controller)
    style.set_pose_mode_enabled(True)

    interactor.SetEventPosition(150, 150)
    interactor.LeftButtonPressEvent()
    interactor.SetEventPosition(170, 160)
    interactor.MouseMoveEvent()
    interactor.SetEventPosition(190, 170)
    interactor.MouseMoveEvent()
    interactor.LeftButtonReleaseEvent()

    print(f"[OK] Recorded calls: {controller.calls}")
    assert controller.calls[0].startswith("begin"), controller.calls
    assert "update(170,160)" in controller.calls, controller.calls
    assert controller.calls[-1] == "end", controller.calls
    assert not controller.is_dragging

    style.set_pose_mode_enabled(False)
    controller.calls.clear()
    interactor.SetEventPosition(150, 150)
    interactor.LeftButtonPressEvent()
    interactor.SetEventPosition(160, 160)
    interactor.MouseMoveEvent()
    interactor.LeftButtonReleaseEvent()
    print(f"[OK] Pose mode off, calls: {controller.calls}")
    assert not controller.calls, "camera drag must not reach the controller"

    print("\n[OK] Smoke test passed!")
