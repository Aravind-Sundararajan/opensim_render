"""Shared actor-positioning utilities for OpenSim model visualization.

Free functions that position VTK actors according to OpenSim model state.
Shared by the scene builder and the per-frame update family.
"""

from __future__ import annotations

from typing import Any

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


def opensim_transform_to_vtk_matrix(transform: Any) -> vtk.vtkMatrix4x4:
    """Convert OpenSim Transform to VTK matrix4x4.

    Args:
        transform: OpenSim Transform object with R() and p() methods

    Returns:
        vtkMatrix4x4 with proper rotation and translation

    Raises:
        AttributeError: If transform lacks required methods (R, p, asMat33)
        RuntimeError: If matrix element setting fails
    """
    matrix = vtk.vtkMatrix4x4()

    rotation = transform.R()
    translation = transform.p()

    # Get rotation matrix elements using asMat33().get(i, j)
    rot_mat = rotation.asMat33()
    for i in range(3):
        for j in range(3):
            val = rot_mat.get(i, j)
            matrix.SetElement(i, j, val)

    # Set translation
    matrix.SetElement(0, 3, translation.get(0))
    matrix.SetElement(1, 3, translation.get(1))
    matrix.SetElement(2, 3, translation.get(2))

    # Set homogeneous coordinate
    matrix.SetElement(3, 3, 1.0)

    return matrix


def update_body_position(
    actor: vtk.vtkActor, body_name: str, model: Any, state: Any
) -> None:
    """Position body actor according to current model state."""
    if model is None:
        return

    # Use getBodySet().get() to retrieve body by name directly
    body = model.getBodySet().get(body_name)
    if not body:
        logger.warning(f"Body not found: {body_name}")
        return

    transform = body.getTransformInGround(state)
    matrix = opensim_transform_to_vtk_matrix(transform)

    vtk_transform = vtk.vtkTransform()
    vtk_transform.SetMatrix(matrix)
    actor.SetUserTransform(vtk_transform)


def create_mass_center_actor(
    body_name: str, model: Any, state: Any
) -> vtk.vtkActor | None:
    """Create a small sphere actor at body's mass center.

    Args:
        body_name: Name of the body
        model: OpenSim model
        state: OpenSim model state

    Returns:
        vtkActor or None if body not found

    Raises:
        AttributeError: If body lacks required methods
        RuntimeError: If VTK geometry creation fails
    """
    body = model.getBodySet().get(body_name)
    if body is None:
        return None

    # Create small sphere
    sphere = vtk.vtkSphereSource()
    sphere.SetRadius(0.005)  # 5mm radius
    sphere.SetThetaResolution(8)
    sphere.SetPhiResolution(8)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(sphere.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(1.0, 0.843, 0.0)  # Gold color

    # Position at mass center
    update_mass_center_position(actor, body_name, model, state)

    return actor


def update_mass_center_position(
    actor: vtk.vtkActor, body_name: str, model: Any, state: Any
) -> None:
    """Position mass center actor at body COM.

    Args:
        actor: vtkActor to position
        body_name: Name of the body
        model: OpenSim model
        state: OpenSim model state

    Raises:
        ValueError: If body not found in model
        AttributeError: If body lacks required methods
        RuntimeError: If transform update fails
    """
    body = model.getBodySet().get(body_name)
    if body is None:
        raise ValueError(f"Body {body_name} not found in model")

    # For now, place mass center sphere at body origin
    # (exact COM offset would require more complex transform math)
    transform = body.getTransformInGround(state)
    matrix = opensim_transform_to_vtk_matrix(transform)

    vtk_transform = vtk.vtkTransform()
    vtk_transform.SetMatrix(matrix)
    actor.SetUserTransform(vtk_transform)


if __name__ == "__main__":
    print("[OK] actor_transforms imports cleanly")
