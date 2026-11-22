"""
Timeline management - frame iteration and state computation over time.

Provides Timeline for managing a sequence of animations with instant
frame access and frame iteration capabilities.
"""

from dataclasses import dataclass
from typing import Iterator, Optional

from osim_render.api.animation.animation import Animation, AnimationState


@dataclass(frozen=True)
class Timeline:
    """
    A timeline containing a sequence of animations.

    Animations are played sequentially. Timeline allows:
    - Getting state at any time instantly (no frame caching)
    - Iterating through frames at a specific frame rate
    - Determining total duration

    Attributes:
        animations: Tuple of animations to play sequentially
    """

    animations: tuple[Animation, ...]

    def __post_init__(self) -> None:
        """Validate timeline."""
        if not self.animations:
            raise ValueError("Timeline requires at least one animation")

    @property
    def duration(self) -> float:
        """Total duration of all animations in seconds."""
        return sum(anim.duration for anim in self.animations)

    def get_state_at_time(self, time: float) -> AnimationState:
        """
        Compute the animation state at any point in the timeline.

        Time is global (absolute position in timeline), not relative to
        individual animations.

        Args:
            time: Absolute time in seconds from start of timeline

        Returns:
            AnimationState at that time

        Examples:
            >>> timeline = Timeline(animations=(anim1, anim2))
            >>> state = timeline.get_state_at_time(0.5)  # First 0.5 seconds
            >>> state = timeline.get_state_at_time(3.5)  # In second animation
        """
        current_time = max(0.0, min(self.duration, time))
        offset = 0.0

        for animation in self.animations:
            if current_time < offset + animation.duration:
                # Time falls within this animation
                relative_time = current_time - offset
                return animation.compute_state(relative_time)
            offset += animation.duration

        # If we reach here, we're past the end
        # Return final state from last animation
        if self.animations:
            return self.animations[-1].compute_state(self.animations[-1].duration)

        # Should not reach here due to __post_init__ validation
        raise RuntimeError("Invalid timeline state")

    def iterate_frames(
        self,
        fps: int = 30,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Iterator[AnimationState]:
        """
        Iterate through animation frames at a specific frame rate.

        Yields AnimationState at each frame time. Useful for exporting
        to image sequences or video files.

        Args:
            fps: Frames per second (default 30)
            start_time: Start time in seconds (default 0.0)
            end_time: End time in seconds (default timeline duration)

        Yields:
            AnimationState for each frame

        Examples:
            >>> timeline = Timeline(animations=(anim,))
            >>> for state in timeline.iterate_frames(fps=60, end_time=5.0):
            ...     render_frame(state)  # Export each frame
        """
        if fps <= 0:
            raise ValueError(f"fps must be positive, got {fps}")

        start = start_time if start_time is not None else 0.0
        end = end_time if end_time is not None else self.duration

        if start < 0:
            start = 0.0
        if end > self.duration:
            end = self.duration

        if start >= end:
            return

        frame_duration = 1.0 / fps
        current_time = start

        while current_time <= end:
            yield self.get_state_at_time(current_time)
            current_time += frame_duration

    def iterate_frames_count(
        self,
        fps: int = 30,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> tuple[Iterator[AnimationState], int]:
        """
        Get both the frame iterator and the total frame count.

        Useful for progress reporting during export.

        Args:
            fps: Frames per second
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Tuple of (frame_iterator, total_frame_count)

        Examples:
            >>> frames, count = timeline.iterate_frames_count(fps=30)
            >>> for i, state in enumerate(frames):
            ...     print(f"Frame {i+1}/{count}")
            ...     render_frame(state)
        """
        start = start_time if start_time is not None else 0.0
        end = end_time if end_time is not None else self.duration

        if start < 0:
            start = 0.0
        if end > self.duration:
            end = self.duration

        if start >= end:
            return iter([]), 0

        # Calculate frame count
        frame_duration = 1.0 / fps
        frame_count = int((end - start) / frame_duration) + 1

        return self.iterate_frames(fps=fps, start_time=start, end_time=end), frame_count


if __name__ == "__main__":
    # Smoke tests
    print("Testing timeline module...")

    from osim_render.api.animation.coordinate_tween import CoordinateTween
    from osim_render.api.animation.tween import TweenConfig

    # Create two simple animations
    tween1 = CoordinateTween("hip", 0, 45, TweenConfig(duration=1.0))
    anim1 = Animation(name="anim1", tweens=(tween1,), duration=1.0)

    tween2 = CoordinateTween("knee", 0, 90, TweenConfig(duration=1.0))
    anim2 = Animation(name="anim2", tweens=(tween2,), duration=1.0)

    # Test Timeline duration
    timeline = Timeline(animations=(anim1, anim2))
    assert timeline.duration == 2.0
    print("[PASS] Timeline duration is correct")

    # Test get_state_at_time
    state = timeline.get_state_at_time(0.0)
    assert state.coordinate_values.get("hip") == 0.0
    print("[PASS] Timeline.get_state_at_time at t=0 returns first animation start")

    state = timeline.get_state_at_time(0.5)
    assert state.coordinate_values.get("hip") == 22.5
    print("[PASS] Timeline.get_state_at_time at t=0.5 returns first animation mid")

    state = timeline.get_state_at_time(1.0)
    assert state.coordinate_values.get("knee") == 0.0
    print("[PASS] Timeline.get_state_at_time at t=1.0 returns second animation start")

    state = timeline.get_state_at_time(1.5)
    assert state.coordinate_values.get("knee") == 45.0
    print("[PASS] Timeline.get_state_at_time at t=1.5 returns second animation mid")

    state = timeline.get_state_at_time(2.0)
    assert state.coordinate_values.get("knee") == 90.0
    print("[PASS] Timeline.get_state_at_time at t=2.0 returns second animation end")

    # Test iterate_frames
    frames = list(timeline.iterate_frames(fps=2, end_time=1.0))
    assert len(frames) == 3  # 0.0, 0.5, 1.0
    print(
        f"[PASS] Timeline.iterate_frames returns correct frame count ({len(frames)} frames at 2 FPS for 1.0s)"
    )

    # Test iterate_frames_count
    frames_iter, count = timeline.iterate_frames_count(fps=30, end_time=0.5)
    frames = list(frames_iter)
    assert count == len(frames)
    print(
        f"[PASS] Timeline.iterate_frames_count returns correct count ({count} frames)"
    )

    print("\n[PASS] All timeline tests passed!")
