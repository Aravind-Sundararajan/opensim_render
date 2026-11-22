"""
M08_camera_orbit.py

Orbit the camera around the model during motion playback.

Parallel to 08_camera_animation.py: where that script animates
both joints and camera together, this adds a full camera orbit
on top of real motion data for a cinematic 360-degree reveal.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim \\
    --scripts M08 -g "C:/OpenSim 4.5/Geometry"
"""

from osim_render.api.loaders.motion_loader import MotionData, MotionFrame
from osim_render.api.animation.timeline import Timeline
from osim_render.api.animation.value_types import CameraState
from pathlib import Path

motion_file = Path("resources/Models/Gait2392_Simbody/Tutorial1/normal.mot")

if not motion_file.exists():
    raise FileNotFoundError(f"Motion file not found: {motion_file}")

# Loop 2 cycles so the orbit has enough time to complete
original = load_motion_from_file(str(motion_file))
cycle_duration = original.end_time - original.start_time
num_cycles = 2

looped_frames = []
for cycle in range(num_cycles):
    offset = cycle * cycle_duration
    for frame in original.frames:
        looped_frames.append(MotionFrame(
            time=frame.time - original.start_time + offset,
            coordinate_values=frame.coordinate_values.copy(),
        ))

motion = MotionData(
    filepath=motion_file,
    frames=tuple(looped_frames),
    num_frames=len(looped_frames),
    start_time=0.0,
    end_time=num_cycles * cycle_duration,
)

duration = motion.end_time

scene = Scene(model_manager, scene_manager, event_bus)
center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom

# Orbit: front -> side -> back -> front over the full duration
scene.animate_camera_to(
    target_state=CameraState.front_view(center=center, distance=dist, zoom=zoom),
    duration=0.3,
    start_time=0,
)

scene.animate_camera_to(
    target_state=CameraState.side_view(center=center, distance=dist, zoom=zoom),
    duration=duration * 0.3,
    start_time=duration * 0.1,
)

scene.animate_camera_to(
    target_state=CameraState.isometric_view(center=center, distance=dist, zoom=zoom),
    duration=duration * 0.3,
    start_time=duration * 0.45,
)

scene.animate_camera_to(
    target_state=CameraState.front_view(center=center, distance=dist, zoom=zoom),
    duration=duration * 0.2,
    start_time=duration * 0.8,
)

motion_animation = create_animation_from_motion(motion)
scene_animation = scene.build_timeline().animations[0]
timeline = Timeline(animations=(ParallelAnimation(animations=(motion_animation, scene_animation)),))

print(f"Camera orbit over {num_cycles} gait cycles: {timeline.duration:.2f}s")
print("  Camera: front -> side -> isometric -> front")
print("Ready to render!")
