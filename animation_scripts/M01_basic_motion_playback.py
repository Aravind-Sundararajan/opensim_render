"""
M01_basic_motion_playback.py

Load a motion file and play it back. The simplest possible M-script.

Rajagopal scaled walking model with the Moco example3DWalking coordinate
solution — real measured walking kinematics replayed on the full-body model.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model resources/Code/CPP/Moco/example3DWalking/subject_walk_scaled.osim \\
    --scripts M01 \\
    -g resources/Code/CPP/Moco/example3DWalking \\
    -g vendor/opensim-gui/opensim-models/Geometry
"""

from osim_render.api.animation.timeline import Timeline
from pathlib import Path

motion_file = Path("resources/Code/CPP/Moco/example3DWalking/coordinates.sto")

if not motion_file.exists():
    raise FileNotFoundError(f"Motion file not found: {motion_file}")

motion = load_motion_from_file(str(motion_file))

print(f"Loaded: {motion_file.name}")
print(f"  Frames:   {motion.num_frames}")
print(f"  Duration: {motion.end_time - motion.start_time:.2f}s")
print(f"  Range:    {motion.start_time:.3f}s - {motion.end_time:.3f}s")

scene = Scene(model_manager, scene_manager, event_bus)
animation = create_animation_from_motion(motion)
timeline = Timeline(animations=(animation,))

print(f"\nTimeline: {timeline.duration:.2f}s, ready to render!")
