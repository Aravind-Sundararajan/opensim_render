"""Tests that per-frame contact force updates respect the visibility toggle.

Contact force arrows are the only actors whose visibility is rewritten on every
frame, so they are uniquely able to override the user's toggle. These tests
build a real SmoothSphereHalfSpaceForce model rather than relying on a shipped
one, because none of the bundled models use that force type.
"""

from pathlib import Path

import opensim
import pytest

from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.managers.visualization_state_manager import (
    VisualizationStateManager,
)
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager

SPHERE_COUNT = 3


def build_contact_model(path: Path, sphere_count: int = SPHERE_COUNT) -> Path:
    """Write a minimal model with SmoothSphereHalfSpaceForce contacts.

    Args:
        path: Destination .osim path
        sphere_count: Number of contact spheres and forces to create

    Returns:
        The path written
    """
    model = opensim.Model()
    model.setName("contact_probe")

    block = opensim.Body("block", 1.0, opensim.Vec3(0), opensim.Inertia(0.1, 0.1, 0.1))
    model.addBody(block)
    model.addJoint(opensim.FreeJoint("ground_block", model.getGround(), block))

    floor = opensim.ContactHalfSpace(
        opensim.Vec3(0),
        opensim.Vec3(0, 0, -1.5707963267948966),
        model.getGround(),
        "floor",
    )
    model.addContactGeometry(floor)

    for index in range(sphere_count):
        sphere = opensim.ContactSphere(
            0.03, opensim.Vec3(0.05 * index, -0.05, 0.0), block, f"sphere_{index}"
        )
        model.addContactGeometry(sphere)

        force = opensim.SmoothSphereHalfSpaceForce(f"contact_{index}", sphere, floor)
        force.set_stiffness(1e6)
        force.set_dissipation(2.0)
        force.set_static_friction(0.8)
        force.set_dynamic_friction(0.8)
        force.set_viscous_friction(0.5)
        model.addForce(force)

    model.finalizeConnections()
    model.initSystem()
    model.printToXML(str(path))
    return path


@pytest.fixture(scope="module")
def contact_model(tmp_path_factory) -> Path:
    """A real model containing SmoothSphereHalfSpaceForce contacts."""
    opensim.Model.setDebugLevel(-1)
    directory = tmp_path_factory.mktemp("contact")
    return build_contact_model(directory / "contact_probe.osim")


@pytest.fixture
def scene(contact_model: Path):
    """A rendered scene with contact force actors and a visibility state."""
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    model_manager.load_model(contact_model)

    offscreen = OffscreenRenderer(resolution=(200, 200))
    scene_manager = SceneManager(model_manager, contact_model)
    scene_manager.create_scene(renderer=offscreen.renderer)
    scene_manager._realize_position()
    return scene_manager


def _visible(scene_manager: SceneManager) -> set[str]:
    """Names of contact force actors currently visible."""
    actors = scene_manager.scene.contact_force_actors or {}
    return {name for name, actor in actors.items() if actor.GetVisibility()}


def _show_all(scene_manager: SceneManager) -> None:
    """Turn every contact force actor on."""
    for actor in (scene_manager.scene.contact_force_actors or {}).values():
        actor.SetVisibility(True)


class TestContactForceActorsExist:
    """The fixture model really does produce contact force arrows."""

    def test_actors_are_built(self, scene) -> None:
        assert len(scene.scene.contact_force_actors or {}) == SPHERE_COUNT

    def test_actors_start_hidden(self, scene) -> None:
        # scene_builder hides them until the user opts in.
        assert _visible(scene) == set()


class TestVisibilityIsRespectedOnUpdate:
    """A frame update must not override the user's toggle."""

    def test_hidden_force_stays_hidden(self, scene) -> None:
        state = VisualizationStateManager()
        names = list(scene.scene.contact_force_actors)
        state.initialize_category("contact_forces", names, default_visible=True)
        scene.set_visualization_state(state)
        _show_all(scene)

        hidden = names[0]
        state.set_visibility("contact_forces", hidden, False)
        scene.scene.contact_force_actors[hidden].SetVisibility(False)

        scene.update_contact_forces()

        assert hidden not in _visible(scene)

    def test_other_forces_remain_visible(self, scene) -> None:
        state = VisualizationStateManager()
        names = list(scene.scene.contact_force_actors)
        state.initialize_category("contact_forces", names, default_visible=True)
        scene.set_visualization_state(state)
        _show_all(scene)

        hidden = names[0]
        state.set_visibility("contact_forces", hidden, False)

        scene.update_contact_forces()

        assert _visible(scene) == set(names[1:])

    def test_hiding_all_survives_repeated_updates(self, scene) -> None:
        state = VisualizationStateManager()
        names = list(scene.scene.contact_force_actors)
        state.initialize_category("contact_forces", names, default_visible=True)
        scene.set_visualization_state(state)
        _show_all(scene)

        state.set_all_visibility("contact_forces", False)
        for _ in range(5):
            scene.update_contact_forces()

        assert _visible(scene) == set()

    def test_showing_all_survives_repeated_updates(self, scene) -> None:
        state = VisualizationStateManager()
        names = list(scene.scene.contact_force_actors)
        state.initialize_category("contact_forces", names, default_visible=True)
        scene.set_visualization_state(state)
        _show_all(scene)

        for _ in range(5):
            scene.update_contact_forces()

        assert _visible(scene) == set(names)

    def test_update_all_actor_positions_also_respects_state(self, scene) -> None:
        """The bug surfaced through the full update pass, not just one call."""
        state = VisualizationStateManager()
        names = list(scene.scene.contact_force_actors)
        state.initialize_category("contact_forces", names, default_visible=True)
        scene.set_visualization_state(state)
        _show_all(scene)

        state.set_all_visibility("contact_forces", False)
        scene.update_all_actor_positions()

        assert _visible(scene) == set()


