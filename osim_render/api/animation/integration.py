"""
Integration layer - AnimationManager for managing animations in the application.

Provides high-level interface for creating, playing, and exporting animations
using the animation system with full integration into existing application systems.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from osim_render.api.animation.animation import Animation, AnimationState
from osim_render.api.animation.scene import Scene
from osim_render.api.animation.timeline import Timeline
from osim_render.api.loaders.motion_loader import MotionData
from osim_render.api.rendering.animation_renderer import AnimationRenderer, RenderConfig
from osim_render.api.animation.coordinate_tween import CoordinateTween
from osim_render.api.animation.tween import TweenConfig
from osim_render.api.managers.events import EventType

if TYPE_CHECKING:
    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.rendering.scene import SceneManager
    from osim_render.api.managers.event_bus import EventBus


class MotionDataAnimation(Animation):
    """
    Animation wrapper that directly uses motion frame data.

    Instead of creating tweens, this animation extracts coordinate values
    directly from MotionData frames and interpolates between them.
    This ensures accurate playback of all intermediate positions.

    Attributes:
        motion_data: MotionData with frames to animate
        _frame_cache: Cached frames for quick lookup
    """

    def __init__(
        self,
        name: str,
        motion_data: MotionData,
        duration: Optional[float] = None,
        time_scale: float = 1.0,
    ):
        """
        Initialize motion data animation.

        Args:
            name: Name for the animation
            motion_data: MotionData with frames
            duration: Optional override for duration
            time_scale: Speed multiplier (e.g. 2.0 = 2x faster, 0.5 = half speed)
        """
        self.motion_data = motion_data
        self.time_scale = time_scale
        self._frame_cache = {f.time: f for f in motion_data.frames}

        # We override get_state_at_time so this tween is never actually used
        dummy_tween = CoordinateTween(
            "dummy",
            0.0,
            0.0,
            TweenConfig(duration=1.0),
        )

        natural_duration = motion_data.end_time - motion_data.start_time
        super().__init__(
            name=name,
            tweens=(dummy_tween,),
            duration=duration or (natural_duration / time_scale),
        )

    def compute_state(self, time: float) -> AnimationState:
        """
        Compute animation state by interpolating motion frames.

        Overrides parent to skip dummy tween evaluation and use motion data directly.

        Args:
            time: Time in seconds relative to animation start

        Returns:
            AnimationState with coordinate values from motion data
        """
        return self.get_state_at_time(time)

    def get_state_at_time(self, time: float) -> AnimationState:
        """
        Get animation state at specific time by interpolating motion frames.

        Args:
            time: Time in seconds

        Returns:
            AnimationState with coordinate values interpolated from motion data
        """
        if not self.motion_data.frames:
            return AnimationState(time=time, coordinate_values={})

        # Map video time to motion time
        # Offset by start_time so timeline t=0 maps to motion start, not 0
        motion_time = (time * self.time_scale) + self.motion_data.start_time

        # Clamp time to motion range
        clamped_time = max(
            self.motion_data.start_time, min(
                motion_time, self.motion_data.end_time)
        )

        frames = self.motion_data.frames

        frame_before = frames[0]
        for frame in frames:
            if frame.time <= clamped_time:
                frame_before = frame
            else:
                break

        frame_after = frame_before
        for frame in frames:
            if frame.time >= clamped_time:
                frame_after = frame
                break

        # If no interpolation needed (at exact frame or single frame)
        if frame_before.time == frame_after.time:
            return AnimationState(
                time=time, coordinate_values=dict(
                    frame_before.coordinate_values)
            )

        # Linear interpolation between frames
        time_diff = frame_after.time - frame_before.time
        alpha = (clamped_time - frame_before.time) / time_diff

        # Interpolate all coordinates
        coord_values = {}
        for coord_name in frame_before.coordinate_values:
            val_before = frame_before.coordinate_values.get(coord_name, 0.0)
            val_after = frame_after.coordinate_values.get(
                coord_name, val_before)
            # Linear interpolation
            coord_values[coord_name] = val_before + \
                (val_after - val_before) * alpha

        return AnimationState(time=time, coordinate_values=coord_values)


class AnimationManager:
    """
    Manages animation creation, playback, and export.

    Provides high-level interface for:
    - Creating animations from motion data (backward compatibility)
    - Creating animations using the manim-style Scene API
    - Playing animations with real-time preview
    - Exporting animations to various formats

    Attributes:
        model_manager: Manager providing access to OpenSim model
        scene_manager: Manager for rendering and visualization
        event_bus: Event system for publishing animation events
        renderer: Current animation renderer instance
    """

    def __init__(
        self,
        model_manager: ModelManager,
        scene_manager: Optional[SceneManager],
        event_bus: EventBus,
    ):
        """
        Initialize animation manager.

        Args:
            model_manager: Manager providing access to OpenSim model
            scene_manager: Manager for rendering and visualization
            event_bus: Event system for publishing animation events
        """
        self.model_manager = model_manager
        self.scene_manager = scene_manager
        self.event_bus = event_bus
        self.renderer: Optional[AnimationRenderer] = None
        self._current_scene: Optional[Scene] = None

    def create_scene(self) -> Scene:
        """
        Create a new animation scene for composition.

        Returns:
            Scene object ready for animation composition

        Examples:
            >>> scene = animation_manager.create_scene()
            >>> scene.animate_coordinate("hip", 0, 45, duration=2.0)
            >>> timeline = scene.build_timeline()
        """
        scene = Scene(self.model_manager, self.scene_manager, self.event_bus)
        self._current_scene = scene
        return scene

    def create_animation_from_motion(
        self, motion_data: MotionData, name: str = "motion_playback"
    ) -> Animation:
        """
        Convert motion data to an Animation for playback through animation system.

        Creates a MotionDataAnimation wrapper that directly uses motion frames,
        ensuring accurate playback of all intermediate positions.

        Args:
            motion_data: MotionData loaded from file
            name: Name for the animation

        Returns:
            Animation that can be played or exported

        Examples:
            >>> motion = motion_loader.load(motion_file)
            >>> animation = animation_manager.create_animation_from_motion(motion)
        """
        if not motion_data.frames:
            raise ValueError("Motion data has no frames")

        animation = MotionDataAnimation(
            name=name,
            motion_data=motion_data,
            duration=motion_data.end_time - motion_data.start_time,
        )
        return animation

    def play_animation(
        self,
        animation: Animation,
        vtk_widget: Any,
        config: Optional[RenderConfig] = None,
    ) -> AnimationRenderer:
        """
        Play an animation with real-time preview.

        Args:
            animation: Animation to play
            vtk_widget: VTK widget for rendering
            config: Optional RenderConfig for playback

        Returns:
            AnimationRenderer controlling playback

        Examples:
            >>> renderer = animation_manager.play_animation(animation, vtk_widget)
            >>> renderer.play()
            >>> renderer.seek(1.0)  # Seek to 1 second
        """
        if self.scene_manager is None:
            raise RuntimeError("Cannot play animation: no model is loaded.")

        if config is None:
            config = RenderConfig()

        timeline = Timeline(animations=(animation,))

        self.renderer = AnimationRenderer(
            self.scene_manager, config=config, timeline=timeline
        )

        self.event_bus.publish_event(
            EventType.ANIMATION_STARTED, {"animation": animation})

        return self.renderer

    def export_to_png_sequence(
        self,
        animation: Animation,
        output_dir: Path,
        fps: int = 30,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """
        Export animation as PNG frame sequence.

        Args:
            animation: Animation to export
            output_dir: Directory to save PNG files
            fps: Frames per second
            progress_callback: Optional progress callback

        Returns:
            Path to output directory

        Examples:
            >>> animation_manager.export_to_png_sequence(
            ...     animation,
            ...     Path("output/frames"),
            ...     fps=30
            ... )
        """
        from osim_render.api.rendering.frame_exporter import (
            FrameExporter,
            FrameExportConfig,
        )

        if self.scene_manager is None:
            raise RuntimeError("Cannot export: no model is loaded.")

        output_dir.mkdir(parents=True, exist_ok=True)

        config = FrameExportConfig(
            output_dir=output_dir,
            fps=fps,
            resolution=(1920, 1080),
        )

        exporter = FrameExporter(self.scene_manager, config)
        timeline = Timeline(animations=(animation,))
        result = exporter.export_timeline(
            timeline, progress_callback=progress_callback)

        if not result.success:
            raise RuntimeError(f"Export failed: {result.error}")

        return output_dir

    def export_to_video(
        self,
        animation: Animation,
        output_file: Path,
        fps: int = 30,
        quality: str = "medium",
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """
        Export animation as MP4 video.

        Args:
            animation: Animation to export
            output_file: Path to save MP4 file
            fps: Frames per second
            quality: Quality level ('high', 'medium', 'low')
            progress_callback: Optional progress callback

        Returns:
            Path to output video file

        Examples:
            >>> animation_manager.export_to_video(
            ...     animation,
            ...     Path("output/animation.mp4"),
            ...     fps=60,
            ...     quality="high"
            ... )
        """
        from osim_render.api.rendering.video_exporter import (
            VideoExporter,
            VideoExportConfig,
        )

        if self.scene_manager is None:
            raise RuntimeError("Cannot export: no model is loaded.")

        output_file.parent.mkdir(parents=True, exist_ok=True)

        config = VideoExportConfig(
            output_file=output_file,
            fps=fps,
            quality=quality,
            resolution=(1920, 1080),
        )

        exporter = VideoExporter(self.scene_manager, config)
        timeline = Timeline(animations=(animation,))
        result = exporter.export_timeline(
            timeline, progress_callback=progress_callback)

        if not result.success:
            raise RuntimeError(f"Export failed: {result.error}")

        return output_file

    def export_screenshot(
        self,
        animation: Animation,
        time: float,
        output_file: Path,
        resolution: tuple[int, int] = (3840, 2160),
    ) -> Path:
        """
        Export a high-resolution screenshot at a specific animation time.

        Args:
            animation: Animation to screenshot
            time: Time in seconds to capture
            output_file: Path to save screenshot
            resolution: Resolution (default 4K)

        Returns:
            Path to output screenshot

        Examples:
            >>> animation_manager.export_screenshot(
            ...     animation,
            ...     time=1.5,
            ...     output_file=Path("output/frame_1.5s.png")
            ... )
        """
        from osim_render.api.rendering.screenshot_exporter import (
            ScreenshotExporter,
            ScreenshotExportConfig,
        )

        if self.scene_manager is None:
            raise RuntimeError("Cannot export screenshot: no model is loaded.")

        timeline = Timeline(animations=(animation,))
        state = timeline.get_state_at_time(time)

        config = ScreenshotExportConfig(
            output_path=output_file,
            resolution=resolution,
        )

        exporter = ScreenshotExporter(self.scene_manager, config)
        result = exporter.export_frame(state)

        if not result.success:
            raise RuntimeError(f"Export failed: {result.error}")

        return output_file


if __name__ == "__main__":
    # Smoke test
    print("Testing integration module...")

    from osim_render.api.managers.model_manager import ModelManager as _ModelManager
    from osim_render.api.managers.event_bus import EventBus as _EventBus

    manager = AnimationManager(
        _ModelManager(_EventBus()),
        None,
        _EventBus(),
    )
    assert manager is not None
    print("[PASS] AnimationManager creation works")

    # Test create_scene
    scene = manager.create_scene()
    assert scene is not None
    print("[PASS] AnimationManager.create_scene works")

    # Test scene API
    scene.animate_coordinate("hip", 0, 45, duration=1.0)
    timeline = scene.build_timeline()
    assert timeline.duration > 0
    print("[PASS] Scene composition and timeline build works")

    print("\n[PASS] All integration tests passed!")
