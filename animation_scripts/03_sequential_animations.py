"""
03_sequential_animations.py

Animate coordinates ONE AFTER ANOTHER in sequence.

Australopithecus afarensis — trunk-to-limb cascade:
lumbar spine bends first, then hip follows, then knee.
This proximal-to-distal sequencing is characteristic of bipedal gait initiation.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/afarensis/model.osim \\
    --scripts 03 \\
    -g models/afarensis/Geometry
"""

scene = Scene(model_manager, scene_manager, event_bus)

# Trunk bends first (lumbar flexion, t=0-1s)
scene.animate_coordinate("lumbar_flexion", 0, 20, duration=1.0, start_time=0)

# Hip follows (t=1-2s)
scene.animate_coordinate("hip_flexion_r", 0, 40, duration=1.0, start_time=1.0)

# Knee last (t=2-3s)
scene.animate_coordinate("knee_angle_r", 0, -50, duration=1.0, start_time=2.0)

timeline = scene.build_timeline()

print("Created sequential animation (Afarensis trunk-to-limb cascade)")
print("Lumbar: 0-1s, Hip: 1-2s, Knee: 2-3s")
print(f"Total duration: {timeline.duration:.2f}s")
