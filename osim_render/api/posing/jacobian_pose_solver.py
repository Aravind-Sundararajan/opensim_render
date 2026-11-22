"""Solve poses from the analytic station Jacobian instead of assemble().

InverseKinematicsSolver re-solves the whole assembly problem numerically on
every mouse-move, which costs 55 ms/step on a 198-coordinate spine model -- 18
fps, well short of a real-time drag. Simbody can hand us the exact derivative of
a station's ground position instead (`calcStationJacobian`, ~7 microseconds), so
the pose can be stepped directly by damped least squares.

Because the derivative is exact rather than finite-differenced, the step
converges quadratically and lands at machine precision, so there is no accuracy
traded away for the speed. The regularization that keeps a drag local is applied
in the null space of the Jacobian, which means it costs no marker accuracy at
all -- unlike weak coordinate references, which spread error into joints that
cannot affect the target (dragging a skull should not flex both elbows).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from osim_render.api.logging import get_logger_for
from osim_render.api.posing.pose_solver import PoseSolution

logger = get_logger_for(__name__)

Array = np.ndarray[Any, Any]

DEFAULT_DAMPING = 1e-3
DEFAULT_NULL_PULL = 0.02
# Loops are held by the null-space step, not by the cost function. This only
# weights them in the accept/reject metric, so it stays near 1.
DEFAULT_LOOP_WEIGHT = 1.0
DEFAULT_TOLERANCE = 1e-5
DEFAULT_MAX_ITERATIONS = 12


class JacobianPoseSolver:
    """Pose a model by dragging a marker, using exact analytic derivatives.

    Interchangeable with PoseSolver: same solve() signature, same PoseSolution.
    """

    def __init__(
        self,
        model: Any,
        damping: float = DEFAULT_DAMPING,
        null_pull: float = DEFAULT_NULL_PULL,
        loop_weight: float = DEFAULT_LOOP_WEIGHT,
        enforce_coordinate_limits: bool = True,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        tolerance: float = DEFAULT_TOLERANCE,
    ):
        """Initialize the solver against an already-built model.

        Args:
            model: OpenSim Model whose system has been built (initSystem called)
            damping: Initial Levenberg-Marquardt damping. Adapts per step; the
                spine drivers are geared ~29x, so an undamped Newton step
                overshoots badly and fixed damping cannot cope.
            null_pull: Strength of the pull back toward the pre-drag pose,
                applied only in directions that do not move the target
            loop_weight: Weight on loop error in the accept/reject metric only.
                Loops are held by the null-space step, not by this, so the
                result is insensitive to it
            enforce_coordinate_limits: Hold coordinates inside declared ranges
            max_iterations: Cap on solver iterations per drag step
            tolerance: Marker error (metres) treated as converged
        """
        self.model = model
        self.damping = damping
        self.null_pull = null_pull
        self.loop_weight = loop_weight
        self.enforce_coordinate_limits = enforce_coordinate_limits
        self.max_iterations = max_iterations
        self.tolerance = tolerance

        self.matter = model.getMatterSubsystem()
        self.coordinates = model.getCoordinateSet()
        self.couplers = self._read_couplers()
        self.driven = self._index_couplers_by_driver()
        self.dependent_names = frozenset(name for name, _, _, _ in self.couplers)
        self.loops = self._read_loop_constraints()
        self.u_index = self._map_coordinates_to_mobilities()

        self._jacobian_buffer = self._new_matrix()

        logger.info(
            f"Jacobian solver ready: {self.coordinates.getSize()} coordinates, "
            f"{len(self.couplers)} couplers, {len(self.loops)} loop constraints"
        )
        self._warn_about_unhandled_constraints()

    def _warn_about_unhandled_constraints(self) -> None:
        """Say so when the model constrains something this solver ignores.

        Only couplers and PointConstraints are modelled. The assembler enforced
        every constraint type, so anything else here -- PointOnLine, Weld,
        ConstantDistance -- will be silently violated by the solved pose. Fail
        loudly rather than quietly returning a pose that breaks the model.
        """
        handled = {"CoordinateCouplerConstraint", "PointConstraint"}
        unhandled = sorted({
            constraint.getConcreteClassName()
            for constraint in self.model.getConstraintSet()
            if constraint.getConcreteClassName() not in handled
        })
        if not unhandled:
            return

        logger.warning(
            f"Model has constraint types this solver does not enforce: "
            f"{', '.join(unhandled)}. Dragged poses may violate them; use "
            f"PoseSolver for this model until they are implemented."
        )

    def _new_matrix(self) -> Any:
        """One reusable Matrix for Simbody to write Jacobians into."""
        import opensim

        return opensim.Matrix()

    def _read_couplers(self) -> list[tuple[str, str, Any, float]]:
        """Collect every coupler as (dependent, driver, function, scale)."""
        import opensim

        # Hold the downcast wrappers. The Function objects below are borrowed
        # from them, and SWIG wrappers are cheap to keep.
        self._coupler_objects = []

        couplers = []
        for constraint in self.model.getConstraintSet():
            coupler = opensim.CoordinateCouplerConstraint.safeDownCast(constraint)
            if coupler is None:
                continue
            self._coupler_objects.append(coupler)
            couplers.append((
                coupler.getDependentCoordinateName(),
                coupler.getIndependentCoordinateNames().get(0),
                coupler.getFunction(),
                opensim.PropertyHelper.getValueDouble(
                    coupler.getPropertyByName("scale_factor")
                ),
            ))
        return couplers

    def _index_couplers_by_driver(self) -> dict[str, list[tuple[str, Any, float]]]:
        """Map each driver to what it drives, so the chain rule stays cheap."""
        driven: dict[str, list[tuple[str, Any, float]]] = {}
        for dependent, driver, function, scale in self.couplers:
            driven.setdefault(driver, []).append((dependent, function, scale))
        return driven

    def _read_loop_constraints(self) -> list[tuple[Any, Any, Any, Any]]:
        """Collect PointConstraints, which have no spline to read.

        A closed loop (an acromioclavicular joint, say) cannot be satisfied by
        propagating couplers; skipping it leaves the loop open by millimetres.
        """
        import opensim

        loops = []
        for constraint in self.model.getConstraintSet():
            point = opensim.PointConstraint.safeDownCast(constraint)
            if point is None:
                continue
            loops.append((
                self._socket_frame(point, "body_1"),
                point.get_location_body_1(),
                self._socket_frame(point, "body_2"),
                point.get_location_body_2(),
            ))
        return loops

    def _socket_frame(self, constraint: Any, socket_name: str) -> Any:
        """Resolve a constraint socket to the frame it points at.

        Args:
            constraint: Constraint owning the socket
            socket_name: Socket to follow

        Returns:
            The connected PhysicalFrame
        """
        import opensim

        connectee = constraint.getSocket(socket_name).getConnecteeAsObject()
        return opensim.PhysicalFrame.safeDownCast(connectee)

    def _map_coordinates_to_mobilities(self) -> dict[str, int]:
        """Find each coordinate's slot in the u vector by probing its speed.

        SimbodyMatterSubsystem.getMobilizedBody is not wrapped, so the index is
        recovered by setting one speed and seeing which slot moves.

        Uses the model's working state rather than calling initSystem(), which
        would rebuild the system, invalidate our matter subsystem reference
        (a segfault or a bogus allocation) and strand the caller's state.

        Returns:
            Mapping of coordinate name to mobility index
        """
        import opensim

        state = opensim.State(self.model.getWorkingState())
        self.model.realizePosition(state)

        index = {}
        for coordinate in self.coordinates:
            probe = opensim.State(state)
            for other in self.coordinates:
                other.setSpeedValue(probe, 0.0)
            coordinate.setSpeedValue(probe, 1.0)
            self.model.realizeVelocity(probe)
            speeds = probe.getU()
            index[coordinate.getName()] = max(
                range(speeds.size()), key=lambda i: abs(speeds.get(i))
            )
        return index

    def free_coordinates(
        self, state: Any, pinned_coordinates: frozenset[str] = frozenset()
    ) -> list[str]:
        """Coordinates this solve is allowed to move.

        Excludes coupler dependents (they follow their drivers), anything the
        caller pinned, and anything the user locked.

        Args:
            state: State whose lock flags decide what is available
            pinned_coordinates: Names to hold fixed for this drag

        Returns:
            Names of the coordinates free to move
        """
        return [
            coordinate.getName()
            for coordinate in self.coordinates
            if coordinate.getName() not in self.dependent_names
            and coordinate.getName() not in pinned_coordinates
            and not coordinate.getLocked(state)
        ]

    def propagate_couplers(self, state: Any) -> None:
        """Set every dependent coordinate from its driver's spline.

        Args:
            state: State to update in place
        """
        import opensim

        for dependent, driver, function, scale in self.couplers:
            # A fresh Vector per lookup. Reusing one via set() poisons later
            # SWIG dispatch: calcDerivative then rejects its own arguments.
            driver_value = opensim.Vector(1, self.coordinates.get(driver).getValue(state))
            self.coordinates.get(dependent).setValue(
                state, function.calcValue(driver_value) * scale, False
            )
        self.model.realizePosition(state)

    def _station_jacobian(self, state: Any, frame: Any, station: Any) -> Array:
        """Exact 3 x nu derivative of a station's ground position.

        Args:
            state: Realized-to-position state
            frame: Frame the station is fixed to
            station: Station location in the frame

        Returns:
            Dense 3 x nu Jacobian
        """
        self.matter.calcStationJacobian(
            state, frame.getMobilizedBodyIndex(), station, self._jacobian_buffer
        )
        buffer = self._jacobian_buffer
        return np.array([
            [buffer.get(row, col) for col in range(buffer.ncol())]
            for row in range(buffer.nrow())
        ])

    def _project_onto_free(
        self, jacobian_u: Array, free_names: list[str], values: dict[str, float]
    ) -> Array:
        """Chain-rule a mobility-space Jacobian onto the free coordinates.

        Moving a driver also moves everything coupled to it, so each column
        picks up its dependents' spline slopes.

        Args:
            jacobian_u: 3 x nu Jacobian in mobility space
            free_names: Coordinates being solved for
            values: Current value of each free coordinate

        Returns:
            3 x len(free_names) Jacobian
        """
        columns = []
        for name in free_names:
            column = jacobian_u[:, self.u_index[name]].copy()
            for dependent, function, scale in self.driven.get(name, ()):
                slope = self._coupler_slope(function, values[name]) * scale
                column += jacobian_u[:, self.u_index[dependent]] * slope
            columns.append(column)
        return np.column_stack(columns)

    def _coupler_slope(self, function: Any, at: float) -> float:
        """Slope of a coupler spline, by central difference on calcValue.

        Function.calcDerivative is avoided deliberately. Its SWIG wrapper
        rejects a valid StdVectorInt once the call is made from inside a solve,
        while the identical call succeeds in isolation. calcValue is reliable,
        and on a smooth spline a central difference matches the analytic slope
        to roughly 1e-10 -- orders of magnitude finer than the Jacobian needs,
        since it only steers the step and never enters the residual.

        Args:
            function: Coupler function to differentiate
            at: Driver value to differentiate at

        Returns:
            First derivative of the function at that value
        """
        import opensim

        step = 1e-6
        ahead = function.calcValue(opensim.Vector(1, at + step))
        behind = function.calcValue(opensim.Vector(1, at - step))
        return float((ahead - behind) / (2.0 * step))

    def _loop_error(self, state: Any) -> Array:
        """How far every closed loop is from shut, in metres."""
        if not self.loops:
            return np.zeros(0)

        gaps = []
        for frame1, point1, frame2, point2 in self.loops:
            here = frame1.findStationLocationInGround(state, point1)
            there = frame2.findStationLocationInGround(state, point2)
            gaps.append(np.array([there.get(i) - here.get(i) for i in range(3)]))
        return np.concatenate(gaps)

    def _loop_jacobian(
        self, state: Any, free_names: list[str], values: dict[str, float]
    ) -> Array:
        """Derivative of every loop gap with respect to the free coordinates."""
        if not self.loops:
            return np.zeros((0, len(free_names)))

        blocks = []
        for frame1, point1, frame2, point2 in self.loops:
            first = self._project_onto_free(
                self._station_jacobian(state, frame1, point1), free_names, values
            )
            second = self._project_onto_free(
                self._station_jacobian(state, frame2, point2), free_names, values
            )
            blocks.append(second - first)
        return np.vstack(blocks)

    def _read_free(self, state: Any, free_names: list[str]) -> Array:
        """Current values of the free coordinates."""
        return np.array([self.coordinates.get(n).getValue(state) for n in free_names])

    def _write_free(
        self, state: Any, free_names: list[str], values: Array
    ) -> None:
        """Write the free coordinates back, clamped to their ranges if asked."""
        for name, value in zip(free_names, values, strict=True):
            coordinate = self.coordinates.get(name)
            if self.enforce_coordinate_limits:
                value = min(
                    max(value, coordinate.getRangeMin()), coordinate.getRangeMax()
                )
            coordinate.setValue(state, value, False)

    def _marker_frame_and_station(self, marker_name: str) -> tuple[Any, Any]:
        """Resolve a marker to the frame it rides and its offset on it.

        Args:
            marker_name: Marker being dragged

        Returns:
            The marker's parent frame and its location on that frame

        Raises:
            ValueError: If the marker is not in the model
        """
        if self.model.getMarkerSet().getIndex(marker_name) < 0:
            raise ValueError(f"Marker not in model: {marker_name}")

        marker = self.model.getMarkerSet().get(marker_name)
        return marker.getParentFrame(), marker.get_location()

    def solve(
        self,
        state: Any,
        marker_name: str,
        target_world: tuple[float, float, float],
        pinned_coordinates: frozenset[str] = frozenset(),
    ) -> PoseSolution:
        """Pose the model so a marker moves toward a world-space target.

        Mutates `state` in place. An unreachable target settles at the closest
        pose the free coordinates can reach rather than failing.

        Args:
            state: SimTK state to pose (warm start and output)
            marker_name: Marker being dragged
            target_world: Desired marker location in ground coordinates
            pinned_coordinates: Coordinates to hold fixed for this solve

        Returns:
            PoseSolution with the resulting coordinate values

        Raises:
            ValueError: If the marker is not in the model
        """
        frame, station = self._marker_frame_and_station(marker_name)
        free_names = self.free_coordinates(state, pinned_coordinates)
        target = np.asarray(target_world, dtype=float)

        if not free_names:
            logger.warning("No free coordinates for this drag, pose unchanged")
            return self._solution(state, frame, station, target, converged=False)

        rest = self._read_free(state, free_names)
        damping = self.damping

        self.propagate_couplers(state)
        drag, residual = self._residual(state, frame, station, target)
        cost = float(np.linalg.norm(residual))

        converged = False
        for _ in range(self.max_iterations):
            if np.linalg.norm(drag) < self.tolerance:
                converged = True
                break

            current = self._read_free(state, free_names)
            values = dict(zip(free_names, current, strict=True))
            drag_jacobian = self._project_onto_free(
                self._station_jacobian(state, frame, station), free_names, values
            )
            loop_jacobian = self._loop_jacobian(state, free_names, values)

            step, cost, drag, residual, damping, accepted = self._take_step(
                state, free_names, frame, station, target,
                drag_jacobian, loop_jacobian, drag, self._loop_error(state),
                cost, current, rest - current, damping,
            )
            if not accepted:
                break

        self.propagate_couplers(state)
        self._close_loops(state, free_names)
        return self._solution(state, frame, station, target, converged)

    def _close_loops(self, state: Any, free_names: list[str], passes: int = 4) -> None:
        """Drive residual loop error down once the drag has converged.

        Each solver iteration only closes the loops to first order, so a little
        second-order error survives -- about 2e-5 on the spine model, looser
        than the 6e-6 the assembler leaves. A few pure Newton projections cost
        almost nothing and take it to machine precision.

        Args:
            state: State to correct in place
            free_names: Coordinates available to close the loops
        """
        if not self.loops:
            return

        for _ in range(passes):
            gap = self._loop_error(state)
            if np.linalg.norm(gap) < 1e-14:
                return

            current = self._read_free(state, free_names)
            values = dict(zip(free_names, current, strict=True))
            jacobian = self._loop_jacobian(state, free_names, values)
            self._write_free(
                state, free_names, current - np.linalg.pinv(jacobian) @ gap
            )
            self.propagate_couplers(state)

    def _take_step(
        self,
        state: Any,
        free_names: list[str],
        frame: Any,
        station: Any,
        target: Array,
        drag_jacobian: Array,
        loop_jacobian: Array,
        drag_residual: Array,
        loop_residual: Array,
        cost: float,
        current: Array,
        drift: Array,
        damping: float,
    ) -> tuple[Array | None, float, Array, Array, float, bool]:
        """Try damped steps until one lowers the cost, raising damping as needed.

        Closed loops are handled as hard constraints rather than as weighted
        objective terms. Stacking them into one least-squares problem forces a
        false trade -- weighting the loops highly enough to hold the shoulder
        girdle shut left a hand drag 37 mm short, and weighting them low enough
        to reach tore the girdle open by 93 mm. Instead the step first closes
        the loops, then pursues the target only within their null space, so
        both are satisfied at once.

        Returns:
            Tuple of (step, cost, drag, residual, damping, accepted)
        """
        drag_jacobian = self._mask_saturated(
            drag_jacobian, free_names, current, drag_residual
        )
        closing, tangent = self._loop_correction(loop_jacobian, loop_residual)

        # Whatever the loop correction already achieves is not the drag's job.
        effective = drag_jacobian @ tangent
        remaining: Array = drag_residual - drag_jacobian @ closing
        null_component = tangent @ (
            drift - np.linalg.pinv(effective) @ (effective @ drift)
        )

        for _ in range(10):
            gram = effective @ effective.T + damping * np.eye(effective.shape[0])
            step = closing + tangent @ (
                effective.T @ np.linalg.solve(gram, remaining)
            )
            step = step + self.null_pull * null_component

            self._write_free(state, free_names, current + step)
            self.propagate_couplers(state)
            drag, residual_try = self._residual(state, frame, station, target)
            cost_try = float(np.linalg.norm(residual_try))

            if cost_try < cost:
                return step, cost_try, drag, residual_try, max(damping / 3.0, 1e-9), True

            self._write_free(state, free_names, current)
            damping *= 5.0

        self.propagate_couplers(state)
        drag, residual = self._residual(state, frame, station, target)
        return None, cost, drag, residual, damping, False

    def _loop_correction(
        self, loop_jacobian: Array, loop_residual: Array
    ) -> tuple[Array, Array]:
        """Step that shuts the loops, and a projector onto their null space.

        Args:
            loop_jacobian: Derivative of each loop gap w.r.t. the free set
            loop_residual: How far each loop currently is from shut

        Returns:
            The closing step, and the projector leaving loops undisturbed
        """
        width = loop_jacobian.shape[1]
        if not loop_jacobian.size:
            return np.zeros(width), np.eye(width)

        # loop_residual is the gap (p2 - p1); closing it means moving against
        # the gap, so the correction is negative.
        inverse = np.linalg.pinv(loop_jacobian)
        return -inverse @ loop_residual, np.eye(width) - inverse @ loop_jacobian

    def _coordinate_bounds(self, free_names: list[str]) -> tuple[Array, Array]:
        """Declared range of each free coordinate.

        Args:
            free_names: Coordinates being solved for

        Returns:
            Lower and upper bound arrays
        """
        lower = np.array([self.coordinates.get(n).getRangeMin() for n in free_names])
        upper = np.array([self.coordinates.get(n).getRangeMax() for n in free_names])
        return lower, upper

    def _mask_saturated(
        self, jacobian: Array, free_names: list[str], current: Array, residual: Array
    ) -> Array:
        """Zero the columns of coordinates the step cannot actually move.

        A coordinate sitting on a range limit can only move inward. Clamping
        the step afterwards instead silently truncates it, so the pose the
        model reaches is not the one the step predicted -- Levenberg-Marquardt
        then rejects it, raises damping and stalls. Several spine-model arm
        coordinates start life exactly on their lower bound, which made a hand
        drag look frozen. Dropping those columns lets the solve find the step
        that is genuinely available instead.

        Args:
            jacobian: Stacked drag and loop Jacobian
            free_names: Coordinates being solved for
            current: Their current values
            residual: Weighted residual being driven to zero

        Returns:
            Jacobian with saturated columns zeroed
        """
        if not self.enforce_coordinate_limits:
            return jacobian

        lower, upper = self._coordinate_bounds(free_names)
        masked = jacobian.copy()
        blocked = np.zeros(len(free_names), dtype=bool)

        for _ in range(3):
            gradient = masked.T @ residual
            outward = ((current <= lower + 1e-9) & (gradient < 0.0)) | (
                (current >= upper - 1e-9) & (gradient > 0.0)
            )
            if not (outward & ~blocked).any():
                break
            blocked |= outward
            masked[:, blocked] = 0.0

        return masked

    def _residual(
        self, state: Any, frame: Any, station: Any, target: Array
    ) -> tuple[Array, Array]:
        """Drag error, and that error stacked over weighted loop error."""
        here = frame.findStationLocationInGround(state, station)
        drag = target - np.array([here.get(i) for i in range(3)])
        return drag, np.concatenate([drag, self.loop_weight * self._loop_error(state)])

    def _solution(
        self, state: Any, frame: Any, station: Any, target: Array, converged: bool
    ) -> PoseSolution:
        """Package the posed state as a PoseSolution."""
        here = frame.findStationLocationInGround(state, station)
        error = float(
            np.linalg.norm(target - np.array([here.get(i) for i in range(3)]))
        )
        return PoseSolution(
            coordinate_values={
                c.getName(): c.getValue(state) for c in self.coordinates
            },
            marker_error=error,
            converged=converged,
        )


if __name__ == "__main__":
    """Smoke test for JacobianPoseSolver."""
    import sys
    import time

    import opensim

    from osim_render.api.posing.drag_marker_rig import DragMarkerRig

    model_path = (
        sys.argv[1] if len(sys.argv) > 1 else "resources/Models/Arm26/arm26.osim"
    )
    print(f"JacobianPoseSolver smoke test on {model_path}")

    opensim.Model.setDebugLevel(-1)
    model = opensim.Model(model_path)
    model.initSystem()
    rig = DragMarkerRig.install(model)
    state = model.initSystem()
    model.realizePosition(state)

    solver = JacobianPoseSolver(model)

    body_name = [b.getName() for b in model.getBodySet()][-1]
    grab_local = (0.0, -0.1, 0.0)
    marker_name = rig.set_grab_point(body_name, grab_local)

    body = model.getBodySet().get(body_name)
    start = body.findStationLocationInGround(state, opensim.Vec3(*grab_local))
    origin = [start.get(i) for i in range(3)]
    print(f"[OK] Grabbed {body_name} at "
          f"({origin[0]:.3f}, {origin[1]:.3f}, {origin[2]:.3f})")

    free = solver.free_coordinates(state)
    print(f"[OK] {len(free)} free coordinates, {len(solver.couplers)} couplers, "
          f"{len(solver.loops)} loops")

    target = (origin[0] + 0.03, origin[1] + 0.02, origin[2])
    solution = solver.solve(state, marker_name, target)
    print(f"[OK] Solved: converged={solution.converged} "
          f"error={solution.marker_error * 1000:.4f} mm")

    print("\nSimulating a 60-step drag...")
    started = time.perf_counter()
    for step in range(60):
        moving = (origin[0] + 0.0005 * step, origin[1] + 0.0003 * step, origin[2])
        solution = solver.solve(state, marker_name, moving)
    elapsed_ms = (time.perf_counter() - started) * 1000
    print(f"[OK] 60 steps in {elapsed_ms:.0f} ms ({elapsed_ms / 60:.2f} ms/step, "
          f"{60000 / elapsed_ms:.0f} fps)")
    print(f"     final error {solution.marker_error * 1000:.4f} mm")

    print("\nChecking unreachable target degrades gracefully...")
    far = (origin[0] + 50.0, origin[1] + 50.0, origin[2])
    solution = solver.solve(state, marker_name, far)
    print(f"[OK] Far target: converged={solution.converged} "
          f"error={solution.marker_error:.3f}")

    print("\nChecking locked coordinates are excluded...")
    locked = model.getCoordinateSet().get(0)
    locked.setLocked(state, True)
    assert locked.getName() not in solver.free_coordinates(state)
    before = locked.getValue(state)
    solver.solve(state, marker_name, (origin[0] + 0.05, origin[1], origin[2]))
    print(f"[OK] {locked.getName()}: {before:.4f} -> {locked.getValue(state):.4f}")
    assert abs(before - locked.getValue(state)) < 1e-9, "locked coordinate moved"

    print("\n[OK] Smoke test passed!")
