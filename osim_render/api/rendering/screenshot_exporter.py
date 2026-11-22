"""
High-resolution screenshot export.

Exports individual frames as high-resolution images (default 4K) in various formats.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Protocol, cast

from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.animation.animation import AnimationState


class _SceneUpdater(Protocol):
    """Supports frame updates for rendering."""

    def update_frame(self, state: AnimationState) -> None: ...


@dataclass(frozen=True)
class ScreenshotExportConfig:
    """
    Configuration for screenshot export.

    Attributes:
        output_path: Path to save screenshot (with extension)
        resolution: Resolution as (width, height) in pixels
        format: Image format ('png', 'jpg', 'tiff')
        jpg_quality: JPEG quality 0-100 (if format is jpg)
        transparent_background: If True, render with a transparent background
            instead of background_color (PNG only)
        background_color: Background RGB color in [0, 1], used when
            transparent_background is False
    """

    output_path: Path
    resolution: tuple[int, int] = (3840, 2160)  # 4K default
    format: Literal["png", "jpg", "tiff"] = "png"
    jpg_quality: int = 95
    transparent_background: bool = False
    background_color: tuple[float, float, float] = (0.2, 0.2, 0.2)

    def __post_init__(self) -> None:
        """Validate config."""
        if self.format not in ("png", "jpg", "tiff"):
            raise ValueError(f"Unsupported format: {self.format}")
        if self.format == "jpg" and (self.jpg_quality < 0 or self.jpg_quality > 100):
            raise ValueError(
                f"jpg_quality must be 0-100, got {self.jpg_quality}")
        if self.transparent_background and self.format != "png":
            raise ValueError("transparent_background requires format='png'")


@dataclass(frozen=True)
class ScreenshotResult:
    """
    Result of screenshot export.

    Attributes:
        success: Whether export succeeded
        output_path: Path to exported screenshot
        resolution: Output resolution
        error: Error message if failed
    """

    success: bool
    output_path: Path
    resolution: tuple[int, int] = (0, 0)
    error: Optional[str] = None


class ScreenshotExporter:
    """
    Exports high-resolution screenshots.

    Provides easy export of animation states as high-res images.

    Attributes:
        scene_manager: Manager for scene rendering
        config: ScreenshotExportConfig with output settings
        renderer: OffscreenRenderer for image generation
    """

    def __init__(self, scene_manager: _SceneUpdater, config: Optional[ScreenshotExportConfig] = None):
        """
        Initialize screenshot exporter.

        Args:
            scene_manager: Manager for scene rendering and updates
            config: ScreenshotExportConfig (uses 4K PNG by default)
        """
        if config is None:
            config = ScreenshotExportConfig(output_path=Path("screenshot.png"))

        self.scene_manager = scene_manager
        self.config = config
        self.renderer = OffscreenRenderer(
            resolution=config.resolution,
            background_color=config.background_color,
            transparent_background=config.transparent_background,
        )

    def export_frame(self, state: AnimationState) -> ScreenshotResult:
        """
        Export a single animation frame as a screenshot.

        Args:
            state: AnimationState to render

        Returns:
            ScreenshotResult with export status

        Raises:
            AttributeError: If scene_manager lacks update_frame method
            RuntimeError: If frame saving fails
        """
        self.scene_manager.update_frame(state)

        self.renderer.save_frame(state, self.config.output_path)

        return ScreenshotResult(
            success=True,
            output_path=self.config.output_path,
            resolution=self.config.resolution,
        )

    @staticmethod
    def create_for_path(
        scene_manager: _SceneUpdater, output_path: Path, resolution: tuple[int, int] = (3840, 2160)
    ) -> "ScreenshotExporter":
        """
        Create a screenshot exporter for a specific output path.

        Convenience method that infers format from file extension.

        Args:
            scene_manager: Manager for scene rendering
            output_path: Output file path
            resolution: Resolution (default 4K)

        Returns:
            ScreenshotExporter configured for the path

        Examples:
            >>> exporter = ScreenshotExporter.create_for_path(
            ...     scene_manager, Path("output/frame.png")
            ... )
        """
        # Infer format from extension
        ext = output_path.suffix.lower().lstrip(".")
        if ext not in ("png", "jpg", "jpeg", "tiff"):
            ext = "png"

        if ext == "jpeg":
            ext = "jpg"

        config = ScreenshotExportConfig(
            output_path=output_path,
            resolution=resolution,
            format=cast(Literal["png", "jpg", "tiff"], ext),
        )

        return ScreenshotExporter(scene_manager, config)


if __name__ == "__main__":
    # Smoke test
    print("Testing screenshot_exporter module...")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "screenshot.png"

        config = ScreenshotExportConfig(
            output_path=output_path,
            resolution=(1920, 1080),
            format="png",
        )
        assert config.output_path == output_path
        print("[PASS] ScreenshotExportConfig creation works")

        class _NoOpSceneUpdater:
            def update_frame(self, state: AnimationState) -> None:
                pass

        _updater = _NoOpSceneUpdater()
        exporter = ScreenshotExporter(_updater, config)
        assert exporter.config == config
        print("[PASS] ScreenshotExporter creation works")

        state = AnimationState(
            time=0.0,
            coordinate_values={"hip": 0.0},
            camera_state=None,
            actor_properties={},
        )

        # Try export (will produce mostly empty image)
        result = exporter.export_frame(state)
        if result.success:
            print("[PASS] ScreenshotExporter.export_frame works")
        else:
            print(
                f"[WARN] ScreenshotExporter.export_frame failed: {result.error}")

        # Test create_for_path
        exporter2 = ScreenshotExporter.create_for_path(
            _updater,
            Path(tmpdir) / "test.jpg",
        )
        assert exporter2.config.format == "jpg"
        print("[PASS] ScreenshotExporter.create_for_path works")

    print("\n[PASS] All screenshot_exporter tests passed!")
