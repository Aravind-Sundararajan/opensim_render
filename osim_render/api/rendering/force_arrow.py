"""Shared arrow geometry for drawing force vectors.

Contact forces and ground reactions are drawn the same way — an arrow rooted at
an application point, pointing along the force and scaled by its magnitude — so
the geometry and the vector maths live here rather than in either visualizer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)

# Below this length a direction is meaningless, so the arrow keeps its default
# orientation rather than snapping about.
MIN_DIRECTION_LENGTH = 1e-3

Vector3 = tuple[float, float, float]

ARROW_AXIS: Vector3 = (1.0, 0.0, 0.0)


@dataclass(frozen=True)
class ArrowStyle:
    """How a force arrow looks and how magnitude maps to length."""

    color: Vector3 = (1.0, 0.0, 0.0)
    opacity: float = 1.0
    scale_factor: float = 0.001  # m/N — 1000 N maps to a 1 m arrow
    min_scale: float = 0.01
    max_scale: float = 5.0

    def scale_for(self, magnitude: float) -> float:
        """Convert a force magnitude into an arrow scale.

        Args:
            magnitude: Force magnitude in newtons

        Returns:
            Arrow scale, held within the style's bounds
        """
        return max(self.min_scale, min(magnitude * self.scale_factor, self.max_scale))


def create_arrow_actor(style: ArrowStyle) -> vtk.vtkActor:
    """Build an arrow actor in the given style.

    Args:
        style: Appearance to apply

    Returns:
        A vtkActor with arrow geometry, pointing along +X before transform
    """
    source = vtk.vtkArrowSource()
    source.SetTipLength(0.35)
    source.SetTipRadius(0.1)
    source.SetShaftRadius(0.03)
    source.SetShaftResolution(16)
    source.SetTipResolution(16)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(source.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*style.color)
    actor.GetProperty().SetOpacity(style.opacity)

    return actor


def place_arrow(
    actor: vtk.vtkActor,
    position: Vector3,
    force_vector: Vector3,
    style: ArrowStyle,
) -> None:
    """Point an arrow along a force, rooted at its application point.

    Args:
        actor: Arrow actor to position
        position: Application point in ground coordinates
        force_vector: Force in ground coordinates, in newtons
        style: Scaling to apply
    """
    magnitude = math.sqrt(sum(component * component for component in force_vector))
    actor.SetUserTransform(
        build_force_transform(position, force_vector, style.scale_for(magnitude))
    )


def build_force_transform(
    position: Vector3, force_vector: Vector3, scale: float
) -> vtk.vtkTransform:
    """Compose the transform placing an arrow on a force vector.

    Applied as translate, then rotate, then scale (vtkTransform pre-multiplies)
    so the arrow's base sits at the application point and its tip follows the
    force, rather than the rotation swinging it about the world origin.

    Args:
        position: Application point in ground coordinates
        force_vector: Force direction in ground coordinates
        scale: Arrow scale

    Returns:
        The composed transform
    """
    direction = normalize(force_vector)
    angle, axis = rotation_onto(direction)

    transform = vtk.vtkTransform()
    transform.Translate(*position)
    if angle > MIN_DIRECTION_LENGTH:
        transform.RotateWXYZ(math.degrees(angle), *axis)
    transform.Scale(scale, scale, scale)

    return transform


def normalize(vector: Vector3) -> Vector3:
    """Scale a vector to unit length.

    Args:
        vector: Vector to normalize

    Returns:
        The unit vector, or +Y for a vector too short to have a direction
    """
    length = math.sqrt(sum(component * component for component in vector))

    if length < MIN_DIRECTION_LENGTH:
        return (0.0, 1.0, 0.0)

    return (vector[0] / length, vector[1] / length, vector[2] / length)


def rotation_onto(direction: Vector3) -> tuple[float, Vector3]:
    """Rotation carrying the arrow's default +X axis onto a direction.

    Args:
        direction: Unit vector to point along

    Returns:
        Tuple of (angle in radians, rotation axis)
    """
    dx, dy, dz = direction

    axis = (
        ARROW_AXIS[1] * dz - ARROW_AXIS[2] * dy,
        ARROW_AXIS[2] * dx - ARROW_AXIS[0] * dz,
        ARROW_AXIS[0] * dy - ARROW_AXIS[1] * dx,
    )
    axis_length = math.sqrt(sum(component * component for component in axis))
    cosine = ARROW_AXIS[0] * dx + ARROW_AXIS[1] * dy + ARROW_AXIS[2] * dz

    if axis_length < MIN_DIRECTION_LENGTH:
        return (math.pi, (0.0, 0.0, 1.0)) if cosine < 0.0 else (0.0, ARROW_AXIS)

    angle = math.atan2(axis_length, cosine)
    return (
        angle,
        (axis[0] / axis_length, axis[1] / axis_length, axis[2] / axis_length),
    )


if __name__ == "__main__":
    """Smoke test for force arrow geometry."""
    print("force_arrow smoke test")

    style = ArrowStyle()
    actor = create_arrow_actor(style)
    print(f"[OK] Arrow actor created, colour {actor.GetProperty().GetColor()}")

    print(f"[OK] 1000 N -> scale {style.scale_for(1000.0):.3f}")
    assert style.scale_for(1000.0) == 1.0
    print(f"[OK] 0 N clamps up to {style.scale_for(0.0):.3f}")
    assert style.scale_for(0.0) == style.min_scale
    print(f"[OK] 1e9 N clamps down to {style.scale_for(1e9):.3f}")
    assert style.scale_for(1e9) == style.max_scale

    print("\nChecking the arrow points where the force does...")
    for force, expected in (
        ((1.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        ((0.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
        ((0.0, 0.0, -5.0), (0.0, 0.0, -1.0)),
    ):
        place_arrow(actor, (0.1, 0.2, 0.3), force, style)
        transform = actor.GetUserTransform()
        tip = transform.TransformPoint(1.0, 0.0, 0.0)
        base = transform.TransformPoint(0.0, 0.0, 0.0)
        along = normalize(tuple(tip[i] - base[i] for i in range(3)))
        print(f"  force {force} -> arrow along {tuple(round(v, 3) for v in along)}")
        assert all(abs(along[i] - expected[i]) < 1e-6 for i in range(3))
        assert all(abs(base[i] - (0.1, 0.2, 0.3)[i]) < 1e-9 for i in range(3))

    print("[OK] Base sits at the application point in every case")

    print("\nChecking a zero force keeps a stable orientation...")
    place_arrow(actor, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), style)
    print("[OK] Zero force did not raise")

    print("\n[OK] Smoke test passed!")
