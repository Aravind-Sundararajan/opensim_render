"""
M05_sagittal_orthographic.py

Render gait in sagittal plane with orthographic (parallel) projection.

Australopithecus afarensis with human locomotion IK data — sagittal
orthographic is the standard clinical view for gait analysis.
Orthographic projection removes depth distortion so joint angles
and segment lengths are visually accurate.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/afarensis/model.osim \\
    --scripts M05 \\
    -g models/afarensis/Geometry
"""

from osim_render.api.animation.timeline import Timeline
from osim_render.api.animation.value_types import CameraState
from pathlib import Path

motion_file = Path("models/afarensis/human_data/ik.sto")

if not motion_file.exists():
    raise FileNotFoundError(f"Motion file not found: {motion_file}")

motion = load_motion_from_file(str(motion_file))

scene = Scene(model_manager, scene_manager, event_bus)
center = scene.model_center
dist   = scene.camera_distance
zoom   = scene.camera.zoom
cx, cy, cz = center

scene.animate_camera_to(
    target_state=CameraState(
        position=(cx + dist, cy, cz),
        focal_point=center,
        view_up=(0, 1, 0),
        zoom=zoom,
        parallel_projection=True,
    ),
    duration=0.3, start_time=0,
)

motion_animation = create_animation_from_motion(motion)
scene_animation  = scene.build_timeline().animations[0]
timeline = Timeline(animations=(ParallelAnimation(animations=(motion_animation, scene_animation)),))

print(f"Sagittal orthographic (Afarensis + human IK): {timeline.duration:.2f}s")
print("  Projection: orthographic (no perspective distortion)")
print("  View: sagittal plane (side view)")
print("Ready to render!")
