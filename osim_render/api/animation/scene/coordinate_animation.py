"""Coordinate animation mixin for the Scene fluent API."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, Self

from osim_render.api.animation.coordinate_tween import CoordinateTween
from osim_render.api.animation.easing import EasingFunction, ease_smooth_step
from osim_render.api.animation.group_tween import ParallelTween
from osim_render.api.animation.tween import TweenConfig

if TYPE_CHECKING:
    from osim_render.api.animation.animation import AnimationBuilder


class CoordinateAnimationMixin:
    """Fluent methods for animating OpenSim coordinates."""

    if TYPE_CHECKING:
        # Shared state owned by Scene (set in Scene.__init__); declared here so
        # the mixin type-checks in isolation under strict mypy.
        time_scale: float
        _current_time: float
        _builder: AnimationBuilder

    def animate_coordinate(
        self,
        coord_name: str,
        start: float,
        end: float,
        duration: float = 1.0,
        easing: Optional[EasingFunction] = None,
        delay: float = 0.0,
        start_time: Optional[float] = None,
        degrees: bool = True,
    ) -> Self:
        """
        Animate a single coordinate from start to end value.

        Args:
            coord_name: Name of the coordinate to animate
            start: Starting coordinate value
            end: Ending coordinate value
            duration: Animation duration in seconds (default 1.0)
            easing: Easing function (default ease_smooth_step)
            delay: Delay before animation starts (default 0.0)
            start_time: Absolute start time in seconds. If provided, pins the
                animation to that time (even 0.0) and does not advance the
                scene cursor. If None, appends sequentially after the current
                cursor position.
            degrees: If True (default), start/end are in degrees and will be
                converted to radians for OpenSim. Set to False for translational
                coordinates (meters) or when passing radians directly.

        Returns:
            Self for method chaining

        Examples:
            >>> scene.animate_coordinate("hip_flexion_r", 0, 45, duration=2.0)
            >>> scene.animate_coordinate("knee", 0, 90, duration=1.5, easing=ease_in_out_cubic)
            >>> scene.animate_coordinate("pelvis_tx", 0, 0.5, duration=2.0, degrees=False)
        """
        if easing is None:
            easing = ease_smooth_step

        if degrees:
            start = math.radians(start)
            end = math.radians(end)

        duration = duration / self.time_scale

        if start_time is not None:
            effective_delay = start_time / self.time_scale
        else:
            effective_delay = delay / self.time_scale + self._current_time

        tween = CoordinateTween(
            coord_name,
            start,
            end,
            TweenConfig(duration=duration, easing=easing,
                        delay=effective_delay),
        )
        self._builder.add_tween(tween)

        if start_time is None:
            self._current_time += duration  # Move forward in time

        return self

    def animate_coordinates(
        self,
        *coord_specs: tuple[str, float, float],
        duration: float = 1.0,
        easing: Optional[EasingFunction] = None,
        delay: float = 0.0,
        start_time: Optional[float] = None,
        degrees: bool = True,
    ) -> Self:
        """
        Animate multiple coordinates simultaneously.

        Each spec is a tuple of (coordinate_name, start_value, end_value).

        Args:
            *coord_specs: Variable number of (coord_name, start, end) tuples
            duration: Animation duration for all coordinates
            easing: Easing function for all coordinates
            delay: Delay for all coordinates
            start_time: Absolute start time. If provided (including 0.0), pins
                all coordinates to that time. If None, appends sequentially.
            degrees: If True (default), start/end values are in degrees and will
                be converted to radians for OpenSim. Set to False for
                translational coordinates (meters) or when passing radians directly.

        Returns:
            Self for method chaining

        Examples:
            >>> scene.animate_coordinates(
            ...     ("hip_flexion_r", 0, 45),
            ...     ("knee_angle_r", 0, 90),
            ...     duration=2.0
            ... )
        """
        if easing is None:
            easing = ease_smooth_step

        duration = duration / self.time_scale

        if start_time is not None:
            effective_delay = start_time / self.time_scale
        else:
            effective_delay = delay / self.time_scale + self._current_time

        if degrees:
            coord_specs = tuple(
                (name, math.radians(start), math.radians(end))
                for name, start, end in coord_specs
            )

        config = TweenConfig(
            duration=duration, easing=easing, delay=effective_delay)
        tweens = tuple(
            CoordinateTween(name, start, end, config)
            for name, start, end in coord_specs
        )

        if len(tweens) == 1:
            self._builder.add_tween(tweens[0])
        else:
            self._builder.add_tween(ParallelTween(tweens=tweens))

        if start_time is None:
            self._current_time += duration  # Move forward in time

        return self


if __name__ == "__main__":
    print(f"[OK] {CoordinateAnimationMixin.__name__} imports cleanly")
