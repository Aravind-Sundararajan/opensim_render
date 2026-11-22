"""Render a high-quality frontal-plane (face-forward) image of the chimp
fullbody model with a transparent background.

Usage:
    poetry run python scripts/render_chimp_frontal.py
"""

from pathlib import Path

from osim_render.api.animation.animation import AnimationState
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager

MODEL_PATH = Path(r"F:\dev\projects\gait_sim\models\chimp_fullbody\model_Feb2026.osim")
GEOMETRY_PATHS = (r"F:\dev\projects\gait_sim\models\chimp_fullbody\Geometry_archived9_2025",)
OUTPUT_PATH = Path("renders/chimp_frontal_hq.png")
RESOLUTION = (2160, 3840)  # portrait HQ

event_bus = EventBus()
model_manager = ModelManager(event_bus)
model_manager.load_model(MODEL_PATH)

offscreen = OffscreenRenderer(resolution=RESOLUTION, transparent_background=True)
scene_manager = SceneManager(model_manager, MODEL_PATH, GEOMETRY_PATHS)
scene_manager.create_scene(renderer=offscreen.renderer)

renderer = offscreen.renderer
renderer.ResetCamera()
camera = renderer.GetActiveCamera()
distance = camera.GetDistance()
cx, cy, cz = camera.GetFocalPoint()

# +X looks at the chimp's anterior side (face-forward / frontal plane)
camera.SetPosition(cx + distance, cy, cz)
camera.SetFocalPoint(cx, cy, cz)
camera.SetViewUp(0, 1, 0)
camera.SetParallelProjection(True)
renderer.ResetCameraClippingRange()

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
state = AnimationState(time=0.0, coordinate_values={}, camera_state=None, actor_properties={})
offscreen.save_frame(state, OUTPUT_PATH)
print(f"Saved {OUTPUT_PATH}")
