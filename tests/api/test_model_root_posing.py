"""Tests for root pinning and the base gizmo on a floating-base model.

These need a model whose pelvis floats, which the bundled arm26 does not have.
"""

from pathlib import Path

import numpy as np
import opensim
import pytest
import vtkmodules.all as vtk

from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.posing.drag_marker_rig import DragMarkerRig
from osim_render.api.posing.model_root import find_model_root
from osim_render.api.posing.pose_applier import PoseApplier
from osim_render.api.posing.pose_solver import PoseSolver
from osim_render.api.posing.root_transform import (
    matrix_to_root_coordinates,
    read_root_matrix,
)
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.tooling_paths import get_opensim_geometry_root
from osim_render.ui.interaction.root_gizmo import (
    RootGizmo,
    _from_vtk_matrix,
    _strip_scale,
    _to_vtk_matrix,
)

_MODEL = Path("resources/Models/Rajagopal/Rajagopal2016.osim")
_GEOMETRY_ROOT = get_opensim_geometry_root()

pytestmark = pytest.mark.skipif(
    not _MODEL.is_file(),
    reason=f"Floating-base model not found at {_MODEL}",
)


@pytest.fixture
def floating_model() -> tuple[opensim.Model, opensim.State, DragMarkerRig]:
    """Full-body model with drag handles installed."""
    model = opensim.Model(str(_MODEL))
    model.initSystem()
    rig = DragMarkerRig.install(model)
    state = model.initSystem()
    model.realizePosition(state)
    return model, state, rig


class TestFloatingBaseDetection:
    """A six-axis pelvis is recognised as a drivable floating base."""

    def test_root_is_a_floating_base(self, floating_model) -> None:
        model, _state, _rig = floating_model

        root = find_model_root(model)

        assert root is not None
        assert root.is_floating_base
        assert root.supports_gizmo
        assert len(root.rotation_coordinates) == 3
        assert len(root.translation_coordinates) == 3

    def test_rotation_sequence_is_read_from_the_joint(self, floating_model) -> None:
        model, _state, _rig = floating_model

        root = find_model_root(model)

        assert root is not None
        assert root.rotation_sequence == "ZXY"


class TestRootPinning:
    """Pinning the base makes a drag articulate joints instead of sliding."""

    def _drag_hand(self, model, state, rig, pinned) -> tuple[float, float]:
        """Drag the left hand and report root motion and marker error."""
        root = find_model_root(model)
        assert root is not None
        solver = PoseSolver(model)
        marker_name = rig.set_grab_point("hand_l", (0.0, -0.05, 0.0))

        before = {
            name: model.getCoordinateSet().get(name).getValue(state)
            for name in root.coordinate_names
        }
        start = model.getBodySet().get("hand_l").findStationLocationInGround(
            state, opensim.Vec3(0.0, -0.05, 0.0)
        )
        target = (start.get(0) + 0.15, start.get(1) + 0.25, start.get(2))

        solution = solver.solve(
            state,
            marker_name,
            target,
            pinned_coordinates=frozenset(root.coordinate_names) if pinned else frozenset(),
        )
        moved = sum(
            abs(solution.coordinate_values[name] - before[name])
            for name in root.coordinate_names
        )
        return moved, solution.marker_error

    def test_unpinned_drag_moves_the_whole_model(self, floating_model) -> None:
        model, state, rig = floating_model

        moved, _error = self._drag_hand(model, state, rig, pinned=False)

        assert moved > 0.05, "expected the free base to drift toward the target"

    def test_pinned_drag_holds_the_base_still(self, floating_model) -> None:
        model, state, rig = floating_model

        moved, _error = self._drag_hand(model, state, rig, pinned=True)

        assert moved == pytest.approx(0.0, abs=1e-9)

    def test_pinning_costs_accuracy_but_still_solves(self, floating_model) -> None:
        model, state, rig = floating_model
        _free_moved, free_error = self._drag_hand(model, state, rig, pinned=False)

        model.initSystem()
        _pinned_moved, pinned_error = self._drag_hand(model, state, rig, pinned=True)

        # A pinned base cannot cheat by walking toward the target.
        assert pinned_error >= free_error


class TestRootTransformRoundTrip:
    """World transforms and root coordinates convert both ways exactly."""

    def test_random_poses_round_trip(self, floating_model) -> None:
        model, state, _rig = floating_model
        root = find_model_root(model)
        assert root is not None
        rng = np.random.default_rng(7)

        worst = 0.0
        for _trial in range(10):
            expected = {name: float(rng.uniform(-0.5, 0.5)) for name in root.coordinate_names}
            for name, value in expected.items():
                model.getCoordinateSet().get(name).setValue(state, value, False)
            model.realizePosition(state)

            world = read_root_matrix(model, state, root)
            recovered = matrix_to_root_coordinates(model, state, root, world)
            worst = max(worst, max(abs(recovered[n] - expected[n]) for n in expected))

        assert worst < 1e-9

    def test_stripping_scale_recovers_rotation(self, floating_model) -> None:
        model, state, _rig = floating_model
        root = find_model_root(model)
        assert root is not None

        original = read_root_matrix(model, state, root)
        scaled = original.copy()
        scaled[:3, :3] = scaled[:3, :3] * 0.42

        restored = _strip_scale(scaled)

        assert np.allclose(restored, original)


