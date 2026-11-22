"""Unit tests for animation timeline and builder."""

import pytest

from osim_render.api.animation.timeline import Timeline
from osim_render.api.animation.animation import AnimationState
from osim_render.api.animation.animation import Animation, AnimationBuilder
from osim_render.api.animation.tween import TweenConfig
from osim_render.api.animation.coordinate_tween import CoordinateTween


class TestAnimationState:
    """Test AnimationState class."""

    def test_empty_state(self) -> None:
        """Test creating empty animation state."""
        state = AnimationState(
            time=0.0,
            coordinate_values={},
            camera_state=None,
            actor_properties={},
        )
        assert state.time == 0.0
        assert state.coordinate_values == {}
        assert state.camera_state is None
        assert state.actor_properties == {}

    def test_with_coordinates(self) -> None:
        """Test animation state with coordinates."""
        state = AnimationState(
            time=0.0,
            coordinate_values={"hip_flexion": 45.0, "knee_angle": 30.0},
            camera_state=None,
            actor_properties={},
        )
        assert state.coordinate_values["hip_flexion"] == 45.0
        assert state.coordinate_values["knee_angle"] == 30.0

    def test_merge_coordinates(self) -> None:
        """Test merging two states."""
        state1 = AnimationState(
            time=0.0,
            coordinate_values={"coord1": 10.0},
            camera_state=None,
            actor_properties={},
        )
        state2 = AnimationState(
            time=0.0,
            coordinate_values={"coord2": 20.0},
            camera_state=None,
            actor_properties={},
        )

        merged = state1.merge(state2)
        assert merged.coordinate_values["coord1"] == 10.0
        assert merged.coordinate_values["coord2"] == 20.0

    def test_merge_overwrites_coordinates(self) -> None:
        """Test merge overwrites conflicting coordinates."""
        state1 = AnimationState(
            time=0.0,
            coordinate_values={"coord1": 10.0},
            camera_state=None,
            actor_properties={},
        )
        state2 = AnimationState(
            time=0.0,
            coordinate_values={"coord1": 20.0},
            camera_state=None,
            actor_properties={},
        )

        merged = state1.merge(state2)
        assert merged.coordinate_values["coord1"] == 20.0

    def test_merge_preserves_original(self) -> None:
        """Test merge doesn't modify original state."""
        state1 = AnimationState(
            time=0.0,
            coordinate_values={"coord1": 10.0},
            camera_state=None,
            actor_properties={},
        )
        state2 = AnimationState(
            time=0.0,
            coordinate_values={"coord2": 20.0},
            camera_state=None,
            actor_properties={},
        )

        state1.merge(state2)
        assert state1.coordinate_values == {"coord1": 10.0}
        assert state2.coordinate_values == {"coord2": 20.0}


