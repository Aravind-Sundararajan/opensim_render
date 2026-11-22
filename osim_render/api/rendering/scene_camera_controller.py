"""Camera state and follow-body control for OpenSim model visualization."""

from __future__ import annotations

import math

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from osim_render.api.animation.value_types import CameraState

from osim_render.api.rendering.render_scene import RenderScene
from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)

# VTK's default perspective view angle; zoom scales it.
BASE_VIEW_ANGLE = 30.0


class SceneCameraController:
    """Own camera-follow state and apply camera transforms to a RenderScene."""

    def __init__(self) -> None:
        # Camera follow-body state
        self._camera_follow_body: Optional[str] = None
        self._camera_follow_initial_body_pos: Optional[
            tuple[float, float, float]
        ] = None
        # Camera pose the follow offset is measured from.
        self._camera_follow_base_camera: Optional[
            tuple[tuple[float, ...], tuple[float, ...]]
        ] = None

    @property
    def is_following(self) -> bool:
        """Whether a follow-body is currently configured."""
        return bool(self._camera_follow_body)

    def get_camera_state(self, scene: RenderScene | None) -> "CameraState":
        """Return the current VTK camera state as a CameraState.

        Returns:
            CameraState reflecting the current camera position, focal point,
            view-up vector, zoom, and projection mode.
        """
        from osim_render.api.animation.value_types import CameraState

        if not scene or not scene.renderer:
            return CameraState.front_view()

        cam = scene.renderer.GetActiveCamera()
        base_angle = BASE_VIEW_ANGLE
        view_angle = cam.GetViewAngle()
        zoom = base_angle / view_angle if view_angle > 0 else 1.0

        px, py, pz = cam.GetPosition()
        fx, fy, fz = cam.GetFocalPoint()
        ux, uy, uz = cam.GetViewUp()

        return CameraState(
            position=(px, py, pz),
            focal_point=(fx, fy, fz),
            view_up=(ux, uy, uz),
            zoom=zoom,
            parallel_projection=bool(cam.GetParallelProjection()),
        )

    def set_camera_follow_body(self, body_name: str) -> None:
        """Configure the camera to follow a body during animation.

        The camera tracks the body's world position, maintaining whatever
        relative offset exists at the first frame. Camera tweens still apply
        on top — the follow offset is added after each tween is evaluated.

        Args:
            body_name: Name of the OpenSim body to follow (e.g. "pelvis")
        """
        self._camera_follow_body = body_name
        self._camera_follow_initial_body_pos = None
        self._camera_follow_base_camera = None

    def clear_camera_follow(self) -> None:
        """Stop following, leaving the camera wherever it currently is."""
        self._camera_follow_body = None
        self._camera_follow_initial_body_pos = None
        self._camera_follow_base_camera = None

    @property
    def followed_body(self) -> Optional[str]:
        """Name of the body being followed, or None."""
        return self._camera_follow_body

    def apply_camera_follow(
        self,
        scene: RenderScene | None,
        model: Any,
        state: Any,
        base_was_set: bool = False,
    ) -> None:
        """Offset the camera by how far the tracked body has moved since frame 0.

        The offset is measured from a fixed base pose rather than from wherever
        the camera happens to be. Adding the total displacement to the current
        pose every frame compounds it, and the camera flies away from the model
        instead of tracking it.

        Args:
            scene: Current RenderScene (or None)
            model: OpenSim model owning the tracked body
            state: State to read the body's position from
            base_was_set: True when a camera tween has just written the pose,
                making that the new base to offset from
        """
        if not scene or not scene.renderer:
            return
        if not model or not state:
            return

        try:
            body = model.getBodySet().get(self._camera_follow_body)
            p = body.getPositionInGround(state)
            current = (p.get(0), p.get(1), p.get(2))
        except RuntimeError as e:
            logger.debug(
                f"Camera-follow body '{self._camera_follow_body}' unavailable: {e}"
            )
            return

        cam = scene.renderer.GetActiveCamera()

        if self._camera_follow_initial_body_pos is None or base_was_set:
            self._camera_follow_base_camera = (cam.GetPosition(), cam.GetFocalPoint())

        if self._camera_follow_initial_body_pos is None:
            self._camera_follow_initial_body_pos = current
            return

        if self._camera_follow_base_camera is None:
            return

        base_position, base_focal = self._camera_follow_base_camera
        offset = tuple(
            current[axis] - self._camera_follow_initial_body_pos[axis]
            for axis in range(3)
        )

        cam.SetPosition(*(base_position[i] + offset[i] for i in range(3)))
        cam.SetFocalPoint(*(base_focal[i] + offset[i] for i in range(3)))

    def apply_camera_state(
        self, scene: RenderScene | None, camera_state: Any
    ) -> None:
        """Apply CameraState to VTK camera.

        Args:
            scene: Current RenderScene (or None)
            camera_state: CameraState with position, focal_point, view_up, zoom, etc.

        Raises:
            AttributeError: If camera_state lacks required attributes
            RuntimeError: If camera operations fail
        """
        if not scene or not scene.renderer:
            return

        camera = scene.renderer.GetActiveCamera()
        camera.SetPosition(*camera_state.position)
        camera.SetFocalPoint(*camera_state.focal_point)
        camera.SetViewUp(*camera_state.view_up)

        view_angle = BASE_VIEW_ANGLE / camera_state.zoom
        camera.SetViewAngle(view_angle)

        camera.SetParallelProjection(1 if camera_state.parallel_projection else 0)

        # In parallel projection VTK ignores the view angle entirely and frames
        # by parallel scale, so zoom would otherwise do nothing at all in the
        # orthographic scripts. Derive the scale that frames the same extent as
        # the perspective view would at this zoom.
        if camera_state.parallel_projection:
            camera.SetParallelScale(
                _parallel_scale_for(camera_state, view_angle)
            )

        # Recalculate near/far clipping planes for the current camera position
        # so nothing gets clipped as the camera moves during animation
        scene.renderer.ResetCameraClippingRange()