class TestUnmanagedSceneStillRenders:
    """Without a visibility state, the physics alone decides."""

    def test_forces_show_when_no_state_attached(self, scene) -> None:
        assert scene.visualization_state is None
        _show_all(scene)

        scene.update_contact_forces()

        assert _visible(scene) == set(scene.scene.contact_force_actors)

    def test_visualizer_defaults_to_showing_active_forces(self, scene) -> None:
        actors = scene.scene.contact_force_actors
        metadata = scene.scene.contact_force_metadata
        _show_all(scene)

        scene.contact_force_visualizer.update_contact_forces(
            actors, metadata, visible_forces=None
        )

        assert _visible(scene) == set(actors)


_TOY_LANDING = Path("resources/Models/ToyDropLanding/ToyLandingModel.osim")


@pytest.mark.skipif(
    not _TOY_LANDING.is_file(), reason=f"model not found at {_TOY_LANDING}"
)
class TestHuntCrossleyArrows:
    """The bundled HuntCrossley models produce toggleable arrows.

    Before contact points were resolved by name, every one of these models
    silently produced zero arrows.
    """

    @pytest.fixture
    def landing_scene(self):
        """A rendered scene for the drop-landing model."""
        event_bus = EventBus()
        model_manager = ModelManager(event_bus)
        model_manager.load_model(_TOY_LANDING)

        offscreen = OffscreenRenderer(resolution=(200, 200))
        scene_manager = SceneManager(model_manager, _TOY_LANDING)
        scene_manager.create_scene(renderer=offscreen.renderer)
        scene_manager._realize_position()
        return scene_manager

    def test_arrows_are_created(self, landing_scene) -> None:
        actors = landing_scene.scene.contact_force_actors or {}

        # Two feet, each with a heel resultant and a forefoot resultant.
        assert sorted(actors) == [
            "foot_l.calcn_l",
            "foot_l.toes_l",
            "foot_r.calcn_r",
            "foot_r.toes_r",
        ]

    def test_hidden_arrow_stays_hidden_across_updates(self, landing_scene) -> None:
        state = VisualizationStateManager()
        names = list(landing_scene.scene.contact_force_actors)
        state.initialize_category("contact_forces", names, default_visible=True)
        landing_scene.set_visualization_state(state)
        _show_all(landing_scene)

        state.set_visibility("contact_forces", "foot_r.toes_r", False)
        for _ in range(3):
            landing_scene.update_all_actor_positions()

        assert "foot_r.toes_r" not in _visible(landing_scene)
        assert "foot_r.calcn_r" in _visible(landing_scene)

    def test_arrows_track_contact(self, landing_scene) -> None:
        """An arrow only appears where the foot actually meets the platform."""
        model = landing_scene.opensim_model
        state = landing_scene.state
        pelvis = model.getCoordinateSet().get("pelvis_ty")
        pelvis.setValue(state, pelvis.getDefaultValue() - 0.56, False)
        landing_scene._realize_position()

        force = model.getForceSet().get("foot_r")
        model.realizeDynamics(state)
        values = force.getRecordValues(state)
        points = landing_scene.scene.contact_force_metadata

        # Right foot is loaded, left foot is still in the air.
        assert points["foot_r.toes_r"].force_vector(values)[1] > 0.0
        left = model.getForceSet().get("foot_l")
        left_values = left.getRecordValues(state)
        assert points["foot_l.toes_l"].force_vector(left_values)[1] == pytest.approx(0.0)


class TestVisibleForcesFiltering:
    """The visualizer honours the set of names it is handed."""

    def test_empty_set_hides_everything(self, scene) -> None:
        actors = scene.scene.contact_force_actors
        metadata = scene.scene.contact_force_metadata
        _show_all(scene)

        scene.contact_force_visualizer.update_contact_forces(
            actors, metadata, visible_forces=set()
        )

        assert _visible(scene) == set()

    def test_subset_shows_only_those_named(self, scene) -> None:
        actors = scene.scene.contact_force_actors
        metadata = scene.scene.contact_force_metadata
        _show_all(scene)
        chosen = {sorted(actors)[1]}

        scene.contact_force_visualizer.update_contact_forces(
            actors, metadata, visible_forces=chosen
        )

        assert _visible(scene) == chosen
