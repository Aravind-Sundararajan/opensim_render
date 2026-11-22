"""
V10_rajagopal_muscles.py

Progressive muscle reveal on the Rajagopal full-body model.

Demonstrates:
- Fading in Rajagopal muscle groups in anatomical order
- Color-coding muscle groups (hip extensors, hip flexors, hamstrings,
  quadriceps, gastroc, soleus)
- Hip and knee flexion to see muscles in action

Rajagopal 2016 has ~80 muscles including upper extremity.
This script reveals the right leg in groups then animates a
deep squat.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model vendor/opensim-gui/opensim-models/Models/Rajagopal/Rajagopal2016.osim \\
    --scripts V10 -g vendor/opensim-gui/opensim-models/Models/Rajagopal/Geometry
"""

from osim_render.api.animation.value_types import CameraState, ColorValue
from osim_render.api.animation.easing import ease_in_out_cubic

scene = Scene(model_manager, scene_manager, event_bus)

center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom

render_scene = scene_manager.get_scene()
muscle_names = set(render_scene.muscle_actors.keys()) if render_scene and render_scene.muscle_actors else set()
print(f"Found {len(muscle_names)} muscles total")

# ============================================
# PHASE 1: Gluteals — hip extensors (0-1s)
# ============================================
glutes = ["glmax1_r", "glmax2_r", "glmax3_r", "glmed1_r", "glmed2_r", "glmed3_r"]
for i, m in enumerate(m for m in glutes if m in muscle_names):
    scene.fade_in(m, duration=0.4, start_time=i * 0.15)
    scene.change_color(m, ColorValue(r=0.9, g=0.3, b=0.1), ColorValue(r=0.9, g=0.3, b=0.1), duration=0.1, start_time=i * 0.15)

# ============================================
# PHASE 2: Hip flexors (1-1.8s)
# ============================================
hip_flexors = ["iliacus_r", "psoas_r", "recfem_r", "tfl_r", "sart_r"]
for i, m in enumerate(m for m in hip_flexors if m in muscle_names):
    scene.fade_in(m, duration=0.4, start_time=1.0 + i * 0.15)
    scene.change_color(m, ColorValue(r=0.1, g=0.5, b=0.9), ColorValue(r=0.1, g=0.5, b=0.9), duration=0.1, start_time=1.0 + i * 0.15)

# ============================================
# PHASE 3: Hamstrings (2-2.8s)
# ============================================
hamstrings = ["bflh_r", "bfsh_r", "semimem_r", "semiten_r"]
for i, m in enumerate(m for m in hamstrings if m in muscle_names):
    scene.fade_in(m, duration=0.4, start_time=2.0 + i * 0.15)
    scene.change_color(m, ColorValue(r=0.9, g=0.7, b=0.1), ColorValue(r=0.9, g=0.7, b=0.1), duration=0.1, start_time=2.0 + i * 0.15)

# ============================================
# PHASE 4: Quadriceps (3-3.6s)
# ============================================
quads = ["vasmed_r", "vasint_r", "vaslat_r"]
for i, m in enumerate(m for m in quads if m in muscle_names):
    scene.fade_in(m, duration=0.4, start_time=3.0 + i * 0.15)
    scene.change_color(m, ColorValue(r=0.2, g=0.9, b=0.4), ColorValue(r=0.2, g=0.9, b=0.4), duration=0.1, start_time=3.0 + i * 0.15)

# ============================================
# PHASE 5: Plantarflexors (4-4.8s)
# ============================================
calves = ["gaslat_r", "gasmed_r", "soleus_r", "tibant_r"]
for i, m in enumerate(m for m in calves if m in muscle_names):
    scene.fade_in(m, duration=0.4, start_time=4.0 + i * 0.15)
    scene.change_color(m, ColorValue(r=0.8, g=0.2, b=0.8), ColorValue(r=0.8, g=0.2, b=0.8), duration=0.1, start_time=4.0 + i * 0.15)

# ============================================
# PHASE 6: Deep squat with all muscles visible (5.5-8.5s)
# ============================================
# Descent (5.5-6.5s)
scene.animate_coordinate("hip_flexion_r", 0, 40, duration=1.0, start_time=5.5, easing=ease_in_out_cubic)
scene.animate_coordinate("knee_angle_r",  0, -90, duration=1.0, start_time=5.5, easing=ease_in_out_cubic)
scene.animate_coordinate("ankle_angle_r", 0,  20, duration=1.0, start_time=5.5, easing=ease_in_out_cubic)

# Hold (6.5-7s)

# Ascent (7-8s)
scene.animate_coordinate("hip_flexion_r", 40, 0, duration=1.0, start_time=7.0, easing=ease_in_out_cubic)
scene.animate_coordinate("knee_angle_r", -90, 0, duration=1.0, start_time=7.0, easing=ease_in_out_cubic)
scene.animate_coordinate("ankle_angle_r",  20, 0, duration=1.0, start_time=7.0, easing=ease_in_out_cubic)

# ============================================
# Camera: side view to see muscle activity
# ============================================
scene.animate_camera_to(
    target_state=CameraState.side_view(center=center, distance=dist, zoom=zoom),
    duration=0.5, start_time=0,
)

timeline = scene.build_timeline()

print("Rajagopal muscle reveal (right leg):")
print("  0-1s:   gluteals (orange-red)")
print("  1-2s:   hip flexors (blue)")
print("  2-3s:   hamstrings (gold)")
print("  3-4s:   quadriceps (green)")
print("  4-5s:   plantarflexors (purple)")
print("  5.5s+:  deep squat")
print(f"Duration: {timeline.duration:.1f}s")
