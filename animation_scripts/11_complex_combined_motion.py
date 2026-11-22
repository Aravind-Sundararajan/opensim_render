"""
11_complex_combined_motion.py

Comprehensive example combining multiple techniques.

Rajagopal scaled model — a full squat with lumbar involvement,
bilateral hip/knee/ankle coordination, and cinematic camera choreography.

Demonstrates:
- Simultaneous multi-joint animation
- Sequential phases (descent → hold → ascent)
- Lumbar spine involvement
- Easing for biomechanically realistic motion
- Camera choreography synchronized with movement phases

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model resources/Code/CPP/Moco/example3DWalking/subject_walk_scaled.osim \\
    --scripts 11 \\
    -g resources/Code/CPP/Moco/example3DWalking \\
    -g vendor/opensim-gui/opensim-models/Geometry
"""

from osim_render.api.animation.value_types import CameraState
from osim_render.api.animation.easing import ease_in_out_cubic, ease_out_cubic
from osim_render.api.animation.tween import TweenConfig

scene = Scene(model_manager, scene_manager, event_bus)

smooth     = TweenConfig(duration=1.0, easing=ease_in_out_cubic)
smooth_out = TweenConfig(duration=1.0, easing=ease_out_cubic)
center = scene.model_center
dist   = scene.camera_distance
zoom   = scene.camera.zoom

# ============================================
# PHASE 1: DESCENT (0 to 1s)
# ============================================
scene.animate_coordinate("lumbar_extension",  0, -10, duration=1.0, start_time=0, easing=smooth.easing)
scene.animate_coordinate("hip_flexion_r",      0,  35, duration=1.0, start_time=0, easing=smooth.easing)
scene.animate_coordinate("knee_angle_r",        0, -90, duration=1.0, start_time=0, easing=smooth.easing)
scene.animate_coordinate("ankle_angle_r",       0,  20, duration=1.0, start_time=0, easing=smooth.easing)

# ============================================
# PHASE 2: HOLD at bottom (1 to 2s) — no new animations needed
# ============================================

# ============================================
# PHASE 3: ASCENT (2 to 3s)
# ============================================
scene.animate_coordinate("lumbar_extension", -10,  0, duration=1.0, start_time=2, easing=smooth_out.easing)
scene.animate_coordinate("hip_flexion_r",     35,  0, duration=1.0, start_time=2, easing=smooth_out.easing)
scene.animate_coordinate("knee_angle_r",      -90, 0, duration=1.0, start_time=2, easing=smooth_out.easing)
scene.animate_coordinate("ankle_angle_r",      20, 0, duration=1.0, start_time=2, easing=smooth_out.easing)

# ============================================
# CAMERA: side → isometric → side
# ============================================
scene.animate_camera_to(
    target_state=CameraState.side_view(center=center, distance=dist, zoom=zoom),
    duration=0.5, start_time=0,
)
scene.animate_camera_to(
    target_state=CameraState.isometric_view(center=center, distance=dist, zoom=zoom),
    duration=1.0, start_time=1.0,
)
scene.animate_camera_to(
    target_state=CameraState.side_view(center=center, distance=dist, zoom=zoom),
    duration=1.0, start_time=2.0,
)

timeline = scene.build_timeline()

print("Created complex squat motion (Rajagopal)")
print("")
print("Phase 1 (0-1s): DESCENT — lumbar, hip, knee, ankle flex together")
print("Phase 2 (1-2s): HOLD    — bottom of squat")
print("Phase 3 (2-3s): ASCENT  — smooth extension back to neutral")
print("")
print("Camera: Side → Isometric → Side")
print(f"Total duration: {timeline.duration:.2f}s")
