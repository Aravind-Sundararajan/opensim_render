"""
M11_production_render.py

Full production render: 3 looped gait cycles with synchronized
camera choreography and orthographic transition.

Parallel to 11_complex_combined_motion.py: where that script
combines phases, easing, and camera into a polished squat animation,
this combines looping, camera choreography, and projection switching
into a polished gait visualization.

Structure:
  Cycle 1 (0-T):       Frontal perspective  — see the whole body
  Cycle 2 (T-2T):      Rotate to sagittal   — classic gait view
  Cycle 3 (2T-3T):     Sagittal orthographic — clinical analysis

USAGE:
  # Standard speed
  poetry run python scripts/render_animation_scripts.py \\
    --model models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim \\
    --scripts M11 -g "C:/OpenSim 4.5/Geometry"

  # Slow motion (2x slower)
  poetry run python scripts/render_animation_scripts.py \\
    --model models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim \\
    --scripts M11 -g "C:/OpenSim 4.5/Geometry" --playback-speed 0.5
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
c = cycle_duration

# ============================================
# CYCLE 1: Frontal perspective
# ============================================
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx, cy, cz + dist), focal_point=center, view_up=(0, 1, 0),
        zoom=zoom, parallel_projection=False,
    ),
    duration=0.3,
    start_time=0,
)

# ============================================
# CYCLE 2: Rotate to sagittal view
# ============================================
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx + dist, cy, cz), focal_point=center, view_up=(0, 1, 0),
        zoom=zoom, parallel_projection=False,
    ),
    duration=c * 0.6,
    start_time=c,
)

# ============================================
# CYCLE 3: Switch to orthographic
# ============================================
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx + dist, cy, cz), focal_point=center, view_up=(0, 1, 0),
        zoom=zoom, parallel_projection=True,
    ),
    duration=0.4,
    start_time=2 * c,
)

motion_animation = create_animation_from_motion(motion)
scene_animation = scene.build_timeline().animations[0]
timeline = Timeline(animations=(ParallelAnimation(animations=(motion_animation, scene_animation)),))

print(f"Production render: {timeline.duration:.2f}s ({num_cycles} gait cycles)")
print(f"  Cycle 1 (0-{c:.1f}s):    frontal, perspective")
print(f"  Cycle 2 ({c:.1f}-{2*c:.1f}s): sagittal, perspective (rotating)")
print(f"  Cycle 3 ({2*c:.1f}-{3*c:.1f}s): sagittal, orthographic")
print(f"  Total frames: {motion.num_frames}")
print("Ready to render!")
