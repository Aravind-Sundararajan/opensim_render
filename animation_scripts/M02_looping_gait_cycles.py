"""
M02_looping_gait_cycles.py

Repeat a single gait cycle multiple times.

Chimp fullbody model with inverse kinematics data from bipedal walking trials.
Three cycles are concatenated end-to-end to fill a longer timeline.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/chimp_fullbody/model.osim \\
    --scripts M02 \\
    -g models/chimp_fullbody/Geometry
"""

from osim_render.api.loaders.motion_loader import MotionData, MotionFrame
from osim_render.api.animation.timeline import Timeline
from pathlib import Path

motion_file = Path("models/chimp_fullbody/abs/ik.sto")

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

print(f"Single cycle: {cycle_duration:.2f}s")
print(f"Looped x{num_cycles}: {motion.end_time:.2f}s total ({motion.num_frames} frames)")

scene = Scene(model_manager, scene_manager, event_bus)
animation = create_animation_from_motion(motion)
timeline = Timeline(animations=(animation,))

print(f"\nTimeline: {timeline.duration:.2f}s, ready to render!")
