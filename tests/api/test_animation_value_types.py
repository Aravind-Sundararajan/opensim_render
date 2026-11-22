"""Unit tests for animation value types."""

from typing import Any, cast

import pytest

from osim_render.api.animation.value_types import (
    ColorValue,
    VectorValue,
    CameraState,
    ScalarValue,
)


class TestColorValue:
    """Test ColorValue class."""

    def test_from_rgb(self) -> None:
        """Test creating ColorValue from RGB."""
        color = ColorValue(r=0.5, g=0.7, b=0.9, a=1.0)
        assert color.r == 0.5
        assert color.g == 0.7
        assert color.b == 0.9
        assert color.a == 1.0

    def test_defaults_alpha(self) -> None:
        """Test ColorValue defaults alpha to 1.0."""
        color = ColorValue(r=0.5, g=0.7, b=0.9)
        assert color.a == 1.0

    def test_as_tuple(self) -> None:
        """Test as_tuple returns RGBA tuple."""
        color = ColorValue(r=1.0, g=0.0, b=0.5, a=0.8)
        assert color.as_tuple() == (1.0, 0.0, 0.5, 0.8)

    def test_as_rgb_tuple(self) -> None:
        """Test as_rgb_tuple returns RGB only."""
        color = ColorValue(r=1.0, g=0.0, b=0.5, a=0.8)
        assert color.as_rgb_tuple() == (1.0, 0.0, 0.5)

    def test_from_hex_white(self) -> None:
        """Test from_hex with white color."""
        color = ColorValue.from_hex("#FFFFFF")
        assert color.r == pytest.approx(1.0)
        assert color.g == pytest.approx(1.0)
        assert color.b == pytest.approx(1.0)

    def test_from_hex_black(self) -> None:
        """Test from_hex with black color."""
        color = ColorValue.from_hex("#000000")
        assert color.r == pytest.approx(0.0)
        assert color.g == pytest.approx(0.0)
        assert color.b == pytest.approx(0.0)

    def test_from_hex_red(self) -> None:
        """Test from_hex with red color."""
        color = ColorValue.from_hex("#FF0000")
        assert color.r == pytest.approx(1.0)
        assert color.g == pytest.approx(0.0)
        assert color.b == pytest.approx(0.0)

    def test_from_hex_custom_alpha(self) -> None:
        """Test from_hex with custom alpha."""
        color = ColorValue.from_hex("#FF0000", alpha=0.5)
        assert color.r == pytest.approx(1.0)
        assert color.a == pytest.approx(0.5)

class TestVectorValue:
    """Test VectorValue class."""

    def test_vector_creation(self) -> None:
        """Test creating a vector."""
        v = VectorValue(value=(3.0, 4.0, 0.0))
        assert v.value == (3.0, 4.0, 0.0)

    def test_vector_magnitude(self) -> None:
        """Test vector magnitude calculation."""
        v = VectorValue(value=(3.0, 4.0, 0.0))
        assert v.magnitude() == pytest.approx(5.0)

    def test_vector_magnitude_3d(self) -> None:
        """Test 3D vector magnitude."""
        v = VectorValue(value=(1.0, 2.0, 2.0))
        assert v.magnitude() == pytest.approx(3.0)

    def test_vector_normalized(self) -> None:
        """Test vector normalization."""
        v = VectorValue(value=(3.0, 4.0, 0.0))
        n = v.normalized()

        assert n.magnitude() == pytest.approx(1.0)
        assert n.value[0] == pytest.approx(0.6)
        assert n.value[1] == pytest.approx(0.8)

    def test_vector_zero_magnitude_normalized_raises(self) -> None:
        """Test normalized zero vector raises ValueError."""
        v = VectorValue(value=(0.0, 0.0, 0.0))
        with pytest.raises(ValueError):
            v.normalized()

class TestScalarValue:
    """Test ScalarValue class."""

    def test_scalar_creation(self) -> None:
        """Test creating a scalar value."""
        s = ScalarValue(value=5.5)
        assert s.value == 5.5

class TestCameraState:
    """Test CameraState class."""

    def test_camera_state_creation(self) -> None:
        """Test creating a camera state."""
        cam = CameraState(
            position=(0.0, 1.0, 5.0),
            focal_point=(0.0, 1.0, 0.0),
            view_up=(0.0, 1.0, 0.0),
        )
        assert cam.position == (0.0, 1.0, 5.0)
        assert cam.focal_point == (0.0, 1.0, 0.0)
        assert cam.view_up == (0.0, 1.0, 0.0)

    def test_front_view(self) -> None:
        """Test front view preset."""
        cam = CameraState.front_view()
        assert cam is not None
        assert isinstance(cam, CameraState)
        assert cam.position[2] > 0  # Camera is in front (positive Z)

    def test_side_view(self) -> None:
        """Test side view preset."""
        cam = CameraState.side_view()
        assert cam is not None
        assert isinstance(cam, CameraState)
        assert cam.position[0] > 0  # Camera is on the side (positive X)

    def test_top_view(self) -> None:
        """Test top view preset."""
        cam = CameraState.top_view()
        assert cam is not None
        assert isinstance(cam, CameraState)
        assert cam.position[1] > 0  # Camera is on top (positive Y)

    def test_isometric_view(self) -> None:
        """Test isometric view preset."""
        cam = CameraState.isometric_view()
        assert cam is not None
        assert isinstance(cam, CameraState)

    def test_default_zoom(self) -> None:
        """Test default zoom is 1.0."""
        cam = CameraState.front_view()
        assert cam.zoom == 1.0

    def test_custom_zoom(self) -> None:
        """Test custom zoom level."""
        cam = CameraState.front_view(zoom=2.0)
        assert cam.zoom == 2.0

    def test_custom_distance(self) -> None:
        """Test custom distance."""
        cam1 = CameraState.front_view(distance=5.0)
        cam2 = CameraState.front_view(distance=10.0)
        # cam2 should be further away
        assert cam2.position[2] > cam1.position[2]


class TestValueTypeValidation:
    """Test value type validation."""

    def test_color_channel_out_of_range_low(self) -> None:
        """Test color channel below [0, 1] raises ValueError."""
        with pytest.raises(ValueError):
            ColorValue(r=-0.1, g=0.0, b=0.0)

    def test_color_channel_out_of_range_high(self) -> None:
        """Test color channel above [0, 1] raises ValueError."""
        with pytest.raises(ValueError):
            ColorValue(r=1.1, g=0.0, b=0.0)

    def test_color_channel_not_numeric(self) -> None:
        """Test color channel must be numeric."""
        with pytest.raises(TypeError):
            ColorValue(r=cast(Any, "red"), g=0.0, b=0.0)

    def test_vector_value_must_be_tuple(self) -> None:
        """Test VectorValue requires tuple."""
        with pytest.raises(TypeError):
            VectorValue(value=cast(Any, [1.0, 2.0, 3.0]))

    def test_scalar_value_must_be_numeric(self) -> None:
        """Test ScalarValue requires numeric."""
        with pytest.raises(TypeError):
            ScalarValue(value=cast(Any, "five"))

    def test_camera_position_must_be_3tuple(self) -> None:
        """Test CameraState position must be 3-tuple."""
        with pytest.raises(TypeError):
            CameraState(
                position=cast(Any, (0.0, 0.0)),
                focal_point=(0.0, 0.0, 0.0),
                view_up=(0.0, 1.0, 0.0),
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
