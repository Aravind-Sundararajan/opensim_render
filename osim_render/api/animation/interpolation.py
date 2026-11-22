"""
Core interpolation functions for animation.

Provides pure functions for interpolating values between start and end points
using various methods (linear, vector, spherical, cubic Bezier).
"""

import math
from typing import Sequence

# Beyond this the two directions are close enough to parallel (or opposite)
# that the rotation axis between them is numerically meaningless.
PARALLEL_TOLERANCE = 0.9995


def lerp(start: float, end: float, t: float) -> float:
    """
    Linear interpolation between two scalar values.

    Args:
        start: Starting value
        end: Ending value
        t: Parameter in [0, 1], where 0 returns start and 1 returns end

    Returns:
        Interpolated value

    Examples:
        >>> lerp(0, 100, 0.0)
        0.0
        >>> lerp(0, 100, 0.5)
        50.0
        >>> lerp(0, 100, 1.0)
        100.0
    """
    return start + (end - start) * t


def lerp_vector(
    start: Sequence[float], end: Sequence[float], t: float
) -> tuple[float, ...]:
    """
    Linear interpolation between two vectors (n-dimensional).

    Args:
        start: Starting vector (tuple, list, or sequence)
        end: Ending vector (must be same dimension as start)
        t: Parameter in [0, 1]

    Returns:
        Interpolated vector as tuple

    Raises:
        ValueError: If start and end have different dimensions

    Examples:
        >>> lerp_vector((0, 0, 0), (10, 20, 30), 0.5)
        (5.0, 10.0, 15.0)
    """
    if len(start) != len(end):
        raise ValueError(
            f"Start and end vectors must have same dimension. "
            f"Got {len(start)} and {len(end)}"
        )
    return tuple(lerp(s, e, t) for s, e in zip(start, end, strict=False))


def _half_turn(
    start: Sequence[float], end: Sequence[float], t: float
) -> tuple[float, ...]:
    """Rotate a unit vector onto its opposite through a perpendicular axis.

    Two opposite directions have no unique shortest arc, so one is chosen.
    Only defined for 3D; anything else falls back to linear interpolation.

    Args:
        start: Starting unit vector
        end: Ending unit vector, pointing nearly opposite to start
        t: Parameter in [0, 1]

    Returns:
        Unit vector rotated t of the way from start to end
    """
    if len(start) != 3:
        return lerp_vector(start, end, t)

    axis = _perpendicular_to(start)
    angle = math.pi * t
    cosine, sine = math.cos(angle), math.sin(angle)

    # Rodrigues' rotation, simplified because the axis is perpendicular to the
    # vector so the (axis . vector) term vanishes.
    cross = (
        axis[1] * start[2] - axis[2] * start[1],
        axis[2] * start[0] - axis[0] * start[2],
        axis[0] * start[1] - axis[1] * start[0],
    )
    return tuple(start[i] * cosine + cross[i] * sine for i in range(3))


def _perpendicular_to(vector: Sequence[float]) -> tuple[float, float, float]:
    """Find a unit vector at right angles to a 3D vector.

    Crosses with whichever basis direction the vector leans on least, so the
    result is never degenerate.

    Args:
        vector: A 3D vector

    Returns:
        A unit vector perpendicular to it
    """
    smallest = min(range(3), key=lambda axis: abs(vector[axis]))
    basis = [0.0, 0.0, 0.0]
    basis[smallest] = 1.0

    cross = (
        vector[1] * basis[2] - vector[2] * basis[1],
        vector[2] * basis[0] - vector[0] * basis[2],
        vector[0] * basis[1] - vector[1] * basis[0],
    )
    length = math.sqrt(sum(component * component for component in cross))
    return (cross[0] / length, cross[1] / length, cross[2] / length)


