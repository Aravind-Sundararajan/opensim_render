"""Camera control abstraction."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Camera:
    """Immutable camera configuration.

    Attributes:
        position: Camera position as (x, y, z)
        focal_point: Look-at point as (x, y, z)
        up_vector: Up direction as (x, y, z)
        view_angle: Field of view in degrees
    """

    position: tuple[float, float, float] = (0.0, 0.0, 10.0)
    focal_point: tuple[float, float, float] = (0.0, 0.0, 0.0)
    up_vector: tuple[float, float, float] = (0.0, 1.0, 0.0)
    view_angle: float = 30.0

    def with_position(self, x: float, y: float, z: float) -> "Camera":
        """Create camera with new position.

        Args:
            x: Position X
            y: Position Y
            z: Position Z

        Returns:
            New Camera instance
        """
        return Camera(
            position=(x, y, z),
            focal_point=self.focal_point,
            up_vector=self.up_vector,
            view_angle=self.view_angle,
        )

    def with_focal_point(self, x: float, y: float, z: float) -> "Camera":
        """Create camera with new focal point.

        Args:
            x: Focal point X
            y: Focal point Y
            z: Focal point Z

        Returns:
            New Camera instance
        """
        return Camera(
            position=self.position,
            focal_point=(x, y, z),
            up_vector=self.up_vector,
            view_angle=self.view_angle,
        )

    def with_view_angle(self, angle: float) -> "Camera":
        """Create camera with new field of view.

        Args:
            angle: FOV in degrees

        Returns:
            New Camera instance
        """
        return Camera(
            position=self.position,
            focal_point=self.focal_point,
            up_vector=self.up_vector,
            view_angle=angle,
        )


if __name__ == "__main__":
    """Smoke test for Camera."""
    print("Camera smoke test")

    camera = Camera()
    print("[OK] Camera created")

    camera2 = camera.with_position(1.0, 2.0, 3.0)
    assert camera2.position == (1.0, 2.0, 3.0)
    print("[OK] Position change works")

    camera3 = camera.with_focal_point(5.0, 5.0, 5.0)
    assert camera3.focal_point == (5.0, 5.0, 5.0)
    print("[OK] Focal point change works")

    camera4 = camera.with_view_angle(45.0)
    assert camera4.view_angle == 45.0
    print("[OK] View angle change works")

    print("\n[OK] All smoke tests passed!")
