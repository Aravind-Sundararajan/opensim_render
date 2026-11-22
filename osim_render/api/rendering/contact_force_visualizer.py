"""Visualization of contact forces as VTK arrow actors.

Contact forces are drawn as red arrows at each contact point, scaled by
magnitude and oriented along the force. Locating those points is the job of
contact_points; this module only turns them into geometry.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for
from osim_render.api.rendering.contact_points import (
    ContactForceType,
    ContactPoint,
    is_contact_force,
    resolve_contact_points,
)

logger = get_logger_for(__name__)

__all__ = ["ContactForceVisualizer", "ContactForceType", "ContactPoint"]


class ContactForceVisualizer:
    """Create VTK arrow actors to visualize contact forces from OpenSim models.

    Contact forces are positioned relative to their parent bodies and scaled
    by magnitude. This visualizer handles multiple force types including
    HuntCrossleyForce, SmoothSphereHalfSpaceForce, and ElasticFoundationForce.

    Metadata stores (frame_object, contact_location_vec3) — identical pattern
    to ContactVisualizer — so getTransformInGround() works for Body and
    PhysicalOffsetFrame parents without BodySet lookups.

    Attributes:
        model: OpenSim model containing forces
        state: Current OpenSim model state
        model_path: Optional path to model file
    """

    DEFAULT_COLOR = (1.0, 0.0, 0.0)
    DEFAULT_OPACITY = 1.0
    ARROW_SCALE_FACTOR = 0.001  # m/N — 1 000 N maps to a 1 m arrow

    def __init__(self, model: Any, state: Any, model_path: str | Path | None = None):
        self.model = model
        self.state = state
        self.model_path = Path(model_path) if model_path else None

    def create_all_contact_force_actors(
        self,
    ) -> tuple[dict[str, vtk.vtkActor], dict[str, ContactPoint]]:
        """Create one arrow actor per contact point in the model.

        A single force may act through several spheres, so it can contribute
        several arrows.

        Returns:
            Tuple of (actors, points), both keyed by contact point key
        """
        actors: dict[str, vtk.vtkActor] = {}
        points: dict[str, ContactPoint] = {}

        force_set = self.model.getForceSet()
        for index in range(force_set.getSize()):
            force = force_set.get(index)
            if not is_contact_force(force):
                continue

            for point in resolve_contact_points(self.model, force):
                actors[point.key] = self._create_arrow_actor()
                points[point.key] = point

        logger.info(
            f"Created {len(actors)} contact force arrows "
            f"across {len({p.force_name for p in points.values()})} forces"
        )
        return actors, points

    def update_contact_forces(
        self,
        actors: dict[str, vtk.vtkActor],
        points: dict[str, ContactPoint],
        visible_forces: set[str] | None = None,
    ) -> None:
        """Update arrow positions and scales for the current state.

        Advances the model to Dynamics stage so record values hold the computed
        forces, then places each arrow.

        An arrow is drawn only when the user has asked to see it AND its force
        is applying. Both matter: this runs every frame, so ignoring the first
        would silently override the visibility toggle.

        Args:
            actors: Map of contact point key -> vtkActor
            points: Map of contact point key -> ContactPoint
            visible_forces: Keys the user has chosen to show. None means no
                caller is managing visibility, so only the physics decides.
        """
        self.model.realizeDynamics(self.state)

        for force_name, force_points in self._group_by_force(points).items():
            self._update_one_force(actors, force_name, force_points, visible_forces)

    def _group_by_force(
        self, points: dict[str, ContactPoint]
    ) -> dict[str, list[ContactPoint]]:
        """Group contact points by their owning force.

        Record values are read once per force rather than once per arrow.

        Args:
            points: Map of contact point key -> ContactPoint

        Returns:
            Map of force name -> its contact points
        """
        grouped: dict[str, list[ContactPoint]] = {}
        for point in points.values():
            grouped.setdefault(point.force_name, []).append(point)
        return grouped

    def _update_one_force(
        self,
        actors: dict[str, vtk.vtkActor],
        force_name: str,
        points: list[ContactPoint],
        visible_forces: set[str] | None,
    ) -> None:
        """Update every arrow belonging to a single force.

        Args:
            actors: Map of contact point key -> vtkActor
            force_name: Name of the owning force
            points: Contact points belonging to that force
            visible_forces: Keys the user wants shown, or None if unmanaged
        """
        force = self.model.getForceSet().get(force_name)
        applying = bool(force.appliesForce(self.state))
        record_values = force.getRecordValues(self.state) if applying else None

        for point in points:
            actor = actors.get(point.key)
            if actor is None:
                continue

            if not applying or not self._is_wanted(point, visible_forces):
                actor.SetVisibility(False)
                continue

            self._update_force_actor(actor, point, record_values)

    def _is_wanted(
        self, point: ContactPoint, visible_forces: set[str] | None
    ) -> bool:
        """Whether the user has asked for this arrow.

        Args:
            point: Contact point to test
            visible_forces: Keys the user wants shown, or None if unmanaged

        Returns:
            True when the user wants this arrow drawn
        """
        return visible_forces is None or point.key in visible_forces

    def _create_arrow_actor(self) -> vtk.vtkActor:
        arrow_source = vtk.vtkArrowSource()
        arrow_source.SetTipLength(0.35)
        arrow_source.SetTipRadius(0.1)
        arrow_source.SetShaftRadius(0.03)
        arrow_source.SetShaftResolution(16)
        arrow_source.SetTipResolution(16)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(arrow_source.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*self.DEFAULT_COLOR)
        actor.GetProperty().SetOpacity(self.DEFAULT_OPACITY)

        return actor

    def _update_force_actor(
        self,
        actor: vtk.vtkActor,
        point: ContactPoint,
        record_values: Any,
    ) -> None:
        """Place and scale a single arrow at its contact point.

        Args:
            actor: vtkActor to update
            point: Contact point being drawn
            record_values: Record output of the point's force
        """
        position = point.location_in_ground(self.state, self.model.getGround())
        force_vector = point.force_vector(record_values)
        magnitude = math.sqrt(sum(v * v for v in force_vector))
        scale = max(0.01, min(magnitude * self.ARROW_SCALE_FACTOR, 5.0))

        actor.SetUserTransform(
            self._create_force_transform(position, force_vector, scale)
        )
        actor.SetVisibility(True)

    def _create_force_transform(
        self,
        position: tuple[float, float, float],
        force_vector: tuple[float, float, float],
        scale: float,
    ) -> vtk.vtkTransform:
        """Build the arrow's full transform: translate to the contact point,
        rotate the +X arrow onto the force direction, then scale.

        Composed in this order (vtkTransform is pre-multiply by default) so the
        arrow's base sits at the contact point and its tip follows the force,
        rather than the rotation displacing the arrow about the world origin.
        """
        normalized = self._normalize_vector(force_vector)
        rotation_angle, rotation_axis = self._compute_rotation_to_vector(normalized)

        transform = vtk.vtkTransform()
        transform.Translate(*position)
        if rotation_angle > 0.001:
            transform.RotateWXYZ(math.degrees(rotation_angle), *rotation_axis)
        transform.Scale(scale, scale, scale)

        return transform

    def _normalize_vector(
        self, vector: tuple[float, float, float]
    ) -> tuple[float, float, float]:
        fx, fy, fz = vector
        length = math.sqrt(fx * fx + fy * fy + fz * fz)

        if length < 0.001:
            return (0.0, 1.0, 0.0)

        return (fx / length, fy / length, fz / length)

    def _compute_rotation_to_vector(
        self, target_vector: tuple[float, float, float]
    ) -> tuple[float, tuple[float, float, float]]:
        """Rotation aligning the arrow's default +X axis with target_vector.

        vtkArrowSource points along +X, so the rotation is measured from +X to
        the (already normalized) force direction. Returns (angle_radians, axis).
        """
        arrow_axis = (1.0, 0.0, 0.0)
        fx, fy, fz = target_vector

        axis = (
            arrow_axis[1] * fz - arrow_axis[2] * fy,
            arrow_axis[2] * fx - arrow_axis[0] * fz,
            arrow_axis[0] * fy - arrow_axis[1] * fx,
        )
        axis_len = math.sqrt(axis[0] * axis[0] + axis[1] * axis[1] + axis[2] * axis[2])
        cos_angle = arrow_axis[0] * fx + arrow_axis[1] * fy + arrow_axis[2] * fz

        if axis_len < 0.001:
            if cos_angle < 0.0:
                return (math.pi, (0.0, 0.0, 1.0))
            return (0.0, (1.0, 0.0, 0.0))

        angle = math.atan2(axis_len, cos_angle)
        normalized_axis = (axis[0] / axis_len, axis[1] / axis_len, axis[2] / axis_len)

        return (angle, normalized_axis)


if __name__ == "__main__":
    """Smoke test for ContactForceVisualizer."""
    print("ContactForceVisualizer smoke test")
    print(f"Supported force types: {[e.value for e in ContactForceType]}")
    print("Run contact_points for per-model resolution detail.")
    print("[OK] ContactForceVisualizer module loaded successfully")
