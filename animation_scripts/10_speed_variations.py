"""
10_speed_variations.py

The same joint movement at fast, medium, and slow speeds.

Chimp fullbody model — shows how duration controls perceived motion speed.
Short duration = quick snap, long duration = deliberate controlled movement.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/chimp_fullbody/model.osim \\
    --scripts 10 \\
    -g models/chimp_fullbody/Geometry
"""

from osim_render.api.animation.easing import ease_in_out_cubic
from osim_render.api.animation.tween import TweenConfig

scene = Scene(model_manager, scene_manager, event_bus)

smooth = TweenConfig(duration=1.0, easing=ease_in_out_cubic)

# Fast: quick hip snap (0.2s)
scene.animate_coordinate("hip_flexion_r", 0, 45, duration=0.2, start_time=0,   easing=smooth.easing)

# Medium: normal knee (1.0s)
scene.animate_coordinate("knee_angle_r",  0, -60, duration=1.0, start_time=0.2, easing=smooth.easing)

# Slow: deliberate ankle (2.0s)
scene.animate_coordinate("ankle_angle_r", 0, 20, duration=2.0, start_time=1.2, easing=smooth.easing)

# Return: all at different speeds
scene.animate_coordinate("hip_flexion_r", 45,  0, duration=0.2, start_time=3.2, easing=smooth.easing)
scene.animate_coordinate("knee_angle_r",  -60, 0, duration=1.0, start_time=2.4, easing=smooth.easing)
scene.animate_coordinate("ankle_angle_r",  20, 0, duration=2.0, start_time=3.2, easing=smooth.easing)

timeline = scene.build_timeline()

print("Created speed variation demo (Chimp)")
print("Hip: Fast (0.2s), Knee: Medium (1.0s), Ankle: Slow (2.0s)")
print(f"Total duration: {timeline.duration:.2f}s")
