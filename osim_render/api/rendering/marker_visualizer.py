"""Visualization of anatomical markers.

Creates small VTK sphere actors at marker locations in the model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for
from osim_render.api.opensim_protocols import FrameProtocol
from osim_render.api.posing.drag_marker_rig import is_drag_marker

logger = get_logger_for(__name__)


class MarkerProtocol(Protocol):
    """Protocol for OpenSim Marker objects."""

    def getName(self) -> str:
        """Get the name of this marker."""
        ...

    def getParentFrame(self) -> FrameProtocol:
        """Get the frame this marker is attached to (must not be None)."""
        ...

    def get_location(self) -> Any:
        """Get marker's location in its frame."""
        ...


class MarkerVisualizer:
    """Create VTK actors for anatomical markers.

    Markers are typically used for motion capture and represent
    anatomical landmarks on the body.
    """

    DEFAULT_RADIUS = 0.005  # 5mm spheres
    DEFAULT_COLOR = (0.0, 1.0, 0.0)  # Green
    DEFAULT_OPACITY = 1.0

    def __init__(self, model: Any, state: Any, model_path: str | Path | None = None):
        """Initialize marker visualizer.

        Args:
            model: OpenSim model (must have getMarkerSet() method)
            state: OpenSim state (for coordinate transformations)
            model_path: Path to model file (for reference, may not be used)

        Raises:
            ValueError: If model is None
        """
        if model is None:
            raise ValueError("Model cannot be None")
        self.model = model
        self.state = state
        self.model_path = Path(model_path) if model_path else None

    def create_all_marker_actors(self) -> tuple[dict[str, Any], dict[str, str]]:
        """Create actors for all markers in the model.

        Returns:
            Tuple of (marker_actors dict, marker_metadata dict)
            - marker_actors: Dictionary mapping marker_name -> vtkActor
            - marker_metadata: Dictionary mapping marker_name -> body_name (frame name)

        Raises:
            AttributeError: If model has no marker set or marker set operations fail
        """
        marker_actors = {}
        marker_metadata = {}

        marker_set = self.model.getMarkerSet()
        for i in range(marker_set.getSize()):
            marker = marker_set.get(i)
            marker_name = marker.getName()

            if is_drag_marker(marker_name):
                continue

            actor = self._create_marker_actor(marker)
            if actor:
                marker_actors[marker_name] = actor

                # Store which body/frame this marker is attached to
                frame = marker.getParentFrame()
                if frame is None:
                    raise ValueError(f"Marker {marker_name} has no frame attached")
                body_name = frame.getName()
                if body_name is None:
                    raise ValueError(f"Frame for marker {marker_name} has no name")
                marker_metadata[marker_name] = body_name

        return marker_actors, marker_metadata

    def _create_marker_actor(self, marker: MarkerProtocol) -> Any:
        """Create VTK actor for a single marker.

        Args:
            marker: OpenSim marker object

        Returns:
            vtkActor positioned at marker location

        Raises:
            RuntimeError: If VTK geometry creation fails
            ValueError: If marker location cannot be determined
        """
        # Create small sphere for marker
        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(self.DEFAULT_RADIUS)
        sphere.SetThetaResolution(16)
        sphere.SetPhiResolution(16)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        # Apply default appearance
        actor.GetProperty().SetColor(*self.DEFAULT_COLOR)
        actor.GetProperty().SetOpacity(self.DEFAULT_OPACITY)

        # Position at marker location (will be updated dynamically)
        self._update_marker_position(actor, marker)

        return actor

    def _update_marker_position(self, actor: Any, marker: MarkerProtocol) -> None:
        """Position marker actor at current marker location.

        Args:
            actor: vtkActor to position
            marker: OpenSim marker object

        Raises:
            ValueError: If marker frame is None
            RuntimeError: If coordinate transformation fails
        """
        import opensim

        # Get marker's frame
        frame = marker.getParentFrame()
        if frame is None:
            raise ValueError(f"Marker {marker.getName()} has no frame attached")

        # Get frame's transform in ground
        frame_transform = frame.getTransformInGround(self.state)

        # Get marker's location in the frame
        marker_location = marker.get_location()

        # Compose frame_transform with marker offset to get world transform.
        # Using compose() avoids the unsupported Rotation * Vec3 multiplication.
        marker_offset = opensim.Transform(marker_location)
        world_transform = frame_transform.compose(marker_offset)

        # Convert to VTK matrix and apply
        matrix = self._opensim_transform_to_vtk_matrix(world_transform)
        vtk_transform = vtk.vtkTransform()
        vtk_transform.SetMatrix(matrix)
        actor.SetUserTransform(vtk_transform)

    def update_marker_positions(self, marker_actors: dict[str, Any]) -> None:
        """Update marker positions based on current state.

        Called whenever the model state changes to reposition markers.

        Args:
            marker_actors: Dictionary mapping marker_name -> vtkActor

        Raises:
            AttributeError: If model has no marker set
            ValueError: If marker cannot be positioned
        """
        marker_set = self.model.getMarkerSet()

        for i in range(marker_set.getSize()):
            marker = marker_set.get(i)
            marker_name = marker.getName()

            if marker_name not in marker_actors:
                continue

            actor = marker_actors[marker_name]
            self._update_marker_position(actor, marker)

    def _opensim_transform_to_vtk_matrix(self, transform: Any) -> Any:
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

        # Get rotation matrix elements
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
