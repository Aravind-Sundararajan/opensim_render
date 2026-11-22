"""
Tweens for animating camera movements and properties.

Allows smooth animation of camera position, focus, zoom, and projection
using various interpolation methods (linear for focal point, slerp for position arc).
"""

import math
from dataclasses import dataclass
from typing import Sequence, cast

from osim_render.api.animation.interpolation import lerp, lerp_vector, slerp
from osim_render.api.animation.tween import TweenConfig, compute_eased_progress
from osim_render.api.animation.value_types import CameraState

# Below this the camera is effectively sitting on its focal point and has no
# orbit direction to interpolate.
MIN_ORBIT_RADIUS = 1e-9


def _subtract(a: Sequence[float], b: Sequence[float]) -> tuple[float, ...]:
    """Subtract two vectors component-wise.

    Args:
        a: Left operand
        b: Right operand

    Returns:
        The difference
    """
    return tuple(x - y for x, y in zip(a, b, strict=False))


def _magnitude(vector: Sequence[float]) -> float:
    """Length of a vector.

    Args:
        vector: The vector

    Returns:
        Its Euclidean length
    """
    return math.sqrt(sum(component * component for component in vector))


def _normalized(vector: Sequence[float]) -> tuple[float, ...]:
    """Scale a vector to unit length, leaving a zero vector untouched.

    Args:
        vector: The vector

    Returns:
        The unit vector
    """
    length = _magnitude(vector)
    if length < MIN_ORBIT_RADIUS:
        return tuple(vector)
    return tuple(component / length for component in vector)


@dataclass(frozen=True)
class CameraTween:
    """
    Tween for animating camera movement and properties.

    Interpolates camera position, focal point, view_up, zoom, and projection mode.
    Uses slerp for position (arc motion on sphere) and linear interpolation for
    other properties.

    Attributes:
        start_state: Starting CameraState
        end_state: Ending CameraState
        config: TweenConfig with duration, easing, and delay
        use_slerp_for_position: If True, uses slerp for smooth arc motion
                               If False, uses linear interpolation

    Examples:
        >>> start = CameraState.front_view(distance=10)
        >>> end = CameraState.side_view(distance=10)
        >>> tween = CameraTween(start, end, TweenConfig(duration=2.0))
        >>> # Returns intermediate CameraState at t=1.0
        >>> state = tween.compute_value(1.0)
    """

    start_state: CameraState
    end_state: CameraState
    config: TweenConfig
    use_slerp_for_position: bool = True

    @property
    def duration(self) -> float:
        """Total duration of the tween in seconds."""
        return self.config.duration + self.config.delay

    def compute_value(self, elapsed_time: float) -> CameraState:
        """
        Compute the camera state at the given elapsed time.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            CameraState with interpolated position, focal point, zoom, etc.
        """
        progress = compute_eased_progress(self.config, elapsed_time)

        # Linear interpolation for focal point
        focal_point = cast(
            tuple[float, float, float],
            tuple(
                lerp(s, e, progress)
                for s, e in zip(
                    self.start_state.focal_point, self.end_state.focal_point, strict=False
                )
            ),
        )

        if self.use_slerp_for_position:
            position = self._orbit_position(progress, focal_point)
        else:
            # Linear interpolation for position
            position = cast(
                tuple[float, float, float],
                tuple(
                    lerp(s, e, progress)
                    for s, e in zip(self.start_state.position, self.end_state.position, strict=False)
                ),
            )

        view_up = self._interpolated_view_up(progress)

        # Linear interpolation for zoom
        zoom = lerp(self.start_state.zoom, self.end_state.zoom, progress)

        # Interpolate projection mode (binary: switch at midpoint)
        parallel_projection = (
            self.end_state.parallel_projection
            if progress >= 0.5
            else self.start_state.parallel_projection
        )

        return CameraState(
            position=position,
            focal_point=focal_point,
            view_up=view_up,
            zoom=zoom,
            parallel_projection=parallel_projection,
        )

    def _orbit_position(
        self, progress: float, focal_point: tuple[float, float, float]
    ) -> tuple[float, float, float]:
        """Swing the camera around the focal point along a spherical arc.

        The arc is taken about the point the camera is looking at, not the
        world origin. Orbiting about the origin makes the camera dive toward
        or away from a model that does not happen to sit there — the framing
        drifts by tens of percent for a model a few metres out.

        Args:
            progress: Eased progress in [0, 1]
            focal_point: The interpolated focal point at this progress

        Returns:
            Camera position in world coordinates
        """
        start_offset = _subtract(self.start_state.position, self.start_state.focal_point)
        end_offset = _subtract(self.end_state.position, self.end_state.focal_point)

        start_radius = _magnitude(start_offset)
        end_radius = _magnitude(end_offset)
        radius = lerp(start_radius, end_radius, progress)

        if start_radius < MIN_ORBIT_RADIUS or end_radius < MIN_ORBIT_RADIUS:
            # Degenerate: the camera sits on its own focal point, so there is
            # no direction to orbit. Fall back to a straight line.
            offset = lerp_vector(start_offset, end_offset, progress)
        else:
            direction = slerp(
                tuple(c / start_radius for c in start_offset),
                tuple(c / end_radius for c in end_offset),
                progress,
            )
            offset = tuple(component * radius for component in direction)

        return cast(
            tuple[float, float, float],
            tuple(focal_point[i] + offset[i] for i in range(3)),
        )

    def _interpolated_view_up(self, progress: float) -> tuple[float, float, float]:
        """Interpolate the view-up vector, keeping it unit length.

        Args:
            progress: Eased progress in [0, 1]

        Returns:
            The interpolated up direction
        """
        blended = slerp(
            _normalized(self.start_state.view_up),
            _normalized(self.end_state.view_up),
            progress,
        )
        return cast(tuple[float, float, float], blended)

    def is_complete(self, elapsed_time: float) -> bool:
        """
        Check if the animation is complete.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            True if elapsed_time >= duration + delay
        """
        return elapsed_time >= self.duration


if __name__ == "__main__":
    # Smoke tests
    print("Testing camera_tween module...")

    # Test CameraTween with front to side view
    start = CameraState.front_view(distance=10)
    end = CameraState.side_view(distance=10)
    tween = CameraTween(
        start, end, TweenConfig(duration=2.0), use_slerp_for_position=True
    )

    # Test at start
    state = tween.compute_value(0.0)
    assert state.position == start.position, "At t=0 should return start position"
    print("[PASS] CameraTween at t=0 returns start state")

    # Test at end
    state = tween.compute_value(2.0)
    assert state.position == end.position, "At t=2 should return end position"
    print("[PASS] CameraTween at t=2 returns end state")

    # Test at midpoint
    state = tween.compute_value(1.0)
    assert isinstance(state, CameraState)
    assert state.zoom == 1.0  # Zoom shouldn't change
    print("[PASS] CameraTween at t=1 returns valid intermediate state")

    # Test is_complete
    assert not tween.is_complete(1.0)
    assert tween.is_complete(2.0)
    assert tween.is_complete(3.0)
    print("[PASS] CameraTween.is_complete works")

    # Test without slerp
    tween_linear = CameraTween(
        start, end, TweenConfig(duration=2.0), use_slerp_for_position=False
    )
    state = tween_linear.compute_value(1.0)
    assert isinstance(state, CameraState)
    print("[PASS] CameraTween without slerp works")

    print("\n[PASS] All camera_tween tests passed!")
