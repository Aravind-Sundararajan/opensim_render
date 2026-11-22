"""
Immutable value types for animation.

Provides frozen dataclasses that represent animatable values with type safety.
Immutability ensures reproducible animations and enables caching.
"""

from dataclasses import dataclass


# ============================================================================
# Scalar Value Types
# ============================================================================


@dataclass(frozen=True)
class ScalarValue:
    """
    A single numeric value that can be animated.

    Represents a scalar (single number) that changes over time.
    Examples: coordinate value, opacity, scale factor.

    Attributes:
        value: The numeric value
    """

    value: float

    def __post_init__(self) -> None:
        """Validate scalar value."""
        if not isinstance(self.value, (int, float)):
            raise TypeError(
                f"ScalarValue requires numeric value, got {type(self.value)}"
            )


@dataclass(frozen=True)
class VectorValue:
    """
    A vector (tuple of numeric values) that can be animated.

    Represents an n-dimensional vector that changes over time.
    Examples: position (3D), scale (3D), angles.

    Attributes:
        value: Tuple of numeric values (position, rotation, scale, etc.)
    """

    value: tuple[float, ...]

    def __post_init__(self) -> None:
        """Validate vector value."""
        if not isinstance(self.value, tuple):
            raise TypeError(f"VectorValue requires tuple, got {type(self.value)}")
        if not all(isinstance(x, (int, float)) for x in self.value):
            raise TypeError("VectorValue requires all numeric components")

    def magnitude(self) -> float:
        """
        Compute the magnitude (length) of the vector.

        Returns:
            Magnitude of the vector
        """
        import math

        return math.sqrt(sum(x * x for x in self.value))

    def normalized(self) -> "VectorValue":
        """
        Return a normalized (unit) version of the vector.

        Returns:
            New VectorValue with magnitude 1

        Raises:
            ValueError: If vector has zero magnitude
        """
        mag = self.magnitude()
        if mag == 0:
            raise ValueError("Cannot normalize zero vector")
        return VectorValue(tuple(x / mag for x in self.value))


# ============================================================================
# Color Value Types
# ============================================================================


