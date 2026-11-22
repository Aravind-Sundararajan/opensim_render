"""
04_easing_smooth_motion.py

Use easing functions for natural, smooth motion.

Rajagopal scaled walking model — three joints with different easing styles.
Linear motion looks robotic. Easing provides biological-looking acceleration
and deceleration.

Available easing functions:
  ease_linear, ease_in/out_quad, ease_in/out_cubic, ease_smooth_step, ...

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model resources/Code/CPP/Moco/example3DWalking/subject_walk_scaled.osim \\
    --scripts 04 \\
    -g resources/Code/CPP/Moco/example3DWalking \\
    -g vendor/opensim-gui/opensim-models/Geometry
"""

from osim_render.api.animation.easing import ease_in_out_cubic, ease_smooth_step
from osim_render.api.animation.tween import TweenConfig

scene = Scene(model_manager, scene_manager, event_bus)

# Linear motion (abrupt start/stop)
scene.animate_coordinate("hip_flexion_r", 0, 45, duration=1.0, start_time=0)

# Smooth cubic easing (accelerates then decelerates)
config_smooth = TweenConfig(duration=1.0, easing=ease_in_out_cubic)
scene.animate_coordinate(
    "knee_angle_r", 0, -60,
    duration=config_smooth.duration,
    easing=config_smooth.easing,
    start_time=1.0,
)

# Ultra-smooth step easing
config_ultra = TweenConfig(duration=1.0, easing=ease_smooth_step)
scene.animate_coordinate(
    "ankle_angle_r", 0, 20,
    duration=config_ultra.duration,
    easing=config_ultra.easing,
    start_time=2.0,
)

timeline = scene.build_timeline()

print("Created animation with different easing functions (Rajagopal)")
print("Hip: linear, Knee: ease_in_out_cubic, Ankle: ease_smooth_step")
print(f"Duration: {timeline.duration:.2f}s")
