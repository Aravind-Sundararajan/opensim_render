"""Camera animation mixin for the Scene fluent API."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, Self

from osim_render.api.animation.camera_tween import CameraTween
from osim_render.api.animation.easing import EasingFunction, ease_smooth_step
from osim_render.api.animation.tween import TweenConfig
from osim_render.api.animation.value_types import CameraState

if TYPE_CHECKING:
    from osim_render.api.animation.animation import AnimationBuilder
    from osim_render.api.rendering.scene import SceneManager


class CameraAnimationMixin:
    """Fluent methods and properties for camera framing and movement."""

    if TYPE_CHECKING:
        # Shared state owned by Scene (set in Scene.__init__); declared here so
        # the mixin type-checks in isolation under strict mypy.
        scene_manager: Optional[SceneManager]
        time_scale: float
        _current_time: float
        _last_camera_state: Optional[CameraState]
        _builder: AnimationBuilder

    @property
    def camera(self) -> "CameraState":
        """Current camera state from the scene manager."""
        if self.scene_manager is not None:
            return self.scene_manager.get_camera_state()
        return CameraState.front_view()

    @property
    def model_center(self) -> tuple[float, float, float]:
        """Focal point of the current camera — the model's visual center.

        Use this with CameraState presets to keep the camera aimed at the model:

            scene.animate_camera_to(
                target_state=CameraState.side_view(center=scene.model_center)
            )
        """
        return self.camera.focal_point

    @property
    def camera_distance(self) -> float:
        """Distance from camera to focal point after scene setup.

        Use this with CameraState presets so orbiting views stay at the
        same zoom level as the initial ResetCamera framing:

            scene.animate_camera_to(
                target_state=CameraState.side_view(
                    center=scene.model_center,
                    distance=scene.camera_distance,
                    zoom=scene.camera.zoom,
                )
            )
        """
        state = self.camera
        return math.sqrt(sum((p - f) ** 2 for p, f in zip(state.position, state.focal_point, strict=False)))

    def animate_camera_to(
        self,
        position: Optional[tuple[float, float, float]] = None,
        focal_point: Optional[tuple[float, float, float]] = None,
        view_up: Optional[tuple[float, float, float]] = None,
        zoom: Optional[float] = None,
        duration: float = 1.0,
        easing: Optional[EasingFunction] = None,
        target_state: Optional["CameraState"] = None,
        start_time: Optional[float] = None,
    ) -> Self:
        """
        Animate camera to new position/orientation/zoom.

        Specified parameters are updated, unspecified ones stay the same.

        Args:
            position: Target camera position (x, y, z) or None
            focal_point: Target focal point (x, y, z) or None
            view_up: Target view-up vector or None
            zoom: Target zoom level or None
            duration: Animation duration in seconds (default 1.0)
            easing: Easing function (default ease_smooth_step)
            start_time: Absolute start time. If provided (including 0.0), pins
                the camera tween to that time. If None, appends sequentially.

        Returns:
            Self for method chaining

        Examples:
            >>> scene.animate_camera_to(position=(10, 0, 0), duration=1.5)
        """
        if easing is None:
            easing = ease_smooth_step

        # Use end state of the previous camera tween so tweens chain smoothly.
        # Fall back to the actual scene camera for the very first tween.
        if self._last_camera_state is not None:
            current_state = self._last_camera_state
        elif self.scene_manager is not None:
            current_state = self.scene_manager.get_camera_state()
        else:
            current_state = CameraState.front_view()

        # Use target_state if provided, otherwise build from individual parameters
        if target_state is not None:
            new_state = target_state
        else:
            new_state = CameraState(
                position=position if position is not None else current_state.position,
                focal_point=focal_point
                if focal_point is not None
                else current_state.focal_point,
                view_up=view_up if view_up is not None else current_state.view_up,
                zoom=zoom if zoom is not None else current_state.zoom,
                parallel_projection=current_state.parallel_projection,
            )

        scaled_duration = duration / self.time_scale
        delay = (
            start_time / self.time_scale) if start_time is not None else self._current_time

        tween = CameraTween(
            current_state,
            new_state,
            TweenConfig(duration=scaled_duration, easing=easing, delay=delay),
        )
        self._builder.add_tween(tween)
        # Chain: next tween starts where this one ends
        self._last_camera_state = new_state

        if start_time is None:
            self._current_time += scaled_duration  # Move forward in time

        return self

    def track_body(self, body_name: str) -> Self:
        """Configure the camera to follow a body during animation.

        The camera tracks the body's world-space position, so the model
        stays in frame even when pelvis translation coordinates move it
        forward (e.g. during Moco walking with pelvis_tx).

        Camera tweens (animate_camera_to) still work — the follow offset
        is applied on top of whatever position the tween sets.

        Args:
            body_name: Name of the OpenSim body to follow, e.g. "pelvis"

        Examples:
            >>> scene.track_body("pelvis")  # camera follows pelvis throughout
        """
        if self.scene_manager is not None:
            self.scene_manager.set_camera_follow_body(body_name)
        return self


if __name__ == "__main__":
    print(f"[OK] {CameraAnimationMixin.__name__} imports cleanly")
