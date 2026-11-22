"""Tests for interactive drag-to-pose backed by OpenSim's IK solver."""

from pathlib import Path

import opensim
import pytest
import vtkmodules.all as vtk

from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.events import EventType
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.posing.body_picker import BodyPicker
from osim_render.api.posing.drag_marker_rig import (
    DragMarkerRig,
    drag_marker_name,
    is_drag_marker,
)
from osim_render.api.posing.drag_plane import DragPlane
from osim_render.api.posing.model_root import find_model_root
from osim_render.api.posing.pose_controller import DragPoseController
from osim_render.api.posing.pose_solver import PoseSolver
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.tooling_paths import get_opensim_geometry_root

# arm26.osim ships with every OpenSim installation
_ARM26 = Path(opensim.__file__).parent / "tests" / "arm26.osim"
_GEOMETRY_ROOT = get_opensim_geometry_root()
_GEOMETRY = str(_GEOMETRY_ROOT)

# The forearm is the distal body in arm26 and carries both degrees of freedom.
_MOVABLE_BODY = "r_ulna_radius_hand"


def _marker_in_ground(
    model: opensim.Model, state: opensim.State, local: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Locate a body-local point in ground without touching cached state.

    Args:
        model: Model holding the body
        state: State to evaluate in
        local: Point in the body's local frame

    Returns:
        The point in ground coordinates
    """
    model.realizePosition(state)
    body = model.getBodySet().get(_MOVABLE_BODY)
    point = body.findStationLocationInGround(state, opensim.Vec3(*local))
    return (point.get(0), point.get(1), point.get(2))


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    """Euclidean distance between two points.

    Args:
        a: First point
        b: Second point

    Returns:
        Distance between the points
    """
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


@pytest.fixture
def posed_model() -> tuple[opensim.Model, opensim.State, DragMarkerRig]:
    """Bare model with the drag rig installed, independent of any scene."""
    model = opensim.Model(str(_ARM26))
    model.initSystem()
    rig = DragMarkerRig.install(model)
    state = model.initSystem()
    model.realizePosition(state)
    return model, state, rig


class TestDragMarkerRig:
    """Drag handles are installed for every body and stay internal."""

    def test_installs_one_marker_per_body(self, posed_model) -> None:
        model, _state, rig = posed_model

        for body in model.getBodySet():
            assert rig.has_marker_for(body.getName())

    def test_marker_names_are_recognisable_as_internal(self) -> None:
        assert is_drag_marker(drag_marker_name("tibia_r"))
        assert not is_drag_marker("R.Heel")

    def test_unknown_body_is_rejected(self, posed_model) -> None:
        _model, _state, rig = posed_model

        assert not rig.has_marker_for("no_such_body")
        with pytest.raises(ValueError, match="No drag marker"):
            rig.set_grab_point("no_such_body", (0.0, 0.0, 0.0))

    def test_grab_point_moves_the_marker(self, posed_model) -> None:
        model, state, rig = posed_model
        rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.25, 0.0))

        stored = model.getMarkerSet().get(drag_marker_name(_MOVABLE_BODY))

        assert stored.get_location().get(1) == pytest.approx(-0.25)

    def test_grab_offset_changes_the_solved_pose(self, posed_model) -> None:
        """Grabbing the wrist must not behave like grabbing the elbow."""
        model, state, rig = posed_model
        solver = PoseSolver(model)
        target = (0.15, 0.30, 0.15)

        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, 0.0, 0.0))
        at_origin = solver.solve(state, marker_name, target).coordinate_values

        model.initSystem()
        rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.15, 0.0))
        offset = solver.solve(state, marker_name, target).coordinate_values

        assert at_origin != offset


class TestPoseSolver:
    """The solver honours the model's mobilizers, limits and locks."""

    def test_solve_moves_marker_toward_target(self, posed_model) -> None:
        model, state, rig = posed_model
        solver = PoseSolver(model)
        local = (0.0, -0.2, 0.0)
        marker_name = rig.set_grab_point(_MOVABLE_BODY, local)

        start = _marker_in_ground(model, state, local)
        target = (start[0] + 0.08, start[1] + 0.04, start[2])

        solution = solver.solve(state, marker_name, target)
        landed = _marker_in_ground(model, state, local)

        assert solution.converged
        moved_toward = _distance(start, target) - _distance(landed, target)
        assert moved_toward > 0.0

    def test_solve_respects_coordinate_ranges(self, posed_model) -> None:
        """Unclamped IK will otherwise wind joints many turns past their limits."""
        model, state, rig = posed_model
        solver = PoseSolver(model)
        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.2, 0.0))

        solution = solver.solve(state, marker_name, (50.0, 50.0, 50.0))

        # An unreachable target must not throw; it settles as close as the
        # joints allow, and never outside the declared ranges.
        assert solution.marker_error > 1.0
        for name, value in solution.coordinate_values.items():
            coordinate = model.getCoordinateSet().get(name)
            assert coordinate.getRangeMin() - 1e-6 <= value
            assert value <= coordinate.getRangeMax() + 1e-6

    def test_limits_can_be_disabled(self, posed_model) -> None:
        model, state, rig = posed_model
        solver = PoseSolver(model, enforce_coordinate_limits=False)
        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.2, 0.0))

        solution = solver.solve(state, marker_name, (50.0, 50.0, 50.0))

        out_of_range = [
            name
            for name, value in solution.coordinate_values.items()
            if value < model.getCoordinateSet().get(name).getRangeMin() - 1e-6
            or value > model.getCoordinateSet().get(name).getRangeMax() + 1e-6
        ]
        assert out_of_range, "expected unclamped solving to leave the declared range"

    def test_clamping_flags_are_restored(self, posed_model) -> None:
        model, state, rig = posed_model
        solver = PoseSolver(model)
        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.2, 0.0))
        before = {c.getName(): c.getClamped(state) for c in model.getCoordinateSet()}

        solver.solve(state, marker_name, (0.2, 0.4, 0.15))

        after = {c.getName(): c.getClamped(state) for c in model.getCoordinateSet()}
        assert after == before

    def test_locked_coordinates_do_not_move(self, posed_model) -> None:
        model, state, rig = posed_model
        solver = PoseSolver(model)
        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.2, 0.0))

        locked = model.getCoordinateSet().get(0)
        locked.setLocked(state, True)
        before = locked.getValue(state)

        solver.solve(state, marker_name, (0.3, 0.6, 0.2))

        assert locked.getValue(state) == pytest.approx(before, abs=1e-9)

    def test_unknown_marker_is_rejected(self, posed_model) -> None:
        model, state, _rig = posed_model
        solver = PoseSolver(model)

        with pytest.raises(ValueError, match="Marker not in model"):
            solver.solve(state, "__not_a_marker__", (0.0, 0.0, 0.0))

    def test_regularization_keeps_drags_local(self, posed_model) -> None:
        model, state, rig = posed_model
        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.2, 0.0))

        free = PoseSolver(model, regularization_weight=0.0)
        free_solution = free.solve(state, marker_name, (0.25, 0.55, 0.15))

        model.initSystem()
        damped = PoseSolver(model, regularization_weight=5.0)
        damped_solution = damped.solve(state, marker_name, (0.25, 0.55, 0.15))

        # Heavier regularization trades marker accuracy for a steadier pose.
        assert damped_solution.marker_error > free_solution.marker_error


