"""Unit tests for animation renderer."""

import pytest

from osim_render.api.rendering.animation_renderer import (
    AnimationRenderer,
    RenderConfig,
    _NoOpTimer,
)
from osim_render.api.animation.tween import TweenConfig
from osim_render.api.animation.coordinate_tween import CoordinateTween
from osim_render.api.animation.animation import Animation, AnimationState
from osim_render.api.animation.timeline import Timeline


class InMemorySceneUpdater:
    """Records frame updates for AnimationRenderer tests."""

    def __init__(self) -> None:
        self.last_state: AnimationState | None = None
        self.update_count: int = 0

    def update_frame(self, state: AnimationState) -> None:
        """Record frame updates."""
        self.last_state = state
        self.update_count += 1


class TestNoOpTimer:
    """Test _NoOpTimer class."""

    def test_timer_creation(self) -> None:
        """Test creating no-op timer."""
        timer = _NoOpTimer()
        assert timer is not None

    def test_set_single_shot(self) -> None:
        """Test setSingleShot doesn't crash."""
        timer = _NoOpTimer()
        timer.setSingleShot(True)
        timer.setSingleShot(False)

    def test_start_and_stop(self) -> None:
        """Test start/stop don't crash."""
        timer = _NoOpTimer()
        timer.start(16)
        timer.stop()

    def test_timeout_signal(self) -> None:
        """Test timeout signal exists and is no-op."""
        timer = _NoOpTimer()
        assert timer.timeout is not None
        # Connect should not crash
        timer.timeout.connect(lambda: None)


class TestRenderConfig:
    """Test RenderConfig class."""

    def test_default_config(self) -> None:
        """Test default render config."""
        config = RenderConfig()
        assert config.resolution == (1920, 1080)
        assert config.background_color == (0.2, 0.2, 0.2)
        assert config.anti_aliasing is True
        assert config.fps == 30

    def test_custom_config(self) -> None:
        """Test custom render config."""
        config = RenderConfig(
            resolution=(1280, 720),
            background_color=(0.0, 0.0, 0.0),
            anti_aliasing=False,
            fps=60,
        )
        assert config.resolution == (1280, 720)
        assert config.background_color == (0.0, 0.0, 0.0)
        assert config.anti_aliasing is False
        assert config.fps == 60

    def test_invalid_fps_raises(self) -> None:
        """Test invalid fps raises ValueError."""
        with pytest.raises(ValueError):
            RenderConfig(fps=0)

        with pytest.raises(ValueError):
            RenderConfig(fps=-1)


