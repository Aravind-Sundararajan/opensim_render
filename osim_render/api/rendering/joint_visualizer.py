"""Visualization of joint parent and child frames as coordinate axes.

Creates simple line-based axes for each joint's parent and child frames.
Uses custom line actors instead of vtkAxesActor to avoid visual clutter.
"""

from __future__ import annotations

from typing import Any

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


class JointVisualizer:
    """Create coordinate axes actors for joint parent and child frames."""

    # Default frame size (in meters). For a ~1.8m human model at typical camera
    # distance, 0.12m (12cm) axes are clearly visible without being overwhelming.
    DEFAULT_FRAME_SIZE = 0.12

    def __init__(self, model: Any, state: Any, frame_size: float = DEFAULT_FRAME_SIZE):
        """Initialize joint visualizer.

        Args:
            model: OpenSim model
            state: OpenSim state
            frame_size: Size of coordinate axes (meters)
        """
        self.model = model
        self.state = state
        self.frame_size = frame_size

    def create_all_joint_actors(self) -> dict[str, tuple[Any, Any]]:
        """Create parent and child frame actors for all joints.

        Returns:
            Dictionary mapping joint_name -> (parent_actor, child_actor)

        Raises:
            AttributeError: If model lacks getJointSet method or joint lacks required methods
            RuntimeError: If actor creation fails
        """
        joint_actors = {}

        joint_set = self.model.getJointSet()
        for i in range(joint_set.getSize()):
            joint = joint_set.get(i)
            joint_name = joint.getName()

            parent_actor, child_actor = self._create_joint_frame_actors(joint)
            joint_actors[joint_name] = (parent_actor, child_actor)

        return joint_actors

    def _create_joint_frame_actors(self, joint: Any) -> tuple[Any, Any]:
        """Create simple line-based parent and child axes actors for a single joint.

        Both use standard RGB colors (X=red, Y=green, Z=blue). Creates 3 lines per frame.

        Args:
            joint: OpenSim joint object

        Returns:
            Tuple of (parent_actor, child_actor)

        Raises:
            RuntimeError: If actor creation fails
        """
        # Create parent frame (assembly of 3 lines)
        parent_actor = self._create_frame_lines()

        # Create child frame (assembly of 3 lines)
        child_actor = self._create_frame_lines()

        return parent_actor, child_actor

    def _create_frame_lines(self) -> Any:
        """Create an assembly of 3 simple line axes.

        Returns:
            vtkAssembly containing X (red), Y (green), Z (blue) lines

        Raises:
            RuntimeError: If VTK assembly creation fails
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

    def update_joint_positions(
        self, parent_actor: Any, child_actor: Any, joint: Any
    ) -> None:
        """Update joint frame actor positions.

        Args:
            parent_actor: Parent frame vtkActor
            child_actor: Child frame vtkActor
            joint: OpenSim joint object

        Raises:
            AttributeError: If joint or actors lack required methods
            RuntimeError: If transform or matrix operations fail
        """
        parent_frame = joint.getParentFrame()
        child_frame = joint.getChildFrame()

        if parent_frame:
            transform = parent_frame.getTransformInGround(self.state)
            matrix = self._opensim_transform_to_vtk_matrix(transform)
            vtk_transform = vtk.vtkTransform()
            vtk_transform.SetMatrix(matrix)
            parent_actor.SetUserTransform(vtk_transform)

        if child_frame:
            transform = child_frame.getTransformInGround(self.state)
            matrix = self._opensim_transform_to_vtk_matrix(transform)
            vtk_transform = vtk.vtkTransform()
            vtk_transform.SetMatrix(matrix)
            child_actor.SetUserTransform(vtk_transform)

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
