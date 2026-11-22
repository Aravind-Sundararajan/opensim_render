"""OpenSim model data structures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Transform:
    """Immutable 3D transform (rotation + translation).

    Rotation specified as Euler angles in radians (rx, ry, rz).
    Translation specified in meters (tx, ty, tz).
    """

    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0
    tx: float = 0.0
    ty: float = 0.0
    tz: float = 0.0

    def to_tuple(self) -> tuple[float, ...]:
        """Convert to tuple for VTK transform matrix."""
        return (self.rx, self.ry, self.rz, self.tx, self.ty, self.tz)


@dataclass(frozen=True)
class DisplayGeometry:
    """Immutable display geometry specification.

    Represents a visual mesh attached to a body with transform and color.
    """

    filepath: Path
    color: tuple[float, float, float] = (0.8, 0.8, 0.8)
    opacity: float = 1.0
    transform: Transform = Transform()
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def get_absolute_path(self, model_dir: Path) -> Path:
        """Resolve geometry file path relative to model directory.

        Args:
            model_dir: Directory containing the .osim file

        Returns:
            Absolute path to geometry file
        """
        if self.filepath.is_absolute():
            return self.filepath
        return model_dir / self.filepath


@dataclass(frozen=True)
class Body:
    """Immutable OpenSim body representation.

    Represents a rigid body in the skeleton with associated geometry.
    """

    name: str
    mass: float = 0.0
    geometry: tuple[DisplayGeometry, ...] = ()

    def has_visible_geometry(self) -> bool:
        """Check if body has any visible geometry."""
        return len(self.geometry) > 0


@dataclass(frozen=True)
class ModelMetadata:
    """Immutable model metadata."""

    name: str
    version: str = ""
    length_units: str = "meters"
    force_units: str = "N"
    gravity: tuple[float, float, float] = (0.0, -9.80665, 0.0)


@dataclass(frozen=True)
class OpenSimModel:
    """Immutable OpenSim model representation.

    Complete model with all bodies and geometries.
    """

    metadata: ModelMetadata
    bodies: tuple[Body, ...] = ()
    model_file: Path | None = None

    def get_visible_bodies(self) -> tuple[Body, ...]:
        """Get bodies with visible geometry.

        Returns:
            Tuple of bodies that have geometry to display
        """
        return tuple(body for body in self.bodies if body.has_visible_geometry())

    def get_body(self, name: str) -> Body | None:
        """Get body by name.

        Args:
            name: Body name

        Returns:
            Body or None if not found
        """
        for body in self.bodies:
            if body.name == name:
                return body
        return None

    def get_all_geometry(self) -> list[tuple[str, DisplayGeometry]]:
        """Get all geometry with body names.

        Returns:
            List of (body_name, geometry) tuples
        """
        result = []
        for body in self.bodies:
            for geom in body.geometry:
                result.append((body.name, geom))
        return result

    def get_model_bounds(self) -> dict[str, Any]:
        """Get approximate model bounds for camera framing.

        Returns:
            Dictionary with min/max x, y, z coordinates
        """
        if not self.bodies:
            return {
                "min_x": 0,
                "max_x": 1,
                "min_y": 0,
                "max_y": 1,
                "min_z": 0,
                "max_z": 1,
            }

        # Estimate based on body count and spacing
        # This is a rough heuristic; real bounds would need actual mesh data
        num_bodies = len(self.bodies)
        scale = (num_bodies**0.5) * 0.5

        return {
            "min_x": -scale,
            "max_x": scale,
            "min_y": -scale,
            "max_y": scale * 2,
            "min_z": -scale,
            "max_z": scale,
        }


if __name__ == "__main__":
    """Smoke test for model data structures."""

    print("Model data structures smoke test")

    # Create a body
    geom = DisplayGeometry(
        filepath=Path("body.vtp"),
        color=(1.0, 0.0, 0.0),
        transform=Transform(tx=0.1, ty=0.2),
    )
    body = Body(name="pelvis", mass=10.0, geometry=(geom,))
    print("[OK] Created body with geometry")

    # Create model
    metadata = ModelMetadata(name="TestModel")
    model = OpenSimModel(metadata=metadata, bodies=(body,))
    print("[OK] Created model")

    # Test methods
    assert model.get_body("pelvis") is not None
    print("[OK] Body retrieval works")

    assert body.has_visible_geometry()
    print("[OK] Visibility check works")

    assert len(model.get_visible_bodies()) == 1
    print("[OK] Get visible bodies works")

    geom_list = model.get_all_geometry()
    assert len(geom_list) == 1
    assert geom_list[0][0] == "pelvis"
    print("[OK] Get all geometry works")

    bounds = model.get_model_bounds()
    assert "min_x" in bounds
    print("[OK] Model bounds calculation works")

    print("\n[OK] All smoke tests passed!")
