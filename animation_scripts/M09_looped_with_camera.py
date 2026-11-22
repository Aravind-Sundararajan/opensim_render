"""
M09_looped_with_camera.py

Three gait cycles with camera transitions synchronized to the cycle timing.

Parallel to 09_oscillating_motion.py: where that script loops
a joint back-and-forth in phases, this loops full gait data
while the camera transitions through views at each cycle boundary.

Camera plan:
  Cycle 1: Frontal view, perspective  (see mediolateral motion)
  Cycle 2: Sagittal view, perspective  (rotate from frontal)
  Cycle 3: Sagittal view, orthographic  (clinical analysis view)

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim \\
    --scripts M09 -g "C:/OpenSim 4.5/Geometry"
"""

from osim_render.api.loaders.motion_loader import MotionData, MotionFrame
from osim_render.api.animation.timeline import Timeline
from osim_render.api.animation.value_types import CameraState
from pathlib import Path

motion_file = Path("resources/Models/Gait2392_Simbody/Tutorial1/normal.mot")

if not motion_file.exists():
    raise FileNotFoundError(f"Motion file not found: {motion_file}")

original = load_motion_from_file(str(motion_file))
cycle_duration = original.end_time - original.start_time
num_cycles = 3

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

scene = Scene(model_manager, scene_manager, event_bus)
center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom
cx, cy, cz = center

# Cycle 1: frontal perspective
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx, cy, cz + dist), focal_point=center, view_up=(0, 1, 0),
        zoom=zoom, parallel_projection=False,
    ),
    duration=0.3,
    start_time=0,
)

# Cycle 2: rotate to sagittal
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx + dist, cy, cz), focal_point=center, view_up=(0, 1, 0),
        zoom=zoom, parallel_projection=False,
    ),
    duration=cycle_duration * 0.5,
    start_time=cycle_duration,
)

# Cycle 3: switch to orthographic
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx + dist, cy, cz), focal_point=center, view_up=(0, 1, 0),
        zoom=zoom, parallel_projection=True,
    ),
    duration=0.3,
    start_time=cycle_duration * 2,
)

motion_animation = create_animation_from_motion(motion)
scene_animation = scene.build_timeline().animations[0]
timeline = Timeline(animations=(ParallelAnimation(animations=(motion_animation, scene_animation)),))

c = cycle_duration
print(f"3 looped cycles with camera transitions: {timeline.duration:.2f}s")
print(f"  Cycle 1 (0-{c:.1f}s):    frontal, perspective")
print(f"  Cycle 2 ({c:.1f}-{2*c:.1f}s): sagittal, perspective (rotating)")
print(f"  Cycle 3 ({2*c:.1f}-{3*c:.1f}s): sagittal, orthographic")
print("Ready to render!")
