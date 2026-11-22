"""
V09_wrapping_geometry.py

Fade in muscle wrapping geometry and show how it constrains muscle paths.

Demonstrates:
- Fading in wrap cylinders around joints
- How wrap objects constrain muscle path routing
- Muscle paths changing as joints flex over wrap objects

Wrap objects are geometric primitives (cylinders, ellipsoids, spheres) that
force muscle paths to route around bony geometry. Without them, muscles would
pass through bones. This script makes them visible so you can see where they are.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model vendor/opensim-gui/opensim-models/Models/Rajagopal/Rajagopal2016.osim \\
    --scripts V09 -g vendor/opensim-gui/opensim-models/Models/Rajagopal/Geometry
"""

from osim_render.api.animation.value_types import CameraState, ColorValue
from osim_render.api.animation.easing import ease_in_out_cubic

scene = Scene(model_manager, scene_manager, event_bus)

center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom

# Discover all wrap actors
render_scene = scene_manager.get_scene()
wrap_names = sorted(render_scene.wrap_actors.keys()) if render_scene and render_scene.wrap_actors else []
print(f"Found {len(wrap_names)} wrap objects: {wrap_names[:8]}...")

# Group wraps by anatomical region (right side shown)
knee_wraps_r   = [w for w in wrap_names if any(k in w for k in ("at_condyles_r", "at_fem_r", "at_shank_r"))]
hip_wraps_r    = [w for w in wrap_names if any(k in w for k in ("at_pelvis_r", "at_brim_r"))]
thigh_wraps_r  = [w for w in wrap_names if "at_femshaft_r" in w]

print(f"  Knee wraps (right): {knee_wraps_r}")
print(f"  Hip wraps (right):  {hip_wraps_r[:4]}")
print(f"  Thigh wraps (right): {thigh_wraps_r}")

t = 0.0

# ============================================
# PHASE 1: Fade in hip wraps (0-1.5s)
# ============================================
for name in hip_wraps_r:
    scene.fade_in(f"wrap:{name}", duration=0.4, start_time=t)
    scene.change_color(f"wrap:{name}", ColorValue(r=0.8, g=0.5, b=0.1), ColorValue(r=0.8, g=0.5, b=0.1), duration=0.1, start_time=t)
    t += 0.2

t = max(t, 1.5)

# ============================================
# PHASE 2: Fade in thigh wraps (1.5-2.5s)
# ============================================
for name in thigh_wraps_r:
    scene.fade_in(f"wrap:{name}", duration=0.4, start_time=t)
    scene.change_color(f"wrap:{name}", ColorValue(r=0.6, g=0.3, b=0.8), ColorValue(r=0.6, g=0.3, b=0.8), duration=0.1, start_time=t)
    t += 0.2

t = max(t, 2.5)

# ============================================
# PHASE 3: Fade in knee wraps (2.5-3.5s)
# ============================================
for name in knee_wraps_r:
    scene.fade_in(f"wrap:{name}", duration=0.4, start_time=t)
    scene.change_color(f"wrap:{name}", ColorValue(r=0.2, g=0.8, b=0.4), ColorValue(r=0.2, g=0.8, b=0.4), duration=0.1, start_time=t)
    t += 0.2

t = max(t, 3.5)

# ============================================
# PHASE 4: Hip flexion — see muscle paths change over wraps (4-7s)
# ============================================
# Flex hip to show iliopsoas routing over pelvic brim wraps
scene.animate_coordinate(
    "hip_flexion_r", 0, 60, duration=2.0, start_time=t, easing=ease_in_out_cubic
)
scene.animate_coordinate(
    "knee_angle_r",  0, -80, duration=2.0, start_time=t, easing=ease_in_out_cubic
)

# Return
scene.animate_coordinate(
    "hip_flexion_r", 60, 0, duration=1.5, start_time=t + 2.0, easing=ease_in_out_cubic
)
scene.animate_coordinate(
    "knee_angle_r",  -80, 0, duration=1.5, start_time=t + 2.0, easing=ease_in_out_cubic
)

# ============================================
# Camera: side view to see lateral muscle routing
# ============================================
scene.animate_camera_to(
    target_state=CameraState.side_view(center=center, distance=dist, zoom=zoom),
    duration=0.5, start_time=0,
)

timeline = scene.build_timeline()

print("\nWrap geometry reveal:")
print("  0-1.5s:  hip/pelvis wraps (orange)")
print("  1.5-2.5s: thigh wraps (purple)")
print("  2.5-3.5s: knee wraps (green)")
print(f"  {t:.1f}s+: hip/knee flex — muscle paths constrained by wraps")
print(f"Duration: {timeline.duration:.1f}s")
