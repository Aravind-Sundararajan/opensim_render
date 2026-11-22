"""
Animation classes representing complete animations with multiple tweens.

Provides Animation for managing a set of tweens over time,
AnimationState for snapshots of animation state, and AnimationBuilder for construction.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from osim_render.api.animation.value_types import CameraState


@dataclass(frozen=True)
class AnimationState:
    """
    Snapshot of animation state at a specific point in time.

    Represents the complete state of the animation at a given time,
    including all coordinate values, camera state, and visual properties.

    Attributes:
        time: Time in seconds since animation start
        coordinate_values: Dict mapping coordinate names to their values
        camera_state: Current CameraState or None if not animated
        actor_properties: Dict mapping actor names to property dicts
                         e.g. {"pelvis": {"color": ColorValue(...), "opacity": 0.5}}
    """

    time: float
    coordinate_values: dict[str, float]
    camera_state: Optional[CameraState] = None
    actor_properties: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate animation state."""
        if self.time < 0:
            raise ValueError(f"time must be non-negative, got {self.time}")

    def merge(self, other: "AnimationState") -> "AnimationState":
        """
        Merge another AnimationState into this one.

        Values from other take precedence. Useful for combining parallel animations.

        Args:
            other: Another AnimationState to merge

        Returns:
            New AnimationState with merged values
        """
        # Merge coordinate values
        merged_coords = {**self.coordinate_values, **other.coordinate_values}

        # Use other's camera state if available, otherwise use this one
        merged_camera = (
            other.camera_state if other.camera_state is not None else self.camera_state
        )

        # Merge actor properties
        merged_props = {**self.actor_properties}
        for actor, props in other.actor_properties.items():
            if actor in merged_props:
                merged_props[actor] = {**merged_props[actor], **props}
            else:
                merged_props[actor] = props

        return AnimationState(
            time=self.time,
            coordinate_values=merged_coords,
            camera_state=merged_camera,
            actor_properties=merged_props,
        )


@dataclass(frozen=True)
class Animation:
    """
    A complete animation with one or more tweens.

    Represents a single animation that can be played or exported.
    Owns tweens and computes combined state at any time.

    Attributes:
        name: Display name for the animation
        tweens: Tuple of tweens that make up this animation
        duration: Total duration in seconds (max of all tween durations)

    Examples:
        >>> from osim_render.api.animation import CoordinateTween, TweenConfig
        >>> tween = CoordinateTween("hip", 0, 45, TweenConfig(duration=2.0))
        >>> animation = Animation(name="hip_flex", tweens=(tween,), duration=2.0)
        >>> state = animation.compute_state(1.0)
    """

    name: str
    tweens: tuple[Any, ...]
    duration: float

    def __post_init__(self) -> None:
        """Validate animation."""
        if not self.tweens:
            raise ValueError("Animation requires at least one tween")
        if self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration}")

    def compute_state(self, time: float) -> AnimationState:
        """
        Compute the complete animation state at the given time.

        Evaluates all tweens and merges their results into a single AnimationState.

        Args:
            time: Time in seconds since animation start

        Returns:
            AnimationState with all coordinate, camera, and property values
        """
        # Clamp time to [0, duration]
        clamped_time = max(0.0, min(self.duration, time))

        # Initialize result
        result = AnimationState(
            time=clamped_time,
            coordinate_values={},
            camera_state=None,
            actor_properties={},
        )

        # Evaluate each tween and merge results
        for tween in self.tweens:
            tween_value = tween.compute_value(clamped_time)

            if isinstance(tween_value, CameraState):
                # Skip camera tweens that haven't started yet (still in delay).
                # Without this, a later tween stuck at its start state would
                # override an earlier tween that is actively animating.
                tween_delay = tween.config.delay
                if clamped_time < tween_delay:
                    continue

                # Camera tween: set camera state
                result = AnimationState(
                    time=clamped_time,
                    coordinate_values=result.coordinate_values,
                    camera_state=tween_value,
                    actor_properties=result.actor_properties,
                )
            elif isinstance(tween_value, dict):
                # Skip tweens still in their delay period — a future tween returning
                # its start_value would otherwise override the currently-active tween.
                tween_delay = tween.config.delay
                if clamped_time < tween_delay:
                    continue
                # Coordinate or property tween: parse the dict
                for key, value in tween_value.items():
                    if isinstance(value, dict):
                        # Property tween: {"actor_name": {"property": value}}
                        if key not in result.actor_properties:
                            object.__setattr__(
                                result,
                                "actor_properties",
                                {**result.actor_properties, key: {}},
                            )
                        actor_props = result.actor_properties[key]
                        actor_props.update(value)
                        merged_props = {**result.actor_properties, key: actor_props}
                        object.__setattr__(result, "actor_properties", merged_props)
                    else:
                        # Coordinate tween: {"coord_name": value}
                        result.coordinate_values[key] = value

        return result


