"""
Animation renderer for real-time playback in the UI.

Provides playback control (play, pause, seek) and integrates with the
main window's VTK widget for live animation preview.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol

from osim_render.api.animation.animation import AnimationState
from osim_render.api.animation.timeline import Timeline


class _SceneUpdater(Protocol):
    """Minimal protocol for objects that receive frame updates."""

    def update_frame(self, state: AnimationState) -> None: ...


class SignalProtocol(Protocol):
    """Protocol for Qt signals."""

    def connect(self, slot: Callable[[], None]) -> Any:
        ...


class TimerProtocol(Protocol):
    """Protocol for timer objects (Qt-agnostic interface)."""

    timeout: SignalProtocol

    def setSingleShot(self, val: bool) -> None:
        ...

    def start(self, ms: int) -> None:
        ...

    def stop(self) -> None:
        ...


class _NoOpSignal:
    """No-op signal for non-GUI environments."""

    def connect(self, slot: Callable[[], None]) -> Any:
        """No-op: Connect signal."""
        return None


class _NoOpTimer:
    """No-op timer for non-GUI environments."""

    def __init__(self) -> None:
        """Initialize no-op timer."""
        self.timeout: SignalProtocol = _NoOpSignal()

    def setSingleShot(self, val: bool) -> None:
        """No-op: Set single shot mode."""
        pass

    def start(self, ms: int) -> None:
        """No-op: Start timer."""
        pass

    def stop(self) -> None:
        """No-op: Stop timer."""
        pass


@dataclass(frozen=True)
class RenderConfig:
    """
    Configuration for animation rendering.

    Attributes:
        resolution: Output resolution as (width, height) in pixels
        background_color: Background RGB color in [0, 1]
        anti_aliasing: Whether to enable anti-aliasing
        fps: Frames per second for playback
    """

    resolution: tuple[int, int] = (1920, 1080)
    background_color: tuple[float, float, float] = (0.2, 0.2, 0.2)
    anti_aliasing: bool = True
    fps: int = 30

    def __post_init__(self) -> None:
        """Validate render config."""
        if self.fps <= 0:
            raise ValueError(f"fps must be positive, got {self.fps}")


class AnimationRenderer:
    """
    Real-time animation renderer for UI preview.

    Manages playback of animations with play, pause, seek functionality.
    Uses QTimer for frame advancement at specified FPS.

    Attributes:
        scene_manager: Manager for scene rendering
        config: RenderConfig with resolution and playback settings
        timeline: Timeline to render
    """

    def __init__(
        self,
        scene_manager: _SceneUpdater,
        timer: Optional[TimerProtocol] = None,
        config: Optional[RenderConfig] = None,
        timeline: Optional[Timeline] = None,
    ):
        """
        Initialize animation renderer.

        Args:
            scene_manager: Manager for scene rendering and updates
            timer: Timer for frame updates (Qt timer or compatible). If None, uses no-op timer.
            config: RenderConfig for rendering parameters
            timeline: Optional initial timeline to render
        """
        self.scene_manager = scene_manager
        self.config = config if config is not None else RenderConfig()
        self.timeline = timeline
        self._timer = timer if timer is not None else _NoOpTimer()
        self._timer.setSingleShot(False)
        self._current_time = 0.0
        self._is_playing = False
        self._playback_speed = 1.0
        # Use fixed high-frequency timer (60 Hz) for smooth interpolation
        # Speed changes affect time advancement, not timer frequency
        self._timer_interval_ms = 16  # 60 Hz = 16.67ms, round to 16ms
        self._time_per_tick = 0.016667  # 1/60 seconds
        self._on_frame_callback: Optional[Callable[[int, int], None]] = None

        # Connect timer to frame update
        self._timer.timeout.connect(self._on_playback_tick)

    def set_timeline(self, timeline: Timeline) -> None:
        """
        Set the timeline to render.

        Args:
            timeline: Timeline to play
        """
        self.timeline = timeline
        self._current_time = 0.0

    def play(self) -> None:
        """Start playback from current time."""
        if not self.timeline:
            return

        self._is_playing = True
        # Use fixed timer interval, speed affects time advancement only
        self._timer.start(self._timer_interval_ms)

    def pause(self) -> None:
        """Pause playback at current time."""
        self._is_playing = False
        self._timer.stop()

    def stop(self) -> None:
        """Stop playback and reset to start."""
        self.pause()
        self._current_time = 0.0
        self._update_frame()

    def seek(self, time: float) -> None:
        """
        Seek to a specific time in the animation.

        Args:
            time: Time in seconds from start of timeline
        """
        if not self.timeline:
            return

        self._current_time = max(0.0, min(self.timeline.duration, time))
        self._update_frame()

    def set_playback_speed(self, speed: float) -> None:
        """
        Set playback speed multiplier.

        Args:
            speed: Speed multiplier (1.0 = normal, 2.0 = double speed, 0.5 = half speed)
        """
        if speed <= 0:
            raise ValueError(f"playback_speed must be positive, got {speed}")

        self._playback_speed = speed
        # No need to restart timer - speed affects time advancement, not timer frequency

    def set_frame_callback(self, callback: Callable[[int, int], None]) -> None:
        """
        Set callback for frame updates.

        Callback is called with (current_frame, total_frames) on each frame.

        Args:
            callback: Function(current_frame, total_frames) -> None
        """
        self._on_frame_callback = callback

    def _on_playback_tick(self) -> None:
        """Internal: Called by timer on each frame."""
        if not self.timeline:
            return

        # Advance time by fixed increment, scaled by playback speed
        # Fixed timer frequency means smooth interpolation at all speeds
        self._current_time += self._time_per_tick * self._playback_speed

        # Loop if we reach the end
        if self._current_time >= self.timeline.duration:
            self._current_time = 0.0

        self._update_frame()

    def _update_frame(self) -> None:
        """Internal: Update visualization for current frame."""
        if not self.timeline:
            return

        # Get animation state at current time
        state = self.timeline.get_state_at_time(self._current_time)

        # Update scene manager with new state
        self.scene_manager.update_frame(state)

        # Call frame callback if set
        if self._on_frame_callback:
            # Calculate frame index based on target render FPS
            frame_duration = 1.0 / self.config.fps if self.config.fps > 0 else 0.033
            frame_index = int(self._current_time / frame_duration)
            total_frames = int(self.timeline.duration / frame_duration) + 1
            self._on_frame_callback(frame_index, total_frames)

    @property
    def is_playing(self) -> bool:
        """Check if animation is currently playing."""
        return self._is_playing

    @property
    def current_time(self) -> float:
        """Get current playback time in seconds."""
        return self._current_time

    @property
    def duration(self) -> float:
        """Get total animation duration in seconds."""
        return self.timeline.duration if self.timeline else 0.0


if __name__ == "__main__":
    # Smoke test
    print("Testing animation_renderer module...")

    from osim_render.api.animation.coordinate_tween import CoordinateTween
    from osim_render.api.animation.tween import TweenConfig
    from osim_render.api.animation.animation import Animation

    # Note: This test doesn't create actual AnimationRenderer instances
    # because QTimer requires a QApplication, which requires a display.
    # In actual usage, AnimationRenderer will be created in the Qt event loop.

    # Create timeline
    tween = CoordinateTween("hip", 0, 45, TweenConfig(duration=1.0))
    anim = Animation(name="test", tweens=(tween,), duration=1.0)
    timeline = Timeline(animations=(anim,))

    # Test that we can create the config
    config = RenderConfig(fps=30)
    assert config.fps == 30
    print("[PASS] RenderConfig creation works")

    assert timeline.duration == 1.0
    print("[PASS] Timeline creation works")

    print("\n[PASS] All animation_renderer tests passed!")
