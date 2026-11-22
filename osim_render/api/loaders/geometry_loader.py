"""Load geometry from OpenSim models.

Extracts geometry from OSIM XML and body transforms from OpenSim API.
Uses hybrid approach: XML for geometry definitions, API for transforms.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import xml.etree.ElementTree as ET


from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


@dataclass(frozen=True)
class GeometryInfo:
    """Immutable geometry information for a mesh attached to a body."""

    name: str
    body_name: str
    geometry_filename: str  # e.g., "femur.vtp"
    transform: tuple[float, float, float, float, float, float]  # rx ry rz tx ty tz
    scale_factors: tuple[float, float, float]  # sx sy sz
    display_preference: int  # 0:Hide 1:Wire 3:Flat 4:Shaded
    opacity: float


@dataclass(frozen=True)
class BodyGeometry:
    """All geometry attached to a single body."""

    body_name: str
    geometries: tuple[GeometryInfo, ...]


class GeometryExtractor:
    """Extract geometry from OSIM XML files.

    Uses configurable geometry search paths to resolve geometry files.
    """

    def __init__(
        self,
        model_path: str | Path,
        geometry_search_paths: tuple[str, ...] | None = None,
    ):
        """Initialize with path to OSIM file and optional search paths.

        Args:
            model_path: Path to .osim XML file
            geometry_search_paths: Paths to search for geometry files.
                If None, uses default OpenSim paths.
        """
        self.model_path = Path(model_path)
        self.model_dir = self.model_path.parent

        if geometry_search_paths is None:
            # Import here to avoid circular dependency
            from osim_render.api.managers.settings_manager import (
                _get_default_geometry_paths,
            )

            self.geometry_search_paths = _get_default_geometry_paths()
        else:
            self.geometry_search_paths = geometry_search_paths

    def extract_all_geometry(self) -> dict[str, BodyGeometry]:
        """Extract geometry for all bodies from OSIM XML.

        Returns:
            Dictionary mapping body name to BodyGeometry

        Raises:
            FileNotFoundError: If model file does not exist
            ET.ParseError: If XML parsing fails
            AttributeError: If expected XML structure is invalid
            RuntimeError: If geometry extraction fails
        """
        geometry_map: dict[str, BodyGeometry] = {}

        # Read the file and preprocess to handle OpenSim's :: scope syntax
        # (e.g., HuntCrossleyForce::ContactParametersSet)
        with open(self.model_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove :: from tag names to make it valid XML for ElementTree
        # This allows parsing models with OpenSim's scope syntax
        import re

        processed_content = re.sub(
            r"<(/?)([a-zA-Z_][a-zA-Z0-9_]*)::([a-zA-Z_][a-zA-Z0-9_]*)",
            r"<\1\2_\3",
            content,
        )

        root = ET.fromstring(processed_content)

        body_set = root.find(".//BodySet")
        if body_set is None:
            return geometry_map

        objects = body_set.find("objects")
        if objects is not None:
            for body_elem in objects.findall("Body"):
                body_geom = self._extract_body_geometry(body_elem)
                if body_geom.geometries:
                    geometry_map[body_elem.get("name", "unknown")] = body_geom

        return geometry_map

    def _extract_body_geometry(self, body_elem: ET.Element) -> BodyGeometry:
        """Extract geometry from a Body XML element.

        Supports both old format (VisibleObject/DisplayGeometry) and new format
        (attached_geometry/Mesh) used in OpenSim 4.5+.

        Args:
            body_elem: XML element for a Body

        Returns:
            BodyGeometry with all geometry objects
        """
        body_name = body_elem.get("name", "unknown")
        geometries = []

        # Old format: VisibleObject/GeometrySet/DisplayGeometry
        visible_obj = body_elem.find("VisibleObject")
        if visible_obj is not None:
            geom_set = visible_obj.find("GeometrySet")
            if geom_set is not None:
                objects = geom_set.find("objects")
                if objects is not None:
                    for display_geom_elem in objects.findall("DisplayGeometry"):
                        geom = self._parse_display_geometry(
                            display_geom_elem, body_name
                        )
                        if geom:
                            geometries.append(geom)

        # New format (OpenSim 4.5+): attached_geometry/Mesh
        attached_geom = body_elem.find("attached_geometry")
        if attached_geom is not None:
            for mesh_elem in attached_geom.findall("Mesh"):
                geom = self._parse_mesh_geometry(mesh_elem, body_name)
                if geom:
                    geometries.append(geom)

        # Meshes hung off a PhysicalOffsetFrame under <components> rather than
        # attached to the body directly. Common wherever one body carries
        # several meshes at different places -- a lumped head-neck segment with
        # a mesh per cervical vertebra, for instance. Without this they are
        # silently dropped and the body renders bare.
        for frame_elem in body_elem.findall("components/PhysicalOffsetFrame"):
            frame_geom = frame_elem.find("attached_geometry")
            if frame_geom is None:
                continue
            transform = self._parse_frame_transform(frame_elem)
            for mesh_elem in frame_geom.findall("Mesh"):
                geom = self._parse_mesh_geometry(
                    mesh_elem, body_name, transform=transform
                )
                if geom:
                    geometries.append(geom)

        return BodyGeometry(body_name=body_name, geometries=tuple(geometries))

    @staticmethod
    def _parse_frame_transform(
        frame_elem: ET.Element,
    ) -> tuple[float, float, float, float, float, float]:
        """Convert a PhysicalOffsetFrame's pose to GeometryInfo's transform.

        OpenSim places a point q at p = t + R*q. GeometryInfo's 6-tuple is
        replayed by BodyVisualizer as RotateX/Y/Z then Translate on a
        vtkTransform, and in VTK's default PreMultiply mode that evaluates as
        p = R*(q + t') -- the translation lands inside the rotation. Passing
        R-transpose * t as the translation makes the two agree.
        """
        def read(tag: str) -> tuple[float, float, float]:
            elem = frame_elem.find(tag)
            if elem is None or not elem.text:
                return (0.0, 0.0, 0.0)
            vals = tuple(float(v) for v in elem.text.split())
            return vals if len(vals) == 3 else (0.0, 0.0, 0.0)

        rx, ry, rz = read("orientation")
        tx, ty, tz = read("translation")

        if rx == 0.0 and ry == 0.0 and rz == 0.0:
            return (0.0, 0.0, 0.0, tx, ty, tz)

        cx, sx = math.cos(rx), math.sin(rx)
        cy, sy = math.cos(ry), math.sin(ry)
        cz, sz = math.cos(rz), math.sin(rz)
        # Body-fixed XYZ, matching OpenSim's convention: R = Rx * Ry * Rz
        r = (
            (cy * cz, -cy * sz, sy),
            (sx * sy * cz + cx * sz, -sx * sy * sz + cx * cz, -sx * cy),
            (-cx * sy * cz + sx * sz, cx * sy * sz + sx * cz, cx * cy),
        )
        t = (tx, ty, tz)
        local = tuple(sum(r[i][k] * t[i] for i in range(3)) for k in range(3))
        return (rx, ry, rz, local[0], local[1], local[2])

    def _parse_display_geometry(
        self, elem: ET.Element, body_name: str
    ) -> GeometryInfo | None:
        """Parse a DisplayGeometry XML element.

        Args:
            elem: DisplayGeometry XML element
            body_name: Name of parent body

        Returns:
            GeometryInfo object or None if element is invalid or geometry is hidden

        Raises:
            ValueError: If geometry filename or values cannot be parsed
            AttributeError: If XML element structure is invalid
        """
        geom_file_elem = elem.find("geometry_file")
        if geom_file_elem is None or not geom_file_elem.text:
            return None

        geometry_file = geom_file_elem.text.strip()
        if not geometry_file:
            return None

        transform_elem = elem.find("transform")
        transform_str = (
            transform_elem.text
            if transform_elem is not None and transform_elem.text is not None
            else "0 0 0 0 0 0"
        )
        transform_vals = tuple(float(x) for x in transform_str.split())
        transform = (
            transform_vals
            if len(transform_vals) == 6
            else (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        )

        scale_elem = elem.find("scale_factors")
        scale_str = (
            scale_elem.text
            if scale_elem is not None and scale_elem.text is not None
            else "1 1 1"
        )
        scale_vals = tuple(float(x) for x in scale_str.split())
        scale_factors = scale_vals if len(scale_vals) == 3 else (1.0, 1.0, 1.0)

        disp_pref_elem = elem.find("display_preference")
        display_preference = (
            int(disp_pref_elem.text)
            if disp_pref_elem is not None and disp_pref_elem.text is not None
            else 4
        )

        opacity_elem = elem.find("opacity")
        opacity = (
            float(opacity_elem.text)
            if opacity_elem is not None and opacity_elem.text is not None
            else 1.0
        )

        if display_preference == 0:
            return None

        return GeometryInfo(
            name=f"{body_name}_geom_{len([])}",
            body_name=body_name,
            geometry_filename=geometry_file,
            transform=transform,
            scale_factors=scale_factors,
            display_preference=display_preference,
            opacity=opacity,
        )

    def _parse_mesh_geometry(
        self,
        elem: ET.Element,
        body_name: str,
        transform: tuple[float, float, float, float, float, float] | None = None,
    ) -> GeometryInfo | None:
        """Parse a Mesh XML element (OpenSim 4.5+ format).

        Args:
            elem: Mesh XML element
            body_name: Name of parent body
            transform: pose of the frame the mesh hangs off, when that is a
                PhysicalOffsetFrame rather than the body itself

        Returns:
            GeometryInfo object or None if element is invalid

        Raises:
            ValueError: If mesh filename or scale values cannot be parsed
            AttributeError: If XML element structure is invalid
        """
        mesh_name = elem.get("name", "mesh")

        mesh_file_elem = elem.find("mesh_file")
        if mesh_file_elem is None or not mesh_file_elem.text:
            return None

        mesh_file = mesh_file_elem.text.strip()
        if not mesh_file:
            return None

        scale_elem = elem.find("scale_factors")
        scale_str = (
            scale_elem.text
            if scale_elem is not None and scale_elem.text is not None
            else "1 1 1"
        )
        scale_vals = tuple(float(x) for x in scale_str.split())
        scale_factors = scale_vals if len(scale_vals) == 3 else (1.0, 1.0, 1.0)

        # Mesh elements in attached_geometry carry no transform of their own;
        # they inherit their Frame's. That is identity when the frame is the
        # body, and the caller's value when it is a PhysicalOffsetFrame.
        if transform is None:
            transform = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Default opacity and visibility for Mesh geometry
        opacity = 1.0
        display_preference = 3  # Shaded

        return GeometryInfo(
            name=f"{body_name}_{mesh_name}",
            body_name=body_name,
            geometry_filename=mesh_file,
            transform=transform,
            scale_factors=scale_factors,
            display_preference=display_preference,
            opacity=opacity,
        )

    def get_geometry_file_path(self, geometry_filename: str) -> Path | None:
        """Resolve geometry file path.

        Searches in priority order:
        1. Model directory
        2. Model/Geometry subdirectory
        3. Configured geometry search paths

        Args:
            geometry_filename: Name of geometry file (e.g., "femur.vtp")

        Returns:
            Full path to geometry file or None if not found
        """
        # Try model directory first
        model_dir_path = self.model_dir / geometry_filename
        if model_dir_path.exists():
            return model_dir_path

        # Try geometry subdirectory in model directory
        geom_path = self.model_dir / "Geometry" / geometry_filename
        if geom_path.exists():
            return geom_path

        # Try configured search paths
        for search_path in self.geometry_search_paths:
            full_path = Path(search_path) / geometry_filename
            if full_path.exists():
                return full_path

        return None


if __name__ == "__main__":
    """Smoke test for geometry extraction."""
    import sys

    model_path = Path("models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim")

    if model_path.exists():
        extractor = GeometryExtractor(model_path)
        geometry_map = extractor.extract_all_geometry()

        print(f"[OK] Extracted geometry for {len(geometry_map)} bodies")
        found_files = 0
        missing_files = 0

        for body_name in sorted(geometry_map.keys()):
            body_geom = geometry_map[body_name]
            print(f"  - {body_name}: {len(body_geom.geometries)} geometries")
            for geom in body_geom.geometries:
                file_path = extractor.get_geometry_file_path(geom.geometry_filename)
                if file_path:
                    found_files += 1
                    status = "OK"
                else:
                    missing_files += 1
                    status = "MISSING"
                print(f"      [{status}] {geom.geometry_filename}")

        print(f"\n[OK] Found: {found_files} files, Missing: {missing_files}")
        if found_files > 0:
            print("[OK] Geometry extraction smoke test passed!")
        else:
            print(
                "[INFO] Geometry files not in model directory (expected for this model)"
            )
    else:
        print(f"[SKIP] Model not found: {model_path}")
        sys.exit(1)
