"""Visualization of wrap objects (cylinders, ellipsoids, spheres, tori).

Creates VTK actors for wrap objects that muscles wrap around, showing the
constraining geometry alongside muscle paths.
"""

from __future__ import annotations

from typing import Any

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


class WrapVisualizer:
    """Create VTK actors for wrap objects."""

    # Default wrap object appearance
    DEFAULT_OPACITY = 0.5  # Semi-transparent to see muscles wrapping
    # Cyan/blue to distinguish from muscles (red)
    DEFAULT_COLOR = (0.2, 0.7, 1.0)

    def __init__(self, model: Any, state: Any):
        """Initialize wrap visualizer.

        Args:
            model: OpenSim model
            state: OpenSim state

        Raises:
            ValueError: If model or state is None
        """
        if model is None:
            raise ValueError("Model cannot be None")
        if state is None:
            raise ValueError("State cannot be None")
        self.model = model
        self.state = state

    def create_all_wrap_actors(self) -> dict[str, Any]:
        """Create actors for all wrap objects in the model.

        Extracts wrap objects from each body and creates appropriate VTK geometry
        for each wrap type (cylinder, ellipsoid, sphere, torus).

        Returns:
            Dictionary mapping "{body_name}_{wrap_name}" -> vtkActor

        Raises:
            AttributeError: If model lacks body set or body lacks wrap object set
            RuntimeError: If actor creation fails
        """
        wrap_actors = {}

        body_set = self.model.getBodySet()

        for i in range(body_set.getSize()):
            body = body_set.get(i)
            body_name = body.getName()

            wrap_set = body.getWrapObjectSet()

            for j in range(wrap_set.getSize()):
                wrap_obj = wrap_set.get(j)
                wrap_name = wrap_obj.getName()
                actor_name = f"{body_name}_{wrap_name}"

                actor = self._create_wrap_actor(wrap_obj, body_name)
                if actor is not None:
                    wrap_actors[actor_name] = actor

        return wrap_actors

    def _create_wrap_actor(self, wrap_obj: Any, body_name: str) -> Any | None:
        """Create VTK actor for a single wrap object.

        Args:
            wrap_obj: OpenSim wrap object
            body_name: Name of parent body (for logging)

        Returns:
            vtkActor or None if wrap type is unsupported

        Raises:
            AttributeError: If wrap object lacks required methods
            RuntimeError: If actor creation fails
        """
        # Import opensim for type casting
        import opensim

        # Determine wrap type and create appropriate geometry
        type_name = wrap_obj.getConcreteClassName()

        actor = None
        if type_name == "WrapCylinder":
            cyl = opensim.WrapCylinder.safeDownCast(wrap_obj)
            if cyl is not None:
                actor = self._create_cylinder_actor(cyl)
        elif type_name == "WrapEllipsoid":
            ell = opensim.WrapEllipsoid.safeDownCast(wrap_obj)
            if ell is not None:
                actor = self._create_ellipsoid_actor(ell)
        elif type_name == "WrapSphere":
            sph = opensim.WrapSphere.safeDownCast(wrap_obj)
            if sph is not None:
                actor = self._create_sphere_actor(sph)
        elif type_name == "WrapTorus":
            tor = opensim.WrapTorus.safeDownCast(wrap_obj)
            if tor is not None:
                actor = self._create_torus_actor(tor)
        else:
            logger.warning(
                f"Unsupported wrap type: {type_name} for {wrap_obj.getName()}"
            )
            return None

        if actor is not None:
            actor.GetProperty().SetColor(*self.DEFAULT_COLOR)
            actor.GetProperty().SetOpacity(self.DEFAULT_OPACITY)
            actor.GetProperty().SetRepresentationToSurface()
            actor.GetProperty().BackfaceCullingOff()

            self._position_wrap_actor(actor, wrap_obj)

        return actor

    def _create_cylinder_actor(self, wrap_cyl: Any) -> Any | None:
        """Create actor for WrapCylinder.

        Args:
            wrap_cyl: WrapCylinder object

        Returns:
            vtkActor or None

        Raises:
            AttributeError: If cylinder lacks required methods
            RuntimeError: If VTK creation fails
        """
        # Get cylinder dimensions
        radius = wrap_cyl.get_radius()
        length = wrap_cyl.get_length()

        # Create cylinder source
        cylinder_source = vtk.vtkCylinderSource()
        cylinder_source.SetRadius(radius)
        cylinder_source.SetHeight(length)
        cylinder_source.SetResolution(32)  # Smooth appearance

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(cylinder_source.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        return actor

    def _create_ellipsoid_actor(self, wrap_ellipsoid: Any) -> Any | None:
        """Create actor for WrapEllipsoid.

        Args:
            wrap_ellipsoid: WrapEllipsoid object

        Returns:
            vtkActor or None

        Raises:
            AttributeError: If ellipsoid lacks required methods
            RuntimeError: If VTK creation fails
        """
        # Get ellipsoid dimensions
        dimensions = wrap_ellipsoid.get_dimensions()

        # Use parametric ellipsoid for smooth representation
        ellipsoid_fn = vtk.vtkParametricEllipsoid()
        ellipsoid_fn.SetXRadius(dimensions.get(0))
        ellipsoid_fn.SetYRadius(dimensions.get(1))
        ellipsoid_fn.SetZRadius(dimensions.get(2))

        # Create surface from parametric function
        param_source = vtk.vtkParametricFunctionSource()
        param_source.SetParametricFunction(ellipsoid_fn)
        param_source.SetUResolution(32)
        param_source.SetVResolution(32)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(param_source.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        return actor

    def _create_sphere_actor(self, wrap_sphere: Any) -> Any | None:
        """Create actor for WrapSphere.

        Args:
            wrap_sphere: WrapSphere object

        Returns:
            vtkActor or None

        Raises:
            AttributeError: If sphere lacks required methods
            RuntimeError: If VTK creation fails
        """
        # Get sphere radius
        radius = wrap_sphere.get_radius()

        # Create sphere source
        sphere_source = vtk.vtkSphereSource()
        sphere_source.SetRadius(radius)
        sphere_source.SetThetaResolution(32)
        sphere_source.SetPhiResolution(32)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere_source.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        return actor

    def _create_torus_actor(self, wrap_torus: Any) -> Any | None:
        """Create actor for WrapTorus.

        Args:
            wrap_torus: WrapTorus object

        Returns:
            vtkActor or None

        Raises:
            AttributeError: If torus lacks required methods
            RuntimeError: If VTK creation fails
        """
        # Get torus dimensions
        inner_radius = wrap_torus.get_inner_radius()
        outer_radius = wrap_torus.get_outer_radius()

        # Use parametric torus
        torus_fn = vtk.vtkParametricTorus()
        torus_fn.SetRingRadius(inner_radius)
        torus_fn.SetCrossSectionRadius(outer_radius)

        # Create surface from parametric function
        param_source = vtk.vtkParametricFunctionSource()
        param_source.SetParametricFunction(torus_fn)
        param_source.SetUResolution(32)
        param_source.SetVResolution(32)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(param_source.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        return actor

    def _position_wrap_actor(self, actor: Any, wrap_obj: Any) -> None:
        """Position wrap actor in ground frame.

        Wraps are attached to bodies, so we get the wrap's frame (which is
        the body frame) and apply the wrap's local transform.

        OpenSim cylinders are oriented along the Z-axis, but VTK's vtkCylinderSource
        is aligned with the Y-axis. We apply a 90-degree rotation around X-axis
        to convert from Z to Y alignment, following OpenSim's approach in
        WrapCylinder::generateDecorations().

        Args:
            actor: vtkActor to position
            wrap_obj: OpenSim wrap object

        Raises:
            AttributeError: If objects lack required methods
            RuntimeError: If transform operations fail
        """
        import opensim
        import math

        # Get the frame that the wrap is attached to
        frame = wrap_obj.getFrame()

        # Get frame transform in ground
        frame_transform = frame.getTransformInGround(self.state)

        # Get wrap's local transform relative to frame
        wrap_transform = wrap_obj.getTransform()

        # Compose the transforms (frame_transform * wrap_transform)
        combined_transform = frame_transform.compose(wrap_transform)

        # Create Z-to-Y rotation transform
        # OpenSim cylinders are oriented along Z, but vtkCylinderSource uses Y
        # Rotate 90 degrees around X-axis to align Z with Y
        rotation = opensim.Rotation()
        rotation.setRotationFromAngleAboutX(math.pi / 2)
        z_to_y_transform = opensim.Transform(rotation)

        # Compose: wrap_position * z_to_y_rotation
        final_transform = combined_transform.compose(z_to_y_transform)

        # Convert to VTK matrix
        matrix = self._opensim_transform_to_vtk_matrix(final_transform)

        # Apply to actor
        vtk_transform = vtk.vtkTransform()
        vtk_transform.SetMatrix(matrix)
        actor.SetUserTransform(vtk_transform)

    def update_wrap_positions(self, actors: dict[str, Any]) -> None:
        """Update wrap object positions when body poses change.

        Wrap objects are attached to bodies, so when joint angles change,
        their positions need to be updated. This should only be called if
        wrap objects are visible (expensive operation).

        Args:
            actors: Dictionary mapping actor_name -> vtkActor

        Raises:
            AttributeError: If model or body operations fail
            RuntimeError: If position updates fail
        """
        body_set = self.model.getBodySet()

        for i in range(body_set.getSize()):
            body = body_set.get(i)
            body_name = body.getName()

            wrap_set = body.getWrapObjectSet()

            for j in range(wrap_set.getSize()):
                wrap_obj = wrap_set.get(j)
                wrap_name = wrap_obj.getName()
                actor_name = f"{body_name}_{wrap_name}"

                if actor_name in actors:
                    self._position_wrap_actor(actors[actor_name], wrap_obj)

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