class TestTimeline:
    """Test Timeline class."""

    def test_requires_at_least_one_animation(self) -> None:
        """Test Timeline requires at least one animation."""
        with pytest.raises(ValueError):
            Timeline(animations=())

    def test_single_animation_duration(self) -> None:
        """Test timeline with single animation."""
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=2.0),
        )
        animation = Animation(name="anim1", tweens=(tween,), duration=2.0)
        timeline = Timeline(animations=(animation,))
        assert timeline.duration == pytest.approx(2.0)

    def test_multiple_animations_sum_duration(self) -> None:
        """Test timeline duration is sum of animations."""
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
        anim1 = Animation(name="anim1", tweens=(tween1,), duration=1.0)
        anim2 = Animation(name="anim2", tweens=(tween2,), duration=2.0)
        timeline = Timeline(animations=(anim1, anim2))
        assert timeline.duration == pytest.approx(3.0)

    def test_get_state_at_time(self) -> None:
        """Test getting state at specific time."""
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        animation = Animation(name="anim1", tweens=(tween,), duration=1.0)
        timeline = Timeline(animations=(animation,))

        state = timeline.get_state_at_time(0.5)
        assert state.coordinate_values["coord1"] == pytest.approx(50.0)

    def test_get_state_at_time_multiple_animations(self) -> None:
        """Test getting state from multiple animations."""
        tween1 = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        tween2 = CoordinateTween(
            coordinate_name="coord2",
            start_value=0.0,
            end_value=50.0,
            config=TweenConfig(duration=2.0),
        )
        anim1 = Animation(name="anim1", tweens=(tween1,), duration=1.0)
        anim2 = Animation(name="anim2", tweens=(tween2,), duration=2.0)
        timeline = Timeline(animations=(anim1, anim2))

        # During first animation
        state1 = timeline.get_state_at_time(0.5)
        assert state1.coordinate_values["coord1"] == pytest.approx(50.0)

        # During second animation (at t=1.5 total, t=0.5 into second anim)
        state2 = timeline.get_state_at_time(1.5)
        assert state2.coordinate_values["coord2"] == pytest.approx(12.5)

    def test_iterate_frames_one_second(self) -> None:
        """Test iterating frames for 1 second at 30 fps."""
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        animation = Animation(name="anim1", tweens=(tween,), duration=1.0)
        timeline = Timeline(animations=(animation,))

        frames = list(timeline.iterate_frames(fps=30))
        assert len(frames) == 31  # 0 to 1.0 inclusive

    def test_iterate_frames_half_second(self) -> None:
        """Test iterating frames for 0.5 seconds at 30 fps."""
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=0.5),
        )
        animation = Animation(name="anim1", tweens=(tween,), duration=0.5)
        timeline = Timeline(animations=(animation,))

        frames = list(timeline.iterate_frames(fps=30))
        assert len(frames) == 16  # 0 to 0.5 inclusive

    def test_iterate_frames_returns_states(self) -> None:
        """Test iterate_frames returns AnimationState objects."""
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        animation = Animation(name="anim1", tweens=(tween,), duration=1.0)
        timeline = Timeline(animations=(animation,))

        frames = list(timeline.iterate_frames(fps=1))
        assert len(frames) >= 1
        for frame in frames:
            assert isinstance(frame, AnimationState)

    def test_get_state_beyond_duration(self) -> None:
        """Test getting state beyond timeline duration."""
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        animation = Animation(name="anim1", tweens=(tween,), duration=1.0)
        timeline = Timeline(animations=(animation,))

        state = timeline.get_state_at_time(2.0)
        # Should return final state
        assert state.coordinate_values["coord1"] == pytest.approx(100.0)


class TestAnimation:
    """Test Animation class."""

    def test_animation_requires_tween(self) -> None:
        """Test Animation requires at least one tween."""
        with pytest.raises(ValueError):
            Animation(name="empty", tweens=(), duration=1.0)

    def test_animation_requires_positive_duration(self) -> None:
        """Test Animation requires positive duration."""
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        with pytest.raises(ValueError):
            Animation(name="bad", tweens=(tween,), duration=0.0)

    def test_compute_state_at_start(self) -> None:
        """Test computing state at start."""
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        animation = Animation(name="anim1", tweens=(tween,), duration=1.0)

        state = animation.compute_state(0.0)
        assert state.coordinate_values["coord1"] == pytest.approx(0.0)

    def test_compute_state_at_end(self) -> None:
        """Test computing state at end."""
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        animation = Animation(name="anim1", tweens=(tween,), duration=1.0)

        state = animation.compute_state(1.0)
        assert state.coordinate_values["coord1"] == pytest.approx(100.0)


class TestAnimationBuilder:
    """Test AnimationBuilder class."""

    def test_builder_creates_animation(self) -> None:
        """Test AnimationBuilder creates animation."""
        builder = AnimationBuilder("test_animation")
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        builder.add_tween(tween)
        animation = builder.build()

        assert animation is not None
        assert animation.name == "test_animation"
        assert animation.duration == pytest.approx(1.0)

    def test_builder_returns_self_for_chaining(self) -> None:
        """Test builder methods return self for chaining."""
        builder = AnimationBuilder("test")
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )

        result = builder.add_tween(tween)
        assert result is builder

    def test_add_multiple_tweens(self) -> None:
        """Test adding multiple tweens to builder."""
        builder = AnimationBuilder("test")
        tween1 = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        tween2 = CoordinateTween(
            coordinate_name="coord2",
            start_value=0.0,
            end_value=50.0,
            config=TweenConfig(duration=2.0),
        )

        builder.add_tween(tween1).add_tween(tween2)
        animation = builder.build()

        assert animation is not None
        # Duration should be max of tween durations
        assert animation.duration == pytest.approx(2.0)

    def test_builder_requires_tween(self) -> None:
        """Test builder requires at least one tween."""
        builder = AnimationBuilder("empty")
        with pytest.raises(ValueError):
            builder.build()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
