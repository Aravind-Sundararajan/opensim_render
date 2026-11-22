"""
V04_advanced_visualization.py - CORRECTED

Advanced visualization techniques combining multiple effects on BODIES.

CRITICAL: This script visualizes BODIES (visual objects), NOT coordinates!

This script demonstrates:
- Fading multiple bodies simultaneously
- Complex color transitions
- Synchronized opacity and color changes
- Layered visualization for focus and clarity

PREREQUISITES:
  - Load a model (File  Open Model)

KEY CONCEPT:
  - All visualization methods work on BODIES (visual actors)
  - NOT on coordinates (which are abstract joint angles)
  - Bodies are: femur, tibia, pelvis, foot, muscles, frames, contact geometry, etc.

This is an advanced visualization example!
"""

from osim_render.api.animation.value_types import ColorValue
from osim_render.api.animation.easing import ease_out_cubic

scene = Scene(model_manager, scene_manager, event_bus)

print("Advanced Visualization Techniques - CORRECTED")
print("=" * 50)
print("")
print("Demonstrating:")
print("  - Multiple simultaneous effects on BODIES")
print("  - Color gradients")
print("  - Opacity layers")
print("  - Emphasis and focus")
print("")

# ============================================
# SECTION 1: Fade in with color transition (0-2 seconds)
# ============================================
print("Section 1 (0-2s): Fade in and color BODIES")

# Gray to vibrant as bodies appear
gray = ColorValue(r=0.5, g=0.5, b=0.5, a=1.0)
purple = ColorValue(r=0.8, g=0.2, b=0.8, a=1.0)
cyan = ColorValue(r=0.2, g=0.8, b=0.8, a=1.0)
lime = ColorValue(r=0.2, g=0.8, b=0.2, a=1.0)

# Pelvis: fade in + color transition
scene.fade_in("pelvis", duration=2.0)
scene.change_color("pelvis", gray, purple, duration=2.0)

# Femur: staggered fade + color
scene.fade_in("femur_r", duration=1.5, start_time=0.25)
scene.change_color("femur_r", gray, cyan, duration=1.5, start_time=0.25)

# Tibia: staggered more
scene.fade_in("tibia_r", duration=1.0, start_time=0.5)
scene.change_color("tibia_r", gray, lime, duration=1.0, start_time=0.5)

# ============================================
# SECTION 2: Opacity layers for focus (2-4 seconds)
# ============================================
print("Section 2 (2-4s): Opacity layers (focus technique)")

# Make femur semi-transparent (background layer)
scene.animate_opacity(
    "femur_r", 1.0, 0.4, duration=1.0, start_time=2.0, easing=ease_out_cubic
)

# Pulse tibia to draw attention
scene.pulse_opacity(
    "tibia_r", min_opacity=0.5, max_opacity=1.0, duration=0.8, cycles=2, start_time=2.2
)

# Pelvis stays prominent
scene.pulse_opacity(
    "pelvis", min_opacity=0.8, max_opacity=1.0, duration=0.6, cycles=2, start_time=2.0
)

# ============================================
# SECTION 3: Sequential reveal (4-6 seconds)
# ============================================
print("Section 3 (4-6s): Sequential reveal")

# Hide supporting structure
scene.animate_opacity("femur_r", 0.4, 0.1, duration=0.5, start_time=4.0)

# Make tibia prominent
scene.animate_opacity("tibia_r", 1.0, 1.0, duration=0.1, start_time=4.0)

# Highlight with bright color
bright_red = ColorValue(r=1.0, g=0.0, b=0.0, a=1.0)
scene.change_color("tibia_r", lime, bright_red, duration=0.8, start_time=4.0)

# ============================================
# SECTION 4: Focus/blur effect (6-8 seconds)
# ============================================
print("Section 4 (6-8s): Focus technique (blur background)")

# Blur (reduce opacity) everything except foot
scene.animate_opacity("pelvis", 1.0, 0.2, duration=1.0, start_time=6.0)
scene.animate_opacity("femur_r", 0.1, 0.15, duration=1.0, start_time=6.0)
scene.animate_opacity("tibia_r", 1.0, 0.2, duration=1.0, start_time=6.0)

# Highlight foot
scene.fade_in("foot_r", duration=0.5, start_time=6.0)
gold = ColorValue(r=1.0, g=0.85, b=0.0, a=1.0)
scene.change_color("foot_r", gray, gold, duration=0.8, start_time=6.1)

# Pulse foot for emphasis
scene.pulse_opacity(
    "foot_r", min_opacity=0.7, max_opacity=1.0, duration=0.6, cycles=1, start_time=6.5
)

# ============================================
# SECTION 5: Restore normal view (8-9 seconds)
# ============================================
print("Section 5 (8-9s): Restore view")

# Fade everything back to normal opacity
scene.animate_opacity("pelvis", 0.2, 1.0, duration=1.0, start_time=8.0)
scene.animate_opacity("femur_r", 0.15, 1.0, duration=1.0, start_time=8.0)
scene.animate_opacity("tibia_r", 0.2, 1.0, duration=1.0, start_time=8.0)
scene.animate_opacity("foot_r", 1.0, 1.0, duration=0.5, start_time=8.0)

# Restore colors to gray
scene.change_color("pelvis", purple, gray, duration=0.8, start_time=8.0)
scene.change_color("femur_r", cyan, gray, duration=0.8, start_time=8.0)
scene.change_color("tibia_r", bright_red, gray, duration=0.8, start_time=8.0)
scene.change_color("foot_r", gold, gray, duration=0.8, start_time=8.0)

# ============================================
# Build the animation
# ============================================
timeline = scene.build_timeline()

print("")
print("Animation Techniques Used:")
print("  - Staggered fade-in for reveal effect")
print("  - Color transitions for visual interest")
print("  - Opacity layers to create focus")
print("  - Pulsing for emphasis")
print("  - Blur effect (reduce opacity) for focus")
print("  - Synchronized multi-actor animations")
print("")
print("Total duration: ~9 seconds")
print("")
print("IMPORTANT:")
print("  - All actor_names (pelvis, femur_r, tibia_r, foot_r) are BODIES")
print("  - These are visual objects rendered in the 3D scene")
print("  - NOT coordinates (which are abstract joint angles)")
print("")
print("Use these techniques for:")
print("  - Medical/anatomical presentations")
print("  - Education and training")
print("  - Scientific visualization")
print("  - Focus and emphasis")
print("")
print("Click 'Load to Animation Panel' to see it!")
