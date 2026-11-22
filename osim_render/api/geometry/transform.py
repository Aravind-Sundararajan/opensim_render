"""Spatial transform representation."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Transform:
    """Immutable 3D spatial transform (position and rotation).

    Represents a rigid body transformation with position and
    Euler angle rotation.

    Attributes:
        tx: Translation X coordinate
        ty: Translation Y coordinate
        tz: Translation Z coordinate
        rx: Rotation around X axis (radians)
        ry: Rotation around Y axis (radians)
        rz: Rotation around Z axis (radians)
    """

    tx: float = 0.0
    ty: float = 0.0
    tz: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0

    def translate(self, dx: float, dy: float, dz: float) -> "Transform":
        """Create new transform with translation applied.

        Args:
            dx: Translation X
            dy: Translation Y
            dz: Translation Z

        Returns:
            New Transform with translation added
        """
        return Transform(
            tx=self.tx + dx,
            ty=self.ty + dy,
            tz=self.tz + dz,
            rx=self.rx,
            ry=self.ry,
            rz=self.rz,
        )

    def rotate(self, rx: float, ry: float, rz: float) -> "Transform":
        """Create new transform with rotation applied.

        Args:
            rx: Rotation around X (radians)
            ry: Rotation around Y (radians)
            rz: Rotation around Z (radians)

        Returns:
            New Transform with rotation added
        """
        return Transform(
            tx=self.tx,
            ty=self.ty,
            tz=self.tz,
            rx=self.rx + rx,
            ry=self.ry + ry,
            rz=self.rz + rz,
        )

    def to_matrix(self) -> list[list[float]]:
        """Convert to 4x4 homogeneous transformation matrix.

        Returns:
            4x4 transformation matrix as nested list
        """
        # Compute rotation matrices
        cos_rx = math.cos(self.rx)
        sin_rx = math.sin(self.rx)
        cos_ry = math.cos(self.ry)
        sin_ry = math.sin(self.ry)
        cos_rz = math.cos(self.rz)
        sin_rz = math.sin(self.rz)

        # Combined rotation matrix (ZYX Euler angles)
        r11 = cos_ry * cos_rz
        r12 = -cos_ry * sin_rz
        r13 = sin_ry
        r21 = sin_rx * sin_ry * cos_rz + cos_rx * sin_rz
        r22 = -sin_rx * sin_ry * sin_rz + cos_rx * cos_rz
        r23 = -sin_rx * cos_ry
        r31 = -cos_rx * sin_ry * cos_rz + sin_rx * sin_rz
        r32 = cos_rx * sin_ry * sin_rz + sin_rx * cos_rz
        r33 = cos_rx * cos_ry

        return [
            [r11, r12, r13, self.tx],
            [r21, r22, r23, self.ty],
            [r31, r32, r33, self.tz],
            [0.0, 0.0, 0.0, 1.0],
        ]


if __name__ == "__main__":
    """Smoke test for Transform."""
    print("Transform smoke test")

    t = Transform(tx=1.0, ty=2.0, tz=3.0)
    print(f"[OK] Created transform: {t}")

    t2 = t.translate(1.0, 0.0, 0.0)
    assert t2.tx == 2.0
    print("[OK] Translation works")

    t3 = t.rotate(0.1, 0.2, 0.3)
    assert t3.rx == 0.1
    print("[OK] Rotation works")

    matrix = t.to_matrix()
    assert len(matrix) == 4
    assert len(matrix[0]) == 4
    print("[OK] Matrix conversion works")

    print("\n[OK] All smoke tests passed!")
