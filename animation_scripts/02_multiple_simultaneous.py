"""
02_multiple_simultaneous.py

Animate multiple coordinates at the SAME TIME.

Chimp fullbody model — hip, knee, and toe coordination running in parallel.
Chimpanzees use toe flexion more actively than humans during bipedal locomotion.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/chimp_fullbody/model.osim \\
    --scripts 02 \\
    -g models/chimp_fullbody/Geometry
"""

scene = Scene(model_manager, scene_manager, event_bus)

scene.animate_coordinates(
    ("hip_flexion_r", 0, 45),
    ("knee_angle_r",  0, -60),
    ("mtp_angle_r",   0,  30),
    duration=2.0,
)

timeline = scene.build_timeline()

print("Created animation with 3 simultaneous coordinates (chimp)")
print(f"Duration: {timeline.duration:.2f}s")
