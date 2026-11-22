"""
Scene - Manim-style animation composition API.

Provides a fluent, chainable interface for building animations using
the scene.play() pattern familiar from manim.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.rendering.scene import SceneManager
    from osim_render.api.managers.event_bus import EventBus
    from osim_render.api.managers.property_control_manager import PropertyControlManager
    from osim_render.api.animation.value_types import CameraState

from osim_render.api.animation.animation import AnimationBuilder
from osim_render.api.animation.coordinate_tween import CoordinateTween
from osim_render.api.animation.group_tween import ParallelTween
from osim_render.api.animation.timeline import Timeline
from osim_render.api.animation.tween import TweenConfig
from osim_render.api.animation.scene.coordinate_animation import (
    CoordinateAnimationMixin,
)
from osim_render.api.animation.scene.camera_animation import CameraAnimationMixin
from osim_render.api.animation.scene.property_animation import (
    PropertyAnimationMixin,
)


class Scene(CoordinateAnimationMixin, CameraAnimationMixin, PropertyAnimationMixin):
    """
    Manim-style scene for composing animations.

    Provides a fluent API for building complex animations with parallel
    and sequential animations. Animates coordinates, cameras, and visual properties.

    Attributes:
        model_manager: Manager providing access to OpenSim model
        scene_manager: Manager for rendering and visualization
        event_bus: Event system for publishing animation events

    Examples:
        >>> scene = Scene(model_manager, scene_manager, event_bus)
        >>> scene.animate_coordinate("hip_flexion_r", 0, 45, duration=2.0)
        >>> scene.wait(0.5)
        >>> scene.animate_coordinate("knee_angle_r", 0, 90, duration=2.0)
        >>> timeline = scene.build_timeline()
    """

    def __init__(
        self,
        model_manager: ModelManager,
        scene_manager: Optional[SceneManager],
        event_bus: EventBus,
        property_manager: Optional[PropertyControlManager] = None,
        time_scale: float = 1.0,
    ) -> None:
        """
        Initialize a scene.

        Args:
            model_manager: Manager providing access to OpenSim model
            scene_manager: Manager for rendering and visualization, or None
            event_bus: Event system for publishing animation events
            property_manager: Optional PropertyControlManager for unified property control
            time_scale: Speed multiplier applied to all durations and start times (default 1.0, 2.0 = 2x faster, 0.5 = half speed)
        """
        self.model_manager = model_manager
        self.scene_manager = scene_manager
        self.event_bus = event_bus
        self.property_manager = property_manager
        self.time_scale = time_scale
        self._builder = AnimationBuilder("Scene")
        self._current_time = 0.0
        self._last_camera_state: Optional[CameraState] = None

    def play(self, *tweens: Any, duration: Optional[float] = None) -> "Scene":
        """
        Play tweens in parallel.

        All tweens start at the same time and play simultaneously.

        Args:
            *tweens: Variable number of tween objects to play in parallel
            duration: Optional override for duration (uses max of all tweens if not specified)

        Returns:
            Self for method chaining

        Examples:
            >>> scene.play(coord_tween, camera_tween, property_tween)
        """
        if not tweens:
            return self

        if len(tweens) == 1:
            self._builder.add_tween(tweens[0])
            tween_duration = tweens[0].duration
        else:
            parallel = ParallelTween(tweens=tweens)
            self._builder.add_tween(parallel)
            tween_duration = parallel.duration

        actual_duration = duration if duration is not None else tween_duration
        self._current_time += actual_duration

        return self

    def wait(self, duration: float) -> "Scene":
        """
        Wait for a specified duration without animating anything.

        Useful for pauses between animations.

        Args:
            duration: Duration to wait in seconds

        Returns:
            Self for method chaining

        Examples:
            >>> scene.animate_coordinate("hip", 0, 45, duration=1.0)
            >>> scene.wait(0.5)  # Pause for half a second
            >>> scene.animate_coordinate("knee", 0, 90, duration=1.0)
        """
        if duration > 0:
            duration = duration / self.time_scale
            noop_tween = CoordinateTween(
                "__wait__", 0, 0, TweenConfig(duration=duration)
            )
            self._builder.add_tween(noop_tween)
            self._current_time += duration

        return self

    def build_timeline(self) -> Timeline:
        """
        Build a Timeline from the composed animations.

        Returns:
            Timeline that can be played or exported

        Examples:
            >>> scene.animate_coordinate("hip", 0, 45, duration=2.0)
            >>> timeline = scene.build_timeline()
            >>> # Now you can play or export the timeline
        """
        animation = self._builder.build()
        return Timeline(animations=(animation,))


if __name__ == "__main__":
    # Smoke tests
    print("Testing scene module...")

    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.managers.event_bus import EventBus as _EventBus

    _model_manager = ModelManager(_EventBus())
    _event_bus = _EventBus()

    # Test Scene creation and basic methods (no scene_manager needed)
    scene = Scene(_model_manager, None, _event_bus)
    assert scene is not None
    print("[PASS] Scene creation works")

    # Test fluent API
    scene.animate_coordinate("hip", 0, 45, duration=1.0)
    assert scene._current_time == 1.0
    print("[PASS] Scene.animate_coordinate updates current_time")

    scene.wait(0.5)
    assert scene._current_time == 1.5
    print("[PASS] Scene.wait updates current_time")

    scene.animate_coordinate("knee", 0, 90, duration=1.0)
    assert scene._current_time == 2.5  # wait duration + knee duration
    print("[PASS] Scene method chaining works")

    # Test build_timeline
    timeline = scene.build_timeline()
    assert isinstance(timeline, Timeline)
    assert timeline.duration > 0
    print(
        f"[PASS] Scene.build_timeline creates timeline (duration: {timeline.duration}s)"
    )

    # Test that we can get state from built timeline
    state = timeline.get_state_at_time(0.0)
    assert state is not None
    print("[PASS] Timeline from scene can compute state")

    print("\n[PASS] All scene tests passed!")