class TestPosingAtNonZeroTime:
    """Posing must work after a motion has advanced the state clock.

    The IK marker reference is looked up at state.getTime(). A reference
    anchored at zero raises "Time t is out of time range [0, 0]" as soon as a
    motion is loaded, and the drag silently does nothing while sliders, which
    never touch IK, keep working.
    """

    @pytest.mark.parametrize("time", [0.0, 0.4, 1.0, 2.5, 123.456])
    def test_solve_works_at_any_state_time(self, posed_model, time) -> None:
        model, state, rig = posed_model
        state.setTime(time)
        model.realizePosition(state)

        solver = PoseSolver(model)
        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.2, 0.0))
        before = _marker_in_ground(model, state, (0.0, -0.2, 0.0))
        target = (before[0] + 0.08, before[1] + 0.04, before[2])

        solution = solver.solve(state, marker_name, target)

        assert solution.converged
        landed = _marker_in_ground(model, state, (0.0, -0.2, 0.0))
        assert _distance(landed, target) < _distance(before, target)

    def test_state_time_is_not_disturbed_by_solving(self, posed_model) -> None:
        model, state, rig = posed_model
        state.setTime(0.75)
        model.realizePosition(state)
        solver = PoseSolver(model)
        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.2, 0.0))

        solver.solve(state, marker_name, (0.2, 0.4, 0.15))

        assert state.getTime() == pytest.approx(0.75)


