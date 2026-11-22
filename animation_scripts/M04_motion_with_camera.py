"""
M04_motion_with_camera.py

Add camera choreography on top of motion data playback.

Rajagopal scaled walking model — camera transitions from frontal to
sagittal view and back, synchronized with the gait cycle timing.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model resources/Code/CPP/Moco/example3DWalking/subject_walk_scaled.osim \\
    --scripts M04 \\
    -g resources/Code/CPP/Moco/example3DWalking \\
    -g vendor/opensim-gui/opensim-models/Geometry
"""

from osim_render.api.animation.timeline import Timeline
from osim_render.api.animation.value_types import CameraState
from pathlib import Path

motion_file = Path("resources/Code/CPP/Moco/example3DWalking/coordinates.sto")

if not motion_file.exists():
    raise FileNotFoundError(f"Motion file not found: {motion_file}")

motion = load_motion_from_file(str(motion_file))
duration = motion.end_time - motion.start_time

scene = Scene(model_manager, scene_manager, event_bus)
center = scene.model_center
dist   = scene.camera_distance
zoom   = scene.camera.zoom

scene.animate_camera_to(
    target_state=CameraState.front_view(center=center, distance=dist, zoom=zoom),
    duration=0.3, start_time=0,
)
scene.animate_camera_to(
    target_state=CameraState.side_view(center=center, distance=dist, zoom=zoom),
    duration=duration * 0.4, start_time=duration * 0.3,
)
scene.animate_camera_to(
    target_state=CameraState.front_view(center=center, distance=dist, zoom=zoom),
    duration=duration * 0.2, start_time=duration * 0.8,
)

motion_animation = create_animation_from_motion(motion)
scene_animation  = scene.build_timeline().animations[0]
timeline = Timeline(animations=(ParallelAnimation(animations=(motion_animation, scene_animation)),))

print(f"Motion + camera: {timeline.duration:.2f}s")
print(f"  Camera: front (0s) -> side ({duration*0.3:.1f}s) -> front ({duration*0.8:.1f}s)")
print("Ready to render!")
