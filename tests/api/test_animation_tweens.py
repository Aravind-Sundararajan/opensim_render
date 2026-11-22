"""Unit tests for animation tweens and easing functions."""

import pytest

from osim_render.api.animation.tween import TweenConfig, compute_eased_progress
from osim_render.api.animation.coordinate_tween import (
    CoordinateTween,
    MultiCoordinateTween,
)
from osim_render.api.animation.camera_tween import CameraTween
from osim_render.api.animation.property_tween import ColorTween, ActorPropertyTween
from osim_render.api.animation.group_tween import SequentialTween, ParallelTween
from osim_render.api.animation.value_types import ColorValue, CameraState
from osim_render.api.animation import easing, interpolation


class TestTweenConfig:
    """Test TweenConfig."""

    def test_default_easing(self) -> None:
        """Test default easing is linear."""
        config = TweenConfig(duration=1.0)
        assert config.duration == 1.0
        assert config.easing is not None

    def test_custom_easing(self) -> None:
        """Test custom easing function."""
        config = TweenConfig(duration=1.0, easing=easing.ease_in_quad)
        assert config.easing == easing.ease_in_quad

    def test_delay(self) -> None:
        """Test delay configuration."""
        config = TweenConfig(duration=1.0, delay=0.5)
        assert config.delay == 0.5

    def test_invalid_duration(self) -> None:
        """Test invalid duration raises ValueError."""
        with pytest.raises(ValueError):
            TweenConfig(duration=0.0)


class TestCoordinateTween:
    """Test CoordinateTween."""

    def test_at_start(self) -> None:
        """Test tween at t=0."""
        tween = CoordinateTween(
            coordinate_name="hip_flexion",
            start_value=0.0,
            end_value=90.0,
            config=TweenConfig(duration=1.0),
        )
        value = tween.compute_value(0.0)
        assert value["hip_flexion"] == pytest.approx(0.0)

    def test_at_end(self) -> None:
        """Test tween at t=duration."""
        tween = CoordinateTween(
            coordinate_name="hip_flexion",
            start_value=0.0,
            end_value=90.0,
            config=TweenConfig(duration=1.0),
        )
        value = tween.compute_value(1.0)
        assert value["hip_flexion"] == pytest.approx(90.0)

    def test_at_midpoint(self) -> None:
        """Test tween at t=duration/2."""
        tween = CoordinateTween(
            coordinate_name="hip_flexion",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        value = tween.compute_value(0.5)
        assert value["hip_flexion"] == pytest.approx(50.0)

    def test_is_complete_before_duration(self) -> None:
        """Test is_complete is False before duration."""
        tween = CoordinateTween(
            coordinate_name="hip_flexion",
            start_value=0.0,
            end_value=90.0,
            config=TweenConfig(duration=1.0),
        )
        assert tween.is_complete(0.5) is False

    def test_is_complete_at_duration(self) -> None:
        """Test is_complete is True at duration."""
        tween = CoordinateTween(
            coordinate_name="hip_flexion",
            start_value=0.0,
            end_value=90.0,
            config=TweenConfig(duration=1.0),
        )
        assert tween.is_complete(1.0) is True

    def test_is_complete_after_duration(self) -> None:
        """Test is_complete is True after duration."""
        tween = CoordinateTween(
            coordinate_name="hip_flexion",
            start_value=0.0,
            end_value=90.0,
            config=TweenConfig(duration=1.0),
        )
        assert tween.is_complete(1.5) is True

    def test_duration_property(self) -> None:
        """Test duration property."""
        tween = CoordinateTween(
            coordinate_name="hip_flexion",
            start_value=0.0,
            end_value=90.0,
            config=TweenConfig(duration=2.5),
        )
        assert tween.duration == 2.5


class TestMultiCoordinateTween:
    """Test MultiCoordinateTween."""

    def test_multiple_coordinates(self) -> None:
        """Test aggregating multiple coordinate tweens."""
        tween1 = CoordinateTween(
            coordinate_name="hip_flexion",
            start_value=0.0,
            end_value=90.0,
            config=TweenConfig(duration=1.0),
        )
        tween2 = CoordinateTween(
            coordinate_name="knee_angle",
            start_value=0.0,
            end_value=45.0,
            config=TweenConfig(duration=1.0),
        )
        multi = MultiCoordinateTween(coordinate_tweens=(tween1, tween2))

        state = multi.compute_value(0.5)
        assert state["hip_flexion"] == pytest.approx(45.0)
        assert state["knee_angle"] == pytest.approx(22.5)

    def test_duration_is_max(self) -> None:
        """Test duration is max of tweens."""
        tween1 = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        tween2 = CoordinateTween(
            coordinate_name="coord2",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=2.0),
        )
        multi = MultiCoordinateTween(coordinate_tweens=(tween1, tween2))
        assert multi.duration == pytest.approx(2.0)


