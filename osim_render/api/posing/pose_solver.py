"""Solve model poses with OpenSim's own InverseKinematicsSolver.

Dragging a point on a body is expressed as a single-marker IK problem: pull the
grabbed marker toward a world-space target and let Simbody's assembler find
coordinate values that satisfy the model's mobilizers and constraints. The
solver warm-starts from the incoming state, so successive drag steps converge
in well under a millisecond and the pose moves smoothly rather than jumping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)

DEFAULT_ACCURACY = 1e-4
DEFAULT_MARKER_WEIGHT = 1.0

# Without regularization the solver happily swings unrelated limbs to satisfy
# the target (dragging a hand rotates the opposite leg). This weight keeps
# drags local while costing only ~2mm of marker accuracy.
DEFAULT_REGULARIZATION = 0.01


@dataclass(frozen=True)
class PoseSolution:
    """Result of a single interactive IK solve."""

    coordinate_values: dict[str, float]
    marker_error: float
    converged: bool


class PoseSolver:
    """Drive OpenSim's InverseKinematicsSolver from a world-space drag target."""

    def __init__(
        self,
        model: Any,
        accuracy: float = DEFAULT_ACCURACY,
        regularization_weight: float = DEFAULT_REGULARIZATION,
        enforce_coordinate_limits: bool = True,
    ):
        """Initialize the pose solver.

        Args:
            model: OpenSim Model with drag markers installed
            accuracy: Solver accuracy passed to InverseKinematicsSolver
            regularization_weight: Weight pulling coordinates toward their
                pre-drag values. 0.0 lets the solver move freely; small
                positive values (~0.01) keep unrelated joints steadier.
            enforce_coordinate_limits: Hold coordinates inside their declared
                ranges while solving. Models often ship with clamping off,
                which lets IK wind joints many turns past anatomical limits.
        """
        self.model = model
        self.accuracy = accuracy
        self.regularization_weight = regularization_weight
        self.enforce_coordinate_limits = enforce_coordinate_limits

    def solve(
        self,
        state: Any,
        marker_name: str,
        target_world: tuple[float, float, float],
        pinned_coordinates: frozenset[str] = frozenset(),
    ) -> PoseSolution:
        """Pose the model so a marker moves toward a world-space target.

        Mutates `state` in place on success. If the target is unreachable the
        solver settles at the closest satisfiable pose rather than failing.

        Args:
            state: SimTK state to pose (warm start and output)
            marker_name: Marker being dragged
            target_world: Desired marker location in ground coordinates
            pinned_coordinates: Coordinates to hold fixed for this solve,
                typically a floating base that would otherwise let the whole
                model drift toward the target

        Returns:
            PoseSolution with the resulting coordinate values

        Raises:
            ValueError: If the marker is not in the model
        """
        if self.model.getMarkerSet().getIndex(marker_name) < 0:
            raise ValueError(f"Marker not in model: {marker_name}")

        previous_values = self._read_coordinates(state)
        previous_clamping = self._apply_coordinate_limits(state)
        previous_locks = self._apply_pins(state, pinned_coordinates)

        solver = self._build_solver(state, marker_name, target_world, previous_values)
        converged = self._assemble(solver, state, previous_values)

        self._restore_locks(state, previous_locks)
        self._restore_clamping(state, previous_clamping)
        self.model.realizePosition(state)

        return PoseSolution(
            coordinate_values=self._read_coordinates(state),
            marker_error=solver.computeCurrentMarkerError(marker_name),
            converged=converged,
        )

    def _assemble(
        self, solver: Any, state: Any, previous_values: dict[str, float]
    ) -> bool:
        """Run the assembler, restoring the prior pose if it fails.

        Args:
            solver: Configured InverseKinematicsSolver
            state: State to assemble
            previous_values: Coordinate values to restore on failure

        Returns:
            True if assembly converged
        """
        try:
            solver.assemble(state)
        except RuntimeError as error:
            logger.warning(f"IK assembly failed, restoring pose: {error}")
            self._write_coordinates(state, previous_values)
            return False
        return True

    def _build_solver(
        self,
        state: Any,
        marker_name: str,
        target_world: tuple[float, float, float],
        current_values: dict[str, float],
    ) -> Any:
        """Construct an InverseKinematicsSolver for one drag target.

        Args:
            state: Current state (used for regularization references)
            marker_name: Marker being dragged
            target_world: Desired marker location in ground
            current_values: Coordinate values to regularize toward

        Returns:
            Configured InverseKinematicsSolver
        """
        import opensim

        markers_reference = self._build_markers_reference(
            marker_name, target_world, state.getTime()
        )
        coordinate_references = self._build_coordinate_references(current_values)

        solver = opensim.InverseKinematicsSolver(
            self.model, markers_reference, coordinate_references
        )
        solver.setAccuracy(self.accuracy)
        return solver

    def _build_markers_reference(
        self,
        marker_name: str,
        target_world: tuple[float, float, float],
        time: float,
    ) -> Any:
        """Build a single-frame MarkersReference holding the drag target.

        The row is stamped with the state's own time, not zero. assemble()
        looks the reference up at state.getTime(), so a table anchored at zero
        raises "Time t is out of time range [0, 0]" the moment a motion has
        advanced the clock, and the drag silently does nothing.

        Args:
            marker_name: Marker being dragged
            target_world: Desired marker location in ground
            time: The state's current time

        Returns:
            MarkersReference with one marker at one time sample
        """
        import opensim

        table = opensim.TimeSeriesTableVec3()
        table.appendRow(time, opensim.RowVectorVec3(1, opensim.Vec3(*target_world)))
        table.setColumnLabels([marker_name])

        weights = opensim.SetMarkerWeights()
        weights.cloneAndAppend(opensim.MarkerWeight(marker_name, DEFAULT_MARKER_WEIGHT))

        reference = opensim.MarkersReference(table, weights)
        reference.setDefaultWeight(DEFAULT_MARKER_WEIGHT)
        return reference

    def _build_coordinate_references(self, current_values: dict[str, float]) -> Any:
        """Build weak references holding coordinates near their current values.

        Args:
            current_values: Coordinate values to pull toward

        Returns:
            SimTK array of CoordinateReference (empty if unregularized)
        """
        import opensim

        references = opensim.SimTKArrayCoordinateReference()
        if self.regularization_weight <= 0.0:
            return references

        for name, value in current_values.items():
            reference = opensim.CoordinateReference(name, opensim.Constant(value))
            reference.setWeight(self.regularization_weight)
            references.push_back(reference)

        return references

    def _apply_coordinate_limits(self, state: Any) -> dict[str, bool]:
        """Turn on clamping so the solve respects declared coordinate ranges.

        Args:
            state: State to clamp

        Returns:
            The clamping flags as they were, for later restoration
        """
        if not self.enforce_coordinate_limits:
            return {}

        previous = {}
        for coordinate in self.model.getCoordinateSet():
            previous[coordinate.getName()] = coordinate.getClamped(state)
            coordinate.setClamped(state, True)
        return previous

    def _apply_pins(
        self, state: Any, pinned_coordinates: frozenset[str]
    ) -> dict[str, bool]:
        """Lock the pinned coordinates so the solve cannot move them.

        Args:
            state: State to pin
            pinned_coordinates: Coordinate names to hold fixed

        Returns:
            The lock flags as they were, for later restoration
        """
        if not pinned_coordinates:
            return {}

        coordinate_set = self.model.getCoordinateSet()
        previous = {}
        for name in pinned_coordinates:
            coordinate = coordinate_set.get(name)
            previous[name] = coordinate.getLocked(state)
            coordinate.setLocked(state, True)
        return previous

    def _restore_locks(self, state: Any, previous: dict[str, bool]) -> None:
        """Release pins without disturbing locks the user set themselves.

        Args:
            state: State to restore
            previous: Lock flags captured before pinning
        """
        coordinate_set = self.model.getCoordinateSet()
        for name, was_locked in previous.items():
            coordinate_set.get(name).setLocked(state, was_locked)

    def _restore_clamping(self, state: Any, previous: dict[str, bool]) -> None:
        """Put clamping flags back the way the model had them.

        Restoring flags does not undo the solved values; it only avoids
        changing how the rest of the application sets coordinates.

        Args:
            state: State to restore
            previous: Flags captured before solving
        """
        coordinate_set = self.model.getCoordinateSet()
        for name, was_clamped in previous.items():
            coordinate_set.get(name).setClamped(state, was_clamped)

    def _read_coordinates(self, state: Any) -> dict[str, float]:
        """Read all coordinate values from a state.

        Args:
            state: State to read

        Returns:
            Mapping of coordinate name to value
        """
        return {
            coordinate.getName(): coordinate.getValue(state)
            for coordinate in self.model.getCoordinateSet()
        }

    def _write_coordinates(self, state: Any, values: dict[str, float]) -> None:
        """Write coordinate values back into a state.

        Args:
            state: State to modify
            values: Mapping of coordinate name to value
        """
        coordinate_set = self.model.getCoordinateSet()
        for name, value in values.items():
            coordinate_set.get(name).setValue(state, value, False)


