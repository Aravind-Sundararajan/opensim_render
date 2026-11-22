"""Check resource models for wrap and contact actors."""

from pathlib import Path

from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.tooling_paths import get_opensim_geometry_root, resolve_tool_path


MODEL_SPECS: tuple[tuple[str, tuple[str | Path, ...]], ...] = (
    (
        "resources/Code/CPP/Moco/example3DWalking/subject_walk_armless.osim",
        ("resources/Code/CPP/Moco/example3DWalking", get_opensim_geometry_root()),
    ),
    (
        "resources/Code/CPP/Moco/example3DWalking/subject_walk_scaled.osim",
        ("resources/Code/CPP/Moco/example3DWalking", get_opensim_geometry_root()),
    ),
    (
        "models/toys/ToyDropLanding/ToyLandingModel.osim",
        ("models/toys/ToyDropLanding/Geometry", get_opensim_geometry_root()),
    ),
)


def inspect_model(model_path_text: str, geometry_path_values: tuple[str | Path, ...]) -> None:
    """Inspect a resource model and print its wrap and contact summary."""
    model_path = resolve_tool_path(model_path_text)
    geometry_paths = tuple(resolve_tool_path(path_value)
                           for path_value in geometry_path_values)
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    model_manager.load_model(model_path)
    offscreen_renderer = OffscreenRenderer(resolution=(320, 240))
    scene_manager = SceneManager(
        model_manager,
        model_path,
        tuple(str(path) for path in geometry_paths),
    )
    scene_manager.create_scene(renderer=offscreen_renderer.renderer)
    scene = scene_manager.get_scene()
    if scene is None:
        raise RuntimeError(f"Scene was not created for {model_path}")
    wraps = sorted(scene.wrap_actors.keys()) if scene.wrap_actors else []
    contacts = sorted(scene.contact_actors.keys()
                      ) if scene.contact_actors else []
    muscles = len(scene.muscle_actors) if scene.muscle_actors else 0
    print(f"\n{model_path}")
    print(f"  muscles={muscles}, wraps={len(wraps)}, contacts={len(contacts)}")
    if wraps:
        print(f"  wrap names: {wraps[:8]}")
    if contacts:
        print(f"  contact names: {contacts}")


def main() -> None:
    """Inspect resource models for wrap and contact actors."""
    for model_path_text, geometry_path_values in MODEL_SPECS:
        try:
            inspect_model(model_path_text, geometry_path_values)
        except Exception as exc:
            print(f"{model_path_text}: ERROR {exc}")


if __name__ == "__main__":
    main()
