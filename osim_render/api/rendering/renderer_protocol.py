"""Abstract renderer protocol."""

from typing import Protocol


class RendererProtocol(Protocol):
    """Protocol for 3D rendering backends.

    Defines the interface that any renderer implementation
    must provide for displaying 3D geometry.
    """

    def add_mesh(
        self,
        name: str,
        vertices: tuple[float, ...],
        indices: tuple[int, ...],
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> None:
        """Add a mesh to the scene.

        Args:
            name: Unique mesh identifier
            vertices: Flattened vertex coordinates [x0,y0,z0,x1,y1,z1,...]
            indices: Triangle vertex indices [v0,v1,v2,v0,v1,v2,...]
            color: RGB color as tuple (0.0-1.0)
        """
        ...

    def remove_mesh(self, name: str) -> None:
        """Remove a mesh from the scene.

        Args:
            name: Mesh identifier to remove
        """
        ...

    def set_mesh_color(self, name: str, color: tuple[float, float, float]) -> None:
        """Set mesh color.

        Args:
            name: Mesh identifier
            color: RGB color (0.0-1.0)
        """
        ...

    def set_background_color(self, r: float, g: float, b: float) -> None:
        """Set viewport background color.

        Args:
            r: Red component (0.0-1.0)
            g: Green component (0.0-1.0)
            b: Blue component (0.0-1.0)
        """
        ...

    def reset_camera(self) -> None:
        """Reset camera to fit all geometry."""
        ...

    def render(self) -> None:
        """Trigger a render update."""
        ...