@dataclass(frozen=True)
class ParallelAnimation:
    """Run multiple animations simultaneously, merging their states.

    All animations evaluate at the same time and their states are merged.
    Useful for combining motion data playback with camera or visual tweens.

    Attributes:
        animations: Tuple of animations to play in parallel
    """

    animations: tuple[Any, ...]

    def __post_init__(self) -> None:
        """Validate parallel animation."""
        if not self.animations:
            raise ValueError("ParallelAnimation requires at least one animation")

    @property
    def duration(self) -> float:
        """Total duration: longest of all contained animations."""
        return float(max(anim.duration for anim in self.animations))

    def compute_state(self, time: float) -> AnimationState:
        """Evaluate all animations at the same time and merge results.

        Args:
            time: Time in seconds since animation start

        Returns:
            Merged AnimationState from all animations
        """
        result = AnimationState(time=time, coordinate_values={})
        for anim in self.animations:
            clamped = max(0.0, min(anim.duration, time))
            state = anim.compute_state(clamped)
            result = result.merge(state)
        return result


class AnimationBuilder:
    """
    Builder pattern for constructing animations fluently.

    Allows incremental construction of animations by adding tweens one at a time.

    Examples:
        >>> builder = AnimationBuilder("my_animation")
        >>> builder.add_tween(tween1)
        >>> builder.add_tween(tween2)
        >>> animation = builder.build()
    """

    def __init__(self, name: str) -> None:
        """Initialize builder with animation name."""
        self.name = name
        self._tweens: list[Any] = []
        self._duration = 0.0

    def add_tween(self, tween: Any) -> "AnimationBuilder":
        """
        Add a tween to the animation.

        Args:
            tween: Tween to add

        Returns:
            Self for method chaining
        """
        self._tweens.append(tween)
        self._duration = max(self._duration, tween.duration)
        return self

    def build(self) -> Animation:
        """
        Build the final Animation.

        Returns:
            Animation with all added tweens

        Raises:
            ValueError: If no tweens were added
        """
        if not self._tweens:
            raise ValueError("Cannot build animation with no tweens")
        return Animation(
            name=self.name, tweens=tuple(self._tweens), duration=self._duration
        )


if __name__ == "__main__":
    # Smoke tests
    print("Testing animation module...")

    from osim_render.api.animation.coordinate_tween import CoordinateTween
    from osim_render.api.animation.tween import TweenConfig

    # Test AnimationState
    state = AnimationState(
        time=0.0,
        coordinate_values={"hip": 0.0},
        camera_state=None,
        actor_properties={},
    )
    assert state.time == 0.0
    print("[PASS] AnimationState creation works")

    # Test AnimationState merge
    state1 = AnimationState(
        time=0.5,
        coordinate_values={"hip": 22.5},
        camera_state=None,
        actor_properties={},
    )
    state2 = AnimationState(
        time=0.5,
        coordinate_values={"knee": 45.0},
        camera_state=None,
        actor_properties={},
    )
    merged = state1.merge(state2)
    assert merged.coordinate_values == {"hip": 22.5, "knee": 45.0}
    print("[PASS] AnimationState merge works")

    # Test Animation
    tween = CoordinateTween("hip", 0, 45, TweenConfig(duration=2.0))
    animation = Animation(name="test", tweens=(tween,), duration=2.0)
    assert animation.name == "test"
    assert animation.duration == 2.0
    print("[PASS] Animation creation works")

    # Test Animation.compute_state
    state = animation.compute_state(0.0)
    assert state.coordinate_values["hip"] == 0.0
    print("[PASS] Animation.compute_state at t=0 returns start state")

    state = animation.compute_state(1.0)
    assert state.coordinate_values["hip"] == 22.5
    print("[PASS] Animation.compute_state at t=1 returns mid state")

    state = animation.compute_state(2.0)
    assert state.coordinate_values["hip"] == 45.0
    print("[PASS] Animation.compute_state at t=2 returns end state")

    # Test AnimationBuilder
    builder = AnimationBuilder("built_animation")
    builder.add_tween(tween)
    animation = builder.build()
    assert animation.name == "built_animation"
    assert animation.duration == 2.0
    print("[PASS] AnimationBuilder works")

    print("\n[PASS] All animation tests passed!")
