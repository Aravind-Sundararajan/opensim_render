"""List all actor names in the gait2392 scene."""

from osim_render.api.logging.logger import get_logger_for
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.tooling_paths import get_opensim_geometry_root, resolve_tool_path

logger = get_logger_for(__name__)


def main() -> None:
    """Load the gait2392 model and print actor collections."""
    model_path = resolve_tool_path(
        "models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim"
    )
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    model_manager.load_model(model_path)
    offscreen_renderer = OffscreenRenderer(resolution=(320, 240))
    scene_manager = SceneManager(
        model_manager,
        model_path,
        (str(get_opensim_geometry_root()),),
    )
    scene_manager.create_scene(renderer=offscreen_renderer.renderer)
    scene = scene_manager.get_scene()
    if scene is None:
        logger.error("scene not created")
        return
    print("BODIES:", sorted(scene.actors.keys()))
    print("MUSCLES:", sorted(scene.muscle_actors.keys())
          if scene.muscle_actors else [])
    print("WRAPS:", sorted(scene.wrap_actors.keys())
          if scene.wrap_actors else [])
    print("CONTACTS:", sorted(scene.contact_actors.keys())
          if scene.contact_actors else [])
    print("MARKERS:", sorted(scene.marker_actors.keys())
          if scene.marker_actors else [])
    print(
        "BODY_ORIGINS:",
        sorted(scene.body_origin_actors.keys()
               ) if scene.body_origin_actors else [],
    )
    print(
        "JOINT_PARENTS:",
        sorted(scene.joint_parent_actors.keys()
               ) if scene.joint_parent_actors else [],
    )


if __name__ == "__main__":
    main()
