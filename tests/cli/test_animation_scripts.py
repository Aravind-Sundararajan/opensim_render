"""Tests that all animation scripts execute and produce valid timelines."""

from pathlib import Path

import pytest

from osim_render.api.animation.script_executor import ScriptExecutor
from osim_render.api.animation.value_types import CameraState
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.animation.animation import AnimationState
from osim_render.api.rendering.scene import RenderScene


class InMemorySceneUpdater:
    """Records frame updates — satisfies _SceneUpdater Protocol for exporters."""

    def update_frame(self, state: AnimationState) -> None:
        """Accept a frame update without rendering."""
        pass


class InMemorySceneManager:
    """Real headless scene manager double for animation-script tests.

    Implements the scene-query surface the animation ``Scene`` and the scripts
    actually use — ``get_camera_state``, ``get_scene``, and
    ``set_camera_follow_body`` — without building a VTK render scene.

    ``get_scene()`` returns ``None``, exactly as a real ``SceneManager`` does
    before ``create_scene()`` is called, so scripts fall back to empty actor
    discovery and still build valid timelines from their unconditional
    coordinate and camera animations. ``get_camera_state()`` returns the same
    default front view the ``Scene`` uses when no scene manager is present, so
    scripts that only query the camera behave identically.
    """

    def __init__(self) -> None:
        """Initialize with no built scene and no followed body."""
        self.followed_body: str | None = None

    def get_camera_state(self) -> CameraState:
        """Return the default front-view camera (unbuilt-scene default)."""
        return CameraState.front_view()

    def get_scene(self) -> RenderScene | None:
        """Return None — no VTK scene has been built in a headless test."""
        return None

    def set_camera_follow_body(self, body_name: str) -> None:
        """Record the followed body without moving a real camera."""
        self.followed_body = body_name


ANIMATION_SCRIPTS_DIR = Path(
    __file__).parent.parent.parent / "animation_scripts"


def _collect_scripts(prefix_exclude: str = "M") -> list[Path]:
    """Return all animation script paths, excluding motion-dependent M-series."""
    return sorted(
        p for p in ANIMATION_SCRIPTS_DIR.glob("*.py")
        if not p.name.startswith(prefix_exclude)
    )


@pytest.fixture
def executor() -> ScriptExecutor:
    """Create script executor with real ModelManager."""
    return ScriptExecutor(
        ModelManager(EventBus()),
        InMemorySceneManager(),
        EventBus(),
    )


SCRIPTS = _collect_scripts()


@pytest.mark.parametrize("script_path", SCRIPTS, ids=[p.name for p in SCRIPTS])
def test_script_executes(executor: ScriptExecutor, script_path: Path) -> None:
    """Each animation script must execute without errors and produce a Timeline."""
    code = script_path.read_text(encoding="utf-8")
    result = executor.execute(code, script_name=script_path.name)

    assert result.success
    assert result.timeline is not None
    assert result.timeline.duration > 0, (
        f"{script_path.name}: timeline.duration must be > 0, got {result.timeline.duration}"
    )


@pytest.mark.parametrize("script_path", SCRIPTS, ids=[p.name for p in SCRIPTS])
def test_script_renders_frames(executor: ScriptExecutor, script_path: Path, tmp_path: Path) -> None:
    """Each script timeline must render to PNG frames without errors."""
    from osim_render.api.rendering.frame_exporter import FrameExporter, FrameExportConfig

    code = script_path.read_text(encoding="utf-8")
    result = executor.execute(code, script_name=script_path.name)

    assert result.timeline is not None
    config = FrameExportConfig(
        output_dir=tmp_path,
        resolution=(320, 240),
        fps=5,
    )
    exporter = FrameExporter(InMemorySceneUpdater(), config)
    export = exporter.export_timeline(result.timeline)

    assert export.success
    assert export.frame_count > 0
    assert all(p.exists() for p in export.frame_paths)


@pytest.mark.parametrize("script_path", SCRIPTS, ids=[p.name for p in SCRIPTS])
def test_script_renders_video(executor: ScriptExecutor, script_path: Path, tmp_path: Path) -> None:
    """Each script timeline must encode to a video file (uses bundled imageio-ffmpeg)."""
    from osim_render.api.rendering.video_exporter import VideoExporter, VideoExportConfig

    code = script_path.read_text(encoding="utf-8")
    result = executor.execute(code, script_name=script_path.name)

    assert result.timeline is not None
    config = VideoExportConfig(
        output_file=tmp_path / f"{script_path.stem}.mp4",
        resolution=(320, 240),
        fps=5,
        quality="low",
    )
    exporter = VideoExporter(InMemorySceneUpdater(), config)
    export = exporter.export_timeline(result.timeline)

    assert export.success
    assert config.output_file.exists()
    assert config.output_file.stat().st_size > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
