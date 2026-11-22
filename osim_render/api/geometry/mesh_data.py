"""Mesh instance data."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from osim_render.api.geometry.transform import Transform


@dataclass(frozen=True)
class MeshInstance:
    """Immutable mesh instance with geometry and transform.

    Represents a mesh displayed in the scene with its geometric
    data and spatial transformation.

    Attributes:
        name: Identifier for this mesh instance
        vertices: Flattened vertex coordinates
        indices: Triangle vertex indices
        transform: Spatial transform applied to mesh
        color: RGB color as (r, g, b) tuple (0.0-1.0)
        source_path: Path to original mesh file
    """

    name: str
    vertices: tuple[float, ...]
    indices: tuple[int, ...]
    transform: Transform = Transform()
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    source_path: Optional[Path] = None

    def vertex_count(self) -> int:
        """Get number of vertices.

        Returns:
            Number of vertices
        """
        return len(self.vertices) // 3

    def triangle_count(self) -> int:
        """Get number of triangles.

        Returns:
            Number of triangles
        """
        return len(self.indices) // 3

    def with_transform(self, transform: Transform) -> "MeshInstance":
        """Create instance with different transform.

        Args:
            transform: New transform

        Returns:
            New MeshInstance with updated transform
        """
        return MeshInstance(
            name=self.name,
            vertices=self.vertices,
            indices=self.indices,
            transform=transform,
            color=self.color,
            source_path=self.source_path,
        )

    def with_color(self, r: float, g: float, b: float) -> "MeshInstance":
        """Create instance with different color.

        Args:
            r: Red (0.0-1.0)
            g: Green (0.0-1.0)
            b: Blue (0.0-1.0)

        Returns:
            New MeshInstance with updated color
        """
        return MeshInstance(
            name=self.name,
            vertices=self.vertices,
            indices=self.indices,
            transform=self.transform,
            color=(r, g, b),
            source_path=self.source_path,
        )


if __name__ == "__main__":
    """Smoke test for MeshInstance."""
    print("MeshInstance smoke test")

    vertices = (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    indices = (0, 1, 2)

    mesh = MeshInstance(
        name="test_mesh",
        vertices=vertices,
        indices=indices,
        color=(1.0, 0.0, 0.0),
    )

    assert mesh.vertex_count() == 3
    assert mesh.triangle_count() == 1
    print("[OK] Mesh instance created")

    mesh2 = mesh.with_color(0.0, 1.0, 0.0)
    assert mesh2.color == (0.0, 1.0, 0.0)
    print("[OK] Color change works")

    mesh3 = mesh.with_transform(Transform(tx=1.0, ty=2.0))
    assert mesh3.transform.tx == 1.0
    print("[OK] Transform change works")

    print("\n[OK] All smoke tests passed!")