if __name__ == "__main__":
    """Smoke test for PoseSolver."""
    import sys
    import time

    import opensim

    from osim_render.api.posing.drag_marker_rig import DragMarkerRig

    model_path = (
        sys.argv[1] if len(sys.argv) > 1 else "resources/Models/Arm26/arm26.osim"
    )
    print(f"PoseSolver smoke test on {model_path}")

    opensim.Model.setDebugLevel(-1)
    model = opensim.Model(model_path)
    model.initSystem()
    rig = DragMarkerRig.install(model)
    state = model.initSystem()
    model.realizePosition(state)

    body_name = [b.getName() for b in model.getBodySet()][-1]
    grab_local = (0.0, -0.2, 0.0)
    marker_name = rig.set_grab_point(body_name, grab_local)

    solver = PoseSolver(model, regularization_weight=0.0)

    model.realizePosition(state)
    start = model.getBodySet().get(body_name).findStationLocationInGround(
        state, opensim.Vec3(*grab_local)
    )
    print(f"[OK] Grabbed {body_name} at ground ({start.get(0):.3f}, {start.get(1):.3f}, {start.get(2):.3f})")

    target = (start.get(0) + 0.10, start.get(1) + 0.05, start.get(2))
    solution = solver.solve(state, marker_name, target)
    print(f"[OK] Solved: converged={solution.converged} error={solution.marker_error:.4f}")
    print(f"     coordinates: {({k: round(v, 3) for k, v in solution.coordinate_values.items()})}")
    assert solution.converged

    print("\nSimulating a 60-step drag...")
    started = time.perf_counter()
    for step in range(60):
        moving_target = (
            start.get(0) + 0.002 * step,
            start.get(1) + 0.001 * step,
            start.get(2),
        )
        solution = solver.solve(state, marker_name, moving_target)
    elapsed_ms = (time.perf_counter() - started) * 1000
    print(f"[OK] 60 steps in {elapsed_ms:.0f} ms ({elapsed_ms / 60:.2f} ms/step)")

    print("\nChecking unreachable target degrades gracefully...")
    far = (start.get(0) + 50.0, start.get(1) + 50.0, start.get(2))
    solution = solver.solve(state, marker_name, far)
    print(f"[OK] Far target: converged={solution.converged} error={solution.marker_error:.3f}")

    print("\nChecking locked coordinates are respected...")
    locked = model.getCoordinateSet().get(0)
    locked.setLocked(state, True)
    before = locked.getValue(state)
    solver.solve(state, marker_name, (start.get(0) + 0.2, start.get(1) + 0.2, start.get(2)))
    after = locked.getValue(state)
    print(f"[OK] {locked.getName()}: {before:.4f} -> {after:.4f}")
    assert abs(before - after) < 1e-9, "locked coordinate moved"

    print("\n[OK] Smoke test passed!")
