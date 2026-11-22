"""
M06_frontal_orthographic.py

Render gait in the frontal (coronal) plane with orthographic projection.

Chimp fullbody model with bipedal IK data — frontal view reveals
mediolateral trunk sway, hip adduction, and the characteristic
wide-based gait of chimpanzee bipedalism.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/chimp_fullbody/model.osim \\
    --scripts M06 \\
    -g models/chimp_fullbody/Geometry
"""

from osim_render.api.animation.timeline import Timeline
from osim_render.api.animation.value_types import CameraState
from pathlib import Path

motion_file = Path("models/chimp_fullbody/abs/ik.sto")

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
        position=(cx, cy, cz + dist),
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

print(f"Frontal orthographic (Chimp bipedal): {timeline.duration:.2f}s")
print("  Projection: orthographic (no perspective distortion)")
print("  View: frontal/coronal plane (front view)")
print("Ready to render!")
