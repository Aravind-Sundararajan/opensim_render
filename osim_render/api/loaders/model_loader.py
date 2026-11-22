"""High-level OpenSim model loader with mesh integration."""

from pathlib import Path

from osim_render.api.geometry.model_data import ModelGeometry, BodyGeometry
from osim_render.api.geometry.mesh_data import MeshInstance
from osim_render.api.loaders.osim_loader import OSIMLoader
from osim_render.api.loaders.mesh_loader import load_mesh
from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


class ModelLoader:
    """High-level model loader that combines OSIM parsing and mesh loading.

    Coordinates OSIM XML parsing with mesh file loading to create
    complete models with geometry data ready for rendering.
    """

    def __init__(self, geometry_search_paths: list[Path] | None = None) -> None:
        """Initialize model loader.

        Args:
            geometry_search_paths: Optional list of paths to search for geometry files
        """
        self._osim_loader = OSIMLoader()
        self._geometry_search_paths = geometry_search_paths or []

    def load(self, filepath: str | Path) -> ModelGeometry:
        """Load complete OpenSim model with geometry.

        Args:
            filepath: Path to .osim file

        Returns:
            ModelGeometry with all meshes loaded and ready to render

        Raises:
            FileNotFoundError: If model or mesh files not found
            ValueError: If parsing fails
        """
        filepath = Path(filepath)
        model_dir = filepath.parent

        model = self._osim_loader.load(filepath)

        # Prepare search paths: model directory first, then configured paths
        search_paths = [model_dir] + self._geometry_search_paths

        bodies_with_meshes = []
        for body in model.bodies:
            meshes_with_data = self._load_body_meshes(body, search_paths)
            body_with_meshes = BodyGeometry(
                name=body.name,
                meshes=tuple(meshes_with_data),
            )
            bodies_with_meshes.append(body_with_meshes)

        return ModelGeometry(
            name=model.name,
            bodies=tuple(bodies_with_meshes),
        )

    def _load_body_meshes(
        self, body: BodyGeometry, search_paths: list[Path]
    ) -> list[MeshInstance]:
        """Load mesh geometry for all instances in a body.

        Args:
            body: BodyGeometry with mesh file references
            search_paths: List of paths to search for geometry files

        Returns:
            List of MeshInstance objects with geometry data loaded
        """
        loaded_meshes = []

        for mesh in body.meshes:
            if mesh.source_path is None:
                continue

            geom = load_mesh(mesh.source_path, search_paths)

            vertices = tuple(geom.vertices.flatten().tolist())
            indices = tuple(geom.indices.flatten().tolist())

            mesh_with_data = MeshInstance(
                name=mesh.name,
                vertices=vertices,
                indices=indices,
                transform=mesh.transform,
                color=mesh.color,
                source_path=geom.source_path,
            )

            loaded_meshes.append(mesh_with_data)

        return loaded_meshes


if __name__ == "__main__":
    """Smoke test for model loader."""
    from pathlib import Path

    print("ModelLoader smoke test")

    # Try different models
    test_models = [
        Path("models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim"),
        Path("models/lowerExtremity/hamner running/FullBodyModel_Hamner2010_v2_0.osim"),
    ]

    for model_path in test_models:
        if not model_path.exists():
            continue

        print(f"\nTesting: {model_path.name}")
        loader = ModelLoader()
        model = loader.load(model_path)

        print(f"[OK] Model loaded: {model.name}")
        print(f"[OK] Bodies: {model.body_count()}")
        print(f"[OK] Total meshes: {model.total_mesh_count()}")

        total_vertices = sum(
            mesh.vertex_count() for body in model.bodies for mesh in body.meshes
        )
        print(f"[OK] Total loaded vertices: {total_vertices}")

        # Show meshes with geometry
        mesh_count = 0
        for body in model.bodies:
            for mesh in body.meshes:
                if mesh.vertex_count() > 0:
                    print(
                        f"    - {body.name}/{mesh.name}: "
                        f"{mesh.vertex_count()} vertices, {mesh.triangle_count()} triangles"
                    )
                    mesh_count += 1
                    if mesh_count >= 3:
                        break
            if mesh_count >= 3:
                break

        break  # Use first available model

    print("\n[OK] Model loader smoke test passed!")
