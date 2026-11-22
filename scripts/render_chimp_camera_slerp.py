"""Slerp the camera from a sagittal (side) view to a frontal (anterior) view
of the chimp fullbody model (May 2025 version), with muscles color-coded by
functional group.

Follows the camera-animation pattern from
animation_scripts/08_camera_animation.py (Scene.animate_camera_to with
CameraTween's slerp-based position interpolation).

Usage:
    poetry run python scripts/render_chimp_camera_slerp.py
"""

from pathlib import Path

from osim_render.api.animation.scene import Scene
from osim_render.api.animation.value_types import CameraState
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.rendering.video_exporter import VideoExporter, VideoExportConfig

MODEL_PATH = Path(r"F:\dev\projects\gait_sim\models\chimp_fullbody\model_May2025.osim")
OUTPUT_PATH = Path("renders/chimp_camera_slerp_sagittal_to_frontal.mp4")
RESOLUTION = (1280, 1280)
FPS = 30
SLERP_DURATION = 4.0  # seconds

# Same muscle-group color palette as render_chimp_may_muscles.py (Rajagopal-style).
MUSCLE_GROUPS: dict[str, tuple[tuple[float, float, float], tuple[str, ...]]] = {
    "glutes_hip_extensors": (
        (0.90, 0.30, 0.10),
        ("glmax1", "glmax2", "glmax3", "glmax4", "glmed1", "glmed2", "glmed3",
         "glmin1", "glmin2", "glmin3", "piri", "gem", "quadfem", "obex"),
    ),
    "hip_flexors": (
        (0.10, 0.50, 0.90),
        ("iliacus", "psoas", "recfem", "sart"),
    ),
    "hamstrings": (
        (0.90, 0.70, 0.10),
        ("bflh", "bfsh", "semimem", "semiten"),
    ),
    "quadriceps": (
        (0.20, 0.90, 0.40),
        ("vasint", "vaslat", "vasmed"),
    ),
    "adductors": (
        (0.70, 0.20, 0.90),
        ("adbrev", "adlong", "admag1", "admag2", "admag3", "admag4", "grac", "pect"),
    ),
    "plantarflexors": (
        (0.95, 0.40, 0.60),
        ("gaslat", "gasmed", "sol", "tibpos", "fdf", "fdt"),
    ),
    "dorsiflexors_evertors": (
        (0.20, 0.85, 0.85),
        ("tibant", "edl", "ehl", "perbrev", "perlong"),
    ),
}


def muscle_color(muscle_name: str) -> tuple[float, float, float] | None:
    """Return the group color for a muscle name, or None if uncategorized."""
    base = muscle_name.removesuffix("_l").removesuffix("_r")
    for color, members in MUSCLE_GROUPS.values():
        if base in members:
            return color
    return None


event_bus = EventBus()
model_manager = ModelManager(event_bus)
model_manager.load_model(MODEL_PATH)

offscreen = OffscreenRenderer(resolution=RESOLUTION, background_color=(0.0, 0.0, 0.0))
scene_manager = SceneManager(model_manager, MODEL_PATH)
render_scene = scene_manager.create_scene(renderer=offscreen.renderer)

muscle_actors = render_scene.muscle_actors
if muscle_actors is None:
    raise SystemExit("Scene has no muscle actors to color")

for muscle_name, muscle_actor in muscle_actors.items():
    color = muscle_color(muscle_name)
    if color is not None:
        muscle_actor.GetProperty().SetColor(*color)
    muscle_actor.SetVisibility(True)

# Sagittal start view: camera along +Z, anterior (+X) faces left/right in frame.
renderer = offscreen.renderer
renderer.ResetCamera()
camera = renderer.GetActiveCamera()
distance = camera.GetDistance()
cx, cy, cz = camera.GetFocalPoint()

camera.SetPosition(cx, cy, cz + distance)
camera.SetFocalPoint(cx, cy, cz)
camera.SetViewUp(0, 1, 0)
camera.SetParallelProjection(True)
renderer.ResetCameraClippingRange()

scene = Scene(model_manager, scene_manager, event_bus)

# Slerp from the sagittal (+Z) start view to a frontal (+X, anterior) view.
frontal_view = CameraState(
    position=(cx + distance, cy, cz),
    focal_point=(cx, cy, cz),
    view_up=(0, 1, 0),
    zoom=scene.camera.zoom,
    parallel_projection=True,
)
scene.animate_camera_to(target_state=frontal_view, duration=SLERP_DURATION, start_time=0.0)

timeline = scene.build_timeline()

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
config = VideoExportConfig(
    output_file=OUTPUT_PATH,
    resolution=RESOLUTION,
    fps=FPS,
    quality="high",
)
exporter = VideoExporter(scene_manager, config, renderer=offscreen)


def progress(current: int, total: int) -> None:
    print(f"Frame {current}/{total}")


result = exporter.export_timeline(timeline, progress_callback=progress)
print(f"Saved {result.output_file}")
