"""
V08_contact_geometry.py

Fade in contact geometry and highlight contact regions.

Demonstrates:
- Fading in contact spheres and half-space geometry
- Changing colors to distinguish contact regions (heel vs ball vs toe)
- Animating a landing/squat to show contacts near the feet

Contact geometry shows where the model can interact with its environment.
ToyDropLanding has heel, metatarsal, and toe contact spheres plus
a ground half-space.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/toys/ToyDropLanding/ToyLandingModel.osim \\
    --scripts V08 -g models/toys/ToyDropLanding/Geometry
"""

from osim_render.api.animation.value_types import CameraState, ColorValue
from osim_render.api.animation.easing import ease_in_out_cubic

scene = Scene(model_manager, scene_manager, event_bus)

center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom

# Discover contact actors from the scene
render_scene = scene_manager.get_scene()
contact_names = sorted(render_scene.contact_actors.keys()) if render_scene and render_scene.contact_actors else []
print(f"Found {len(contact_names)} contact objects: {contact_names}")

# ============================================
# PHASE 1: Fade in ground surface (0-0.5s)
# ============================================
if "platform_surface" in contact_names:
    scene.fade_in("contact:platform_surface", duration=0.5, start_time=0)
    scene.change_color("contact:platform_surface", ColorValue(r=0.6, g=0.6, b=0.6), ColorValue(r=0.6, g=0.6, b=0.6), duration=0.1, start_time=0)

# ============================================
# PHASE 2: Fade in heel contacts (0.5-1s)
# ============================================
for name in ("heel_r", "heel_l"):
    if name in contact_names:
        scene.fade_in(f"contact:{name}", duration=0.4, start_time=0.5)
        # Blue = heel
        scene.change_color(f"contact:{name}", ColorValue(r=0.2, g=0.4, b=1.0), ColorValue(r=0.2, g=0.4, b=1.0), duration=0.1, start_time=0.5)

# ============================================
# PHASE 3: Fade in metatarsal ball contacts (1-1.5s)
# ============================================
for name in ("ball_big_toe_r", "ball_big_toe_l"):
    if name in contact_names:
        scene.fade_in(f"contact:{name}", duration=0.4, start_time=1.0)
        # Green = ball of foot
        scene.change_color(f"contact:{name}", ColorValue(r=0.2, g=1.0, b=0.3), ColorValue(r=0.2, g=1.0, b=0.3), duration=0.1, start_time=1.0)

# ============================================
# PHASE 4: Fade in toe contacts (1.5-2s)
# ============================================
for name in ("small_toe_r", "small_toe_l"):
    if name in contact_names:
        scene.fade_in(f"contact:{name}", duration=0.4, start_time=1.5)
        # Yellow = toes
        scene.change_color(f"contact:{name}", ColorValue(r=1.0, g=0.9, b=0.1), ColorValue(r=1.0, g=0.9, b=0.1), duration=0.1, start_time=1.5)

# ============================================
# PHASE 5: Squat — contacts track with the feet (2.5-5s)
# ============================================
# Descent (2.5-3.5s)
scene.animate_coordinate("hip_flexion_r",  0, 35, duration=1.0, start_time=2.5, easing=ease_in_out_cubic)
scene.animate_coordinate("hip_flexion_l",  0, 35, duration=1.0, start_time=2.5, easing=ease_in_out_cubic)
scene.animate_coordinate("knee_angle_r",   0, -80, duration=1.0, start_time=2.5, easing=ease_in_out_cubic)
scene.animate_coordinate("knee_angle_l",   0, -80, duration=1.0, start_time=2.5, easing=ease_in_out_cubic)
scene.animate_coordinate("ankle_angle_r",  0,  20, duration=1.0, start_time=2.5, easing=ease_in_out_cubic)
scene.animate_coordinate("ankle_angle_l",  0,  20, duration=1.0, start_time=2.5, easing=ease_in_out_cubic)

# Ascent (3.5-4.5s)
scene.animate_coordinate("hip_flexion_r",  35, 0, duration=1.0, start_time=3.5, easing=ease_in_out_cubic)
scene.animate_coordinate("hip_flexion_l",  35, 0, duration=1.0, start_time=3.5, easing=ease_in_out_cubic)
scene.animate_coordinate("knee_angle_r",  -80, 0, duration=1.0, start_time=3.5, easing=ease_in_out_cubic)
scene.animate_coordinate("knee_angle_l",  -80, 0, duration=1.0, start_time=3.5, easing=ease_in_out_cubic)
scene.animate_coordinate("ankle_angle_r",  20, 0, duration=1.0, start_time=3.5, easing=ease_in_out_cubic)
scene.animate_coordinate("ankle_angle_l",  20, 0, duration=1.0, start_time=3.5, easing=ease_in_out_cubic)

# ============================================
# Camera: front view for symmetry
# ============================================
scene.animate_camera_to(
    target_state=CameraState.front_view(center=center, distance=dist, zoom=zoom),
    duration=0.5, start_time=0,
)

timeline = scene.build_timeline()

print("Contact geometry reveal:")
print("  0.0s: ground platform (grey)")
print("  0.5s: heel contacts (blue)")
print("  1.0s: metatarsal contacts (green)")
print("  1.5s: toe contacts (yellow)")
print("  2.5s: bilateral squat — contacts move with feet")
print(f"Duration: {timeline.duration:.1f}s")
