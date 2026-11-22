"""Project viewport motion onto a world-space plane.

A mouse position is only two-dimensional, so dragging needs a surface to
resolve depth. The grab point's plane parallel to the image plane keeps the
dragged point under the cursor from every camera angle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)

MIN_RAY_DENOMINATOR = 1e-9

Point3D = tuple[float, float, float]


@dataclass(frozen=True)
class DragPlane:
    """An infinite plane that drag rays are projected onto."""

    origin: Point3D
    normal: Point3D

    @classmethod
    def facing_camera(cls, camera: Any, through_point: Point3D) -> "DragPlane":
        """Build a plane through a point, parallel to the image plane.

        Args:
            camera: Active vtkCamera
            through_point: World point the plane passes through

        Returns:
            DragPlane oriented toward the camera
        """
        return cls(origin=through_point, normal=tuple(camera.GetViewPlaneNormal()))

    def project_display_point(
        self, renderer: vtk.vtkRenderer, display_x: float, display_y: float
    ) -> Point3D | None:
        """Intersect the ray through a viewport pixel with this plane.

        Args:
            renderer: Renderer defining the camera and viewport
            display_x: Viewport x coordinate
            display_y: Viewport y coordinate

        Returns:
            World-space intersection point, or None if the ray is parallel
            to the plane
        """
        near = _display_to_world(renderer, display_x, display_y, 0.0)
        far = _display_to_world(renderer, display_x, display_y, 1.0)
        return self._intersect_ray(near, far)

    def _intersect_ray(self, near: Point3D, far: Point3D) -> Point3D | None:
        """Intersect a segment with the plane.

        Args:
            near: Ray start in world coordinates
            far: Ray end in world coordinates

        Returns:
            Intersection point, or None if the ray runs parallel
        """
        direction = _subtract(far, near)
        denominator = _dot(self.normal, direction)

        if abs(denominator) < MIN_RAY_DENOMINATOR:
            return None

        distance = _dot(self.normal, _subtract(self.origin, near)) / denominator
        return (
            near[0] + direction[0] * distance,
            near[1] + direction[1] * distance,
            near[2] + direction[2] * distance,
        )


def _display_to_world(
    renderer: vtk.vtkRenderer, display_x: float, display_y: float, depth: float
) -> Point3D:
    """Convert a viewport position at a given depth into world coordinates.

    Args:
        renderer: Renderer to convert through
        display_x: Viewport x coordinate
        display_y: Viewport y coordinate
        depth: Normalized depth, 0.0 at the near plane and 1.0 at the far plane

    Returns:
        World-space point
    """
    renderer.SetDisplayPoint(display_x, display_y, depth)
    renderer.DisplayToWorld()
    world = renderer.GetWorldPoint()

    if abs(world[3]) < MIN_RAY_DENOMINATOR:
        return (world[0], world[1], world[2])
    return (world[0] / world[3], world[1] / world[3], world[2] / world[3])


def _subtract(a: Point3D, b: Point3D) -> Point3D:
    """Subtract two 3D points.

    Args:
        a: Left operand
        b: Right operand

    Returns:
        Component-wise difference
    """
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Point3D, b: Point3D) -> float:
    """Compute the dot product of two 3D vectors.

    Args:
        a: Left operand
        b: Right operand

    Returns:
        Scalar dot product
    """
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


if __name__ == "__main__":
    """Smoke test for DragPlane."""
    print("DragPlane smoke test")

    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.SetOffScreenRendering(1)
    render_window.AddRenderer(renderer)
    render_window.SetSize(400, 400)

    sphere = vtk.vtkSphereSource()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(sphere.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    renderer.AddActor(actor)
    renderer.ResetCamera()
    render_window.Render()

    camera = renderer.GetActiveCamera()
    grab_point = (0.0, 0.0, 0.0)
    plane = DragPlane.facing_camera(camera, grab_point)
    print(f"[OK] Plane normal {tuple(round(v, 3) for v in plane.normal)}")

    centre = plane.project_display_point(renderer, 200, 200)
    assert centre is not None
    print(f"[OK] Viewport centre projects to {tuple(round(v, 3) for v in centre)}")
    assert all(abs(c - g) < 1e-6 for c, g in zip(centre, grab_point, strict=False)), centre
    print("[OK] Centre round-trips to the grab point")

    right = plane.project_display_point(renderer, 300, 200)
    assert right is not None
    print(f"[OK] Right of centre projects to {tuple(round(v, 3) for v in right)}")
    assert right != centre, "moving the cursor should move the projection"

    moved = sum((r - c) ** 2 for r, c in zip(right, centre, strict=False)) ** 0.5
    print(f"[OK] 100px moved {moved:.4f} world units")
    assert moved > 0.0

    print("\n[OK] Smoke test passed!")
