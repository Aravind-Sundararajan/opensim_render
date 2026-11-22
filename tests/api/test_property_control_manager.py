import pytest
import opensim
from pathlib import Path

from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.managers.visualization_state_manager import VisualizationStateManager
from osim_render.api.managers.property_control_manager import PropertyControlManager
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.tooling_paths import get_opensim_geometry_root
from osim_render.api.animation.value_types import ColorValue

# arm26.osim ships with every OpenSim installation
_ARM26 = Path(opensim.__file__).parent / "tests" / "arm26.osim"
_GEOMETRY_ROOT = get_opensim_geometry_root()
_GEOMETRY = str(_GEOMETRY_ROOT)

# Without the shared geometry meshes no body actors are built, and every
# assertion here degrades into an unexplained "actor not found". Skip loudly
# instead. See .env.example for OSIM_RENDER_OPENSIM_GEOMETRY_DIR.
pytestmark = pytest.mark.skipif(
    not _GEOMETRY_ROOT.is_dir(),
    reason=(
        f"OpenSim shared geometry not found at {_GEOMETRY_ROOT}. "
        "Set OSIM_RENDER_OPENSIM_GEOMETRY_DIR to an OpenSim Geometry directory."
    ),
)


@pytest.fixture(scope="module")
def scene_manager() -> SceneManager:
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    model_manager.load_model(_ARM26)
    offscreen = OffscreenRenderer(resolution=(320, 240))
    sm = SceneManager(model_manager, _ARM26, (_GEOMETRY,))
    sm.create_scene(renderer=offscreen.renderer)
    return sm


@pytest.fixture(scope="module")
def vis_state(scene_manager: SceneManager) -> VisualizationStateManager:
    scene = scene_manager.get_scene()
    assert scene is not None
    vs = VisualizationStateManager()
    vs.initialize_category("bodies", list(scene.actors.keys()))
    if scene.muscle_actors:
        vs.initialize_category("muscles", list(scene.muscle_actors.keys()))
    return vs


@pytest.fixture(scope="module")
def pcm(scene_manager: SceneManager, vis_state: VisualizationStateManager) -> PropertyControlManager:
    return PropertyControlManager(scene_manager, vis_state, EventBus())


class TestFindActor:
    def test_finds_body_by_name(self, pcm: PropertyControlManager) -> None:
        actor = pcm.find_actor("r_humerus")
        assert actor is not None

    def test_finds_body_with_category(self, pcm: PropertyControlManager) -> None:
        actor = pcm.find_actor("r_humerus", category="bodies")
        assert actor is not None

    def test_finds_muscle_by_name(self, pcm: PropertyControlManager) -> None:
        actor = pcm.find_actor("BIClong")
        assert actor is not None

    def test_finds_muscle_with_category(self, pcm: PropertyControlManager) -> None:
        actor = pcm.find_actor("BIClong", category="muscles")
        assert actor is not None

    def test_returns_none_for_unknown_actor(self, pcm: PropertyControlManager) -> None:
        assert pcm.find_actor("does_not_exist") is None

    def test_returns_none_for_wrong_category(self, pcm: PropertyControlManager) -> None:
        # r_humerus is a body, not a muscle
        assert pcm.find_actor("r_humerus", category="muscles") is None


class TestSetVisibility:
    def test_hide_body_actor(self, pcm: PropertyControlManager) -> None:
        result = pcm.set_visibility("r_humerus", False, category="bodies")
        assert result is True
        actor = pcm.find_actor("r_humerus")
        assert actor is not None
        assert actor.GetVisibility() == 0

    def test_show_body_actor(self, pcm: PropertyControlManager) -> None:
        pcm.set_visibility("r_humerus", False, category="bodies")
        result = pcm.set_visibility("r_humerus", True, category="bodies")
        assert result is True
        actor = pcm.find_actor("r_humerus")
        assert actor is not None
        assert actor.GetVisibility() == 1

    def test_syncs_vis_state_manager(self, pcm: PropertyControlManager, vis_state: VisualizationStateManager) -> None:
        pcm.set_visibility("r_humerus", False, category="bodies")
        assert vis_state.get_visibility("bodies", "r_humerus") is False
        pcm.set_visibility("r_humerus", True, category="bodies")
        assert vis_state.get_visibility("bodies", "r_humerus") is True

    def test_returns_false_for_unknown_actor(self, pcm: PropertyControlManager) -> None:
        assert pcm.set_visibility("ghost", True) is False


