"""
M03_motion_segment.py

Extract and render a specific time window from a motion file.

Australopithecus afarensis model with human locomotion IK data.
Renders only the first half of the gait cycle (stance phase).

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/afarensis/model.osim \\
    --scripts M03 \\
    -g models/afarensis/Geometry
"""

from osim_render.api.loaders.motion_loader import MotionData
from osim_render.api.animation.timeline import Timeline
from pathlib import Path

motion_file = Path("models/afarensis/human_data/ik.sto")

if not motion_file.exists():
    raise FileNotFoundError(f"Motion file not found: {motion_file}")

full = load_motion_from_file(str(motion_file))
full_duration = full.end_time - full.start_time

print(f"Full motion: {full.num_frames} frames, {full_duration:.2f}s")

# Render only the first half (stance phase)
start_window = full.start_time
end_window   = full.start_time + full_duration * 0.5

segment_frames = [f for f in full.frames if start_window <= f.time <= end_window]

segment = MotionData(
    filepath=motion_file,
    frames=tuple(segment_frames),
    num_frames=len(segment_frames),
    start_time=start_window,
    end_time=end_window,
)

print(f"Segment: {segment.num_frames} frames, {end_window - start_window:.2f}s")
print(f"  [{start_window:.3f}s -> {end_window:.3f}s] (first 50% — stance phase)")

scene = Scene(model_manager, scene_manager, event_bus)
animation = create_animation_from_motion(segment)
timeline = Timeline(animations=(animation,))

print(f"\nTimeline: {timeline.duration:.2f}s, ready to render!")
