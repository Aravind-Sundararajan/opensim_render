"""
V11_rajagopal_motion.py

Rajagopal model walking with muscles and wrap geometry visible.

This is the full showcase: real walking motion data, muscles color-coded
by group, and wrap cylinders highlighted to show how muscle paths route
around bony geometry during movement.

Uses the Moco example3DWalking subject (a scaled Rajagopal model)
with its coordinate solution.

USAGE:
  poetry run python scripts/render_animation_scripts.py \\
    --model resources/Code/CPP/Moco/example3DWalking/subject_walk_scaled.osim \\
    --scripts V11 \\
    -g resources/Code/CPP/Moco/example3DWalking \\
    -g vendor/opensim-gui/opensim-models/Geometry
"""

from osim_render.api.loaders.motion_loader import MotionData, MotionFrame
from osim_render.api.animation.timeline import Timeline
from osim_render.api.animation.value_types import CameraState, ColorValue
from pathlib import Path

motion_file = Path("resources/Code/CPP/Moco/example3DWalking/coordinates.sto")

if not motion_file.exists():
    print(f"ERROR: Motion file not found: {motion_file}")
    raise FileNotFoundError(f"Motion file not found: {motion_file}")

# Load motion and loop 3 cycles
original = load_motion_from_file(str(motion_file))
cycle_duration = original.end_time - original.start_time
num_cycles = 3

looped_frames = []
for cycle in range(num_cycles):
    offset = cycle * cycle_duration
    for frame in original.frames:
        looped_frames.append(MotionFrame(
            time=frame.time - original.start_time + offset,
            coordinate_values=frame.coordinate_values.copy(),
        ))

motion = MotionData(
    filepath=motion_file,
    frames=tuple(looped_frames),
    num_frames=len(looped_frames),
    start_time=0.0,
    end_time=num_cycles * cycle_duration,
)

total_duration = motion.end_time

print(f"Loaded motion: {motion_file.name}")
print(f"  {num_cycles} cycles x {cycle_duration:.2f}s = {total_duration:.2f}s total")

# Discover available visual layers
scene = Scene(model_manager, scene_manager, event_bus)
scene.track_body("pelvis")  # camera follows pelvis so model stays in frame
render_scene = scene_manager.get_scene()

muscle_names = set(render_scene.muscle_actors.keys()) if render_scene and render_scene.muscle_actors else set()
wrap_names   = set(render_scene.wrap_actors.keys())   if render_scene and render_scene.wrap_actors   else set()

print(f"  {len(muscle_names)} muscles, {len(wrap_names)} wrap objects")

center = scene.model_center
dist   = scene.camera_distance
zoom   = scene.camera.zoom

# ============================================
# Muscle groups with color coding
# (fade in before motion starts — start_time < 0 clamps to 0)
# ============================================
muscle_groups = [
    (["glmax1_r", "glmax2_r", "glmax3_r", "glmed1_r", "glmed2_r", "glmed3_r",
      "glmax1_l", "glmax2_l", "glmax3_l", "glmed1_l", "glmed2_l", "glmed3_l"],
     ColorValue(r=0.9, g=0.3, b=0.1)),   # gluteals: orange-red

    (["bflh_r", "bfsh_r", "semimem_r", "semiten_r",
      "bflh_l", "bfsh_l", "semimem_l", "semiten_l"],
     ColorValue(r=0.9, g=0.7, b=0.1)),   # hamstrings: gold

    (["recfem_r", "vasmed_r", "vasint_r", "vaslat_r",
      "recfem_l", "vasmed_l", "vasint_l", "vaslat_l"],
     ColorValue(r=0.2, g=0.9, b=0.4)),   # quadriceps: green

    (["gaslat_r", "gasmed_r", "soleus_r", "tibant_r",
      "gaslat_l", "gasmed_l", "soleus_l", "tibant_l"],
     ColorValue(r=0.8, g=0.2, b=0.8)),   # plantarflexors: purple

    (["iliacus_r", "psoas_r", "iliacus_l", "psoas_l"],
     ColorValue(r=0.1, g=0.5, b=0.9)),   # hip flexors: blue
]

t_reveal = 0.0
for muscles, color in muscle_groups:
    for i, m in enumerate(m for m in muscles if m in muscle_names):
        scene.fade_in(m, duration=0.3, start_time=t_reveal + i * 0.05)
        scene.change_color(m, color, color, duration=0.05, start_time=t_reveal + i * 0.05)
    t_reveal += 0.4

# ============================================
# Highlight knee and hip wraps in teal
# ============================================
knee_wraps = [w for w in wrap_names if any(k in w for k in ("at_condyles", "at_fem_", "at_shank"))]
for i, w in enumerate(sorted(knee_wraps)):
    scene.fade_in(f"wrap:{w}", duration=0.3, start_time=t_reveal + i * 0.1)
    scene.change_color(f"wrap:{w}", ColorValue(r=0.0, g=0.8, b=0.8), ColorValue(r=0.0, g=0.8, b=0.8), duration=0.05, start_time=t_reveal + i * 0.1)

# ============================================
# Camera: frontal → sagittal → orthographic
# timed to the walking cycles (start_time is relative to motion start)
# ============================================
cx, cy, cz = center

# Start frontal
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx, cy, cz + dist), focal_point=center, view_up=(0, 1, 0),
        zoom=zoom, parallel_projection=False,
    ),
    duration=0.5, start_time=0,
)

# Rotate to sagittal at cycle 1 boundary
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx + dist, cy, cz), focal_point=center, view_up=(0, 1, 0),
        zoom=zoom, parallel_projection=False,
    ),
    duration=cycle_duration * 0.5,
    start_time=cycle_duration,
)

# Switch to orthographic at cycle 2 boundary
scene.animate_camera_to(
    target_state=CameraState(
        position=(cx + dist, cy, cz), focal_point=center, view_up=(0, 1, 0),
        zoom=zoom, parallel_projection=True,
    ),
    duration=0.4,
    start_time=cycle_duration * 2,
)

# motion uses normalized frames (start_time=0), plays in parallel with scene tweens
motion_animation = create_animation_from_motion(motion)
scene_animation = scene.build_timeline().animations[0]
timeline = Timeline(animations=(ParallelAnimation(animations=(motion_animation, scene_animation)),))

print(f"\nShowcase timeline: {timeline.duration:.2f}s")
print(f"  0 - {t_reveal:.1f}s:  muscle and wrap reveal (concurrent with motion)")
print(f"  Motion: {num_cycles} walking cycles ({total_duration:.2f}s)")
print("  Camera: frontal (cycle 1) -> sagittal -> orthographic (cycle 2)")
print("Ready to render!")
