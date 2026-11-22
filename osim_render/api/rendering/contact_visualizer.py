"""Visualization of contact geometry.

Creates VTK actors for contact surfaces like half-spaces, spheres, and meshes.
Uses OpenSim's generateDecorations() API to get proper transforms, colors, and opacity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import opensim

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for
from osim_render.api.opensim_protocols import FrameProtocol
from osim_render.api.rendering.mesh_reader import read_polydata

logger = get_logger_for(__name__)


class ContactGeometryProtocol(Protocol):
    """Protocol for OpenSim ContactGeometry objects."""

    def getName(self) -> str:
        """Get the name of this contact geometry."""
        ...

    def getFrame(self) -> FrameProtocol:
        """Get the frame this contact is attached to."""
        ...

    def getTransform(self) -> Any:
        """Get the contact's local transform in its frame."""
        ...

    def getLocation(self) -> Any:
        """Get the contact's location as Vec3."""
        ...

    def getConcreteClassName(self) -> str:
        """Get the concrete class name."""
        ...

    def generateDecorations(
        self, fixed: bool, hints: Any, state: Any, decorations: Any
    ) -> None:
        """Generate decorative geometry."""
        ...


class ContactVisualizer:
    """Create VTK actors for contact geometry.

    Uses OpenSim's generateDecorations() API to visualize contact objects with
    proper transforms, colors, and opacity that match opensim-gui rendering.
    """

    def __init__(self, model: Any, state: Any, model_path: str | Path | None = None):
        """Initialize contact visualizer.

        Args:
            model: OpenSim model
            state: OpenSim state
            model_path: Path to model file (for resolving relative mesh paths)

        Raises:
            ValueError: If model or state is None
        """
        if model is None:
            raise ValueError("Model cannot be None")
        if state is None:
            raise ValueError("State cannot be None")
        self.model = model
        self.state = state
        self.model_path = Path(model_path) if model_path else None

    def create_all_contact_actors(
        self,
    ) -> tuple[dict[str, Any], dict[str, tuple[str, Any]]]:
        """Create actors for all contact geometry.

        Uses OpenSim's generateDecorations() to get proper transforms and appearance.

        Returns:
            Tuple of (contact_actors dict, contact_metadata dict)
            - contact_actors: Dictionary mapping contact_name -> vtkActor
            - contact_metadata: Dictionary mapping contact_name -> (parent_frame, contact_local_transform)

        Raises:
            AttributeError: If model has no contact geometry set
            RuntimeError: If contact actor creation fails
        """
        contact_actors = {}
        contact_metadata = {}

        contact_set = self.model.getContactGeometrySet()
        num_contacts = contact_set.getSize()
        logger.info(f"Creating contact actors: found {num_contacts} contact geometries")

        for i in range(num_contacts):
            contact = contact_set.get(i)
            contact_name = contact.getName()

            actor, metadata = self._create_contact_actor(contact)
            if actor is not None:
                contact_actors[contact_name] = actor
                if metadata is not None:
                    contact_metadata[contact_name] = metadata

        logger.info(f"Created {len(contact_actors)} contact actors with {len(contact_metadata)} metadata entries")
        return contact_actors, contact_metadata

    def _create_contact_actor(
        self, contact_geom: ContactGeometryProtocol
    ) -> tuple[Any | None, tuple[Any, Any] | None]:
        """Create VTK actor for a single contact geometry.

        Uses OpenSim's generateDecorations() API to get proper rendering information.
        Stores local contact transform so it can be updated when parent body moves.

        Args:
            contact_geom: OpenSim contact geometry object

        Returns:
            Tuple of (vtkActor or None, metadata or None)
            metadata is (parent_body_name, contact_local_transform)

        Raises:
            AttributeError: If contact lacks required methods
            RuntimeError: If actor creation or positioning fails
        """
        decorations = opensim.ArrayDecorativeGeometry()
        hints = opensim.ModelDisplayHints()
        contact_geom.generateDecorations(False, hints, self.state, decorations)

        has_decorations = not decorations.empty()
        if not has_decorations:
            logger.debug(f"No decorations generated for {contact_geom.getName()}")

        decoration = decorations.at(0) if has_decorations else None

        # Determine contact type for geometry creation
        geom_type = contact_geom.getConcreteClassName()

        actor = None
        if geom_type == "ContactHalfSpace":
            actor = self._create_halfspace_actor(contact_geom)
        elif geom_type == "ContactSphere":
            actor = self._create_sphere_actor(contact_geom)
        elif geom_type == "ContactMesh":
            actor = self._create_mesh_actor(contact_geom)
        else:
            logger.warning(
                f"Unsupported contact geometry type: {geom_type} "
                f"(contact: {contact_geom.getName()})"
            )
            return None, None

        contact_local_transform = None

        frame = contact_geom.getFrame()
        if frame is None:
            raise ValueError(f"Contact {contact_geom.getName()} has no frame attached")

        if actor:
            if has_decorations and decoration:
                # This ensures we match opensim-gui's visualization
                color = decoration.getColor()
                opacity = decoration.getOpacity()

                actor.GetProperty().SetColor(color.get(0), color.get(1), color.get(2))
                actor.GetProperty().SetOpacity(opacity)

                # Get decoration's transform for initial placement (in ground frame)
                decoration_transform = decoration.getTransform()
                vtk_matrix = self._opensim_transform_to_vtk_matrix(decoration_transform)
                actor.SetUserMatrix(vtk_matrix)

                # Store contact's own transform (relative to its parent frame)
                contact_local_transform = contact_geom.getTransform()
                if contact_local_transform:
                    pos = contact_local_transform.p()
                    logger.debug(f"Contact {contact_geom.getName()} stored transform position: ({pos.get(0):.3f}, {pos.get(1):.3f}, {pos.get(2):.3f})")

                scale = decoration.getScaleFactors()
                actor.SetScale(scale.get(0), scale.get(1), scale.get(2))

                logger.debug(
                    f"Applied decoration properties to {contact_geom.getName()}"
                )
            else:
                # No decoration generated — apply full composed transform so
                # both position AND rotation of the contact are respected.
                contact_local_transform = contact_geom.getTransform()
                frame_transform = frame.getTransformInGround(self.state)
                global_transform = frame_transform.compose(contact_local_transform)
                vtk_matrix = self._opensim_transform_to_vtk_matrix(global_transform)
                actor.SetUserMatrix(vtk_matrix)
                actor.GetProperty().SetColor(1.0, 0.8, 0.0)  # Yellow/gold
                actor.GetProperty().SetOpacity(0.5)
                logger.debug(f"Applied manual positioning to {contact_geom.getName()}")

        metadata = None
        contact_name = contact_geom.getName()
        if contact_local_transform:
            # Store the frame object (not just its name) so update_contact_positions
            # can call getTransformInGround() on it directly. This handles both
            # Body frames and PhysicalOffsetFrames correctly.
            metadata = (frame, contact_local_transform)
            logger.debug(f"Contact {contact_name}: parent frame={frame.getName()}, has_transform=True")
        else:
            logger.warning(f"Contact {contact_name}: no local transform, skipping metadata")

        return actor, metadata

    def _create_halfspace_actor(self, contact: Any) -> Any | None:
        """Create actor for ContactHalfSpace.

        Args:
            contact: ContactHalfSpace object

        Returns:
            vtkActor or None

        Raises:
            RuntimeError: If VTK geometry creation fails
        """
        # ContactHalfSpace boundary is the x=0 plane in the contact's local frame,
        # with the outward normal pointing in +X. The plane is defined in the YZ
        # plane here so that the contact's transform (which rotates +X to the world
        # surface normal, e.g. +Y for a floor) lands in the correct orientation.
        plane = vtk.vtkPlaneSource()
        plane.SetOrigin(0, -5, -5)
        plane.SetPoint1(0,  5, -5)
        plane.SetPoint2(0, -5,  5)
        plane.SetResolution(10, 10)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(plane.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        # Note: Transform will be applied in _create_contact_actor via decoration
        return actor

    def _create_sphere_actor(self, contact: Any) -> Any | None:
        """Create actor for ContactSphere.

        Args:
            contact: ContactSphere object (will be downcast for actual parameters)

        Returns:
            vtkActor or None

        Raises:
            AttributeError: If sphere contact lacks required methods
            RuntimeError: If VTK geometry creation fails
        """
        # Downcast to ContactSphere to access actual radius
        sphere_contact = opensim.ContactSphere.safeDownCast(contact)
        if sphere_contact is None:
            raise ValueError("Contact is not a ContactSphere")
        radius = sphere_contact.getRadius()

        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(radius)
        sphere.SetThetaResolution(32)  # Smooth sphere
        sphere.SetPhiResolution(32)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        # Note: Transform will be applied in _create_contact_actor via decoration
        return actor

    def _create_mesh_actor(self, contact: Any) -> Any | None:
        """Create actor for ContactMesh.

        Args:
            contact: ContactMesh object

        Returns:
            vtkActor or None

        Raises:
            AttributeError: If contact lacks getFileName method
            FileNotFoundError: If mesh file cannot be resolved
            RuntimeError: If mesh loading fails
        """
        mesh_file = contact.getFileName()

        if not mesh_file:
            logger.warning(f"Contact mesh has no file: {contact.getName()}")
            return None

        # Resolve mesh file path
        mesh_path = self._resolve_mesh_path(mesh_file)
        if not mesh_path or not mesh_path.exists():
            logger.warning(f"Mesh file not found: {mesh_file}")
            return None

        poly_data = self._load_mesh_file(mesh_path)
        if poly_data is None:
            return None

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly_data)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        # Note: Transform will be applied in _create_contact_actor via decoration
        return actor

    def _resolve_mesh_path(self, mesh_file: str) -> Path | None:
        """Resolve mesh file path.

        Args:
            mesh_file: Mesh filename (relative or absolute)

        Returns:
            Resolved Path or None if not found

        Raises:
            ValueError: If mesh_file is empty
        """
        if not mesh_file:
            raise ValueError("Mesh file path cannot be empty")

        mesh_path = Path(mesh_file)

        # If absolute, use as-is
        if mesh_path.is_absolute():
            if mesh_path.exists():
                return mesh_path
            return None

        # Try relative to model file
        if self.model_path:
            resolved = self.model_path.parent / mesh_file
            if resolved.exists():
                return resolved

        # Try as-is relative
        if mesh_path.exists():
            return mesh_path

        return None

    def _load_mesh_file(self, file_path: Path) -> Any | None:
        """Load mesh file.

        Args:
            file_path: Path to mesh file

        Returns:
            vtkPolyData or None if file format is unsupported

        Raises:
            FileNotFoundError: If file does not exist
            RuntimeError: If VTK reader fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Mesh file not found: {file_path}")

        poly_data = read_polydata(file_path)
        if poly_data is None:
            logger.warning(f"Unsupported mesh format: {file_path.suffix.lower()}")
        return poly_data

    def update_contact_positions(
        self,
        contact_actors: dict[str, Any],
        contact_metadata: dict[str, tuple[Any, Any]],
    ) -> None:
        """Update contact actor positions based on current frame poses.

        Each contact is positioned at: parent_frame_world_transform * contact_local_transform.
        The parent frame may be a Body or a PhysicalOffsetFrame — both support
        getTransformInGround() so no special-casing is needed.

        Args:
            contact_actors: Dictionary mapping contact_name -> vtkActor
            contact_metadata: Dictionary mapping contact_name -> (parent_frame, contact_local_transform)

        Raises:
            KeyError: If contact_name is in metadata but missing from actors dict
        """
        if not contact_metadata:
            logger.warning("update_contact_positions called with empty metadata")
            return

        logger.debug(f"Updating {len(contact_metadata)} contact positions")

        for contact_name, (parent_frame, contact_local_transform) in contact_metadata.items():
            actor = contact_actors[contact_name]
            frame_transform = parent_frame.getTransformInGround(self.state)
            global_transform = frame_transform.compose(contact_local_transform)
            vtk_matrix = self._opensim_transform_to_vtk_matrix(global_transform)
            actor.SetUserMatrix(vtk_matrix)

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

        rot_mat = rotation.asMat33()
        for i in range(3):
            for j in range(3):
                val = rot_mat.get(i, j)
                matrix.SetElement(i, j, val)

        matrix.SetElement(0, 3, translation.get(0))
        matrix.SetElement(1, 3, translation.get(1))
        matrix.SetElement(2, 3, translation.get(2))

        matrix.SetElement(3, 3, 1.0)

        return matrix
