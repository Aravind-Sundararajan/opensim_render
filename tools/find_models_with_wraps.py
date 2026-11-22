"""Find local models that have wrap objects and contact geometry."""

from pathlib import Path

from osim_render.api.logging.logger import get_logger_for
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.tooling_paths import get_opensim_geometry_root, resolve_tool_path

logger = get_logger_for(__name__)


MODEL_SPECS: tuple[tuple[str, tuple[str | Path, ...]], ...] = (
    (
        "models/lowerExtremity/Gait10dof18musc/gait10dof18musc.osim",
        (get_opensim_geometry_root(),),
    ),
    (
        "models/toys/ToyDropLanding/ToyLandingModel.osim",
        ("models/toys/ToyDropLanding/Geometry",),
    ),
    ("models/toys/Tug_of_War/Tug_of_War.osim", (get_opensim_geometry_root(),)),
    ("models/upperExtremity/Arm26/arm26.osim", (get_opensim_geometry_root(),)),
    (
        "models/lowerExtremity/Leg6Dof9Musc/leg6dof9musc.osim",
        (get_opensim_geometry_root(),),
    ),
)


def inspect_model(model_path_text: str, geometry_path_values: tuple[str | Path, ...]) -> None:
    """Load a model and print summary counts for its rendered geometry."""
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
        logger.error("scene not created for %s", model_path)
        return
    wraps = sorted(scene.wrap_actors.keys()) if scene.wrap_actors else []
    contacts = sorted(scene.contact_actors.keys()
                      ) if scene.contact_actors else []
    muscles = len(scene.muscle_actors) if scene.muscle_actors else 0
    print(f"\n{model_path}")
    print(f"  wraps={len(wraps)}: {wraps[:5]}")
    print(f"  contacts={len(contacts)}: {contacts[:5]}")
    print(f"  muscles={muscles}")


def main() -> None:
    """Inspect several local models for wrap and contact geometry."""
    for model_path_text, geometry_path_values in MODEL_SPECS:
        try:
            inspect_model(model_path_text, geometry_path_values)
        except Exception as exc:
            print(f"{model_path_text}: ERROR {exc}")


if __name__ == "__main__":
    main()
