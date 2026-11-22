"""
V05_muscles.py

Progressive muscle reveal with motion.

Demonstrates:
- Fading in muscle groups one at a time
- Muscles visible during joint motion
- Highlighting individual muscles

Muscles start hidden by default. This script reveals them progressively
by muscle group, then animates a squat so you can see the muscles move.
"""

from osim_render.api.animation.value_types import CameraState
from osim_render.api.animation.easing import ease_in_out_cubic

scene = Scene(model_manager, scene_manager, event_bus)

center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom

# ============================================
# PHASE 1: Reveal knee extensors (0-1s)
# ============================================
# Quadriceps: rectus femoris, vasti
scene.fade_in("rect_fem_r", duration=0.5, start_time=0)
scene.fade_in("vas_lat_r",  duration=0.5, start_time=0.1)
scene.fade_in("vas_med_r",  duration=0.5, start_time=0.2)
scene.fade_in("vas_int_r",  duration=0.5, start_time=0.3)

# ============================================
# PHASE 2: Reveal hamstrings (1-2s)
# ============================================
scene.fade_in("bifemlh_r", duration=0.5, start_time=1.0)
scene.fade_in("bifemsh_r", duration=0.5, start_time=1.1)
scene.fade_in("semimem_r", duration=0.5, start_time=1.2)
scene.fade_in("semiten_r", duration=0.5, start_time=1.3)

# ============================================
# PHASE 3: Reveal calf muscles (2-3s)
# ============================================
scene.fade_in("lat_gas_r", duration=0.5, start_time=2.0)
scene.fade_in("med_gas_r", duration=0.5, start_time=2.1)
scene.fade_in("soleus_r",  duration=0.5, start_time=2.2)

# ============================================
# PHASE 4: Reveal hip muscles (3-4s)
# ============================================
scene.fade_in("glut_max1_r", duration=0.5, start_time=3.0)
scene.fade_in("glut_max2_r", duration=0.5, start_time=3.1)
scene.fade_in("glut_max3_r", duration=0.5, start_time=3.2)
scene.fade_in("glut_med1_r", duration=0.5, start_time=3.3)
scene.fade_in("iliacus_r",   duration=0.5, start_time=3.4)
scene.fade_in("psoas_r",     duration=0.5, start_time=3.5)

# ============================================
# PHASE 5: Squat motion with muscles visible (4-6s)
# ============================================
# Descent (4-5s)
scene.animate_coordinate("hip_flexion_r", 0, 30, duration=1.0, start_time=4.0, easing=ease_in_out_cubic)
scene.animate_coordinate("knee_angle_r", 0, -70, duration=1.0, start_time=4.0, easing=ease_in_out_cubic)
scene.animate_coordinate("ankle_angle_r", 0, 15, duration=1.0, start_time=4.0, easing=ease_in_out_cubic)

# Ascent (5-6s)
scene.animate_coordinate("hip_flexion_r", 30, 0, duration=1.0, start_time=5.0, easing=ease_in_out_cubic)
scene.animate_coordinate("knee_angle_r", -70, 0, duration=1.0, start_time=5.0, easing=ease_in_out_cubic)
scene.animate_coordinate("ankle_angle_r", 15, 0, duration=1.0, start_time=5.0, easing=ease_in_out_cubic)

# Camera stays at side view to show muscles clearly
scene.animate_camera_to(
    target_state=CameraState.side_view(center=center, distance=dist, zoom=zoom),
    duration=0.5, start_time=0
)

timeline = scene.build_timeline()

print("Muscle reveal: quadriceps → hamstrings → calves → hip muscles")
print("Then squat motion with muscles visible")
print(f"Duration: {timeline.duration:.1f}s")
