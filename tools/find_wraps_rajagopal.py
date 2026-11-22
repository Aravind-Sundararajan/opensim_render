"""Check the Rajagopal model for wrap and contact actors."""

import traceback
from pathlib import Path

from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.tooling_paths import resolve_tool_path


MODEL_SPECS: tuple[tuple[str, tuple[str | Path, ...]], ...] = (
    (
        "vendor/opensim-gui/opensim-models/Models/Rajagopal/Rajagopal2016.osim",
        ("vendor/opensim-gui/opensim-models/Models/Rajagopal/Geometry",),
    ),
)


def inspect_model(model_path_text: str, geometry_path_values: tuple[str | Path, ...]) -> None:
    """Inspect the Rajagopal model and print its actor counts."""
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
    bodies = sorted(scene.actors.keys()) if scene.actors else []
    muscles = sorted(scene.muscle_actors.keys()) if scene.muscle_actors else []
    print(f"\n{model_path}")
    print(f"  bodies={len(bodies)}: {bodies[:6]}")
    print(f"  muscles={len(muscles)}: {muscles[:4]}")
    print(f"  wraps={len(wraps)}: {wraps[:8]}")
    print(f"  contacts={len(contacts)}: {contacts[:8]}")


def main() -> None:
    """Inspect the Rajagopal model for rendered wrap and contact actors."""
    for model_path_text, geometry_path_values in MODEL_SPECS:
        try:
            inspect_model(model_path_text, geometry_path_values)
        except Exception as exc:
            print(f"{model_path_text}: ERROR {exc}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
