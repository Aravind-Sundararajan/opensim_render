"""
07_leg_swing_motion.py

Swing phase of bipedal gait — proximal-to-distal coordination.

Australopithecus afarensis — the swing phase involves lumbar lateral
bending to clear the foot, a deep hip swing, then rapid knee extension
before heel contact. A. afarensis likely had a somewhat more ape-like
gait with greater lumbar contribution than modern humans.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/afarensis/model.osim \\
    --scripts 07 \\
    -g models/afarensis/Geometry
"""

from osim_render.api.animation.easing import ease_in_out_cubic, ease_out_cubic
from osim_render.api.animation.tween import TweenConfig

scene = Scene(model_manager, scene_manager, event_bus)

smooth     = TweenConfig(duration=1.0, easing=ease_in_out_cubic)
smooth_out = TweenConfig(duration=1.0, easing=ease_out_cubic)

# Phase 1: Lumbar laterally flexes to unload swing limb (0-0.3s)
scene.animate_coordinate("lumbar_bending", 0, 8, duration=0.3, start_time=0, easing=smooth.easing)

# Phase 2: Hip swings forward (0-0.5s)
scene.animate_coordinate("hip_flexion_r", 0, 35, duration=0.5, start_time=0, easing=smooth.easing)

# Phase 3: Knee flexes to clear ground (0.1-0.6s)
scene.animate_coordinate("knee_angle_r", 0, -55, duration=0.5, start_time=0.1, easing=smooth.easing)

# Phase 4: Ankle dorsiflexes for heel strike preparation (0.2-0.6s)
scene.animate_coordinate("ankle_angle_r", 0, 10, duration=0.4, start_time=0.2, easing=smooth.easing)

# Phase 5: Leg extends toward heel contact
scene.animate_coordinate("knee_angle_r",  -55, 0, duration=0.5, start_time=0.65, easing=smooth_out.easing)
scene.animate_coordinate("ankle_angle_r",  10, 0, duration=0.4, start_time=0.7,  easing=smooth_out.easing)
scene.animate_coordinate("hip_flexion_r",  35, 0, duration=0.5, start_time=0.75, easing=smooth_out.easing)
scene.animate_coordinate("lumbar_bending",  8, 0, duration=0.3, start_time=0.9,  easing=smooth_out.easing)

timeline = scene.build_timeline()

print("Created Afarensis swing phase")
print(f"Total duration: {timeline.duration:.2f}s")
print("Phase 1 (0-0.3s):    Lumbar lateral flexion (limb unloading)")
print("Phase 2 (0-0.5s):    Hip swings forward")
print("Phase 3 (0.1-0.6s):  Knee flexes to clear ground")
print("Phase 4 (0.65s+):    Leg extends toward heel contact")
