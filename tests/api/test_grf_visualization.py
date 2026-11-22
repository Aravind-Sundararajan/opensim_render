"""Tests for drawing ground reaction forces in the scene.

Ground reactions are the first thing rendered from recorded data rather than
from the model state, so these cover the time channel as well as the arrows.
"""

from pathlib import Path

import opensim
import pytest

from osim_render.api.loaders.grf_loader import load_ground_reactions
from osim_render.api.loaders.motion_loader import MotionFrame
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.managers.visualization_state_manager import (
    VisualizationStateManager,
)
from osim_render.api.rendering.grf_visualizer import GroundReactionVisualizer
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager

_GAIT2354 = Path("resources/Models/Gait2354_Simbody")
_MODEL = _GAIT2354 / "gait2354_simbody.osim"
_XML = _GAIT2354 / "subject01_walk1_grf.xml"

pytestmark = pytest.mark.skipif(
    not _XML.is_file() or not _MODEL.is_file(),
    reason=f"trial data not found in {_GAIT2354}",
)


@pytest.fixture
def scene() -> SceneManager:
    """A rendered gait scene with no ground reactions loaded yet."""
    opensim.Model.setDebugLevel(-1)
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    model_manager.load_model(_MODEL)

    offscreen = OffscreenRenderer(resolution=(200, 200))
    scene_manager = SceneManager(model_manager, _MODEL)
    scene_manager.create_scene(renderer=offscreen.renderer)
    scene_manager._realize_position()
    return scene_manager


def _visible(scene_manager: SceneManager) -> set[str]:
    """Names of ground reaction arrows currently visible."""
    actors = scene_manager.scene.ground_reaction_actors or {}
    return {name for name, actor in actors.items() if actor.GetVisibility()}


def _coordinates(scene_manager: SceneManager) -> dict[str, float]:
    """A neutral pose for driving frames."""
    return {
        coordinate.getName(): 0.0
        for coordinate in scene_manager.opensim_model.getCoordinateSet()
    }


class TestVisualizerArrows:
    """The visualizer draws recorded forces at their centre of pressure."""

    @pytest.fixture
    def visualizer(self, scene) -> GroundReactionVisualizer:
        """A visualizer holding the trial's ground reactions."""
        visualizer = GroundReactionVisualizer(
            scene.opensim_model, scene.state
        )
        visualizer.set_data(load_ground_reactions(_XML))
        return visualizer

    def test_creates_one_arrow_per_source(self, visualizer) -> None:
        actors = visualizer.create_actors()

        assert sorted(actors) == ["left", "right"]

    def test_arrow_sits_at_the_centre_of_pressure(self, visualizer) -> None:
        actors = visualizer.create_actors()
        source = visualizer.data.sources[0]
        sample = visualizer.data.sample(source, 1.2)
        assert sample is not None

        visualizer.update(actors, 1.2)

        base = actors[source.name].GetUserTransform().TransformPoint(0.0, 0.0, 0.0)
        assert base == pytest.approx(sample.point, abs=1e-9)

    def test_arrow_points_along_the_measured_force(self, visualizer) -> None:
        actors = visualizer.create_actors()
        source = visualizer.data.sources[0]
        sample = visualizer.data.sample(source, 1.2)
        assert sample is not None

        visualizer.update(actors, 1.2)

        transform = actors[source.name].GetUserTransform()
        base = transform.TransformPoint(0.0, 0.0, 0.0)
        tip = transform.TransformPoint(1.0, 0.0, 0.0)
        along = [tip[axis] - base[axis] for axis in range(3)]

        length = sum(value * value for value in along) ** 0.5
        expected = [value / sample.magnitude for value in sample.force]
        assert [value / length for value in along] == pytest.approx(expected, abs=1e-6)

    def test_unloaded_plate_is_hidden(self, visualizer) -> None:
        actors = visualizer.create_actors()
        source = visualizer.data.sources[0]
        quiet = next(
            time
            for time in visualizer.data.times
            if visualizer.data.sample(source, time).magnitude < 1.0
        )

        visualizer.update(actors, quiet)

        assert not actors[source.name].GetVisibility()

    def test_time_outside_the_recording_hides_everything(self, visualizer) -> None:
        actors = visualizer.create_actors()

        visualizer.update(actors, visualizer.data.end_time + 5.0)

        assert not any(actor.GetVisibility() for actor in actors.values())

    def test_visibility_filter_is_respected(self, visualizer) -> None:
        actors = visualizer.create_actors()

        visualizer.update(actors, 1.2, visible_sources={"right"})

        assert actors["right"].GetVisibility()
        assert not actors["left"].GetVisibility()

    def test_no_data_hides_everything(self, scene) -> None:
        visualizer = GroundReactionVisualizer(scene.opensim_model, scene.state)
        visualizer.set_data(load_ground_reactions(_XML))
        actors = visualizer.create_actors()
        visualizer.update(actors, 1.2)

        visualizer.set_data(None)
        visualizer.update(actors, 1.2)

        assert not any(actor.GetVisibility() for actor in actors.values())