class TestPinnedCoordinates:
    """Pinning holds chosen coordinates still for the duration of a solve."""

    def test_pinned_coordinate_does_not_move(self, posed_model) -> None:
        model, state, rig = posed_model
        solver = PoseSolver(model)
        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.2, 0.0))
        pinned = model.getCoordinateSet().get(0).getName()
        before = model.getCoordinateSet().get(pinned).getValue(state)

        solution = solver.solve(
            state, marker_name, (0.3, 0.5, 0.2), pinned_coordinates=frozenset([pinned])
        )

        assert solution.coordinate_values[pinned] == pytest.approx(before, abs=1e-9)

    def test_pinning_does_not_leak_lock_flags(self, posed_model) -> None:
        model, state, rig = posed_model
        solver = PoseSolver(model)
        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.2, 0.0))
        pinned = model.getCoordinateSet().get(0).getName()

        solver.solve(
            state, marker_name, (0.3, 0.5, 0.2), pinned_coordinates=frozenset([pinned])
        )

        assert not model.getCoordinateSet().get(pinned).getLocked(state)

    def test_pinning_preserves_a_user_lock(self, posed_model) -> None:
        """Releasing a pin must not unlock something the user locked."""
        model, state, rig = posed_model
        solver = PoseSolver(model)
        marker_name = rig.set_grab_point(_MOVABLE_BODY, (0.0, -0.2, 0.0))
        pinned = model.getCoordinateSet().get(0).getName()
        model.getCoordinateSet().get(pinned).setLocked(state, True)

        solver.solve(
            state, marker_name, (0.3, 0.5, 0.2), pinned_coordinates=frozenset([pinned])
        )

        assert model.getCoordinateSet().get(pinned).getLocked(state)


class TestModelRoot:
    """Root detection separates a floating base from a plain articulation."""

    def test_arm26_root_is_not_a_floating_base(self, posed_model) -> None:
        model, _state, _rig = posed_model

        root = find_model_root(model)

        assert root is not None
        assert not root.is_floating_base
        assert not root.supports_gizmo

    def test_model_without_ground_joint_returns_none(self) -> None:
        empty = opensim.Model()
        empty.initSystem()

        assert find_model_root(empty) is None


class TestDragPlane:
    """Screen positions project onto a stable world-space plane."""

    def test_centre_projects_back_to_the_grab_point(self) -> None:
        offscreen = OffscreenRenderer(resolution=(400, 400))
        renderer = offscreen.renderer
        renderer.ResetCamera()

        grab_point = (0.0, 0.0, 0.0)
        plane = DragPlane.facing_camera(renderer.GetActiveCamera(), grab_point)

        projected = plane.project_display_point(renderer, 200, 200)

        assert projected is not None
        assert projected == pytest.approx(grab_point, abs=1e-6)

    def test_cursor_movement_moves_the_projection(self) -> None:
        offscreen = OffscreenRenderer(resolution=(400, 400))
        renderer = offscreen.renderer
        renderer.ResetCamera()

        plane = DragPlane.facing_camera(renderer.GetActiveCamera(), (0.0, 0.0, 0.0))

        centre = plane.project_display_point(renderer, 200, 200)
        shifted = plane.project_display_point(renderer, 300, 200)

        assert centre is not None and shifted is not None
        assert shifted != centre


class TestBodyPicker:
    """Picking resolves viewport clicks to bodies, and misses cleanly."""

    def test_pick_hits_body_and_misses_empty_space(self) -> None:
        offscreen = OffscreenRenderer(resolution=(400, 400))
        renderer = offscreen.renderer

        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(1.0)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.SetUserTransform(vtk.vtkTransform())
        renderer.AddActor(actor)
        renderer.ResetCamera()
        offscreen.render_window.Render()

        picker = BodyPicker({"only_body": actor})

        hit = picker.pick(renderer, 200, 200)
        assert hit is not None
        assert hit.body_name == "only_body"

        assert picker.pick(renderer, 2, 2) is None


# Body actors only exist when the shared geometry meshes are available.
_needs_geometry = pytest.mark.skipif(
    not _GEOMETRY_ROOT.is_dir(),
    reason=(
        f"OpenSim shared geometry not found at {_GEOMETRY_ROOT}. "
        "Set OSIM_RENDER_OPENSIM_GEOMETRY_DIR to an OpenSim Geometry directory."
    ),
)