@dataclass(frozen=True)
class ColorValue:
    """
    An RGBA color value that can be animated.

    Stores color as floating-point RGBA channels [0, 1].

    Attributes:
        r: Red channel [0, 1]
        g: Green channel [0, 1]
        b: Blue channel [0, 1]
        a: Alpha channel [0, 1] (default 1.0 = opaque)

    Examples:
        >>> red = ColorValue(r=1.0, g=0.0, b=0.0)
        >>> semi_transparent = ColorValue(r=1.0, g=0.0, b=0.0, a=0.5)
    """

    r: float
    g: float
    b: float
    a: float = 1.0

    def __post_init__(self) -> None:
        """Validate color channels are in valid range."""
        for channel, name in [
            (self.r, "r"),
            (self.g, "g"),
            (self.b, "b"),
            (self.a, "a"),
        ]:
            if not isinstance(channel, (int, float)):
                raise TypeError(
                    f"ColorValue.{name} must be numeric, got {type(channel)}"
                )
            if not (0.0 <= channel <= 1.0):
                raise ValueError(f"ColorValue.{name} must be in [0, 1], got {channel}")

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return color as (r, g, b, a) tuple."""
        return (self.r, self.g, self.b, self.a)

    def as_rgb_tuple(self) -> tuple[float, float, float]:
        """Return color as (r, g, b) tuple (without alpha)."""
        return (self.r, self.g, self.b)

    @staticmethod
    def from_rgb(r: float, g: float, b: float) -> "ColorValue":
        """Create opaque color from RGB values."""
        return ColorValue(r=r, g=g, b=b, a=1.0)

    @staticmethod
    def from_hex(hex_color: str, alpha: float = 1.0) -> "ColorValue":
        """
        Create color from hex string.

        Args:
            hex_color: Hex color string like "#FF0000" or "FF0000"
            alpha: Alpha channel [0, 1]

        Returns:
            ColorValue with RGB parsed from hex

        Examples:
            >>> ColorValue.from_hex("#FF0000")  # Red
            >>> ColorValue.from_hex("00FF00", alpha=0.5)  # Green, semi-transparent
        """
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            raise ValueError(f"Hex color must be 6 characters, got {hex_color}")

        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0

        return ColorValue(r=r, g=g, b=b, a=alpha)


# ============================================================================
# Camera State Type
# ============================================================================


@dataclass(frozen=True)
class CameraState:
    """
    Complete camera configuration that can be animated.

    Stores all camera parameters needed to render a view.

    Attributes:
        position: Camera position in 3D space (x, y, z)
        focal_point: Point the camera looks at (x, y, z)
        view_up: Vector defining "up" direction (x, y, z)
        zoom: Camera zoom level (default 1.0)
        parallel_projection: Whether to use parallel projection vs perspective

    Examples:
        >>> # Front view
        >>> state = CameraState(
        ...     position=(0, 0, 10),
        ...     focal_point=(0, 0, 0),
        ...     view_up=(0, 1, 0)
        ... )
    """

    position: tuple[float, float, float]
    focal_point: tuple[float, float, float]
    view_up: tuple[float, float, float]
    zoom: float = 1.0
    parallel_projection: bool = False

    def __post_init__(self) -> None:
        """Validate camera state."""
        for attr, name in [
            (self.position, "position"),
            (self.focal_point, "focal_point"),
            (self.view_up, "view_up"),
        ]:
            if not isinstance(attr, tuple) or len(attr) != 3:
                raise TypeError(f"{name} must be 3-tuple, got {attr}")
            if not all(isinstance(x, (int, float)) for x in attr):
                raise TypeError(f"{name} must contain numeric values")

        if not isinstance(self.zoom, (int, float)):
            raise TypeError(f"zoom must be numeric, got {type(self.zoom)}")
        if self.zoom <= 0:
            raise ValueError(f"zoom must be positive, got {self.zoom}")

        magnitude = sum(x * x for x in self.view_up) ** 0.5
        if magnitude < 0.001:
            raise ValueError("view_up vector cannot be zero")

    @staticmethod
    def front_view(
        distance: float = 10.0,
        zoom: float = 1.0,
        center: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> "CameraState":
        """
        Create a front view camera state.

        Args:
            distance: Distance from object to camera
            zoom: Camera zoom level
            center: Point to look at (model center). Defaults to origin.

        Returns:
            CameraState looking at center from front (+Z direction)
        """
        cx, cy, cz = center
        return CameraState(
            position=(cx, cy, cz + distance),
            focal_point=center,
            view_up=(0, 1, 0),
            zoom=zoom,
        )

    @staticmethod
    def side_view(
        distance: float = 10.0,
        zoom: float = 1.0,
        center: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> "CameraState":
        """
        Create a side view camera state.

        Args:
            distance: Distance from object to camera
            zoom: Camera zoom level
            center: Point to look at (model center). Defaults to origin.

        Returns:
            CameraState looking at center from the side (+X direction)
        """
        cx, cy, cz = center
        return CameraState(
            position=(cx + distance, cy, cz),
            focal_point=center,
            view_up=(0, 1, 0),
            zoom=zoom,
        )

    @staticmethod
    def top_view(
        distance: float = 10.0,
        zoom: float = 1.0,
        center: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> "CameraState":
        """
        Create a top view camera state.

        Args:
            distance: Distance from object to camera
            zoom: Camera zoom level
            center: Point to look at (model center). Defaults to origin.

        Returns:
            CameraState looking at center from top (+Y direction)
        """
        cx, cy, cz = center
        return CameraState(
            position=(cx, cy + distance, cz),
            focal_point=center,
            view_up=(0, 0, -1),
            zoom=zoom,
        )

    @staticmethod
    def isometric_view(
        distance: float = 10.0,
        zoom: float = 1.0,
        center: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> "CameraState":
        """
        Create an isometric view camera state.

        Args:
            distance: Distance from object to camera
            zoom: Camera zoom level
            center: Point to look at (model center). Defaults to origin.

        Returns:
            CameraState in isometric view looking at center
        """
        import math

        cx, cy, cz = center
        iso_dist = distance / math.sqrt(3)
        return CameraState(
            position=(cx + iso_dist, cy + iso_dist, cz + iso_dist),
            focal_point=center,
            view_up=(0, 1, 0),
            zoom=zoom,
        )


if __name__ == "__main__":
    # Smoke tests
    print("Testing value_types module...")

    # Test ScalarValue
    scalar = ScalarValue(value=42.0)
    assert scalar.value == 42.0
    print("[PASS] ScalarValue creation works")

    # Test VectorValue
    vec = VectorValue(value=(1.0, 2.0, 3.0))
    assert vec.magnitude() > 0
    print(f"[PASS] VectorValue creation works (magnitude: {vec.magnitude():.3f})")

    # Test normalization
    unit_vec = vec.normalized()
    assert abs(unit_vec.magnitude() - 1.0) < 0.001
    print("[PASS] VectorValue normalization works")

    # Test ColorValue
    color = ColorValue(r=1.0, g=0.0, b=0.0)
    assert color.as_tuple() == (1.0, 0.0, 0.0, 1.0)
    print("[PASS] ColorValue creation works")

    # Test ColorValue.from_hex
    red_from_hex = ColorValue.from_hex("#FF0000")
    assert red_from_hex.r > 0.99  # Allow small floating point error
    assert red_from_hex.g < 0.01
    assert red_from_hex.b < 0.01
    print("[PASS] ColorValue.from_hex works")

    # Test CameraState
    cam = CameraState.front_view(distance=10)
    assert cam.position == (0, 0, 10)
    assert cam.zoom == 1.0
    print("[PASS] CameraState creation works")

    # Test camera presets
    side = CameraState.side_view()
    top = CameraState.top_view()
    iso = CameraState.isometric_view()
    print("[PASS] CameraState presets work")

    print("\n[PASS] All value_types tests passed!")