class TestSceneIntegration:
    """Ground reactions load into a live scene and follow playback time."""

    def test_loading_adds_arrows_to_the_scene(self, scene) -> None:
        names = scene.load_ground_reactions(_XML)

        assert names == ("right", "left")
        assert sorted(scene.scene.ground_reaction_actors) == ["left", "right"]

    def test_arrows_start_hidden(self, scene) -> None:
        scene.load_ground_reactions(_XML)

        assert _visible(scene) == set()

    def test_loading_before_a_scene_exists_is_reported(self) -> None:
        opensim.Model.setDebugLevel(-1)
        event_bus = EventBus()
        model_manager = ModelManager(event_bus)
        model_manager.load_model(_MODEL)
        bare = SceneManager(model_manager, _MODEL)

        with pytest.raises(RuntimeError, match="before a scene exists"):
            bare.load_ground_reactions(_XML)

    def test_clearing_removes_the_arrows(self, scene) -> None:
        scene.load_ground_reactions(_XML)

        scene.clear_ground_reactions()

        assert scene.scene.ground_reaction_actors == {}

    def test_reloading_replaces_rather_than_accumulates(self, scene) -> None:
        scene.load_ground_reactions(_XML)
        scene.load_ground_reactions(_XML)

        assert len(scene.scene.ground_reaction_actors) == 2


class TestPlaybackTime:
    """The scene tracks the time of the frame it is showing."""

    def test_update_frame_records_the_time(self, scene) -> None:
        scene.update_frame(MotionFrame(time=0.75, coordinate_values=_coordinates(scene)))

        assert scene.current_time == pytest.approx(0.75)

    def test_update_frame_stamps_the_opensim_state(self, scene) -> None:
        scene.update_frame(MotionFrame(time=0.75, coordinate_values=_coordinates(scene)))

        assert scene.state.getTime() == pytest.approx(0.75)

    def test_arrows_follow_playback_time(self, scene) -> None:
        names = scene.load_ground_reactions(_XML)
        state = VisualizationStateManager()
        state.initialize_category("ground_reactions", list(names), default_visible=True)
        scene.set_visualization_state(state)
        coordinates = _coordinates(scene)

        seen = []
        for time in (0.0, 0.25, 0.6, 0.9):
            scene.update_frame(MotionFrame(time=time, coordinate_values=coordinates))
            seen.append(frozenset(_visible(scene)))

        # Walking alternates support, so the visible set must change over time.
        assert len(set(seen)) > 1

    def test_toggle_survives_repeated_frames(self, scene) -> None:
        names = scene.load_ground_reactions(_XML)
        state = VisualizationStateManager()
        state.initialize_category("ground_reactions", list(names), default_visible=True)
        scene.set_visualization_state(state)
        coordinates = _coordinates(scene)

        state.set_all_visibility("ground_reactions", False)
        for _ in range(4):
            scene.update_frame(MotionFrame(time=0.1, coordinate_values=coordinates))

        assert _visible(scene) == set()

    def test_single_source_can_be_shown(self, scene) -> None:
        names = scene.load_ground_reactions(_XML)
        state = VisualizationStateManager()
        state.initialize_category("ground_reactions", list(names), default_visible=False)
        scene.set_visualization_state(state)
        state.set_visibility("ground_reactions", "right", True)

        scene.update_frame(MotionFrame(time=1.2, coordinate_values=_coordinates(scene)))

        assert _visible(scene) == {"right"}
