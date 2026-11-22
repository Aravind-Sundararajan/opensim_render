"""Visualization of body origin frames as coordinate axes.

Creates simple line-based axes for each body's origin frame showing X/Y/Z axes.
Uses custom line actors instead of vtkAxesActor to avoid visual clutter.
"""

from __future__ import annotations

from typing import Any

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


class FrameVisualizer:
    """Create coordinate axes actors for body origin frames."""

    # Default frame size (in meters). For a ~1.8m human model at typical camera
    # distance, 0.15m (15cm) axes are clearly visible without being overwhelming.
    DEFAULT_FRAME_SIZE = 0.15

    def __init__(self, model: Any, state: Any, frame_size: float = DEFAULT_FRAME_SIZE):
        """Initialize frame visualizer.

        Args:
            model: OpenSim model
            state: OpenSim state
            frame_size: Size of coordinate axes (meters)
        """
        self.model = model
        self.state = state
        self.frame_size = frame_size

    def create_all_frame_actors(self) -> dict[str, Any]:
        """Create frame actors for all bodies.

        Returns:
            Dictionary mapping body_name -> vtkActor (assembly of line axes)

        Raises:
            AttributeError: If model lacks getBodyList or getGround methods
            RuntimeError: If actor creation fails
        """
        frame_actors = {}

        body_list = self.model.getBodyList()
        ground = self.model.getGround()
        ground_name = ground.getName()

        for body in body_list:
            body_name = body.getName()

            # Skip ground body (frame at origin is redundant)
            if body_name == ground_name:
                continue

            actor = self._create_frame_actor(body_name)
            frame_actors[body_name] = actor

        return frame_actors

    def _create_frame_actor(self, body_name: str) -> Any:
        """Create simple line-based axes actor for a single body frame.

        Creates 3 simple lines (X=red, Y=green, Z=blue) without arrows or labels.

        Args:
            body_name: Name of the body

        Returns:
            vtkActor (assembly of 3 line actors)

        Raises:
            RuntimeError: If VTK assembly or line creation fails
        """
        # Create an assembly to hold all 3 axes
        assembly = vtk.vtkAssembly()

        # X-axis (Red)
        x_actor = self._create_axis_line((1, 0, 0), (1.0, 0.0, 0.0))
        assembly.AddPart(x_actor)

        # Y-axis (Green)
        y_actor = self._create_axis_line((0, 1, 0), (0.0, 1.0, 0.0))
        assembly.AddPart(y_actor)

        # Z-axis (Blue)
        z_actor = self._create_axis_line((0, 0, 1), (0.0, 0.0, 1.0))
        assembly.AddPart(z_actor)

        return assembly

    def _create_axis_line(
        self, direction: tuple[float, float, float], color: tuple[float, float, float]
    ) -> Any:
        """Create a single axis line.

        Args:
            direction: Direction vector (x, y, or z)
            color: RGB color tuple

        Returns:
            vtkActor

        Raises:
            RuntimeError: If VTK line or actor creation fails
        """
        # Create line from origin to direction * frame_size
        line = vtk.vtkLineSource()
        line.SetPoint1(0, 0, 0)
        line.SetPoint2(
            direction[0] * self.frame_size,
            direction[1] * self.frame_size,
            direction[2] * self.frame_size,
        )

        # Create mapper and actor
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(line.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetLineWidth(3.0)

        return actor

    def update_frame_position(self, actor: Any, body_name: str) -> None:
        """Update frame actor position to follow body.

        Args:
            actor: vtkActor to update
            body_name: Name of the body

        Raises:
            AttributeError: If model or actor lacks required methods
            RuntimeError: If transform or matrix operations fail
        """
        body = self.model.getBodySet().get(body_name)
        if not body:
            raise ValueError(f"Body not found: {body_name}")

        transform = body.getTransformInGround(self.state)
        matrix = self._opensim_transform_to_vtk_matrix(transform)

        vtk_transform = vtk.vtkTransform()
        vtk_transform.SetMatrix(matrix)
        actor.SetUserTransform(vtk_transform)

    def _opensim_transform_to_vtk_matrix(self, transform: Any) -> Any:
        """Convert OpenSim Transform to VTK matrix4x4.

        Args:
            transform: OpenSim Transform object with R() and p() methods

        Returns:
            vtkMatrix4x4 with rotation and translation

        Raises:
            AttributeError: If transform lacks required methods (R, p, asMat33)
            RuntimeError: If matrix operations fail
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
