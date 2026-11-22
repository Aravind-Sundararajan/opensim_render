"""Check ostrich-related models for wrap and contact actors."""

import traceback
from pathlib import Path

from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.tooling_paths import get_opensim_geometry_root, resolve_tool_path


MODEL_SPECS: tuple[tuple[str, tuple[str | Path, ...]], ...] = (
    (
        "models/toys/Rankin et al 2016/Ostrich_Run_Rigid_Tendon.osim",
        ("models/toys/Rankin et al 2016/geometry",),
    ),
    ("models/toys/1 joint/simple12.osim", (get_opensim_geometry_root(),)),
)


def inspect_model(model_path_text: str, geometry_path_values: tuple[str | Path, ...]) -> None:
    """Inspect a model and print its rendered actor collections."""
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
    bodies = sorted(scene.actors.keys()) if scene.actors else []
    print(f"\n{model_path}")
    print(f"  bodies={bodies}")
    print(f"  muscles={muscles}")
    print(f"  wraps={len(wraps)}: {wraps}")
    print(f"  contacts={len(contacts)}: {contacts}")


def main() -> None:
    """Inspect ostrich-related models for rendered actors."""
    for model_path_text, geometry_path_values in MODEL_SPECS:
        try:
            inspect_model(model_path_text, geometry_path_values)
        except Exception as exc:
            print(f"{model_path_text}: ERROR {exc}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
