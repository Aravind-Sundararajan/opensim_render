"""OpenSim model (.osim) file loader."""

import xml.etree.ElementTree as ET
from pathlib import Path

from osim_render.api.geometry.model_data import ModelGeometry, BodyGeometry
from osim_render.api.geometry.mesh_data import MeshInstance
from osim_render.api.geometry.transform import Transform


class OSIMLoader:
    """Loader for OpenSim model files (.osim).

    Parses XML-based OpenSim model format and extracts
    model structure, bodies, and geometry references.
    """

    def __init__(self) -> None:
        """Initialize OpenSim loader."""
        self._error = ""

    def load(self, filepath: str | Path) -> ModelGeometry:
        """Load OpenSim model from .osim file.

        Args:
            filepath: Path to .osim file

        Returns:
            ModelGeometry with parsed bodies and geometry

        Raises:
            FileNotFoundError: If file not found
            ET.ParseError: If XML parsing fails
            AttributeError: If expected XML structure is missing
            RuntimeError: If model loading fails
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")

        tree = ET.parse(filepath)
        root = tree.getroot()

        # Find Model element (could be root or child)
        model_elem = root.find(".//Model")
        if model_elem is None:
            model_elem = root

        model_name = model_elem.get("name", filepath.stem)

        bodies = self._parse_bodies(root, filepath.parent)

        return ModelGeometry(
            name=model_name,
            bodies=tuple(bodies),
        )

    def get_error(self) -> str:
        """Get last error message.

        Returns:
            Error string from last operation
        """
        return self._error

    def _parse_bodies(self, root: ET.Element, model_dir: Path) -> list[BodyGeometry]:
        """Parse Body elements from OpenSim XML.

        Args:
            root: Root XML element
            model_dir: Directory containing model file

        Returns:
            List of BodyGeometry objects
        """
        bodies: list[BodyGeometry] = []

        # Find BodySet element
        body_set = root.find(".//BodySet")
        if body_set is None:
            return bodies

        # Search for Body elements in different XML structures
        objects = body_set.find("objects")
        body_elements = (
            objects.findall("Body")
            if objects is not None
            else body_set.findall("Body")
        )

        # Parse each Body
        for body_elem in body_elements:
            body_name = body_elem.get("name", "Unknown")
            meshes = self._parse_display_geometry(body_name, body_elem, model_dir)

            bodies.append(
                BodyGeometry(
                    name=body_name,
                    meshes=tuple(meshes),
                )
            )

        return bodies

    def _parse_display_geometry(
        self, body_name: str, body_elem: ET.Element, model_dir: Path
    ) -> list[MeshInstance]:
        """Parse display geometry for a body.

        Args:
            body_name: Name of body
            body_elem: Body XML element
            model_dir: Directory containing model

        Returns:
            List of MeshInstance objects
        """
        meshes: list[MeshInstance] = []

        # Find VisibleObject
        visible_obj = body_elem.find(".//VisibleObject")
        if visible_obj is None:
            return meshes

        # Find GeometrySet
        geom_set = visible_obj.find(".//GeometrySet")
        if geom_set is None:
            return meshes

        # Find DisplayGeometry elements
        objects = geom_set.find("objects")
        if objects is not None:
            display_geoms = objects.findall("DisplayGeometry")
        else:
            display_geoms = geom_set.findall("DisplayGeometry")

        for idx, display_geom in enumerate(display_geoms):
            mesh = self._parse_display_geometry_element(
                body_name, idx, display_geom, model_dir
            )
            if mesh is not None:
                meshes.append(mesh)

        return meshes

    def _parse_display_geometry_element(
        self, body_name: str, idx: int, geom_elem: ET.Element, model_dir: Path
    ) -> MeshInstance | None:
        """Parse single DisplayGeometry element.

        Args:
            body_name: Name of body
            idx: Index of geometry in body
            geom_elem: DisplayGeometry XML element
            model_dir: Directory containing model

        Returns:
            MeshInstance or None if geometry_file is empty

        Raises:
            ValueError: If color or transform values cannot be parsed
            AttributeError: If expected XML attributes are missing
        """
        # Parse geometry file
        geom_file_elem = geom_elem.find("geometry_file")
        if geom_file_elem is None or not geom_file_elem.text:
            return None

        geom_file_text = geom_file_elem.text.strip()
        if not geom_file_text:
            return None

        geom_path = model_dir / geom_file_text

        # Parse color (default: light gray)
        color = (0.8, 0.8, 0.8)
        color_elem = geom_elem.find("color")
        if color_elem is not None and color_elem.text:
            color_vals = [float(x) for x in color_elem.text.split()]
            if len(color_vals) >= 3:
                color = (color_vals[0], color_vals[1], color_vals[2])

        # Parse transform
        transform = Transform()
        transform_elem = geom_elem.find("transform")
        if transform_elem is not None and transform_elem.text:
            values = [float(x) for x in transform_elem.text.split()]
            if len(values) >= 6:
                transform = Transform(
                    rx=values[0],
                    ry=values[1],
                    rz=values[2],
                    tx=values[3],
                    ty=values[4],
                    tz=values[5],
                )

        # Create mesh instance with empty geometry
        # (Actual mesh data would be loaded by mesh loader later)
        mesh = MeshInstance(
            name=f"{body_name}_{idx}",
            vertices=(),
            indices=(),
            transform=transform,
            color=color,
            source_path=geom_path,
        )

        return mesh


if __name__ == "__main__":
    """Smoke test for OSIMLoader."""
    import tempfile

    print("OSIMLoader smoke test")

    # Create test .osim file
    osim_content = """<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument version="40000">
    <Model name="TestModel">
        <BodySet nObjects="2">
            <Body name="ground">
            </Body>
            <Body name="pelvis">
                <AttachmentGeometry>
                    <Mesh name="pelvis_mesh">
                    </Mesh>
                </AttachmentGeometry>
            </Body>
        </BodySet>
    </Model>
</OpenSimDocument>
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        osim_path = Path(tmpdir) / "test.osim"
        osim_path.write_text(osim_content)

        loader = OSIMLoader()
        model = loader.load(osim_path)

        assert model is not None
        assert model.name == "TestModel"
        assert model.body_count() == 2
        print("[OK] Model loaded successfully")

        ground = model.get_body("ground")
        assert ground is not None
        print("[OK] Body lookup works")

    print("\n[OK] All smoke tests passed!")
