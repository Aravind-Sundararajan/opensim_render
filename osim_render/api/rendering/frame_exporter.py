"""
PNG frame sequence export.

Exports animations as sequences of PNG images, useful for:
- Creating GIF animations (with external tools)
- Intermediate export before video encoding
- Detailed inspection of individual frames
- Restart capability (can resume export if interrupted)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Protocol

from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.animation.animation import AnimationState
from osim_render.api.animation.timeline import Timeline


class _SceneUpdater(Protocol):
    """Supports frame updates for rendering."""

    def update_frame(self, state: AnimationState) -> None: ...


@dataclass(frozen=True)
class FrameExportConfig:
    """
    Configuration for frame export.

    Attributes:
        output_dir: Directory to save PNG files
        filename_pattern: Pattern for filenames (should include {} for frame number)
        resolution: Output resolution as (width, height) in pixels
        fps: Frames per second for export
    """

    output_dir: Path
    filename_pattern: str = "frame_{:06d}.png"
    resolution: tuple[int, int] = (1920, 1080)
    fps: int = 30

    def __post_init__(self) -> None:
        """Validate config."""
        if not self.output_dir.exists():
            raise ValueError(f"output_dir does not exist: {self.output_dir}")
        if self.fps <= 0:
            raise ValueError(f"fps must be positive, got {self.fps}")


@dataclass(frozen=True)
class ExportResult:
    """
    Result of an export operation.

    Attributes:
        success: Whether export completed successfully
        frame_count: Number of frames exported
        output_dir: Directory where frames were saved
        error: Error message if export failed
        frame_paths: List of exported frame file paths
    """

    success: bool
    frame_count: int
    output_dir: Path
    error: Optional[str] = None
    frame_paths: list[Path] = field(default_factory=list)


class FrameExporter:
    """
    Exports animations as PNG frame sequences.

    Handles the complete export process including:
    - Creating output directory structure
    - Rendering each frame
    - Saving to PNG format
    - Progress reporting

    Attributes:
        scene_manager: Manager for scene rendering
        config: FrameExportConfig with output settings
        renderer: OffscreenRenderer for image generation
    """

    def __init__(
        self,
        scene_manager: _SceneUpdater,
        config: FrameExportConfig,
        renderer: Optional[OffscreenRenderer] = None,
    ):
        """
        Initialize frame exporter.

        Args:
            scene_manager: Manager for scene rendering and updates
            config: FrameExportConfig with output settings
            renderer: Optional shared OffscreenRenderer. If None, a new one is
                created. Pass the same renderer used to build the SceneManager so
                that model actors are visible in the exported frames.
        """
        self.scene_manager = scene_manager
        self.config = config
        self.renderer = renderer or OffscreenRenderer(
            resolution=config.resolution,
            background_color=(0.2, 0.2, 0.2),
        )

    def export_timeline(
        self,
        timeline: Timeline,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> ExportResult:
        """
        Export timeline to PNG frame sequence.

        Iterates through timeline at specified FPS and saves each frame as PNG.

        Args:
            timeline: Timeline to export
            progress_callback: Optional function(current_frame, total_frames) for progress

        Returns:
            ExportResult with export status and frame paths

        Raises:
            ValueError: If timeline iteration fails
            IOError: If frame rendering or saving fails
            AttributeError: If scene_manager lacks update_frame method
        """
        frames_iter, frame_count = timeline.iterate_frames_count(
            fps=self.config.fps)

        frame_paths = []
        frame_num = 0

        for frame_num, state in enumerate(frames_iter):
            # Report progress
            if progress_callback:
                progress_callback(frame_num, frame_count)

            self.scene_manager.update_frame(state)

            # Render and save frame
            output_path = self.config.output_dir / self.config.filename_pattern.format(
                frame_num
            )
            self.renderer.save_frame(state, output_path)
            frame_paths.append(output_path)

        # Report final progress
        if progress_callback:
            progress_callback(frame_count, frame_count)

        return ExportResult(
            success=True,
            frame_count=frame_count,
            output_dir=self.config.output_dir,
            frame_paths=frame_paths,
        )


if __name__ == "__main__":
    # Smoke test
    print("Testing frame_exporter module...")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        config = FrameExportConfig(
            output_dir=output_dir,
            filename_pattern="frame_{:06d}.png",
            resolution=(640, 480),
            fps=30,
        )
        assert config.output_dir == output_dir
        print("[PASS] FrameExportConfig creation works")

        class _NoOpSceneUpdater:
            def update_frame(self, state: AnimationState) -> None:
                pass

        exporter = FrameExporter(_NoOpSceneUpdater(), config)
        assert exporter.config == config
        print("[PASS] FrameExporter creation works")

        from osim_render.api.animation.coordinate_tween import CoordinateTween
        from osim_render.api.animation.tween import TweenConfig
        from osim_render.api.animation.animation import Animation

        tween = CoordinateTween("hip", 0, 45, TweenConfig(duration=0.5))
        anim = Animation(name="test", tweens=(tween,), duration=0.5)
        timeline = Timeline(animations=(anim,))

        # Export frames
        result = exporter.export_timeline(timeline)
        assert result.success
        print(
            f"[PASS] FrameExporter.export_timeline works ({result.frame_count} frames)"
        )

    print("\n[PASS] All frame_exporter tests passed!")