class TestSetOpacity:
    def test_set_partial_opacity(self, pcm: PropertyControlManager) -> None:
        result = pcm.set_opacity("r_humerus", 0.4)
        assert result is True
        actor = pcm.find_actor("r_humerus")
        assert actor is not None
        assert abs(actor.GetProperty().GetOpacity() - 0.4) < 1e-6

    def test_set_full_opacity(self, pcm: PropertyControlManager) -> None:
        pcm.set_opacity("r_humerus", 0.4)
        pcm.set_opacity("r_humerus", 1.0)
        actor = pcm.find_actor("r_humerus")
        assert actor is not None
        assert abs(actor.GetProperty().GetOpacity() - 1.0) < 1e-6

    def test_clamps_opacity_above_one(self, pcm: PropertyControlManager) -> None:
        pcm.set_opacity("r_humerus", 1.5)
        actor = pcm.find_actor("r_humerus")
        assert actor is not None
        assert actor.GetProperty().GetOpacity() <= 1.0

    def test_clamps_opacity_below_zero(self, pcm: PropertyControlManager) -> None:
        pcm.set_opacity("r_humerus", -0.5)
        actor = pcm.find_actor("r_humerus")
        assert actor is not None
        assert actor.GetProperty().GetOpacity() >= 0.0


class TestSetColor:
    def test_set_color_tuple(self, pcm: PropertyControlManager) -> None:
        result = pcm.set_color("r_humerus", (1.0, 0.0, 0.0))
        assert result is True
        actor = pcm.find_actor("r_humerus")
        assert actor is not None
        r, g, b = actor.GetProperty().GetColor()
        assert abs(r - 1.0) < 1e-6
        assert abs(g - 0.0) < 1e-6
        assert abs(b - 0.0) < 1e-6

    def test_set_color_value_object(self, pcm: PropertyControlManager) -> None:
        color = ColorValue(r=0.0, g=1.0, b=0.0, a=0.7)
        result = pcm.set_color("r_humerus", color)
        assert result is True
        actor = pcm.find_actor("r_humerus")
        assert actor is not None
        r, g, b = actor.GetProperty().GetColor()
        assert abs(g - 1.0) < 1e-6
        # ColorValue with alpha should also set opacity
        assert abs(actor.GetProperty().GetOpacity() - 0.7) < 1e-6


class TestSetCategoryVisibility:
    def test_hide_all_bodies(self, pcm: PropertyControlManager, scene_manager: SceneManager) -> None:
        pcm.set_category_visibility("bodies", False)
        scene = scene_manager.get_scene()
        assert scene is not None
        for actor in scene.actors.values():
            assert actor.GetVisibility() == 0

    def test_show_all_bodies(self, pcm: PropertyControlManager, scene_manager: SceneManager) -> None:
        pcm.set_category_visibility("bodies", False)
        pcm.set_category_visibility("bodies", True)
        scene = scene_manager.get_scene()
        assert scene is not None
        for actor in scene.actors.values():
            assert actor.GetVisibility() == 1

    def test_hide_all_muscles(self, pcm: PropertyControlManager, scene_manager: SceneManager) -> None:
        pcm.set_category_visibility("muscles", False)
        scene = scene_manager.get_scene()
        assert scene is not None
        if scene.muscle_actors:
            for actor in scene.muscle_actors.values():
                assert actor.GetVisibility() == 0


class TestActorRegistry:
    def test_registry_contains_all_bodies(self, pcm: PropertyControlManager, scene_manager: SceneManager) -> None:
        pcm._rebuild_actor_registry()
        scene = scene_manager.get_scene()
        assert scene is not None
        for body_name in scene.actors:
            assert body_name in pcm._actor_registry

    def test_registry_contains_all_muscles(self, pcm: PropertyControlManager, scene_manager: SceneManager) -> None:
        pcm._rebuild_actor_registry()
        scene = scene_manager.get_scene()
        assert scene is not None
        if scene.muscle_actors:
            for muscle_name in scene.muscle_actors:
                assert muscle_name in pcm._actor_registry

    def test_registry_maps_correct_category(self, pcm: PropertyControlManager) -> None:
        pcm._rebuild_actor_registry()
        categories = [cat for cat, _ in pcm._actor_registry["r_humerus"]]
        assert "bodies" in categories
        categories = [cat for cat, _ in pcm._actor_registry["BIClong"]]
        assert "muscles" in categories
