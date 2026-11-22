"""
M07_crouch_gait.py

Play back a crouch gait pattern from the OpenSim Tutorial 1 data.

Parallel to 07_leg_swing_motion.py: where that script isolates a
single leg movement, this loads a different motion file entirely
to show a pathological gait pattern.

The Tutorial 1 dataset includes four crouch levels (crouch1-4)
representing increasing degrees of crouch severity, from mild (1)
to severe (4).

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim \\
    --scripts M07 -g "C:/OpenSim 4.5/Geometry"
"""

from osim_render.api.animation.timeline import Timeline
from osim_render.api.animation.value_types import CameraState
from pathlib import Path

# Moderate crouch gait (try crouch1.mot through crouch4.mot for comparison)
motion_file = Path("resources/Models/Gait2392_Simbody/Tutorial1/crouch2.mot")

if not motion_file.exists():
    raise FileNotFoundError(f"Motion file not found: {motion_file}")

motion = load_motion_from_file(str(motion_file))
duration = motion.end_time - motion.start_time

print(f"Loaded: {motion_file.name}")
print(f"  Frames: {motion.num_frames}, Duration: {duration:.2f}s")

scene = Scene(model_manager, scene_manager, event_bus)
center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom
cx, cy, cz = center

# Sagittal orthographic - best view for comparing crouch severity
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx + dist, cy, cz),
        focal_point=center,
        view_up=(0, 1, 0),
        zoom=zoom,
        parallel_projection=True,
    ),
    duration=0.3,
    start_time=0,
)

motion_animation = create_animation_from_motion(motion)
camera_timeline = scene.build_timeline()
timeline = Timeline(animations=(motion_animation,) + camera_timeline.animations)

print(f"\nTimeline: {timeline.duration:.2f}s, ready to render!")
print("Tip: change motion_file to crouch1-4.mot to see severity progression")
