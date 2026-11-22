"""
V03_motion_with_highlights.py - CORRECTED

Visualize motion while highlighting specific bodies.

CRITICAL: Combines COORDINATE animation with BODY visualization!

This script demonstrates:
- Animating coordinates (joint angles) to move the model
- Highlighting specific bodies (bones) during motion
- Changing body colors to emphasize movement
- Creating cinematic motion visualizations

PREREQUISITES:
  - Load a model (File  Open Model)
  - Optionally load a motion file (File  Open Motion File)

KEY CONCEPT:
  - COORDINATES (hip_flexion_r) = joint angles - use animate_coordinate()
  - BODIES (femur_r, tibia_r) = visual bones - use fade_in(), change_color()
  - Use BOTH together!

Perfect for emphasizing specific joints or showing joint articulation!
"""

scene = Scene(model_manager, scene_manager, event_bus)

print("Motion with Highlights - CORRECTED")
print("=" * 50)
print("")
print("Combining coordinate animation with body visualization")
print("- Coordinates: Changes joint angles (pose)")
print("- Bodies: Changes appearance (color, opacity)")
print("")

# If motion data is available, use it; otherwise create manual animation
if motion_data is not None:
    print("Using loaded motion file!")
    print(f"Frames: {motion_data.num_frames}")
    print(f"Duration: {motion_data.end_time - motion_data.start_time:.2f}s")
    print("")

    # Create animation from motion
    animation = create_animation_from_motion()

    # Get motion duration for timing effects
    motion_duration = motion_data.end_time - motion_data.start_time
    print(f"Adding body highlights during the {motion_duration:.2f}s motion...")
    print("")

    # Add body visualization synchronized with motion timing
    # Highlight different bodies at different times
    times = [
        (0, 0.2, "pelvis", "Motion starts"),
        (motion_duration * 0.25, 0.3, "femur_r", "Quarter way through"),
        (motion_duration * 0.5, 0.3, "tibia_r", "Halfway"),
        (motion_duration * 0.75, 0.3, "foot_r", "Three-quarters"),
    ]

    for start_t, dur, body_name, desc in times:
        if start_t < motion_duration:
            scene.highlight_actor(body_name, start_time=start_t)
            print(f"  {desc} (t={start_t:.2f}s): Highlight {body_name}")

    # Build timeline with motion
    from osim_render.api.animation.timeline import Timeline

    timeline = Timeline(animations=(animation,) + scene.build_timeline().animations)

    print("")
    print("Animation created!")
    print("Watch how bodies highlight as motion progresses.")

else:
    print("No motion file loaded. Creating manual animation instead.")
    print("Demonstrating how to combine coordinate animation + body visualization")
    print("")

    # Create manual animation with highlights
    # This shows the CORRECT pattern:
    # 1. animate_coordinate() - changes joint angle
    # 2. highlight/color body - shows appearance change

    reach_duration = 2.0

    # Phase 1: Hip movement
    print("0-0.5s: Hip flexes, highlight femur...")
    scene.animate_coordinate("hip_flexion_r", 0, 45, duration=0.5)
    # CORRECT: Highlight the BODY that moves with this joint
    scene.highlight_actor("femur_r", start_time=0)

    # Phase 2: Knee movement
    print("0.5-1.0s: Knee flexes, highlight tibia...")
    scene.animate_coordinate("knee_angle_r", 0, -90, duration=0.5, start_time=0.5)
    # CORRECT: Highlight the body that moves
    scene.highlight_actor("tibia_r", start_time=0.5)

    # Phase 3: Ankle movement
    print("1.0-2.0s: Ankle flexes, highlight foot...")
    scene.animate_coordinate("ankle_angle_r", 0, 30, duration=0.5, start_time=1.0)
    # CORRECT: Highlight the body
    scene.highlight_actor("foot_r", start_time=1.0)

    # Fade out at end
    print("2.0s: Fading bodies out...")
    scene.fade_out("femur_r", "tibia_r", "foot_r", duration=0.5, start_time=1.5)

    timeline = scene.build_timeline()

    print("")
    print("Animation created!")
    print("Watch how bodies highlight as joints animate!")

print("")
print("KEY LESSON:")
print("   Use animate_coordinate() for joint angles")
print("   Use highlight_actor() for body visualization")
print("   Use both together for complete control!")
print("")
print("Click 'Load to Animation Panel' to play!")