def _parallel_scale_for(camera_state: Any, view_angle: float) -> float:
    """Half-height of the orthographic view that matches a perspective one.

    Args:
        camera_state: CameraState being applied
        view_angle: The perspective view angle in degrees at this zoom

    Returns:
        Parallel scale to frame the same extent
    """
    distance = math.sqrt(
        sum(
            (p - f) ** 2
            for p, f in zip(
                camera_state.position, camera_state.focal_point, strict=False
            )
        )
    )
    return distance * math.tan(math.radians(view_angle) / 2.0)


if __name__ == "__main__":
    """Smoke test for camera state application."""
    import vtkmodules.all as vtk

    from osim_render.api.animation.value_types import CameraState

    print("scene_camera_controller smoke test")

    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.SetOffScreenRendering(1)
    render_window.AddRenderer(renderer)

    scene = RenderScene(
        model_name="smoke",
        renderer=renderer,
        render_window=render_window,
        interactor=vtk.vtkRenderWindowInteractor(),
        actors={},
    )
    controller = SceneCameraController()
    camera = renderer.GetActiveCamera()

    print("\nPerspective: zoom drives the view angle")
    for zoom in (1.0, 2.0):
        state = CameraState.front_view(center=(0.0, 0.0, 0.0), distance=4.0)
        controller.apply_camera_state(
            scene, CameraState(state.position, state.focal_point, state.view_up, zoom)
        )
        print(f"  zoom={zoom} -> view angle {camera.GetViewAngle():.3f}")
    assert camera.GetViewAngle() == BASE_VIEW_ANGLE / 2.0

    print("\nOrthographic: zoom drives the parallel scale")
    scales = []
    for zoom in (1.0, 2.0, 4.0):
        state = CameraState.front_view(center=(0.0, 0.0, 0.0), distance=4.0)
        controller.apply_camera_state(
            scene,
            CameraState(
                state.position,
                state.focal_point,
                state.view_up,
                zoom,
                parallel_projection=True,
            ),
        )
        scales.append(camera.GetParallelScale())
        print(f"  zoom={zoom} -> parallel scale {camera.GetParallelScale():.4f}")

    assert scales[0] > scales[1] > scales[2], "zooming in must narrow the view"
    print("[OK] Zoom now has an effect in orthographic mode")

    print("\n[OK] Smoke test passed!")
