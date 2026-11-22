"""
Easing functions for animation timing curves.

Provides pure functions that map time [0, 1] to easing [0, 1] with various
timing curves (linear, quadratic, cubic, sine, etc.).

All easing functions follow the convention:
- Input t in [0, 1] represents normalized time
- Output in [0, 1] represents normalized progress
- At t=0, easing(0) = 0 (animation starts)
- At t=1, easing(1) = 1 (animation ends)
"""

import math
from typing import Callable

# Type alias for easing functions
EasingFunction = Callable[[float], float]


# ============================================================================
# Basic Easings
# ============================================================================


def ease_linear(t: float) -> float:
    """
    Linear easing (no acceleration or deceleration).

    Constant speed throughout the animation.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]

    Examples:
        >>> ease_linear(0.5)
        0.5
    """
    return t


# ============================================================================
# Quadratic Easings
# ============================================================================


def ease_in_quad(t: float) -> float:
    """
    Quadratic easing in (accelerating from zero velocity).

    Curve: t^2

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]

    Examples:
        >>> ease_in_quad(0.5)
        0.25
    """
    return t * t


def ease_out_quad(t: float) -> float:
    """
    Quadratic easing out (decelerating to zero velocity).

    Curve: 1 - (1-t)^2

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]

    Examples:
        >>> ease_out_quad(0.5)
        0.75
    """
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_out_quad(t: float) -> float:
    """
    Quadratic easing in-out (accelerate then decelerate).

    Fast start and end, slow middle.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]

    Examples:
        >>> ease_in_out_quad(0.25)
        0.125
        >>> ease_in_out_quad(0.75)
        0.875
    """
    if t < 0.5:
        return 2.0 * t * t
    else:
        return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0


# ============================================================================
# Cubic Easings
# ============================================================================


def ease_in_cubic(t: float) -> float:
    """
    Cubic easing in (stronger acceleration than quadratic).

    Curve: t^3

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    return t * t * t


def ease_out_cubic(t: float) -> float:
    """
    Cubic easing out (stronger deceleration than quadratic).

    Curve: 1 - (1-t)^3

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    """
    Cubic easing in-out (strong start and end, slow middle).

    Fast start and end, slow middle. Stronger acceleration/deceleration
    than quadratic.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]

    Examples:
        >>> ease_in_out_cubic(0.5)
        0.5
    """
    if t < 0.5:
        return 4.0 * t * t * t
    else:
        return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


# ============================================================================
# Sine Easings
# ============================================================================


def ease_in_sine(t: float) -> float:
    """
    Sine easing in (smooth acceleration).

    Based on sin curve. Very smooth compared to polynomial easings.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    return 1.0 - math.cos((t * math.pi) / 2.0)


def ease_out_sine(t: float) -> float:
    """
    Sine easing out (smooth deceleration).

    Based on sin curve. Very smooth compared to polynomial easings.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    return math.sin((t * math.pi) / 2.0)


