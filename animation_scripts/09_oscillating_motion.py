"""
09_oscillating_motion.py

Oscillating (back and forth) motion.

Ostrich model — pendulum-like leg swing. The ostrich uses passive
pendulum dynamics in the lower limb to reduce metabolic cost.
This script demonstrates oscillation and damped oscillation patterns.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/toys/rankin/Ostrich_Walk_Rigid_Tendon.osim \\
    --scripts 09 \\
    -g models/toys/rankin/geometry
"""

from osim_render.api.animation.easing import ease_in_out_cubic
from osim_render.api.animation.tween import TweenConfig

scene = Scene(model_manager, scene_manager, event_bus)

smooth = TweenConfig(duration=1.0, easing=ease_in_out_cubic)

# Hip oscillation (pendulum swing)
scene.animate_coordinate("R_hip_extension",   0, -30,
                         duration=0.5, start_time=0,   easing=smooth.easing)
scene.animate_coordinate("R_hip_extension", -30,  30,
                         duration=1.0, start_time=0.5, easing=smooth.easing)
scene.animate_coordinate("R_hip_extension",  30, -30,
                         duration=1.0, start_time=1.5, easing=smooth.easing)
scene.animate_coordinate("R_hip_extension", -30,   0,
                         duration=0.5, start_time=2.5, easing=smooth.easing)

# Knee (ankle): damped oscillation — amplitude decreasing each cycle
scene.animate_coordinate("R_knee_angle",  0,  50,
                         duration=0.5, start_time=0,   easing=smooth.easing)
scene.animate_coordinate("R_knee_angle", 50, -15,
                         duration=0.5, start_time=0.5, easing=smooth.easing)
scene.animate_coordinate("R_knee_angle", -15, 25,
                         duration=0.5, start_time=1.0, easing=smooth.easing)
scene.animate_coordinate("R_knee_angle",  25, -5,
                         duration=0.5, start_time=1.5, easing=smooth.easing)
scene.animate_coordinate("R_knee_angle",  -5,  0,
                         duration=0.5, start_time=2.0, easing=smooth.easing)

timeline = scene.build_timeline()

print("Created ostrich pendulum oscillation")
print("Hip: 3 full swings")
print("Knee: Damped oscillation (decreasing amplitude)")
print(f"Duration: {timeline.duration:.2f}s")
