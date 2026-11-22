"""
V02_progressive_reveal.py - CORRECTED

Progressive reveal animation - show bodies one by one.

CRITICAL: This script visualizes BODIES (femur, tibia, etc.), NOT coordinates!

This script demonstrates:
- Sequentially revealing different bodies (bones)
- Building a skeleton step-by-step
- Color coding different body segments
- Creating clarity and focus

PREREQUISITES:
  - Load a model (File  Open Model)

KEY CONCEPT:
  - Coordinates = joint angles (numerical values)
  - Bodies = visual bones (what you see rendered)
  - This script visualizes BODIES!

Great for educational/presentation purposes!
"""

from osim_render.api.animation.value_types import ColorValue

scene = Scene(model_manager, scene_manager, event_bus)

print("Progressive Reveal Animation - CORRECTED")
print("=" * 50)
print("")
print("Revealing bodies (bones) one by one")
print("NOT coordinates - bodies are visual objects!")
print("")

# Define colors for different body parts
color_pelvis = ColorValue(r=0.9, g=0.3, b=0.3, a=1.0)  # Red
color_femur = ColorValue(r=0.9, g=0.6, b=0.3, a=1.0)  # Orange
color_tibia = ColorValue(r=0.9, g=0.9, b=0.3, a=1.0)  # Yellow
color_foot = ColorValue(r=0.3, g=0.9, b=0.3, a=1.0)  # Green
gray = ColorValue(r=0.5, g=0.5, b=0.5, a=1.0)  # Gray

time = 0

# ============================================
# Step 1: Show pelvis (0-1 second)
# ============================================
print(f"Step 1 (t={time}s): Reveal pelvis (red)")

scene.fade_in("pelvis", duration=0.8, start_time=time)
scene.change_color("pelvis", gray, color_pelvis, duration=0.8, start_time=time)
time += 1.0

# ============================================
# Step 2: Show femur (1-2 seconds)
# ============================================
print(f"Step 2 (t={time}s): Reveal femur_r (orange)")

scene.fade_in("femur_r", duration=0.8, start_time=time)
scene.change_color("femur_r", gray, color_femur, duration=0.8, start_time=time)

# Highlight pelvis to show connection
scene.highlight_actor("pelvis", start_time=time + 0.4)
time += 1.0

# ============================================
# Step 3: Show tibia (2-3 seconds)
# ============================================
print(f"Step 3 (t={time}s): Reveal tibia_r (yellow)")

scene.fade_in("tibia_r", duration=0.8, start_time=time)
scene.change_color("tibia_r", gray, color_tibia, duration=0.8, start_time=time)

# Highlight femur to show connection
scene.highlight_actor("femur_r", start_time=time + 0.4)
time += 1.0

# ============================================
# Step 4: Show foot (3-4 seconds)
# ============================================
print(f"Step 4 (t={time}s): Reveal foot_r (green)")

scene.fade_in("foot_r", duration=0.8, start_time=time)
scene.change_color("foot_r", gray, color_foot, duration=0.8, start_time=time)

# Highlight tibia to show connection
scene.highlight_actor("tibia_r", start_time=time + 0.4)
time += 1.0

# ============================================
# Step 5: Pulse all (4-6 seconds)
# ============================================
print(f"Step 5 (t={time}s): Pulse entire leg")

scene.pulse_opacity(
    "pelvis", min_opacity=0.7, max_opacity=1.0, duration=1.5, cycles=1, start_time=time
)
scene.pulse_opacity(
    "femur_r", min_opacity=0.7, max_opacity=1.0, duration=1.5, cycles=1, start_time=time
)
scene.pulse_opacity(
    "tibia_r", min_opacity=0.7, max_opacity=1.0, duration=1.5, cycles=1, start_time=time
)
scene.pulse_opacity(
    "foot_r", min_opacity=0.7, max_opacity=1.0, duration=1.5, cycles=1, start_time=time
)
time += 2.0

# ============================================
# Build the animation
# ============================================
timeline = scene.build_timeline()

print("")
print("Animation Summary:")
print("  1. Pelvis appears (red)")
print("  2. Femur appears (orange), pelvis highlights")
print("  3. Tibia appears (yellow), femur highlights")
print("  4. Foot appears (green), tibia highlights")
print("  5. All bodies pulse together")
print("")
print(f"Total duration: {time} seconds")
print("")
print("IMPORTANT:")
print("  - pelvis, femur_r, tibia_r, foot_r are BODY names")
print("  - These are visual objects that render in the 3D scene")
print("  - NOT coordinates (which are joint angles)")
print("")
print("Use this for:")
print("  - Educational presentations")
print("  - Step-by-step anatomy demonstrations")
print("  - Explaining skeletal hierarchies")
print("")
print("Click 'Load to Animation Panel' to see it!")
