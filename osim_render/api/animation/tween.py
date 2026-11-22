"""
Base tween classes and protocols.

A tween is an animation primitive that interpolates a value from start to end
over a specified duration with an easing function.

Tweens can be composed together (sequential or parallel) to create complex animations.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from osim_render.api.animation.easing import EasingFunction, ease_linear


@dataclass(frozen=True)
class TweenConfig:
    """
    Configuration for tween animation behavior.

    Attributes:
        duration: Animation duration in seconds
        easing: Easing function for timing curve (default: linear)
        delay: Delay before animation starts in seconds (default: 0)
    """

    duration: float
    easing: EasingFunction = ease_linear
    delay: float = 0.0

    def __post_init__(self) -> None:
        """Validate tween config."""
        if self.duration <= 0:
            raise ValueError(f"duration must be positive, got {self.duration}")
        if self.delay < 0:
            raise ValueError(f"delay must be non-negative, got {self.delay}")
        if not callable(self.easing):
            raise TypeError(f"easing must be callable, got {type(self.easing)}")


class Tween(Protocol):
    """
    Protocol for tween animation primitives.

    Any class that implements compute_value() and is_complete() is a Tween.
    All tweens must expose their TweenConfig so callers can read delay/duration
    without duck-typing.

    Methods:
        compute_value(elapsed_time): Compute animated value at given time
        is_complete(elapsed_time): Check if animation is finished
    """

    config: TweenConfig

    def compute_value(self, elapsed_time: float) -> Any:
        """
        Compute the animated value at the given elapsed time.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            Animated value appropriate for this tween type
            (e.g., dict for coordinate tween, CameraState for camera tween)
        """
        ...

    def is_complete(self, elapsed_time: float) -> bool:
        """
        Check if the animation is complete.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            True if animation is finished (elapsed_time >= duration + delay)
        """
        ...

    @property
    def duration(self) -> float:
        """Total duration of the tween in seconds."""
        ...


def compute_eased_progress(config: TweenConfig, elapsed_time: float) -> float:
    """
    Compute the eased progress [0, 1] for a tween at elapsed time.

    Takes into account delay and easing function.

    Args:
        config: TweenConfig with duration, delay, and easing
        elapsed_time: Time elapsed since animation start

    Returns:
        Eased progress in [0, 1], where:
        - 0 means animation hasn't started yet (still in delay)
        - Values between 0 and 1 represent animation progress
        - 1 means animation is complete

    Examples:
        >>> config = TweenConfig(duration=2.0, delay=0.5, easing=ease_linear)
        >>> compute_eased_progress(config, 0.0)  # Before delay
        0.0
        >>> compute_eased_progress(config, 0.5)  # At delay boundary
        0.0
        >>> compute_eased_progress(config, 1.5)  # Half through animation
        0.5
        >>> compute_eased_progress(config, 2.5)  # After animation completes
        1.0
    """
    # Check if still in delay
    if elapsed_time < config.delay:
        return 0.0

    # Compute time since animation started (after delay)
    time_since_start = elapsed_time - config.delay

    # Compute raw progress [0, 1]
    raw_progress = min(1.0, time_since_start / config.duration)

    # Apply easing function
    return config.easing(raw_progress)


if __name__ == "__main__":
    # Smoke tests
    print("Testing tween module...")

    from osim_render.api.animation.easing import ease_smooth_step

    # Test TweenConfig
    config = TweenConfig(duration=2.0, easing=ease_smooth_step, delay=0.5)
    assert config.duration == 2.0
    assert config.delay == 0.5
    print("[PASS] TweenConfig creation works")

    # Test compute_eased_progress
    progress = compute_eased_progress(config, 0.0)
    assert progress == 0.0, f"Before delay should return 0, got {progress}"
    print("[PASS] compute_eased_progress before delay returns 0")

    progress = compute_eased_progress(config, 0.5)
    assert progress == 0.0, f"At delay should return 0, got {progress}"
    print("[PASS] compute_eased_progress at delay returns 0")

    progress = compute_eased_progress(config, 1.5)
    assert 0.4 < progress < 0.6, f"Mid animation should be ~0.5, got {progress}"
    print(
        f"[PASS] compute_eased_progress mid animation returns ~0.5 (got {progress:.3f})"
    )

    progress = compute_eased_progress(config, 2.5)
    assert progress == 1.0, f"After animation should return 1, got {progress}"
    print("[PASS] compute_eased_progress after animation returns 1")

    print("\n[PASS] All tween tests passed!")
