"""
Tweens for animating OpenSim model coordinates.

Allows smooth animation of joint angles and other model coordinates
from start to end values over a specified duration.
"""

from dataclasses import dataclass

from osim_render.api.animation.interpolation import lerp
from osim_render.api.animation.tween import TweenConfig, compute_eased_progress


@dataclass(frozen=True)
class CoordinateTween:
    """
    Tween for animating a single OpenSim coordinate.

    Interpolates a coordinate's value from start to end over the duration,
    using the easing function to control the timing curve.

    Attributes:
        coordinate_name: Name of the coordinate to animate
        start_value: Starting coordinate value
        end_value: Ending coordinate value
        config: TweenConfig with duration, easing, and delay

    Examples:
        >>> tween = CoordinateTween(
        ...     coordinate_name="hip_flexion_r",
        ...     start_value=0.0,
        ...     end_value=45.0,
        ...     config=TweenConfig(duration=2.0)
        ... )
        >>> # After 1 second: returns {"hip_flexion_r": 22.5}
        >>> tween.compute_value(1.0)
        {'hip_flexion_r': 22.5}
    """

    coordinate_name: str
    start_value: float
    end_value: float
    config: TweenConfig

    @property
    def duration(self) -> float:
        """Total duration of the tween in seconds."""
        return self.config.duration + self.config.delay

    def compute_value(self, elapsed_time: float) -> dict[str, float]:
        """
        Compute the coordinate value at the given elapsed time.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            Dictionary with single entry: {coordinate_name: interpolated_value}
        """
        progress = compute_eased_progress(self.config, elapsed_time)
        value = lerp(self.start_value, self.end_value, progress)
        return {self.coordinate_name: value}

    def is_complete(self, elapsed_time: float) -> bool:
        """
        Check if the animation is complete.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            True if elapsed_time >= duration + delay
        """
        return elapsed_time >= self.duration


@dataclass(frozen=True)
class MultiCoordinateTween:
    """
    Tween for animating multiple OpenSim coordinates simultaneously.

    All coordinates animate in parallel, each with its own interpolation.

    Attributes:
        coordinate_tweens: Tuple of CoordinateTween objects to animate together

    Examples:
        >>> tween1 = CoordinateTween("hip_flexion_r", 0, 45, TweenConfig(duration=2.0))
        >>> tween2 = CoordinateTween("knee_angle_r", 0, 90, TweenConfig(duration=2.0))
        >>> multi = MultiCoordinateTween(coordinate_tweens=(tween1, tween2))
        >>> # After 1 second: returns {"hip_flexion_r": 22.5, "knee_angle_r": 45.0}
        >>> multi.compute_value(1.0)
        {'hip_flexion_r': 22.5, 'knee_angle_r': 45.0}
    """

    coordinate_tweens: tuple["CoordinateTween", ...]

    def __post_init__(self) -> None:
        """Validate that we have at least one coordinate tween."""
        if not self.coordinate_tweens:
            raise ValueError(
                "MultiCoordinateTween requires at least one CoordinateTween"
            )

    @property
    def duration(self) -> float:
        """Duration is the maximum of all coordinate tween durations."""
        return max(tween.duration for tween in self.coordinate_tweens)

    def compute_value(self, elapsed_time: float) -> dict[str, float]:
        """
        Compute values for all coordinates at the given elapsed time.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            Dictionary mapping coordinate names to their interpolated values
        """
        result = {}
        for tween in self.coordinate_tweens:
            result.update(tween.compute_value(elapsed_time))
        return result

    def is_complete(self, elapsed_time: float) -> bool:
        """
        Check if all coordinate animations are complete.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            True if elapsed_time >= maximum duration
        """
        return elapsed_time >= self.duration


if __name__ == "__main__":
    # Smoke tests
    print("Testing coordinate_tween module...")

    from osim_render.api.animation.easing import ease_smooth_step

    # Test CoordinateTween
    tween = CoordinateTween(
        coordinate_name="hip_flexion_r",
        start_value=0.0,
        end_value=90.0,
        config=TweenConfig(duration=2.0, easing=ease_smooth_step),
    )

    # Test at key times
    result = tween.compute_value(0.0)
    assert result == {
        "hip_flexion_r": 0.0
    }, f"At t=0 should return start value, got {result}"
    print("[PASS] CoordinateTween at t=0 returns start value")

    result = tween.compute_value(1.0)
    assert "hip_flexion_r" in result
    assert (
        40.0 < result["hip_flexion_r"] < 50.0
    ), f"Mid animation should be ~45, got {result}"
    print(
        f"[PASS] CoordinateTween at t=1 returns mid value ({result['hip_flexion_r']:.1f})"
    )

    result = tween.compute_value(2.0)
    assert result == {
        "hip_flexion_r": 90.0
    }, f"At t=2 should return end value, got {result}"
    print("[PASS] CoordinateTween at t=2 returns end value")

    # Test is_complete
    assert not tween.is_complete(1.0)
    assert tween.is_complete(2.0)
    assert tween.is_complete(3.0)
    print("[PASS] CoordinateTween.is_complete works")

    # Test MultiCoordinateTween
    tween1 = CoordinateTween("hip_flexion_r", 0.0, 45.0, TweenConfig(duration=2.0))
    tween2 = CoordinateTween("knee_angle_r", 0.0, 90.0, TweenConfig(duration=2.0))
    multi = MultiCoordinateTween(coordinate_tweens=(tween1, tween2))

    result = multi.compute_value(0.0)
    assert result == {"hip_flexion_r": 0.0, "knee_angle_r": 0.0}
    print("[PASS] MultiCoordinateTween at t=0 returns all start values")

    result = multi.compute_value(1.0)
    assert result == {"hip_flexion_r": 22.5, "knee_angle_r": 45.0}
    print("[PASS] MultiCoordinateTween at t=1 returns correct values")

    result = multi.compute_value(2.0)
    assert result == {"hip_flexion_r": 45.0, "knee_angle_r": 90.0}
    print("[PASS] MultiCoordinateTween at t=2 returns all end values")

    print("\n[PASS] All coordinate_tween tests passed!")