class TestCameraTween:
    """Test CameraTween."""

    def test_at_start(self) -> None:
        """Test camera tween at t=0."""
        start = CameraState.front_view()
        end = CameraState.side_view()
        tween = CameraTween(start, end, TweenConfig(duration=1.0))

        state = tween.compute_value(0.0)
        assert state.position == start.position

    def test_at_end(self) -> None:
        """Test camera tween at t=duration."""
        start = CameraState.front_view()
        end = CameraState.side_view()
        tween = CameraTween(start, end, TweenConfig(duration=1.0))

        state = tween.compute_value(1.0)
        assert state.position == end.position

    def test_at_midpoint(self) -> None:
        """Test camera tween at t=duration/2."""
        start = CameraState.front_view()
        end = CameraState.side_view()
        tween = CameraTween(start, end, TweenConfig(duration=1.0))

        state = tween.compute_value(0.5)
        # At midpoint, should be interpolated
        assert state is not None
        assert isinstance(state, CameraState)


class TestColorTween:
    """Test ColorTween."""

    def test_at_start(self) -> None:
        """Test color tween at t=0."""
        start = ColorValue(r=1.0, g=0.0, b=0.0)
        end = ColorValue(r=0.0, g=0.0, b=1.0)
        tween = ColorTween("pelvis", start, end, TweenConfig(duration=1.0))

        color_dict = tween.compute_value(0.0)
        color = color_dict["pelvis"]["color"]
        assert color.r == pytest.approx(1.0)
        assert color.g == pytest.approx(0.0)
        assert color.b == pytest.approx(0.0)

    def test_at_end(self) -> None:
        """Test color tween at t=duration."""
        start = ColorValue(r=1.0, g=0.0, b=0.0)
        end = ColorValue(r=0.0, g=0.0, b=1.0)
        tween = ColorTween("pelvis", start, end, TweenConfig(duration=1.0))

        color_dict = tween.compute_value(1.0)
        color = color_dict["pelvis"]["color"]
        assert color.r == pytest.approx(0.0)
        assert color.g == pytest.approx(0.0)
        assert color.b == pytest.approx(1.0)

    def test_at_midpoint(self) -> None:
        """Test color tween at t=duration/2."""
        start = ColorValue(r=0.0, g=0.0, b=0.0)
        end = ColorValue(r=1.0, g=1.0, b=1.0)
        tween = ColorTween("pelvis", start, end, TweenConfig(duration=1.0))

        color_dict = tween.compute_value(0.5)
        color = color_dict["pelvis"]["color"]
        assert color.r == pytest.approx(0.5)
        assert color.g == pytest.approx(0.5)
        assert color.b == pytest.approx(0.5)


class TestActorPropertyTween:
    """Test ActorPropertyTween."""

    def test_opacity_tween(self) -> None:
        """Test opacity property tween."""
        tween = ActorPropertyTween(
            actor_name="actor1",
            property_name="opacity",
            start_value=1.0,
            end_value=0.0,
            config=TweenConfig(duration=1.0),
        )

        assert tween.actor_name == "actor1"
        assert tween.property_name == "opacity"
        assert tween.duration == 1.0

    def test_compute_value(self) -> None:
        """Test computing property value."""
        tween = ActorPropertyTween(
            actor_name="actor1",
            property_name="opacity",
            start_value=1.0,
            end_value=0.0,
            config=TweenConfig(duration=1.0),
        )

        value_dict = tween.compute_value(0.5)
        assert value_dict["actor1"]["opacity"] == pytest.approx(0.5)