class TestAnimationRenderer:
    """Test AnimationRenderer class."""

    @pytest.fixture
    def fake_scene_manager(self) -> InMemorySceneUpdater:
        """Create fake scene manager."""
        return InMemorySceneUpdater()

    @pytest.fixture
    def simple_timeline(self) -> Timeline:
        """Create a simple timeline for testing."""
        tween = CoordinateTween(
            coordinate_name="coord1",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        animation = Animation(name="anim1", tweens=(tween,), duration=1.0)
        return Timeline(animations=(animation,))

    @pytest.fixture
    def renderer(
        self,
        fake_scene_manager: InMemorySceneUpdater,
        simple_timeline: Timeline,
    ) -> AnimationRenderer:
        """Create animation renderer with no-op timer."""
        return AnimationRenderer(
            scene_manager=fake_scene_manager,
            timer=_NoOpTimer(),
            config=RenderConfig(),
            timeline=simple_timeline,
        )

    def test_initialization(self, renderer: AnimationRenderer) -> None:
        """Test renderer initialization."""
        assert renderer.is_playing is False
        assert renderer.current_time == 0.0

    def test_duration_property(self, renderer: AnimationRenderer, simple_timeline: Timeline) -> None:
        """Test duration property."""
        assert renderer.duration == pytest.approx(simple_timeline.duration)

    def test_play_sets_playing_flag(self, renderer: AnimationRenderer) -> None:
        """Test play sets is_playing to True."""
        renderer.play()
        assert renderer.is_playing is True

    def test_pause_clears_playing_flag(self, renderer: AnimationRenderer) -> None:
        """Test pause sets is_playing to False."""
        renderer.play()
        renderer.pause()
        assert renderer.is_playing is False

    def test_stop_resets_time(self, renderer: AnimationRenderer) -> None:
        """Test stop resets to start."""
        renderer.seek(0.5)
        renderer.stop()
        assert renderer.current_time == pytest.approx(0.0)
        assert renderer.is_playing is False

    def test_seek_sets_time(self, renderer: AnimationRenderer) -> None:
        """Test seek sets current time."""
        renderer.seek(0.5)
        assert renderer.current_time == pytest.approx(0.5)

    def test_seek_clamps_below_zero(self, renderer: AnimationRenderer) -> None:
        """Test seek clamps negative time to 0."""
        renderer.seek(-0.5)
        assert renderer.current_time == pytest.approx(0.0)

    def test_seek_clamps_above_duration(self, renderer: AnimationRenderer, simple_timeline: Timeline) -> None:
        """Test seek clamps time above duration."""
        renderer.seek(2.0)
        assert renderer.current_time == pytest.approx(simple_timeline.duration)

    def test_set_playback_speed(self, renderer: AnimationRenderer) -> None:
        """Test setting playback speed."""
        renderer.set_playback_speed(2.0)
        assert renderer._playback_speed == 2.0

    def test_set_invalid_playback_speed_raises(self, renderer: AnimationRenderer) -> None:
        """Test invalid playback speed raises."""
        with pytest.raises(ValueError):
            renderer.set_playback_speed(0.0)

        with pytest.raises(ValueError):
            renderer.set_playback_speed(-1.0)

    def test_set_timeline(self, renderer: AnimationRenderer) -> None:
        """Test setting a new timeline."""
        tween = CoordinateTween(
            coordinate_name="coord2",
            start_value=0.0,
            end_value=50.0,
            config=TweenConfig(duration=2.0),
        )
        animation = Animation(name="anim2", tweens=(tween,), duration=2.0)
        new_timeline = Timeline(animations=(animation,))

        renderer.set_timeline(new_timeline)
        assert renderer.duration == pytest.approx(2.0)

    def test_frame_callback_registration(self, renderer: AnimationRenderer) -> None:
        """Test registering frame callback."""
        called: list[tuple[int, int]] = []

        def callback(frame: int, total: int) -> None:
            called.append((frame, total))

        renderer.set_frame_callback(callback)
        assert renderer._on_frame_callback is not None

    def test_no_timeline_doesnt_crash(self, fake_scene_manager: InMemorySceneUpdater) -> None:
        """Test renderer works without timeline."""
        renderer = AnimationRenderer(
            scene_manager=fake_scene_manager,
            timer=_NoOpTimer(),
        )
        assert renderer.duration == 0.0

    def test_update_frame_calls_scene_manager(
        self,
        renderer: AnimationRenderer,
        fake_scene_manager: InMemorySceneUpdater,
    ) -> None:
        """Test _update_frame calls scene manager."""
        initial_count = fake_scene_manager.update_count
        renderer.seek(0.5)
        assert fake_scene_manager.update_count > initial_count

    def test_seek_updates_scene(
        self,
        renderer: AnimationRenderer,
        fake_scene_manager: InMemorySceneUpdater,
    ) -> None:
        """Test seeking updates scene with correct state."""
        renderer.seek(0.5)
        state = fake_scene_manager.last_state
        assert state is not None
        assert state.coordinate_values["coord1"] == pytest.approx(50.0)

    def test_play_without_timeline_safe(self, fake_scene_manager: InMemorySceneUpdater) -> None:
        """Test playing without timeline is safe."""
        renderer = AnimationRenderer(
            scene_manager=fake_scene_manager,
            timer=_NoOpTimer(),
        )
        renderer.play()  # Should not crash

    def test_seek_without_timeline_safe(self, fake_scene_manager: InMemorySceneUpdater) -> None:
        """Test seeking without timeline is safe."""
        renderer = AnimationRenderer(
            scene_manager=fake_scene_manager,
            timer=_NoOpTimer(),
        )
        renderer.seek(1.0)  # Should not crash
        assert renderer.current_time == 0.0  # No timeline, so no seek


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
