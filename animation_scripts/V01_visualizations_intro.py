"""
V01_visualizations_intro.py - CORRECTED

Introduction to visualization features: opacity, colors, and actor visibility.

CRITICAL: This script visualizes BODIES (femur, tibia, etc.), NOT coordinates!

This script demonstrates:
- Fading bodies in and out
- Changing body colors smoothly (lerp)
- Highlighting specific bodies
- Toggling body visibility
- Pulsing opacity for emphasis

PREREQUISITES:
  - Load a model (File  Open Model)

KEY CONCEPT:
  - Coordinates (hip_flexion_r, knee_angle_r) = joint angles (pose)
  - Bodies (femur_r, tibia_r) = visual objects (what you see)
  - This script visualizes BODIES, not coordinates!

See VISUALIZATION_CONCEPTS.md for full explanation.
"""

from osim_render.api.animation.value_types import ColorValue

scene = Scene(model_manager, scene_manager, event_bus)

print("Visualization Effects Demo")
print("=" * 50)
print("")
print("Demonstrating visualization of BODIES (not coordinates)")
print("Bodies are the visual bones you see in the scene")
print("")

# ============================================
# PHASE 1: Fade in body parts (0-1 second)
# ============================================
print("Phase 1 (0-1s): Fade in bodies")

# Note: These are BODY names (things you can see)
# NOT coordinate names!
scene.fade_in("pelvis", duration=1.0)
scene.fade_in("femur_r", duration=1.0, start_time=0)
scene.fade_in("tibia_r", duration=1.0, start_time=0)

# ============================================
# PHASE 2: Highlight different bodies (1-3 seconds)
# ============================================
print("Phase 2 (1-3s): Highlight and color bodies")

# Highlight pelvis
scene.highlight_actor("pelvis", start_time=1.0)

# Change femur color to red
red = ColorValue(r=1.0, g=0.2, b=0.2, a=1.0)
gray = ColorValue(r=0.5, g=0.5, b=0.5, a=1.0)
scene.change_color("femur_r", gray, red, duration=1.0, start_time=1.5)

# Change tibia color to blue
blue = ColorValue(r=0.2, g=0.2, b=1.0, a=1.0)
scene.change_color("tibia_r", gray, blue, duration=1.0, start_time=1.5)

# ============================================
# PHASE 3: Opacity effects (3-5 seconds)
# ============================================
print("Phase 3 (3-5s): Opacity effects")

# Make femur semi-transparent
scene.animate_opacity("femur_r", 1.0, 0.5, duration=1.0, start_time=3.0)

# Pulse the tibia
scene.pulse_opacity(
    "tibia_r", min_opacity=0.3, max_opacity=1.0, duration=1.0, cycles=2, start_time=3.0
)

# ============================================
# PHASE 4: Hide and show (5-7 seconds)
# ============================================
print("Phase 4 (5-7s): Hide and show bodies")

scene.set_visibility("femur_r", False)
scene.set_visibility("tibia_r", False)

scene.set_visibility("femur_r", True)
scene.set_visibility("tibia_r", True)

# ============================================
# Build the animation
# ============================================
timeline = scene.build_timeline()

print("")
print("Animation Effects Summary:")
print("  - Fade in: pelvis, femur_r, tibia_r (BODIES)")
print("  - Highlight: pelvis (yellow)")
print("  - Color change: femur  red, tibia  blue")
print("  - Opacity: femur  50% transparent")
print("  - Pulse: tibia (2 cycles)")
print("  - Hide/Show: femur and tibia disappear then reappear")
print("")
print("Total duration: ~7 seconds")
print("")
print("IMPORTANT:")
print("  - These actor_names (femur_r, tibia_r) are BODIES")
print("  - They are visual objects that render in the 3D scene")
print("  - NOT coordinates (which are joint angles)")
print("")
print("Click 'Load to Animation Panel' to see the effects!")
