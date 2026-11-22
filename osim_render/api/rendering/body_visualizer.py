"""Visualization of OpenSim bodies and geometry.

Creates VTK actors for bodies with their attached geometry.
Handles geometry loading, positioning, and rendering properties.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

import vtkmodules.all as vtk

from osim_render.api.loaders.geometry_loader import GeometryExtractor, GeometryInfo
from osim_render.api.rendering.mesh_reader import read_polydata
from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


@dataclass(frozen=True)
class BodyVisuals:
    """Immutable visualization data for a body."""

    body_name: str
    actor: Any  # vtkActor
    geometry_files: tuple[str, ...]  # Resolved file paths


class BodyVisualizer:
    """Create VTK visualizations for OpenSim bodies."""

    def __init__(
        self,
        model_path: str | Path,
        geometry_search_paths: tuple[str, ...] | None = None,
    ):
        """Initialize body visualizer.

        Args:
            model_path: Path to OSIM file
            geometry_search_paths: Custom geometry search paths
        """
        self.model_path = Path(model_path)
        self.geometry_extractor = GeometryExtractor(
            model_path, geometry_search_paths)
        self.geometry_map = self.geometry_extractor.extract_all_geometry()

    def create_body_actor(self, body_name: str) -> BodyVisuals | None:
        """Create a VTK actor for a body's geometry.

        Args:
            body_name: Name of body

        Returns:
            BodyVisuals with VTK actor or None if no geometry
        """
        if body_name not in self.geometry_map:
            return None

        body_geom = self.geometry_map[body_name]

        # Combine all geometry for this body into a single actor
        combined_geom = vtk.vtkAppendPolyData()
        resolved_files = []

        for geom_info in body_geom.geometries:
            geom_file = self.geometry_extractor.get_geometry_file_path(
                geom_info.geometry_filename
            )
            if not geom_file:
                continue

            resolved_files.append(str(geom_file))

            mesh_data = self._load_mesh(geom_file, geom_info)
            if mesh_data:
                combined_geom.AddInputData(mesh_data)

        combined_geom.Update()
        if (
            not combined_geom.GetOutput()
            or combined_geom.GetOutput().GetNumberOfCells() == 0
        ):
            return None

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(combined_geom.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.8, 0.8, 0.8)  # Light gray default

        return BodyVisuals(
            body_name=body_name,
            actor=actor,
            geometry_files=tuple(resolved_files),
        )

    def _load_mesh(self, file_path: Path, geom_info: GeometryInfo) -> Any | None:
        """Load a mesh file and return VTK PolyData.

        Args:
            file_path: Path to geometry file (VTP, OBJ, or STL)
            geom_info: Geometry information with transforms and scale

        Returns:
            vtkPolyData or None if load fails

        Raises:
            IOError: If mesh file cannot be loaded
            AttributeError: If geometry reader fails
        """
        poly_data = read_polydata(file_path)
        if poly_data is None:
            return None

        sx, sy, sz = geom_info.scale_factors
        if not (sx == 1.0 and sy == 1.0 and sz == 1.0):
            transform = vtk.vtkTransform()
            transform.Scale(sx, sy, sz)
            transform_filter = vtk.vtkTransformPolyDataFilter()
            transform_filter.SetInputData(poly_data)
            transform_filter.SetTransform(transform)
            transform_filter.Update()
            poly_data = transform_filter.GetOutput()

        # Transform format: rx ry rz tx ty tz (rotations in radians, translations in meters)
        rx, ry, rz, tx, ty, tz = geom_info.transform
        if not all(v == 0.0 for v in [rx, ry, rz, tx, ty, tz]):
            transform = vtk.vtkTransform()
            transform.RotateX(np.degrees(rx))
            transform.RotateY(np.degrees(ry))
            transform.RotateZ(np.degrees(rz))
            transform.Translate(tx, ty, tz)

            transform_filter = vtk.vtkTransformPolyDataFilter()
            transform_filter.SetInputData(poly_data)
            transform_filter.SetTransform(transform)
            transform_filter.Update()
            poly_data = transform_filter.GetOutput()

        return poly_data


if __name__ == "__main__":
    """Smoke test for body visualization."""
    model_path = Path(
        "models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim")

    if model_path.exists():
        visualizer = BodyVisualizer(model_path)
        geometry_map = visualizer.geometry_map

        print(
            f"[OK] Initialized body visualizer for {len(geometry_map)} bodies")

        test_bodies = ["pelvis", "femur_r", "tibia_r"]
        for body_name in test_bodies:
            visuals = visualizer.create_body_actor(body_name)
            if visuals:
                print(
                    f"[OK] Created actor for {body_name} with {len(visuals.geometry_files)} files"
                )
            else:
                print(f"[INFO] No geometry for {body_name}")

        print("\n[OK] Body visualization smoke test passed!")
    else:
        print(f"[SKIP] Model not found: {model_path}")
