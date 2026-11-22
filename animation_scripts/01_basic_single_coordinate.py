"""
01_basic_single_coordinate.py

The simplest animation: move a single coordinate from one value to another.

Rajagopal scaled walking model — hip flexion from neutral to 45 degrees.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model resources/Code/CPP/Moco/example3DWalking/subject_walk_scaled.osim \\
    --scripts 01 \\
    -g resources/Code/CPP/Moco/example3DWalking \\
    -g vendor/opensim-gui/opensim-models/Geometry
"""

scene = Scene(model_manager, scene_manager, event_bus)

scene.animate_coordinate("hip_flexion_r", 0, 45, duration=2.0)

timeline = scene.build_timeline()

print(f"Created animation: {timeline.duration:.2f}s duration")