@pytest.fixture
def scene_setup() -> tuple[SceneManager, DragPoseController, EventBus, vtk.vtkRenderer]:
    """Full scene wired for dragging, as the application assembles it."""
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    model_manager.load_model(_ARM26)

    offscreen = OffscreenRenderer(resolution=(600, 600))
    scene_manager = SceneManager(model_manager, _ARM26, (_GEOMETRY,))
    scene_manager.create_scene(renderer=offscreen.renderer)
    offscreen.renderer.ResetCamera()
    offscreen.render_window.Render()

    rig = model_manager.get_drag_rig()
    assert rig is not None
    controller = DragPoseController(scene_manager, rig, event_bus)
    return scene_manager, controller, event_bus, offscreen.renderer


def _grab_movable_body(
    controller: DragPoseController, renderer: vtk.vtkRenderer
) -> tuple[int, int]:
    """Sweep the viewport until the movable body is grabbed.

    Args:
        controller: Controller under test
        renderer: Renderer showing the model

    Returns:
        Viewport position where the body was grabbed
    """
    for x in range(60, 560, 12):
        for y in range(60, 560, 12):
            if not controller.begin_drag(renderer, x, y):
                continue
            session = controller.session
            assert session is not None
            if session.body_name == _MOVABLE_BODY:
                return (x, y)
            controller.end_drag()

    pytest.fail(f"never picked {_MOVABLE_BODY} anywhere in the viewport")


@_needs_geometry
class TestDragPoseController:
    """Dragging a body drives the model through the real scene pipeline."""

    def test_drag_changes_coordinates(self, scene_setup) -> None:
        scene_manager, controller, _bus, renderer = scene_setup
        model = scene_manager.opensim_model
        grabbed = _grab_movable_body(controller, renderer)

        before = {
            c.getName(): c.getValue(scene_manager.state)
            for c in model.getCoordinateSet()
        }
        for step in range(1, 25):
            controller.update_drag(renderer, grabbed[0] + step * 2, grabbed[1] + step)
        after = {
            c.getName(): c.getValue(scene_manager.state)
            for c in model.getCoordinateSet()
        }

        assert any(abs(after[k] - before[k]) > 1e-4 for k in before)

    def test_drag_publishes_pose_events(self, scene_setup) -> None:
        _scene_manager, controller, event_bus, renderer = scene_setup
        started: list[str] = []
        changed: list[dict] = []
        ended: list[str] = []

        event_bus.subscribe(
            EventType.POSE_DRAG_STARTED, lambda e: started.append(e.data["body_name"])
        )
        event_bus.subscribe(EventType.POSE_CHANGED, lambda e: changed.append(e.data))
        event_bus.subscribe(
            EventType.POSE_DRAG_ENDED, lambda e: ended.append(e.data["body_name"])
        )

        grabbed = _grab_movable_body(controller, renderer)
        controller.update_drag(renderer, grabbed[0] + 20, grabbed[1] + 10)
        controller.end_drag()

        assert _MOVABLE_BODY in started
        assert changed and "coordinate_values" in changed[-1]
        assert ended[-1] == _MOVABLE_BODY

    def test_click_on_empty_space_does_not_start_a_drag(self, scene_setup) -> None:
        _scene_manager, controller, _bus, renderer = scene_setup

        assert controller.begin_drag(renderer, 1, 1) is False
        assert not controller.is_dragging

    def test_update_without_a_drag_is_a_no_op(self, scene_setup) -> None:
        _scene_manager, controller, _bus, renderer = scene_setup

        assert controller.update_drag(renderer, 300, 300) is False

    def test_end_drag_clears_the_session(self, scene_setup) -> None:
        _scene_manager, controller, _bus, renderer = scene_setup
        _grab_movable_body(controller, renderer)

        assert controller.is_dragging
        controller.end_drag()

        assert not controller.is_dragging
        assert controller.session is None

    def test_drag_markers_are_not_rendered(self, scene_setup) -> None:
        scene_manager, _controller, _bus, _renderer = scene_setup
        scene = scene_manager.scene

        assert scene is not None
        assert scene.marker_actors is not None
        assert not any(is_drag_marker(name) for name in scene.marker_actors)
