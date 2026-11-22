"""
Video export via imageio-ffmpeg.

Exports animations to MP4 and other video formats using the imageio-ffmpeg
package, which bundles the ffmpeg binary — no system installation required.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Protocol

import imageio

from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.animation.animation import AnimationState
from osim_render.api.animation.timeline import Timeline


class _SceneUpdater(Protocol):
    """Supports frame updates for rendering."""

    def update_frame(self, state: AnimationState) -> None: ...


@dataclass(frozen=True)
class VideoExportConfig:
    """
    Configuration for video export.

    Attributes:
        output_file: Path to output video file
        resolution: Output resolution as (width, height) in pixels
        fps: Frames per second
        codec: Video codec (e.g., 'libx264' for H.264)
        quality: Quality level ('high', 'medium', 'low')
    """

    output_file: Path
    resolution: tuple[int, int] = (1920, 1080)
    fps: int = 30
    codec: str = "libx264"
    quality: str = "medium"

    def __post_init__(self) -> None:
        """Validate config."""
        if self.fps <= 0:
            raise ValueError(f"fps must be positive, got {self.fps}")
        if self.quality not in ("high", "medium", "low"):
            raise ValueError(f"quality must be high/medium/low, got {self.quality}")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def get_crf(self) -> int:
        """Return CRF value for H.264 (lower = better quality)."""
        return {"high": 18, "medium": 23, "low": 28}[self.quality]


@dataclass(frozen=True)
class ExportResult:
    """
    Result of video export operation.

    Attributes:
        success: Whether export completed successfully
        output_file: Path to exported video file
        frame_count: Number of frames encoded
        error: Error message if export failed
        duration: Duration of exported video in seconds
    """

    success: bool
    output_file: Path
    frame_count: int = 0
    error: Optional[str] = None
    duration: float = 0.0


class VideoExporter:
    """
    Exports animations to video files using imageio-ffmpeg.

    No system ffmpeg installation required — imageio-ffmpeg bundles the binary.

    Attributes:
        scene_manager: Manager for scene rendering
        config: VideoExportConfig with output settings
        renderer: OffscreenRenderer for frame generation
    """

    def __init__(
        self,
        scene_manager: _SceneUpdater,
        config: VideoExportConfig,
        renderer: Optional[OffscreenRenderer] = None,
    ):
        """
        Initialize video exporter.

        Args:
            scene_manager: Manager for scene rendering and updates
            config: VideoExportConfig with output settings
            renderer: Optional shared OffscreenRenderer. If None, a new one is
                created. Pass the same renderer used to build the SceneManager so
                that model actors are visible in the exported video.
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
        Export timeline to video file.

        Args:
            timeline: Timeline to export
            progress_callback: Optional function(current_frame, total_frames) for progress

        Returns:
            ExportResult with export status and file info

        Raises:
            AttributeError: If scene_manager or renderer lacks required methods
        """
        frames_iter, frame_count = timeline.iterate_frames_count(fps=self.config.fps)

        output_params = ["-crf", str(self.config.get_crf()), "-preset", "medium"]

        with imageio.get_writer(
            str(self.config.output_file),
            fps=self.config.fps,
            codec=self.config.codec,
            output_params=output_params,
        ) as writer:
            for frame_num, state in enumerate(frames_iter):
                if progress_callback:
                    progress_callback(frame_num, frame_count)

                self.scene_manager.update_frame(state)
                frame_array = self.renderer.render_frame(state)
                writer.append_data(frame_array)

        if progress_callback:
            progress_callback(frame_count, frame_count)

        if not self.config.output_file.exists():
            raise RuntimeError(
                f"imageio did not produce output file: {self.config.output_file}"
            )

        return ExportResult(
            success=True,
            output_file=self.config.output_file,
            frame_count=frame_count,
            duration=timeline.duration,
        )


if __name__ == "__main__":
    import tempfile

    print("Testing video_exporter module...")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_output.mp4"

        config = VideoExportConfig(
            output_file=output_path,
            resolution=(640, 480),
            fps=30,
            quality="low",
        )
        assert config.get_crf() == 28
        print(f"[PASS] VideoExportConfig creation works (CRF={config.get_crf()})")

        class FakeSceneManager:
            def update_frame(self, state: AnimationState) -> None:
                pass

        exporter = VideoExporter(FakeSceneManager(), config)
        assert exporter.config == config
        print("[PASS] VideoExporter creation works")

    print("\n[PASS] All video_exporter tests passed!")
