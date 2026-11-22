"""
05_walking_motion.py

One walking cycle with phase-offset joint movements.

Chimp fullbody model — bipedal walking pattern with characteristic
chimp kinematics: greater knee flexion and more crouched posture
than modern humans.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/chimp_fullbody/model.osim \\
    --scripts 05 \\
    -g models/chimp_fullbody/Geometry
"""

from osim_render.api.animation.easing import ease_in_out_cubic

scene = Scene(model_manager, scene_manager, event_bus)

# Hip swings forward then back
scene.animate_coordinate("hip_flexion_r",  0,  25, duration=0.5, start_time=0,    easing=ease_in_out_cubic)
scene.animate_coordinate("hip_flexion_r", 25,   0, duration=0.5, start_time=0.5,  easing=ease_in_out_cubic)

# Knee more flexed than human (offset by 0.25s, deeper bend)
scene.animate_coordinate("knee_angle_r",  0, -70, duration=0.5, start_time=0.25, easing=ease_in_out_cubic)
scene.animate_coordinate("knee_angle_r", -70,  0, duration=0.5, start_time=0.75, easing=ease_in_out_cubic)

# Ankle follows
scene.animate_coordinate("ankle_angle_r",  0, 15, duration=0.5, start_time=0.25, easing=ease_in_out_cubic)
scene.animate_coordinate("ankle_angle_r", 15,  0, duration=0.5, start_time=0.75, easing=ease_in_out_cubic)

timeline = scene.build_timeline()

print("Created chimp walking motion (one bipedal cycle)")
print(f"Cycle duration: {timeline.duration:.2f}s")
print("Greater knee flexion than human gait (~70° vs ~60°)")
