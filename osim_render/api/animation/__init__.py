"""Animation system for osim_render.

Provides a manim-style Python API for creating complex animations with:
- Model coordinate animation
- Camera movements
- Visual property changes (colors, transparency)
- Multi-format export (real-time preview, MP4/AVI, PNG sequences, high-res screenshots)

Quick start example:

    from osim_render.api.animation import Scene, ease_in_out_cubic

    scene = Scene(model_manager, scene_manager, event_bus)
    scene.animate_coordinate("hip_flexion_r", start=0.0, end=45.0, duration=2.0)
    timeline = scene.build_timeline()
    animation_manager.play_animation(timeline.animations[0], vtk_widget)

Architecture (5 layers):

    1. Foundation: interpolation.py, easing.py, value_types.py
    2. Tween: tween.py, coordinate_tween.py, camera_tween.py, property_tween.py, group_tween.py
    3. Scene/Timeline: animation.py, timeline.py, scene.py
    4. Rendering: animation_renderer.py, frame_exporter.py, video_exporter.py, screenshot_exporter.py
    5. Integration: integration.py
"""

# Layer 1: Foundation exports
from osim_render.api.animation.easing import (
    EasingFunction,
    ease_back_in,
    ease_back_in_out,
    ease_back_out,
    ease_bounce_in,
    ease_bounce_out,
    ease_elastic_in,
    ease_elastic_out,
    ease_in_cubic,
    ease_in_out_cubic,
    ease_in_out_quad,
    ease_in_out_sine,
    ease_in_quad,
    ease_in_sine,
    ease_linear,
    ease_out_cubic,
    ease_out_quad,
    ease_out_sine,
    ease_smooth_step,
    ease_smoother_step,
)
from osim_render.api.animation.interpolation import (
    bezier_cubic,
    lerp,
    lerp_vector,
    slerp,
)
from osim_render.api.animation.value_types import (
    CameraState,
    ColorValue,
    ScalarValue,
    VectorValue,
)

__all__ = [
    # Interpolation functions
    "lerp",
    "lerp_vector",
    "slerp",
    "bezier_cubic",
    # Easing functions
    "EasingFunction",
    "ease_linear",
    "ease_in_quad",
    "ease_out_quad",
    "ease_in_out_quad",
    "ease_in_cubic",
    "ease_out_cubic",
    "ease_in_out_cubic",
    "ease_in_sine",
    "ease_out_sine",
    "ease_in_out_sine",
    "ease_smooth_step",
    "ease_smoother_step",
    "ease_back_in",
    "ease_back_out",
    "ease_back_in_out",
    "ease_elastic_in",
    "ease_elastic_out",
    "ease_bounce_in",
    "ease_bounce_out",
    # Value types
    "ScalarValue",
    "VectorValue",
    "ColorValue",
    "CameraState",
]