def slerp(start: Sequence[float], end: Sequence[float], t: float) -> tuple[float, ...]:
    """
    Spherical linear interpolation (slerp) between two unit vectors.

    Provides smooth interpolation along the shortest arc on a unit sphere.
    Useful for camera position movement and rotation interpolation.

    Args:
        start: Starting unit vector (should be normalized)
        end: Ending unit vector (should be normalized)
        t: Parameter in [0, 1]

    Returns:
        Interpolated unit vector as tuple

    Raises:
        ValueError: If vectors have different dimensions

    Notes:
        - Vectors should be normalized (magnitude = 1)
        - For nearly parallel vectors, falls back to linear interpolation
        - Produces constant-speed arc interpolation
    """
    if len(start) != len(end):
        raise ValueError(
            f"Start and end vectors must have same dimension. "
            f"Got {len(start)} and {len(end)}"
        )

    # Compute dot product
    dot_product = sum(s * e for s, e in zip(start, end, strict=False))

    # Clamp to avoid numerical errors
    dot = max(-1.0, min(1.0, dot_product))

    # Nearly the same direction: the arc is negligible, so lerp is both
    # accurate and free of the degenerate axis.
    if dot > PARALLEL_TOLERANCE:
        return lerp_vector(start, end, t)

    # Nearly opposite: every arc between them is equally short, so there is no
    # axis to interpolate about. Lerping here would pass through the origin —
    # for a camera that means flying through the focal point rather than
    # orbiting around it. Rotate through a chosen perpendicular instead.
    if dot < -PARALLEL_TOLERANCE:
        return _half_turn(start, end, t)

    # Compute angle between vectors
    theta = math.acos(dot)
    sin_theta = math.sin(theta)

    # Compute slerp weights
    w0 = math.sin((1.0 - t) * theta) / sin_theta
    w1 = math.sin(t * theta) / sin_theta

    # Interpolate
    result = tuple(w0 * s + w1 * e for s, e in zip(start, end, strict=False))

    # Normalize to ensure unit vector
    magnitude = math.sqrt(sum(x * x for x in result))
    if magnitude > 0:
        result = tuple(x / magnitude for x in result)

    return result


def bezier_cubic(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    """
    Cubic Bezier interpolation using 4 control points.

    Produces smooth curves with tangent control via intermediate points.

    Args:
        p0: First control point (start value)
        p1: Second control point (start tangent influence)
        p2: Third control point (end tangent influence)
        p3: Fourth control point (end value)
        t: Parameter in [0, 1]

    Returns:
        Interpolated value

    Notes:
        - p0 and p3 are the curve endpoints
        - p1 and p2 control the curve shape (not on the curve itself)
        - For easing functions, typically use p0=0, p1=ease1, p2=ease2, p3=1

    Examples:
        >>> # Linear curve: control points on the line
        >>> bezier_cubic(0, 1/3, 2/3, 1, 0.5)  # Close to 0.5
        >>> # Ease-out: steeper at start
        >>> bezier_cubic(0, 0.5, 1, 1, 0.5)  # > 0.5
    """
    # De Casteljau's algorithm for numerical stability
    # First level
    q0 = lerp(p0, p1, t)
    q1 = lerp(p1, p2, t)
    q2 = lerp(p2, p3, t)

    # Second level
    r0 = lerp(q0, q1, t)
    r1 = lerp(q1, q2, t)

    # Final level
    return lerp(r0, r1, t)


if __name__ == "__main__":
    # Smoke tests
    print("Testing interpolation module...")

    # Test lerp
    assert lerp(0, 100, 0.0) == 0.0
    assert lerp(0, 100, 0.5) == 50.0
    assert lerp(0, 100, 1.0) == 100.0
    print("[PASS] lerp tests passed")

    # Test lerp_vector
    result = lerp_vector((0, 0, 0), (10, 20, 30), 0.5)
    assert result == (5.0, 10.0, 15.0)
    print("[PASS] lerp_vector tests passed")

    # Test slerp
    result = slerp((1, 0, 0), (0, 1, 0), 0.5)
    # Should be approximately (0.707, 0.707, 0)
    assert abs(result[0] - 0.707) < 0.01
    assert abs(result[1] - 0.707) < 0.01
    assert abs(result[2]) < 0.01
    print("[PASS] slerp tests passed")

    # Test bezier_cubic
    bezier_result: float = bezier_cubic(0, 0.33, 0.67, 1, 0.5)
    assert 0.4 < bezier_result < 0.6  # Should be close to 0.5
    print("[PASS] bezier_cubic tests passed")

    print("\n[PASS] All interpolation tests passed!")
