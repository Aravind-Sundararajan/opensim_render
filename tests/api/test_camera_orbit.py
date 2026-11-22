"""Tests for camera orbit interpolation.

A camera tween should sweep around the point it is looking at. Two ways this
silently went wrong: interpolating opposite directions collapsed the camera
onto the focal point, and the arc was taken about the world origin so framing
drifted for any model not sitting there.
"""

import math

import pytest

from osim_render.api.animation.camera_tween import CameraTween
from osim_render.api.animation.interpolation import slerp
from osim_render.api.animation.tween import TweenConfig
from osim_render.api.animation.value_types import CameraState

_SAMPLES = tuple(index / 20 for index in range(21))


def _radius(state: CameraState) -> float:
    """Distance from the camera to the point it is looking at."""
    return math.sqrt(
        sum((p - f) ** 2 for p, f in zip(state.position, state.focal_point, strict=False))
    )


def _magnitude(vector) -> float:
    """Length of a vector."""
    return math.sqrt(sum(component * component for component in vector))


class TestSlerpDegenerateCases:
    """Opposite and identical directions both need special handling."""

    def test_opposite_directions_stay_on_the_sphere(self) -> None:
        for t in _SAMPLES:
            result = slerp((0.0, 0.0, 1.0), (0.0, 0.0, -1.0), t)

            assert _magnitude(result) == pytest.approx(1.0, abs=1e-9)

    def test_opposite_directions_do_not_pass_through_the_origin(self) -> None:
        """Lerping opposite vectors crosses zero; the camera must not."""
        midpoint = slerp((0.0, 0.0, 1.0), (0.0, 0.0, -1.0), 0.5)

        assert _magnitude(midpoint) == pytest.approx(1.0, abs=1e-9)

    def test_opposite_directions_reach_their_endpoints(self) -> None:
        start, end = (0.0, 0.0, 1.0), (0.0, 0.0, -1.0)

        assert slerp(start, end, 0.0) == pytest.approx(start, abs=1e-9)
        assert slerp(start, end, 1.0) == pytest.approx(end, abs=1e-9)

    def test_identical_directions_are_stable(self) -> None:
        start = (0.0, 1.0, 0.0)

        for t in _SAMPLES:
            assert slerp(start, start, t) == pytest.approx(start, abs=1e-9)

    def test_right_angle_arc_keeps_unit_length(self) -> None:
        for t in _SAMPLES:
            result = slerp((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), t)

            assert _magnitude(result) == pytest.approx(1.0, abs=1e-9)


class TestOrbitKeepsFraming:
    """The camera holds its distance to the model throughout a move."""

    @pytest.mark.parametrize(
        "center",
        [(0.0, 0.0, 0.0), (0.0, 0.9, 0.0), (5.0, 0.9, 0.0), (20.0, 1.0, -3.0)],
    )
    def test_distance_is_held_wherever_the_model_sits(self, center) -> None:
        """Orbiting about the world origin made this drift by tens of percent."""
        start = CameraState.front_view(center=center, distance=3.0)
        end = CameraState.side_view(center=center, distance=3.0)
        tween = CameraTween(start, end, TweenConfig(duration=1.0))

        for t in _SAMPLES:
            assert _radius(tween.compute_value(t)) == pytest.approx(3.0, abs=1e-9)

    def test_half_turn_never_reaches_the_model(self) -> None:
        """front -> back is the case that used to fly through the focal point."""
        center = (0.0, 0.9, 0.0)
        start = CameraState.front_view(center=center, distance=4.0)
        end = CameraState(
            position=(center[0], center[1], center[2] - 4.0),
            focal_point=center,
            view_up=(0.0, 1.0, 0.0),
            zoom=1.0,
        )
        tween = CameraTween(start, end, TweenConfig(duration=1.0))

        for t in _SAMPLES:
            assert _radius(tween.compute_value(t)) == pytest.approx(4.0, abs=1e-9)

    def test_differing_start_and_end_distance_blends(self) -> None:
        center = (1.0, 2.0, 3.0)
        start = CameraState.front_view(center=center, distance=2.0)
        end = CameraState.side_view(center=center, distance=6.0)
        tween = CameraTween(start, end, TweenConfig(duration=1.0))

        radii = [_radius(tween.compute_value(t)) for t in _SAMPLES]

        assert radii[0] == pytest.approx(2.0, abs=1e-9)
        assert radii[-1] == pytest.approx(6.0, abs=1e-9)
        assert radii == sorted(radii), "distance should change monotonically"

    def test_focal_point_moves_with_the_model(self) -> None:
        start = CameraState.front_view(center=(0.0, 0.0, 0.0), distance=3.0)
        end = CameraState.front_view(center=(4.0, 0.0, 0.0), distance=3.0)
        tween = CameraTween(start, end, TweenConfig(duration=1.0))

        midpoint = tween.compute_value(0.5)

        assert midpoint.focal_point[0] == pytest.approx(2.0, abs=1e-9)
        assert _radius(midpoint) == pytest.approx(3.0, abs=1e-9)


class TestEndpointsAndContinuity:
    """A tween starts where it says and ends where it says."""

    def test_endpoints_are_exact(self) -> None:
        center = (1.0, 2.0, 3.0)
        start = CameraState.front_view(center=center, distance=4.0)
        end = CameraState.side_view(center=center, distance=4.0)
        tween = CameraTween(start, end, TweenConfig(duration=1.0))

        assert tween.compute_value(0.0).position == pytest.approx(start.position)
        assert tween.compute_value(1.0).position == pytest.approx(end.position)

    def test_motion_is_continuous(self) -> None:
        """No frame-to-frame jump should dwarf its neighbours."""
        center = (0.0, 0.9, 0.0)
        start = CameraState.front_view(center=center, distance=4.0)
        end = CameraState(
            position=(center[0], center[1], center[2] - 4.0),
            focal_point=center,
            view_up=(0.0, 1.0, 0.0),
            zoom=1.0,
        )
        tween = CameraTween(start, end, TweenConfig(duration=1.0))

        positions = [tween.compute_value(t).position for t in _SAMPLES]
        steps = [
            math.sqrt(sum((a - b) ** 2 for a, b in zip(positions[i + 1], positions[i], strict=False)))
            for i in range(len(positions) - 1)
        ]

        assert max(steps) < 3 * (sum(steps) / len(steps))

    def test_view_up_stays_unit_length(self) -> None:
        start = CameraState.front_view(center=(0.0, 0.0, 0.0), distance=4.0)
        end = CameraState.top_view(center=(0.0, 0.0, 0.0), distance=4.0)
        tween = CameraTween(start, end, TweenConfig(duration=1.0))

        for t in _SAMPLES:
            assert _magnitude(tween.compute_value(t).view_up) == pytest.approx(
                1.0, abs=1e-9
            )
