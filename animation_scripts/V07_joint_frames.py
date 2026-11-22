"""
V07_joint_frames.py

Show joint parent and child frames.

Demonstrates:
- Joint coordinate frames (parent and child sides)
- How frames separate as a joint moves
- Frame alignment at neutral pose vs. flexed pose

Joint frames show where each joint is and its orientation.
Parent frame = how the proximal body sees the joint.
Child frame  = how the distal body sees the joint.
At neutral pose they overlap. As the joint moves they diverge.
"""

from osim_render.api.animation.value_types import CameraState
from osim_render.api.animation.easing import ease_in_out_cubic

scene = Scene(model_manager, scene_manager, event_bus)

center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom

render_scene = scene_manager.get_scene()
parent_names = sorted(render_scene.joint_parent_actors.keys()) if render_scene and render_scene.joint_parent_actors else []
child_names  = sorted(render_scene.joint_child_actors.keys())  if render_scene and render_scene.joint_child_actors  else []

print(f"Found {len(parent_names)} joint frames: {parent_names}")

# ============================================
# PHASE 1: Reveal hip, knee, ankle frames (0-2s)
# ============================================
joints_of_interest = ["hip_r", "knee_r", "ankle_r"]

t = 0.0
for joint in joints_of_interest:
    if joint in parent_names:
        scene.fade_in(f"joint_parent:{joint}", duration=0.4, start_time=t)
        t += 0.3

# Reveal child frames at same time
t = 0.0
for joint in joints_of_interest:
    if joint in child_names:
        scene.fade_in(f"joint_child:{joint}", duration=0.4, start_time=t)
        t += 0.3

# ============================================
# PHASE 2: Hip flexion — watch frames diverge (2-4s)
# ============================================
scene.animate_coordinate(
    "hip_flexion_r", 0, 60, duration=2.0, start_time=2.0, easing=ease_in_out_cubic
)

# ============================================
# PHASE 3: Knee flexion — watch frames diverge (4-6s)
# ============================================
scene.animate_coordinate(
    "knee_angle_r", 0, -90, duration=2.0, start_time=4.0, easing=ease_in_out_cubic
)

# ============================================
# PHASE 4: Return to neutral (6-8s)
# ============================================
scene.animate_coordinate(
    "hip_flexion_r", 60, 0, duration=1.0, start_time=6.0, easing=ease_in_out_cubic
)
scene.animate_coordinate(
    "knee_angle_r", -90, 0, duration=1.0, start_time=6.0, easing=ease_in_out_cubic
)

# Camera stays at side view to show frame separation clearly
scene.animate_camera_to(
    target_state=CameraState.side_view(center=center, distance=dist, zoom=zoom),
    duration=0.5, start_time=0
)

timeline = scene.build_timeline()

print("Joint frames revealed, then flexion shows parent/child frame separation")
print(f"Duration: {timeline.duration:.1f}s")
