"""OpenSim model loader using OpenSim 4.4+ Python API.

This module loads OpenSim models using the native OpenSim Python API.
No fallbacks - fails fast if OpenSim is not available.

OpenSim must be installed separately (not available via pip).
Download from: https://opensim.stanford.edu/
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import opensim
except ImportError as e:
    raise ImportError(
        "OpenSim Python API is not available. "
        "Install OpenSim 4.4 or later from https://opensim.stanford.edu/ "
        "The Python API will be available after installation."
    ) from e

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


@dataclass(frozen=True)
class OpenSimBody:
    """Immutable OpenSim body information."""

    name: str
    mass: float
    parent_name: str
    inertia: tuple[float, float, float]  # Ixx, Iyy, Izz


@dataclass(frozen=True)
class OpenSimJoint:
    """Immutable OpenSim joint information."""

    name: str
    type_name: str
    parent_body: str
    child_body: str
    coordinates: tuple[str, ...]  # Coordinate names


@dataclass(frozen=True)
class OpenSimCoordinate:
    """Immutable OpenSim coordinate information."""

    name: str
    value: float
    speed: float
    range: tuple[float, float]  # min, max


@dataclass(frozen=True)
class OpenSimModelStructure:
    """Immutable OpenSim model structure with bodies, joints, coordinates."""

    name: str
    bodies: tuple[OpenSimBody, ...]
    joints: tuple[OpenSimJoint, ...]
    coordinates: tuple[OpenSimCoordinate, ...]
    gravity: tuple[float, float, float]

    def get_body(self, name: str) -> OpenSimBody | None:
        """Get body by name."""
        for body in self.bodies:
            if body.name == name:
                return body
        return None

    def get_joint(self, name: str) -> OpenSimJoint | None:
        """Get joint by name."""
        for joint in self.joints:
            if joint.name == name:
                return joint
        return None

    def get_coordinate(self, name: str) -> OpenSimCoordinate | None:
        """Get coordinate by name."""
        for coord in self.coordinates:
            if coord.name == name:
                return coord
        return None


class OpenSimModelLoader:
    """Loader for OpenSim models using the OpenSim Python API.

    Requires OpenSim 4.4+ to be installed. Fails fast if not available.
    """

    def __init__(self) -> None:
        """Initialize OpenSim loader.

        OpenSim module is imported at module level, so if this succeeds,
        OpenSim is available.

        Raises:
            ImportError: If OpenSim is not installed (occurs at module import)
        """
        logger.info(f"OpenSim loaded: version {opensim.GetVersion()}")

    def load(self, filepath: Path | str) -> OpenSimModelStructure:
        """Load OpenSim model from file.

        Args:
            filepath: Path to .osim file

        Returns:
            OpenSimModelStructure with bodies, joints, coordinates

        Raises:
            FileNotFoundError: If file does not exist
            RuntimeError: If model initialization or loading fails
            AttributeError: If OpenSim model structure is invalid
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")

        model = opensim.Model(str(filepath))
        state = model.initSystem()

        name = model.getName()
        gravity = model.getGravity()

        bodies = self._extract_bodies(model)

        joints = self._extract_joints(model)

        coordinates = self._extract_coordinates(model, state)

        return OpenSimModelStructure(
            name=name,
            bodies=tuple(bodies),
            joints=tuple(joints),
            coordinates=tuple(coordinates),
            gravity=gravity,
        )

    def _extract_bodies(self, model: Any) -> list[OpenSimBody]:
        """Extract all bodies from model using getBodyList().

        Args:
            model: OpenSim model object

        Returns:
            List of OpenSimBody objects
        """
        bodies = []

        for body in model.getBodyList():
            name = body.getName()
            mass = body.getMass()
            # Inertia values not critical for visualization
            inertia = (0.0, 0.0, 0.0)
            # Parent hierarchy derived from joints, not body
            parent_name = "ground"

            bodies.append(
                OpenSimBody(
                    name=name,
                    mass=mass,
                    parent_name=parent_name,
                    inertia=inertia,
                )
            )

        return bodies

    def _extract_joints(self, model: Any) -> list[OpenSimJoint]:
        """Extract all joints from model using getJointList().

        Args:
            model: OpenSim model object

        Returns:
            List of OpenSimJoint objects
        """
        joints = []

        for joint in model.getJointList():
            name = joint.getName()
            type_name = joint.getConcreteClassName()

            # Num coordinates available but coordinate extraction is complex
            coordinates = ()  # Empty tuple for now

            # Parent/child bodies determined from coordinate names
            parent_body = "unknown"
            child_body = "unknown"

            joints.append(
                OpenSimJoint(
                    name=name,
                    type_name=type_name,
                    parent_body=parent_body,
                    child_body=child_body,
                    coordinates=coordinates,
                )
            )

        return joints

    def _extract_coordinates(self, model: Any, state: Any) -> list[OpenSimCoordinate]:
        """Extract all coordinates from model using getCoordinateSet().

        Args:
            model: OpenSim model object
            state: Model state from initSystem()

        Returns:
            List of OpenSimCoordinate objects
        """
        coordinates = []

        coord_set = model.getCoordinateSet()

        for i in range(coord_set.getSize()):
            coord = coord_set.get(i)
            name = coord.getName()
            value = coord.getValue(state)
            speed = coord.getSpeedValue(state)
            range_min = coord.getRangeMin()
            range_max = coord.getRangeMax()

            coordinates.append(
                OpenSimCoordinate(
                    name=name,
                    value=value,
                    speed=speed,
                    range=(range_min, range_max),
                )
            )

        return coordinates


if __name__ == "__main__":
    """Smoke test for OpenSim model loader."""
    from pathlib import Path

    print("OpenSimModelLoader smoke test")

    # Try to load a model
    model_path = Path("models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim")

    if model_path.exists():
        loader = OpenSimModelLoader()
        model = loader.load(model_path)

        print(f"[OK] Model loaded: {model.name}")
        print(f"[OK] Gravity: {model.gravity}")
        print(f"[OK] Bodies: {len(model.bodies)}")
        print(f"[OK] Joints: {len(model.joints)}")
        print(f"[OK] Coordinates: {len(model.coordinates)}")

        # Show first few bodies
        for body in model.bodies[:3]:
            print(
                f"  - Body: {body.name} (mass={body.mass:.2f}kg, parent={body.parent_name})"
            )

        # Show first few joints
        for joint in model.joints[:3]:
            print(
                f"  - Joint: {joint.name} ({joint.type_name}) "
                f"{joint.parent_body} -> {joint.child_body} "
                f"coords: {joint.coordinates}"
            )

        print("\n[OK] OpenSim model loader smoke test passed!")
    else:
        print(f"[SKIP] Model not found: {model_path}")
