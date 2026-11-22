"""
06_running_motion.py

Running motion — faster and with larger joint excursions than walking.

Rajagopal scaled model — human running kinematics with lumbar extension
counter-rotation and larger hip/knee/ankle angles.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model resources/Code/CPP/Moco/example3DWalking/subject_walk_scaled.osim \\
    --scripts 06 \\
    -g resources/Code/CPP/Moco/example3DWalking \\
    -g vendor/opensim-gui/opensim-models/Geometry
"""

from osim_render.api.animation.easing import ease_in_out_cubic

scene = Scene(model_manager, scene_manager, event_bus)

# Lumbar extends in counter-rotation during running
scene.animate_coordinate("lumbar_extension",  0,  10, duration=0.3, start_time=0,    easing=ease_in_out_cubic)
scene.animate_coordinate("lumbar_extension", 10,   0, duration=0.3, start_time=0.35, easing=ease_in_out_cubic)

# Hip: larger range than walking (0-45°)
scene.animate_coordinate("hip_flexion_r",  0, 45, duration=0.35, start_time=0,    easing=ease_in_out_cubic)
scene.animate_coordinate("hip_flexion_r", 45,  0, duration=0.35, start_time=0.35, easing=ease_in_out_cubic)

# Knee: deep flexion in swing (0 to -90°)
scene.animate_coordinate("knee_angle_r",  0, -90, duration=0.35, start_time=0.15, easing=ease_in_out_cubic)
scene.animate_coordinate("knee_angle_r", -90,  0, duration=0.35, start_time=0.5,  easing=ease_in_out_cubic)

# Ankle: plantarflexion push-off then dorsiflexion
scene.animate_coordinate("ankle_angle_r",  0,  20, duration=0.35, start_time=0.15, easing=ease_in_out_cubic)
scene.animate_coordinate("ankle_angle_r", 20, -10, duration=0.35, start_time=0.5,  easing=ease_in_out_cubic)

timeline = scene.build_timeline()

print("Created running motion (Rajagopal)")
print(f"Cycle duration: {timeline.duration:.2f}s")
print("Hip: 0-45°, Knee: 0-90°, Ankle: -10 to 20°, Lumbar: 0-10°")
