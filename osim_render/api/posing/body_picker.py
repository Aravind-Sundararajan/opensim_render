"""Pick OpenSim bodies from viewport clicks.

Picking is restricted to body actors so that markers, muscles, wrap surfaces
and contact geometry never steal a drag.
"""

from __future__ import annotations

from dataclasses import dataclass

import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)

DEFAULT_TOLERANCE = 0.005


@dataclass(frozen=True)
class BodyPick:
    """A successful pick of a body in the viewport."""

    body_name: str
    world_point: tuple[float, float, float]
    local_point: tuple[float, float, float]


class BodyPicker:
    """Map viewport coordinates to the OpenSim body under the cursor."""

    def __init__(self, actors: dict[str, vtk.vtkActor], tolerance: float = DEFAULT_TOLERANCE):
        """Initialize the picker for a set of body actors.

        Args:
            actors: Mapping of body name to vtkActor (RenderScene.actors)
            tolerance: vtkCellPicker tolerance
        """
        self.actors = actors
        self._names_by_actor_id = {id(actor): name for name, actor in actors.items()}
        self._picker = vtk.vtkCellPicker()
        self._picker.SetTolerance(tolerance)
        self._restrict_pick_list()

    def _restrict_pick_list(self) -> None:
        """Limit picking to body actors only."""
        self._picker.InitializePickList()
        for actor in self.actors.values():
            self._picker.AddPickList(actor)
        self._picker.PickFromListOn()

    def pick(
        self, renderer: vtk.vtkRenderer, display_x: int, display_y: int
    ) -> BodyPick | None:
        """Find the body under a viewport position.

        Args:
            renderer: Renderer containing the body actors
            display_x: Viewport x coordinate
            display_y: Viewport y coordinate

        Returns:
            BodyPick if a body was hit, otherwise None
        """
        if not self._picker.Pick(display_x, display_y, 0, renderer):
            return None

        actor = self._picker.GetActor()
        if actor is None:
            return None

        body_name = self._names_by_actor_id.get(id(actor))
        if body_name is None:
            return None

        picked = self._picker.GetPickPosition()
        world_point = (picked[0], picked[1], picked[2])
        return BodyPick(
            body_name=body_name,
            world_point=world_point,
            local_point=self._to_actor_local(actor, world_point),
        )

    def _to_actor_local(
        self, actor: vtk.vtkActor, world_point: tuple[float, float, float]
    ) -> tuple[float, float, float]:
        """Convert a world point into the actor's local frame.

        Body actors are placed with SetUserTransform from the body's ground
        transform, so inverting that transform yields the point in the
        OpenSim body's local frame.

        Args:
            actor: Picked body actor
            world_point: Pick position in world coordinates

        Returns:
            Point in the body's local frame
        """
        user_transform = actor.GetUserTransform()
        if user_transform is None:
            return world_point

        inverse = vtk.vtkTransform()
        inverse.SetMatrix(user_transform.GetMatrix())
        inverse.Inverse()
        local = inverse.TransformPoint(world_point)
        return (local[0], local[1], local[2])


if __name__ == "__main__":
    """Smoke test for BodyPicker."""
    print("BodyPicker smoke test")

    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.SetOffScreenRendering(1)
    render_window.AddRenderer(renderer)
    render_window.SetSize(400, 400)

    sphere = vtk.vtkSphereSource()
    sphere.SetRadius(1.0)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(sphere.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    offset = vtk.vtkTransform()
    offset.Translate(0.0, 0.0, 0.0)
    actor.SetUserTransform(offset)
    renderer.AddActor(actor)
    renderer.ResetCamera()
    render_window.Render()

    picker = BodyPicker({"test_body": actor})

    hit = picker.pick(renderer, 200, 200)
    assert hit is not None, "expected a pick at viewport centre"
    print(f"[OK] Picked {hit.body_name} at world {tuple(round(v, 3) for v in hit.world_point)}")
    print(f"[OK] Local point {tuple(round(v, 3) for v in hit.local_point)}")

    miss = picker.pick(renderer, 2, 2)
    print(f"[OK] Corner click returned {miss}")
    assert miss is None, "expected no pick in empty corner"

    print("\n[OK] Smoke test passed!")
