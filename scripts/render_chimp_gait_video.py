"""Render a slow-motion sagittal-plane video of the chimp fullbody
muscle-tracking simulation, with leg-bone color-coding and muscle paths.

Usage:
    poetry run python scripts/render_chimp_gait_video.py
"""

from pathlib import Path

import imageio

from osim_render.api.animation.integration import MotionDataAnimation
from osim_render.api.animation.timeline import Timeline
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.loaders.motion_loader import MotionLoader
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager

SIM_DIR = Path(
    r"F:\dev\projects\gait_sim\output\muscle\chimp_fullbody\EMG\Tracking_wEMG_w0_june2026\met"
)
# The tracking model's muscles use FunctionBasedPath (no visual geometry), so
# use model_May2025.osim instead - it has the same lower-limb coordinate names
# but its DeGrooteFregly2016Muscle actuators use a visualizable GeometryPath.
MODEL_PATH = Path(r"F:\dev\projects\gait_sim\models\chimp_fullbody\model_May2025.osim")
MOTION_PATH = SIM_DIR / "states.sto"
OUTPUT_PATH = Path("renders/chimp_gait_sagittal.mp4")
RESOLUTION = (960, 1280)
FPS = 30
TIME_SCALE = 0.2  # slow-motion: stretch the ~0.8s cycle to ~4s

event_bus = EventBus()
model_manager = ModelManager(event_bus)
model_manager.load_model(MODEL_PATH)

motion_loader = MotionLoader()
motion_data = motion_loader.load(MOTION_PATH, model_manager.get_opensim_model())

offscreen = OffscreenRenderer(resolution=RESOLUTION, background_color=(0.0, 0.0, 0.0))
scene_manager = SceneManager(model_manager, MODEL_PATH)
scene = scene_manager.create_scene(renderer=offscreen.renderer)

LEFT_LEG_COLOR = (0.2, 0.4, 1.0)
RIGHT_LEG_COLOR = (1.0, 0.2, 0.2)
LEG_BODIES = ("femur", "tibia", "talus", "toes", "hallux")

for body_name, actor in scene.actors.items():
    if not any(body_name.startswith(leg_body) for leg_body in LEG_BODIES):
        continue
    if body_name.endswith("_l"):
        actor.GetProperty().SetColor(*LEFT_LEG_COLOR)
    elif body_name.endswith("_r"):
        actor.GetProperty().SetColor(*RIGHT_LEG_COLOR)

MUSCLE_COLOR = (1.0, 0.84, 0.0)  # gold, distinct from the leg-bone red/blue
muscle_actors = scene.muscle_actors
if muscle_actors is None:
    raise SystemExit("Scene has no muscle actors to render")

for muscle_actor in muscle_actors.values():
    muscle_actor.SetVisibility(True)
    muscle_actor.GetProperty().SetColor(*MUSCLE_COLOR)

renderer = offscreen.renderer
model = model_manager.get_opensim_model()
state = model_manager.get_opensim_state()
if model is None or state is None:
    raise SystemExit(f"Model failed to load from {MODEL_PATH}")
camera = renderer.GetActiveCamera()

animation = MotionDataAnimation(name="gait", motion_data=motion_data, time_scale=TIME_SCALE)
timeline = Timeline(animations=(animation,))
frames, frame_count = timeline.iterate_frames_count(fps=FPS)

camera_distance: float | None = None
focal_y: float | None = None
focal_z: float | None = None

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with imageio.get_writer(
    str(OUTPUT_PATH),
    fps=FPS,
    codec="libx264",
    output_params=["-crf", "18", "-preset", "medium"],
) as writer:
    for frame_num, anim_state in enumerate(frames):
        scene_manager.update_frame(anim_state)
        scene_manager.update_muscle_paths()

        pelvis_pos = model.getBodySet().get("pelvis").getPositionInGround(state)
        pelvis_x = pelvis_pos.get(0)

        if camera_distance is None:
            renderer.ResetCamera()
            camera_distance = camera.GetDistance()
            focal_point = camera.GetFocalPoint()
            focal_y, focal_z = focal_point[1], focal_point[2]
            camera.SetViewUp(0, 1, 0)
            camera.SetParallelProjection(True)

        assert focal_y is not None and focal_z is not None
        camera.SetFocalPoint(pelvis_x, focal_y, focal_z)
        camera.SetPosition(pelvis_x, focal_y, focal_z + camera_distance)
        renderer.ResetCameraClippingRange()

        image = offscreen.render_frame(anim_state)
        writer.append_data(image)
        print(f"Frame {frame_num + 1}/{frame_count}")

print(f"Saved {OUTPUT_PATH}")
