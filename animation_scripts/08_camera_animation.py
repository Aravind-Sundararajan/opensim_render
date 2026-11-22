"""
08_camera_animation.py

Animate the camera while the model moves.

Ostrich model — avian bipedalism has a horizontal trunk and a "knee"
that is actually the ankle (the true knee is hidden inside the body).
Camera orbits to reveal the unique limb structure from multiple angles.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model models/toys/rankin/Ostrich_Walk_Rigid_Tendon.osim \\
    --scripts 08 \\
    -g models/toys/rankin/geometry
"""

from osim_render.api.animation.value_types import CameraState
from osim_render.api.animation.easing import ease_in_out_cubic
from osim_render.api.animation.tween import TweenConfig

scene = Scene(model_manager, scene_manager, event_bus)

smooth = TweenConfig(duration=1.0, easing=ease_in_out_cubic)
center = scene.model_center
dist = scene.camera_distance
zoom = scene.camera.zoom

# Ostrich hip swings forward and back
scene.animate_coordinate("R_hip_extension",  0, -35,
                         duration=1.0, start_time=0,   easing=smooth.easing)
scene.animate_coordinate("R_hip_extension", -35,  0,
                         duration=1.0, start_time=1.0, easing=smooth.easing)

# "Knee" (ankle joint) flexes
scene.animate_coordinate("R_knee_angle",  0, 60,
                         duration=1.0, start_time=0,   easing=smooth.easing)
scene.animate_coordinate("R_knee_angle", 60,  0,
                         duration=1.0, start_time=1.0, easing=smooth.easing)

# Camera: front -> side -> isometric to reveal limb structure
scene.animate_camera_to(
    target_state=CameraState.front_view(
        center=center, distance=dist, zoom=zoom),
    duration=0.5, start_time=0,
)
scene.animate_camera_to(
    target_state=CameraState.side_view(
        center=center, distance=dist, zoom=zoom),
    duration=1.0, start_time=0.5,
)
scene.animate_camera_to(
    target_state=CameraState.isometric_view(
        center=center, distance=dist, zoom=zoom),
    duration=0.5, start_time=1.5,
)

timeline = scene.build_timeline()

print("Created ostrich limb animation with camera orbit")
print(f"Duration: {timeline.duration:.2f}s")
print("Camera: Front -> Side -> Isometric")
print("Note: the visible 'knee' is actually the ankle — the true knee is inside the body feathers")
