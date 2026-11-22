"""
Tween composition - sequential and parallel animation groups.

Allows building complex animations by combining simple tweens in sequences
or parallel groups.
"""

from dataclasses import dataclass
from typing import Any

from osim_render.api.animation.tween import TweenConfig


@dataclass(frozen=True)
class SequentialTween:
    """
    Tween that plays a sequence of tweens one after another.

    Each tween starts when the previous one completes. Total duration is
    the sum of all tween durations.

    Attributes:
        tweens: Tuple of tweens to play sequentially

    Examples:
        >>> # Animate hip, then wait, then animate knee
        >>> hip_tween = CoordinateTween("hip", 0, 45, TweenConfig(duration=1.0))
        >>> knee_tween = CoordinateTween("knee", 0, 90, TweenConfig(duration=1.0, delay=0.5))
        >>> seq = SequentialTween(tweens=(hip_tween, knee_tween))
        >>> seq.compute_value(0.5)  # During hip animation
        >>> seq.compute_value(2.0)  # During knee animation
    """

    tweens: tuple[Any, ...]

    def __post_init__(self) -> None:
        """Validate that we have at least one tween."""
        if not self.tweens:
            raise ValueError("SequentialTween requires at least one tween")

    @property
    def config(self) -> TweenConfig:
        """TweenConfig with this tween's total duration and zero delay."""
        return TweenConfig(duration=self.duration)

    @property
    def duration(self) -> float:
        """Total duration is the sum of all tween durations."""
        total = 0.0
        for i, tween in enumerate(self.tweens):
            # For sequential, delay only counts for the first tween
            tween_duration = tween.duration
            if i == 0:
                total = tween_duration
            else:
                total += tween_duration
        return total

    def compute_value(self, elapsed_time: float) -> dict[str, Any]:
        """
        Compute the combined values of all tweens at the given time.

        Only the active tween (based on elapsed_time) contributes values.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            Dictionary with values from the currently active tween
        """
        # Find which tween is active
        current_time = elapsed_time
        for tween in self.tweens:
            if current_time < tween.duration:
                # This tween is active
                result = tween.compute_value(current_time)
                if isinstance(result, dict):
                    return result
                else:
                    return {"value": result}

        # If we're past the end, return the final state from the last tween
        if self.tweens:
            result = self.tweens[-1].compute_value(self.tweens[-1].duration)
            if isinstance(result, dict):
                return result
            else:
                return {"value": result}

        return {}

    def is_complete(self, elapsed_time: float) -> bool:
        """
        Check if all tweens are complete.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            True if elapsed_time >= total duration
        """
        return elapsed_time >= self.duration


@dataclass(frozen=True)
class ParallelTween:
    """
    Tween that plays multiple tweens simultaneously.

    All tweens start at the same time and animate in parallel. Total duration
    is the maximum of all tween durations.

    Attributes:
        tweens: Tuple of tweens to play in parallel

    Examples:
        >>> # Animate hip and knee together
        >>> hip_tween = CoordinateTween("hip", 0, 45, TweenConfig(duration=2.0))
        >>> knee_tween = CoordinateTween("knee", 0, 90, TweenConfig(duration=2.0))
        >>> cam_tween = CameraTween(start_cam, end_cam, TweenConfig(duration=2.0))
        >>> parallel = ParallelTween(tweens=(hip_tween, knee_tween, cam_tween))
        >>> parallel.compute_value(1.0)  # Returns combined dict
    """

    tweens: tuple[Any, ...]

    def __post_init__(self) -> None:
        """Validate that we have at least one tween."""
        if not self.tweens:
            raise ValueError("ParallelTween requires at least one tween")

    @property
    def config(self) -> TweenConfig:
        """TweenConfig with this tween's total duration and zero delay."""
        return TweenConfig(duration=self.duration)

    @property
    def duration(self) -> float:
        """Total duration is the maximum of all tween durations."""
        return float(max(tween.duration for tween in self.tweens))

    def compute_value(self, elapsed_time: float) -> dict[str, Any]:
        """
        Compute the combined values of all tweens at the given time.

        Returns a merged dictionary with values from all tweens.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            Dictionary merging values from all tweens
        """
        result = {}

        for tween in self.tweens:
            tween_value = tween.compute_value(elapsed_time)

            # Merge tween result into result dict
            if isinstance(tween_value, dict):
                result.update(tween_value)
            else:
                # If tween returns non-dict, wrap it
                result[f"tween_{id(tween)}"] = tween_value

        return result

    def is_complete(self, elapsed_time: float) -> bool:
        """
        Check if all tweens are complete.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            True if elapsed_time >= maximum duration
        """
        return elapsed_time >= self.duration


if __name__ == "__main__":
    # Smoke tests
    print("Testing group_tween module...")

    from osim_render.api.animation.coordinate_tween import CoordinateTween
    from osim_render.api.animation.tween import TweenConfig

    # Create simple tweens
    tween1 = CoordinateTween("hip", 0, 45, TweenConfig(duration=1.0))
    tween2 = CoordinateTween("knee", 0, 90, TweenConfig(duration=1.0))

    # Test SequentialTween
    seq = SequentialTween(tweens=(tween1, tween2))
    assert seq.duration == 2.0, f"Sequential duration should be 2.0, got {seq.duration}"
    print("[PASS] SequentialTween duration is correct")

    result = seq.compute_value(0.5)
    assert "hip" in result
    assert "knee" not in result
    print("[PASS] SequentialTween at t=0.5 returns hip value only")

    result = seq.compute_value(1.5)
    assert "knee" in result
    assert "hip" not in result
    print("[PASS] SequentialTween at t=1.5 returns knee value only")

    # Test ParallelTween
    parallel = ParallelTween(tweens=(tween1, tween2))
    assert (
        parallel.duration == 1.0
    ), f"Parallel duration should be 1.0, got {parallel.duration}"
    print("[PASS] ParallelTween duration is correct")

    result = parallel.compute_value(0.5)
    assert "hip" in result
    assert "knee" in result
    assert result["hip"] == 22.5
    assert result["knee"] == 45.0
    print("[PASS] ParallelTween at t=0.5 returns both values")

    result = parallel.compute_value(1.0)
    assert result["hip"] == 45.0
    assert result["knee"] == 90.0
    print("[PASS] ParallelTween at t=1.0 returns end values")

    print("\n[PASS] All group_tween tests passed!")