class TestSequentialTween:
    """Test SequentialTween."""

    def test_duration_is_sum(self) -> None:
        """Test sequential duration is sum of child tweens."""
        tween1 = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        tween2 = CoordinateTween(
            coordinate_name="coord2",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=2.0),
        )
        sequential = SequentialTween(tweens=(tween1, tween2))

        assert sequential.duration == pytest.approx(3.0)

    def test_first_tween_plays_first(self) -> None:
        """Test first tween plays during first part."""
        tween1 = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        tween2 = CoordinateTween(
            coordinate_name="coord2",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        sequential = SequentialTween(tweens=(tween1, tween2))

        state = sequential.compute_value(0.5)
        # Should be from first tween
        assert "coord1" in state


class TestParallelTween:
    """Test ParallelTween."""

    def test_duration_is_max(self) -> None:
        """Test parallel duration is max of child tweens."""
        tween1 = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        tween2 = CoordinateTween(
            coordinate_name="coord2",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=2.0),
        )
        parallel = ParallelTween(tweens=(tween1, tween2))

        assert parallel.duration == pytest.approx(2.0)

    def test_merges_all_values(self) -> None:
        """Test parallel merges values from all tweens."""
        tween1 = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        tween2 = CoordinateTween(
            coordinate_name="coord2",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        parallel = ParallelTween(tweens=(tween1, tween2))

        state = parallel.compute_value(0.5)
        assert state["coord1"] == pytest.approx(50.0)
        assert state["coord2"] == pytest.approx(50.0)


class TestComputeEasedProgress:
    """Test compute_eased_progress function."""

    def test_linear_progress(self) -> None:
        """Test linear progress computation."""
        config = TweenConfig(duration=1.0, easing=easing.ease_linear)
        progress = compute_eased_progress(config, 0.5)
        assert progress == pytest.approx(0.5)

    def test_before_delay(self) -> None:
        """Test progress is 0 before delay."""
        config = TweenConfig(duration=1.0, delay=0.5)
        progress = compute_eased_progress(config, 0.2)
        assert progress == pytest.approx(0.0)

    def test_at_delay(self) -> None:
        """Test progress at delay boundary."""
        config = TweenConfig(duration=1.0, delay=0.5)
        progress = compute_eased_progress(config, 0.5)
        assert progress == pytest.approx(0.0)

    def test_after_delay(self) -> None:
        """Test progress after delay."""
        config = TweenConfig(duration=1.0, delay=0.5)
        # At elapsed_time=1.0: time_since_start = 1.0 - 0.5 = 0.5
        # raw_progress = min(1.0, 0.5 / 1.0) = 0.5
        progress = compute_eased_progress(config, 1.0)
        assert progress == pytest.approx(0.5)

    def test_at_end_after_delay(self) -> None:
        """Test progress at end of animation after delay."""
        config = TweenConfig(duration=1.0, delay=0.5)
        # Total duration = 1.0 + 0.5 = 1.5
        # At elapsed_time=1.5: time_since_start = 1.5 - 0.5 = 1.0
        # raw_progress = min(1.0, 1.0 / 1.0) = 1.0
        progress = compute_eased_progress(config, 1.5)
        assert progress == pytest.approx(1.0)


class TestEasingFunctions:
    """Test easing functions."""

    def test_ease_linear_endpoints(self) -> None:
        """Test linear easing at endpoints."""
        assert easing.ease_linear(0.0) == pytest.approx(0.0)
        assert easing.ease_linear(1.0) == pytest.approx(1.0)

    def test_ease_linear_midpoint(self) -> None:
        """Test linear easing at midpoint."""
        assert easing.ease_linear(0.5) == pytest.approx(0.5)

    def test_ease_in_quad_endpoints(self) -> None:
        """Test quadratic ease-in at endpoints."""
        assert easing.ease_in_quad(0.0) == pytest.approx(0.0)
        assert easing.ease_in_quad(1.0) == pytest.approx(1.0)

    def test_ease_out_quad_endpoints(self) -> None:
        """Test quadratic ease-out at endpoints."""
        assert easing.ease_out_quad(0.0) == pytest.approx(0.0)
        assert easing.ease_out_quad(1.0) == pytest.approx(1.0)

    def test_ease_in_out_quad_endpoints(self) -> None:
        """Test quadratic ease-in-out at endpoints."""
        assert easing.ease_in_out_quad(0.0) == pytest.approx(0.0)
        assert easing.ease_in_out_quad(1.0) == pytest.approx(1.0)


class TestInterpolationFunctions:
    """Test interpolation functions."""

    def test_lerp_at_start(self) -> None:
        """Test linear interpolation at t=0."""
        result = interpolation.lerp(0.0, 10.0, 0.0)
        assert result == pytest.approx(0.0)

    def test_lerp_at_end(self) -> None:
        """Test linear interpolation at t=1."""
        result = interpolation.lerp(0.0, 10.0, 1.0)
        assert result == pytest.approx(10.0)

    def test_lerp_at_midpoint(self) -> None:
        """Test linear interpolation at t=0.5."""
        result = interpolation.lerp(0.0, 10.0, 0.5)
        assert result == pytest.approx(5.0)

    def test_lerp_negative_range(self) -> None:
        """Test linear interpolation with negative range."""
        result = interpolation.lerp(-5.0, 5.0, 0.5)
        assert result == pytest.approx(0.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
