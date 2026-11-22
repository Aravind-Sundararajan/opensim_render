"""
M10_normal_vs_crouch.py

Play normal gait followed immediately by crouch gait for comparison.

Parallel to 10_speed_variations.py: where that script shows the same
motion at different speeds, this shows different motion files back-to-back
so you can directly compare normal and pathological gait kinematics.

The two motions are concatenated into one timeline:
  t=0 to t=T1:      normal.mot  (one full cycle)
  t=T1 to t=T1+T2:  crouch2.mot (one full cycle)

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim \\
    --scripts M10 -g "C:/OpenSim 4.5/Geometry"
"""

from osim_render.api.loaders.motion_loader import MotionData, MotionFrame
from osim_render.api.animation.timeline import Timeline
from osim_render.api.animation.value_types import CameraState
from pathlib import Path

normal_file = Path("resources/Models/Gait2392_Simbody/Tutorial1/normal.mot")
crouch_file = Path("resources/Models/Gait2392_Simbody/Tutorial1/crouch2.mot")

for f in (normal_file, crouch_file):
    if not f.exists():
        raise FileNotFoundError(f"Motion file not found: {f}")

normal = load_motion_from_file(str(normal_file))
crouch = load_motion_from_file(str(crouch_file))

normal_duration = normal.end_time - normal.start_time
crouch_duration = crouch.end_time - crouch.start_time

# Concatenate: normal first, then crouch offset by normal's duration
combined_frames = []

for frame in normal.frames:
    combined_frames.append(MotionFrame(
        time=frame.time - normal.start_time,
        coordinate_values=frame.coordinate_values.copy(),
    ))

for frame in crouch.frames:
    combined_frames.append(MotionFrame(
        time=frame.time - crouch.start_time + normal_duration,
        coordinate_values=frame.coordinate_values.copy(),
    ))

combined = MotionData(
    filepath=normal_file,
    frames=tuple(combined_frames),
    num_frames=len(combined_frames),
    start_time=0.0,
    end_time=normal_duration + crouch_duration,
)

print(f"Normal:  {normal_duration:.2f}s ({normal.num_frames} frames)")
print(f"Crouch:  {crouch_duration:.2f}s ({crouch.num_frames} frames)")
print(f"Combined: {combined.end_time:.2f}s total")

scene = Scene(model_manager, scene_manager, event_bus)
center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom
cx, cy, cz = center

# Hold sagittal orthographic throughout for clean comparison
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx + dist, cy, cz), focal_point=center, view_up=(0, 1, 0),
        zoom=zoom, parallel_projection=True,
    ),
    duration=0.3,
    start_time=0,
)

motion_animation = create_animation_from_motion(combined)
camera_timeline = scene.build_timeline()
timeline = Timeline(animations=(motion_animation,) + camera_timeline.animations)

print(f"\nTimeline: {timeline.duration:.2f}s")
print(f"  0 - {normal_duration:.1f}s: normal gait")
print(f"  {normal_duration:.1f} - {combined.end_time:.1f}s: crouch gait")
print("Ready to render!")
