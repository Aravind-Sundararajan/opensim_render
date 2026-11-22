"""
V06_body_frames.py

Show body coordinate frames (origin axes).

Demonstrates:
- Body origin frames (X/Y/Z axes at each body's origin)
- Progressive reveal body by body
- Camera orbiting to show 3D frame orientations

Each body has a coordinate frame shown as colored axes:
  Red   = X axis
  Green = Y axis
  Blue  = Z axis

These are hidden by default. This script fades them in.
"""

from osim_render.api.animation.value_types import CameraState

scene = Scene(model_manager, scene_manager, event_bus)

center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom

# Get available body frame names from the scene
render_scene = scene_manager.get_scene()
frame_names = sorted(render_scene.body_origin_actors.keys()) if render_scene and render_scene.body_origin_actors else []

print(f"Found {len(frame_names)} body frames: {frame_names}")

# ============================================
# PHASE 1: Reveal frames from ground up (0-3s)
# ============================================
# Order from foot to head
ordered_bodies = [
    "toes_r", "toes_l",
    "calcn_r", "calcn_l",
    "talus_r", "talus_l",
    "tibia_r", "tibia_l",
    "femur_r", "femur_l",
    "pelvis",
    "torso",
]

t = 0.0
for body in ordered_bodies:
    if body in frame_names:
        scene.fade_in(f"body_frame:{body}", duration=0.4, start_time=t)
        t += 0.2

# ============================================
# PHASE 2: Camera orbit to show 3D frames (3-7s)
# ============================================
# Front view
scene.animate_camera_to(
    target_state=CameraState.front_view(center=center, distance=dist, zoom=zoom),
    duration=0.5, start_time=t
)

# Isometric view
scene.animate_camera_to(
    target_state=CameraState.isometric_view(center=center, distance=dist, zoom=zoom),
    duration=1.5, start_time=t + 0.5
)

# Side view
scene.animate_camera_to(
    target_state=CameraState.side_view(center=center, distance=dist, zoom=zoom),
    duration=1.5, start_time=t + 2.0
)

# Back to front
scene.animate_camera_to(
    target_state=CameraState.front_view(center=center, distance=dist, zoom=zoom),
    duration=1.5, start_time=t + 3.5
)

timeline = scene.build_timeline()

print("Body coordinate frames revealed ground-up, then camera orbits")
print(f"Duration: {timeline.duration:.1f}s")