# The gizmo needs body actors, which need the shared geometry meshes.
@pytest.mark.skipif(
    not _GEOMETRY_ROOT.is_dir(),
    reason=f"OpenSim shared geometry not found at {_GEOMETRY_ROOT}",
)
class TestRootGizmo:
    """The gizmo drives the base through its joint coordinates."""

    @pytest.fixture
    def gizmo_setup(self) -> tuple[RootGizmo, SceneManager, opensim.Model]:
        """A gizmo attached to a rendered full-body scene."""
        event_bus = EventBus()
        model_manager = ModelManager(event_bus)
        model_manager.load_model(_MODEL)

        offscreen = OffscreenRenderer(resolution=(400, 400))
        scene_manager = SceneManager(model_manager, _MODEL, (str(_GEOMETRY_ROOT),))
        scene_manager.create_scene(renderer=offscreen.renderer)
        offscreen.renderer.ResetCamera()
        offscreen.render_window.Render()

        interactor = vtk.vtkRenderWindowInteractor()
        interactor.SetRenderWindow(offscreen.render_window)

        model = model_manager.get_opensim_model()
        root = find_model_root(model)
        assert root is not None

        gizmo = RootGizmo(
            scene_manager,
            root,
            PoseApplier(scene_manager, event_bus),
            offscreen.renderer,
            interactor,
        )
        return gizmo, scene_manager, model

    def test_translating_the_gizmo_moves_the_base(self, gizmo_setup) -> None:
        gizmo, scene_manager, model = gizmo_setup
        state = scene_manager.state

        transform = gizmo.representation.GetTransform()
        moved = _from_vtk_matrix(transform.GetMatrix())
        moved[:3, 3] += np.array([0.20, 0.05, -0.10])
        transform.SetMatrix(_to_vtk_matrix(moved))
        gizmo._on_interaction(None, "InteractionEvent")

        landed = read_root_matrix(model, state, gizmo.root)
        assert np.allclose(landed[:3, 3], moved[:3, 3], atol=1e-9)

    def test_rotating_the_gizmo_orients_the_base(self, gizmo_setup) -> None:
        gizmo, scene_manager, model = gizmo_setup
        state = scene_manager.state
        gizmo.sync_from_model()

        desired = _strip_scale(
            _from_vtk_matrix(gizmo.representation.GetTransform().GetMatrix())
        )
        turn = vtk.vtkTransform()
        turn.RotateY(20.0)
        desired[:3, :3] = _from_vtk_matrix(turn.GetMatrix())[:3, :3] @ desired[:3, :3]

        scaled = desired.copy()
        scaled[:3, :3] = scaled[:3, :3] * gizmo._handle_scale()
        gizmo.representation.GetTransform().SetMatrix(_to_vtk_matrix(scaled))
        gizmo._on_interaction(None, "InteractionEvent")

        landed = read_root_matrix(model, state, gizmo.root)
        assert np.allclose(landed[:3, :3], desired[:3, :3], atol=1e-9)

    def test_gizmo_tracks_the_model_after_sync(self, gizmo_setup) -> None:
        gizmo, scene_manager, model = gizmo_setup
        state = scene_manager.state

        model.getCoordinateSet().get("pelvis_tx").setValue(state, 0.6, False)
        model.realizePosition(state)
        gizmo.sync_from_model()

        shown = _strip_scale(
            _from_vtk_matrix(gizmo.representation.GetTransform().GetMatrix())
        )
        assert np.allclose(shown, read_root_matrix(model, state, gizmo.root))

    def test_gizmo_respects_a_locked_root_coordinate(self, gizmo_setup) -> None:
        gizmo, scene_manager, model = gizmo_setup
        state = scene_manager.state
        model.getCoordinateSet().get("pelvis_tx").setLocked(state, True)
        before = model.getCoordinateSet().get("pelvis_tx").getValue(state)

        transform = gizmo.representation.GetTransform()
        moved = _from_vtk_matrix(transform.GetMatrix())
        moved[:3, 3] += np.array([0.30, 0.0, 0.0])
        transform.SetMatrix(_to_vtk_matrix(moved))
        gizmo._on_interaction(None, "InteractionEvent")

        after = model.getCoordinateSet().get("pelvis_tx").getValue(state)
        assert after == pytest.approx(before, abs=1e-9)

    def test_toggling_visibility(self, gizmo_setup) -> None:
        gizmo, _scene_manager, _model = gizmo_setup

        gizmo.set_enabled(True)
        assert gizmo.is_enabled

        gizmo.set_enabled(False)
        assert not gizmo.is_enabled