def ease_in_out_sine(t: float) -> float:
    """
    Sine easing in-out (smooth acceleration and deceleration).

    Smoothest of the basic easings.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    return -(math.cos(math.pi * t) - 1.0) / 2.0


# ============================================================================
# Smooth Step Functions
# ============================================================================


def ease_smooth_step(t: float) -> float:
    """
    Smooth step easing (Hermite interpolation).

    Commonly used in computer graphics for smooth animation.
    Formula: 3t^2 - 2t^3

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]

    Examples:
        >>> ease_smooth_step(0.0)
        0.0
        >>> ease_smooth_step(0.5)
        0.5
        >>> ease_smooth_step(1.0)
        1.0
    """
    return t * t * (3.0 - 2.0 * t)


def ease_smoother_step(t: float) -> float:
    """
    Smoother step easing (Ken Perlin's improved Hermite).

    Smoother than smooth_step with zero derivative at endpoints.
    Formula: 6t^5 - 15t^4 + 10t^3

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


# ============================================================================
# Other Useful Easings
# ============================================================================


def ease_back_in(t: float) -> float:
    """
    Back easing in (slight overshoot at start).

    Creates a "pulling back" effect before acceleration.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    c1 = 1.70158
    c3 = c1 + 1.0
    return c3 * t * t * t - c1 * t * t


def ease_back_out(t: float) -> float:
    """
    Back easing out (slight overshoot at end).

    Creates a "bouncing back" effect after deceleration.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def ease_back_in_out(t: float) -> float:
    """
    Back easing in-out (overshoot at both start and end).

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    c1 = 1.70158
    c2 = c1 * 1.525
    if t < 0.5:
        return ((2.0 * t) ** 2 * ((c2 + 1.0) * 2.0 * t - c2)) / 2.0
    else:
        return ((2.0 * t - 2.0) ** 2 * ((c2 + 1.0) * (t * 2.0 - 2.0) + c2) + 2.0) / 2.0


def ease_elastic_in(t: float) -> float:
    """
    Elastic easing in (oscillates at start).

    Creates a spring-like effect with oscillations.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    if t == 0.0:
        return 0.0
    elif t == 1.0:
        return 1.0
    else:
        c4 = (2.0 * math.pi) / 3.0
        result = -(2.0 ** (10.0 * t - 10.0)) * math.sin((t * 10.0 - 10.75) * c4)
        return float(result)


def ease_elastic_out(t: float) -> float:
    """
    Elastic easing out (oscillates at end).

    Creates a spring-like effect with oscillations.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    if t == 0.0:
        return 0.0
    elif t == 1.0:
        return 1.0
    else:
        c4 = (2.0 * math.pi) / 3.0
        result = (2.0 ** (-10.0 * t)) * math.sin((t * 10.0 - 0.75) * c4) + 1.0
        return float(result)


def ease_bounce_out(t: float) -> float:
    """
    Bounce easing out (bounces at end).

    Creates a bouncing ball effect.

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    c1 = 7.5625

    if t < 1.0 / 2.75:
        return c1 * t * t
    elif t < 2.0 / 2.75:
        return c1 * (t - 1.5 / 2.75) ** 2 + 0.75
    elif t < 2.5 / 2.75:
        return c1 * (t - 2.25 / 2.75) ** 2 + 0.9375
    else:
        return c1 * (t - 2.625 / 2.75) ** 2 + 0.984375


def ease_bounce_in(t: float) -> float:
    """
    Bounce easing in (bounces at start).

    Args:
        t: Time parameter in [0, 1]

    Returns:
        Eased value in [0, 1]
    """
    return 1.0 - ease_bounce_out(1.0 - t)


if __name__ == "__main__":
    # Smoke tests
    print("Testing easing module...")

    # Test all easing functions with key points
    easings = [
        ("linear", ease_linear),
        ("in_quad", ease_in_quad),
        ("out_quad", ease_out_quad),
        ("in_out_quad", ease_in_out_quad),
        ("in_cubic", ease_in_cubic),
        ("out_cubic", ease_out_cubic),
        ("in_out_cubic", ease_in_out_cubic),
        ("in_sine", ease_in_sine),
        ("out_sine", ease_out_sine),
        ("in_out_sine", ease_in_out_sine),
        ("smooth_step", ease_smooth_step),
        ("smoother_step", ease_smoother_step),
        ("back_in", ease_back_in),
        ("back_out", ease_back_out),
        ("back_in_out", ease_back_in_out),
        ("elastic_in", ease_elastic_in),
        ("elastic_out", ease_elastic_out),
        ("bounce_out", ease_bounce_out),
        ("bounce_in", ease_bounce_in),
    ]

    for name, easing_fn in easings:
        # Test key points (with epsilon for floating point errors)
        epsilon = 1e-10
        v0 = easing_fn(0.0)
        v1 = easing_fn(1.0)
        assert abs(v0 - 0.0) < epsilon, f"{name} at t=0 should return 0, got {v0}"
        assert abs(v1 - 1.0) < epsilon, f"{name} at t=1 should return 1, got {v1}"

        # Test that function runs without error (may overshoot in some easing functions)
        mid = easing_fn(0.5)
        assert isinstance(
            mid, (int, float)
        ), f"{name} should return numeric value at t=0.5"

        print(f"[PASS] {name}: 0={v0:.3f}, 0.5={mid:.3f}, 1={v1:.3f}")

    print("\n[PASS] All easing tests passed!")
