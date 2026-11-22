"""Immutable render scene data structure for OpenSim model visualization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import vtkmodules.all as vtk


@dataclass(frozen=True)
class RenderScene:
    """Immutable rendering scene with bodies and VTK components."""

    model_name: str
    renderer: vtk.vtkRenderer
    render_window: vtk.vtkRenderWindow
    interactor: vtk.vtkRenderWindowInteractor
    actors: dict[str, vtk.vtkActor]  # body_name -> vtkActor
    body_origin_actors: dict[
        str, vtk.vtkAssembly
    ] | None = None  # body_name -> axes assembly
    body_mass_center_actors: dict[
        str, vtk.vtkActor
    ] | None = None  # body_name -> sphere actor
    joint_parent_actors: dict[
        str, vtk.vtkAssembly
    ] | None = None  # joint_name -> parent axes assembly
    joint_child_actors: dict[
        str, vtk.vtkAssembly
    ] | None = None  # joint_name -> child axes assembly
    contact_actors: dict[str, vtk.vtkActor] | None = None  # contact_name -> vtkActor
    contact_metadata: dict[
        str, tuple[Any, Any]
    ] | None = None  # contact_name -> (parent_frame, local_transform)
    contact_force_actors: dict[
        str, vtk.vtkActor
    ] | None = None  # force_name -> arrow actor
    contact_force_metadata: dict[
        str, Any
    ] | None = None  # contact point key -> ContactPoint
    ground_reaction_actors: dict[
        str, vtk.vtkActor
    ] | None = None  # grf source name -> arrow actor; filled when GRF is loaded
    marker_actors: dict[str, vtk.vtkActor] | None = None  # marker_name -> vtkActor
    marker_metadata: dict[str, str] | None = None  # marker_name -> body_name
    muscle_actors: dict[str, vtk.vtkActor] | None = None  # muscle_name -> tube actor
    wrap_actors: dict[str, vtk.vtkActor] | None = None  # wrap_name -> vtkActor


if __name__ == "__main__":
    print("[OK] render_scene imports cleanly")
