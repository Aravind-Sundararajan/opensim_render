"""Visualization of muscle paths as tubes.

Creates tube actors along muscle paths showing the line of action.
"""

from __future__ import annotations

from typing import Any, Protocol

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for
from osim_render.api.opensim_protocols import FrameProtocol

logger = get_logger_for(__name__)


class PathPointProtocol(Protocol):
    """Protocol for OpenSim path point objects."""

    def getName(self) -> str:
        """Get name of this path point."""
        ...

    def getLocationInGround(self, state: Any) -> Any:
        """Get location in ground frame."""
        ...


class ArrayPathPointProtocol(Protocol):
    """Protocol for ArrayPathPoint (current path from muscle)."""

    def size(self) -> int:
        """Get number of points in path."""
        ...

    def get(self, index: int) -> PathPointProtocol:
        """Get point at index."""
        ...

    def findIndex(self, point: PathPointProtocol) -> int:
        """Find index of a specific path point (-1 if not found)."""
        ...


class MuscleVisualizer:
    """Create tube actors for muscle paths."""

    # Default muscle appearance
    DEFAULT_RADIUS = 0.005  # Meters
    DEFAULT_COLOR = (1.0, 0.0, 0.0)  # Red (active)
    PASSIVE_COLOR = (0.6, 0.6, 0.6)  # Gray (passive)

    def __init__(self, model: Any, state: Any, tube_radius: float = DEFAULT_RADIUS):
        """Initialize muscle visualizer.

        Args:
            model: OpenSim model
            state: OpenSim state
            tube_radius: Radius of tube representation (meters)
        """
        self.model = model
        self.state = state
        self.tube_radius = tube_radius

    def create_all_muscle_actors(self) -> dict[str, Any]:
        """Create actors for all muscles.

        Returns:
            Dictionary mapping muscle_name -> vtkActor

        Raises:
            AttributeError: If model has no getMuscles() method
            RuntimeError: If muscle actor creation fails
        """
        muscle_actors = {}

        muscles = self.model.getMuscles()
        for i in range(muscles.getSize()):
            muscle = muscles.get(i)
            muscle_name = muscle.getName()

            actor = self._create_muscle_actor(muscle)
            if actor is not None:
                muscle_actors[muscle_name] = actor

        return muscle_actors

    def _create_muscle_actor(self, muscle: Any) -> Any | None:
        """Create tube actor for a single muscle.

        Uses the algorithm from opensim-gui: segment-based wrapping detection
        with intelligent point sampling along wrap paths.

        Args:
            muscle: OpenSim muscle object

        Returns:
            vtkActor or None if muscle has insufficient path points

        Raises:
            AttributeError: If muscle or its paths lack required methods
            RuntimeError: If VTK geometry creation fails
            ValueError: If path transformation fails
        """
        # Muscles using a FunctionBasedPath (e.g. Moco DeGrooteFregly2016Muscle)
        # have no GeometryPath to visualize - getGeometryPath() would raise.
        if not muscle.hasVisualPath():
            logger.debug(f"Muscle {muscle.getName()} has no visual path, skipping")
            return None

        # Get geometry path
        geom_path = muscle.getGeometryPath()
        if not geom_path:
            logger.warning(f"Muscle {muscle.getName()} has no geometry path")
            return None

        # Get the path point set (property-defined points) and current path (computed)
        path_point_set = geom_path.getPathPointSet()
        if path_point_set.getSize() < 2:
            logger.warning(
                f"Muscle {muscle.getName()} has fewer than 2 path points")
            return None

        current_path = geom_path.getCurrentPath(self.state)
        if current_path.size() < 2:
            logger.warning(
                f"Muscle {muscle.getName()} has fewer than 2 computed path points"
            )
            return None

        # Get ground frame for coordinate transformations
        ground_frame = self._get_ground_frame()

        # Create polyline by processing segments between property points
        points = vtk.vtkPoints()

        for seg_idx in range(path_point_set.getSize() - 1):
            first_point = path_point_set.get(seg_idx)
            second_point = path_point_set.get(seg_idx + 1)

            # Find these points in the computed path
            first_index = current_path.findIndex(first_point)
            second_index = current_path.findIndex(second_point)

            # Handle different segment types
            if first_index == -1:
                # First point is inactive, skip this segment
                continue

            # Add the first point (it's active)
            first_loc = first_point.getLocationInGround(self.state)
            points.InsertNextPoint(first_loc.get(
                0), first_loc.get(1), first_loc.get(2))

            if second_index == -1:
                # Second point is inactive (conditional path point)
                # Add the inactive point at its computed location
                # and skip to the next active point
                second_loc = second_point.getLocationInGround(self.state)
                points.InsertNextPoint(
                    second_loc.get(0), second_loc.get(1), second_loc.get(2)
                )
                # Continue to next segment (will find next active point)
                continue

            # Check if there's wrapping in this segment
            if second_index == first_index + 1:
                # No wrapping - adjacent points
                pass  # Will add second point below
            else:
                # Wrapping detected - there are PathWrapPoints between
                self._add_wrap_path_points(
                    current_path, first_index, second_index, ground_frame, points
                )

            # Add the second point
            second_loc = second_point.getLocationInGround(self.state)
            points.InsertNextPoint(
                second_loc.get(0), second_loc.get(1), second_loc.get(2)
            )

        if points.GetNumberOfPoints() < 2:
            logger.warning(
                f"Muscle {muscle.getName()} has fewer than 2 points after processing"
            )
            return None

        # Create polyline
        polyline = vtk.vtkPolyLine()
        polyline.GetPointIds().SetNumberOfIds(points.GetNumberOfPoints())
        for i in range(points.GetNumberOfPoints()):
            polyline.GetPointIds().SetId(i, i)

        # Create cell array and polydata
        cells = vtk.vtkCellArray()
        cells.InsertNextCell(polyline)

        poly_data = vtk.vtkPolyData()
        poly_data.SetPoints(points)
        poly_data.SetLines(cells)

        # Apply tube filter for visibility
        tube_filter = vtk.vtkTubeFilter()
        tube_filter.SetInputData(poly_data)
        tube_filter.SetRadius(self.tube_radius)
        tube_filter.SetNumberOfSides(8)

        # Create mapper and actor
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(tube_filter.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        # Set color (red for now, could update based on activation)
        actor.GetProperty().SetColor(*self.DEFAULT_COLOR)

        return actor

    def _get_ground_frame(self) -> Any:
        """Get the ground frame from the model.

        Returns:
            Ground frame object

        Raises:
            AttributeError: If model has no getGround() method
        """
        return self.model.getGround()

    def _add_wrap_path_points(
        self,
        current_path: ArrayPathPointProtocol,
        first_index: int,
        second_index: int,
        ground_frame: FrameProtocol,
        points: Any,
    ) -> None:
        """Add intelligent sampled points from wrap paths between two indices.

        Uses opensim-gui algorithm:
        1. Count total surface points from all PathWrapPoints
        2. Allocate visualization points proportionally
        3. Sample evenly across each wrap path
        4. Transform to ground frame

        Args:
            current_path: ArrayPathPoint from getCurrentPath()
            first_index: Index of first point in current_path
            second_index: Index of second point in current_path
            ground_frame: Ground frame for coordinate transformation
            points: vtkPoints object to add points to

        Raises:
            ImportError: If opensim module cannot be imported
            AttributeError: If wrap objects lack expected methods
            RuntimeError: If wrap point transformation fails
        """
        import opensim

        # Count total surface points from all PathWrapPoints in this segment
        total_surface_points = 0
        wrap_path_info = {}  # Map index to wrap point and its surface points

        for wrap_idx in range(first_index + 1, second_index):
            wrap_point = current_path.get(wrap_idx)
            wrap_point_obj = opensim.PathWrapPoint.safeDownCast(wrap_point)

            if wrap_point_obj:
                surface_points = wrap_point_obj.getWrapPath(self.state)
                # Call size() method - raises AttributeError if not available
                size = surface_points.size()

                if size > 0:
                    wrap_path_info[wrap_idx] = (
                        wrap_point_obj,
                        surface_points,
                        size,
                    )
                    total_surface_points += size

        if total_surface_points == 0:
            # No wrap points or no surface points
            return

        # Allocate visualization points proportionally
        # Using opensim-gui approach: 8 points per wrap object in segment
        num_wrap_objects = len(wrap_path_info)
        num_intermediate_points = 8 * num_wrap_objects

        # Add sampled points from each wrap path
        for (
            wrap_point_obj,
            surface_points,
            size,
        ) in wrap_path_info.values():
            # Calculate how many points to visualize for this wrap
            num_vis_points = (
                size * num_intermediate_points) // total_surface_points
            if num_vis_points == 0:
                num_vis_points = 1  # At least one point

            # Sample indices evenly across the wrap path
            if num_vis_points == 1:
                # Use middle point
                idx = size // 2
                self._add_single_wrap_point(
                    surface_points, idx, wrap_point_obj, ground_frame, points
                )
            else:
                # Sample evenly from first to last
                for j in range(num_vis_points):
                    # Sample index: j * (size-1) / (num_vis_points-1)
                    idx = (j * (size - 1)) // (num_vis_points - 1)
                    self._add_single_wrap_point(
                        surface_points, idx, wrap_point_obj, ground_frame, points
                    )

    def _add_single_wrap_point(
        self,
        surface_points: Any,
        index: int,
        wrap_point_obj: Any,
        ground_frame: FrameProtocol,
        points: Any,
    ) -> None:
        """Add a single wrap surface point to the visualization.

        Args:
            surface_points: Array of surface points from wrap path
            index: Index into surface_points array
            wrap_point_obj: PathWrapPoint object
            ground_frame: Ground frame for transformation
            points: vtkPoints object to add to

        Raises:
            AttributeError: If wrap point lacks required methods
            RuntimeError: If coordinate transformation fails
        """
        surface_point = surface_points.get(index)
        frame = wrap_point_obj.getParentFrame()

        # Transform from frame coordinates to ground frame
        # Use findStationLocationInAnotherFrame for proper coordinate transformation
        ground_loc = frame.findStationLocationInAnotherFrame(
            self.state, surface_point, ground_frame
        )

        points.InsertNextPoint(ground_loc.get(
            0), ground_loc.get(1), ground_loc.get(2))

    def update_muscle_paths(self, actors: dict[str, Any]) -> None:
        """Rebuild muscle path geometry (wrapping points change with joint angles).

        This is the most expensive update operation and should only be called
        if muscles are visible.

        Args:
            actors: Dictionary mapping muscle_name -> vtkActor

        Raises:
            AttributeError: If model has no getMuscles() method
            RuntimeError: If muscle path updates fail
        """
        muscles = self.model.getMuscles()
        for i in range(muscles.getSize()):
            muscle = muscles.get(i)
            muscle_name = muscle.getName()

            if muscle_name not in actors:
                continue

            # Rebuild geometry for this muscle
            new_actor = self._create_muscle_actor(muscle)
            if new_actor is not None:
                # Update the existing actor's mapper
                old_actor = actors[muscle_name]
                old_actor.SetMapper(new_actor.GetMapper())
