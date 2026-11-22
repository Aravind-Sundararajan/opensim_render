"""OpenSim model geometry data structures."""

from dataclasses import dataclass

from osim_render.api.geometry.mesh_data import MeshInstance


@dataclass(frozen=True)
class BodyGeometry:
    """Immutable geometry for a single body.

    Attributes:
        name: Body name
        meshes: Sequence of mesh instances for this body
    """

    name: str
    meshes: tuple[MeshInstance, ...] = ()

    def mesh_count(self) -> int:
        """Get number of meshes for this body.

        Returns:
            Number of mesh instances
        """
        return len(self.meshes)


@dataclass(frozen=True)
class ModelGeometry:
    """Immutable complete model geometry.

    Contains geometry for all bodies in a model.

    Attributes:
        name: Model name
        bodies: Sequence of body geometries
    """

    name: str
    bodies: tuple[BodyGeometry, ...] = ()

    def body_count(self) -> int:
        """Get number of bodies.

        Returns:
            Number of bodies
        """
        return len(self.bodies)

    def total_mesh_count(self) -> int:
        """Get total mesh instances in model.

        Returns:
            Sum of all meshes in all bodies
        """
        return sum(body.mesh_count() for body in self.bodies)

    def get_body(self, name: str) -> BodyGeometry | None:
        """Get body geometry by name.

        Args:
            name: Body name

        Returns:
            BodyGeometry or None if not found
        """
        for body in self.bodies:
            if body.name == name:
                return body
        return None


if __name__ == "__main__":
    """Smoke test for model geometry."""
    print("ModelGeometry smoke test")

    # Create mesh instances
    vertices = (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    indices = (0, 1, 2)

    mesh = MeshInstance(
        name="pelvis_mesh",
        vertices=vertices,
        indices=indices,
    )

    # Create body
    body = BodyGeometry(
        name="pelvis",
        meshes=(mesh,),
    )

    assert body.mesh_count() == 1
    print("[OK] Body created")

    # Create model
    model = ModelGeometry(
        name="TestModel",
        bodies=(body,),
    )

    assert model.body_count() == 1
    assert model.total_mesh_count() == 1
    print("[OK] Model created")

    found_body = model.get_body("pelvis")
    assert found_body is not None
    assert found_body.mesh_count() == 1
    print("[OK] Body lookup works")

    print("\n[OK] All smoke tests passed!")
