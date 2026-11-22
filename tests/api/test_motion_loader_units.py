"""Unit tests for motion loader coordinate unit detection and conversion."""

import math


from osim_render.api.loaders.motion_loader import MotionLoader


class TestCoordinateUnitConversion:
    """Test suite for coordinate unit detection and conversion."""

    def test_degrees_to_radians_conversion(self) -> None:
        """Test converting degree values to radians."""
        loader = MotionLoader()

        # 360 degrees = 2π radians
        result = loader._convert_coordinate_value(360, "degrees", "radians")
        assert abs(result - 2 * math.pi) < 1e-10

        # 180 degrees = π radians
        result = loader._convert_coordinate_value(180, "degrees", "radians")
        assert abs(result - math.pi) < 1e-10

        # 90 degrees = π/2 radians
        result = loader._convert_coordinate_value(90, "degrees", "radians")
        assert abs(result - math.pi / 2) < 1e-10

    def test_radians_to_degrees_conversion(self) -> None:
        """Test converting radian values to degrees."""
        loader = MotionLoader()

        # 2π radians = 360 degrees
        result = loader._convert_coordinate_value(
            2 * math.pi, "radians", "degrees")
        assert abs(result - 360) < 1e-10

        # π radians = 180 degrees
        result = loader._convert_coordinate_value(
            math.pi, "radians", "degrees")
        assert abs(result - 180) < 1e-10

    def test_same_unit_conversion(self) -> None:
        """Test that same unit conversion returns original value."""
        loader = MotionLoader()

        value = 45.5
        result = loader._convert_coordinate_value(value, "degrees", "degrees")
        assert result == value

        result = loader._convert_coordinate_value(value, "radians", "radians")
        assert result == value

    def test_negative_angle_conversion(self) -> None:
        """Test converting negative angles."""
        loader = MotionLoader()

        # -180 degrees = -π radians
        result = loader._convert_coordinate_value(-180, "degrees", "radians")
        assert abs(result - (-math.pi)) < 1e-10

        # -90 degrees = -π/2 radians
        result = loader._convert_coordinate_value(-90, "degrees", "radians")
        assert abs(result - (-math.pi / 2)) < 1e-10

    def test_detect_data_units_radians(self) -> None:
        """Test detecting radian data based on range."""
        loader = MotionLoader()

        # Small values in [-π, π] should be detected as radians
        radian_values = [0.5, 1.0, -0.5, -1.5]
        result = loader._detect_data_units(radian_values)
        assert result == "radians"

    def test_detect_data_units_degrees(self) -> None:
        """Test detecting degree data based on range."""
        loader = MotionLoader()

        # Large values outside [-π, π] should be detected as degrees
        degree_values = [45.0, 90.0, 180.0, -45.0, -90.0]
        result = loader._detect_data_units(degree_values)
        assert result == "degrees"

    def test_detect_data_units_full_range_degrees(self) -> None:
        """Test detecting degrees with full rotation range."""
        loader = MotionLoader()

        # Values from -180 to 180 should be degrees
        degree_values = [-180.0, -90.0, 0.0, 90.0, 180.0]
        result = loader._detect_data_units(degree_values)
        assert result == "degrees"

    def test_detect_data_units_full_range_radians(self) -> None:
        """Test detecting radians with full rotation range."""
        loader = MotionLoader()

        # Values from -π to π should be radians
        radian_values = [-math.pi, -math.pi / 2, 0, math.pi / 2, math.pi]
        result = loader._detect_data_units(radian_values)
        assert result == "radians"

    def test_detect_data_units_empty_list(self) -> None:
        """Test detecting units with empty list defaults to radians."""
        loader = MotionLoader()

        result = loader._detect_data_units([])
        assert result == "radians"

    def test_detect_data_units_single_value(self) -> None:
        """Test detecting units with single value."""
        loader = MotionLoader()

        # Single small value - radians
        result = loader._detect_data_units([0.5])
        assert result == "radians"

        # Single large value - degrees
        result = loader._detect_data_units([45])
        assert result == "degrees"

    def test_detect_data_units_ambiguous_large_spread(self) -> None:
        """Test detecting units with large spread indicates degrees."""
        loader = MotionLoader()

        # Spread larger than π suggests degrees
        values = [-2 * math.pi, 0, 2 * math.pi]
        result = loader._detect_data_units(values)
        assert result == "degrees"

    def test_zero_value_conversion(self) -> None:
        """Test converting zero value."""
        loader = MotionLoader()

        result = loader._convert_coordinate_value(0, "degrees", "radians")
        assert result == 0

        result = loader._convert_coordinate_value(0, "radians", "degrees")
        assert result == 0

    def test_small_angle_conversion_precision(self) -> None:
        """Test precision of small angle conversion."""
        loader = MotionLoader()

        # 0.1 degrees
        result = loader._convert_coordinate_value(0.1, "degrees", "radians")
        expected = math.radians(0.1)
        assert abs(result - expected) < 1e-10

    def test_detect_data_units_mixed_values(self) -> None:
        """Test detecting units with mixed positive/negative values."""
        loader = MotionLoader()

        # Symmetric around zero in degree range
        degree_values = [-90.0, -45.0, 0.0, 45.0, 90.0]
        result = loader._detect_data_units(degree_values)
        assert result == "degrees"

        # Symmetric around zero in radian range
        radian_values = [-math.pi / 2, -math.pi /
                         4, 0, math.pi / 4, math.pi / 2]
        result = loader._detect_data_units(radian_values)
        assert result == "radians"

    def test_large_degree_values(self) -> None:
        """Test detecting very large degree values."""
        loader = MotionLoader()

        # Multiple full rotations in degrees
        degree_values = [0.0, 360.0, 720.0, -360.0, -720.0]
        result = loader._detect_data_units(degree_values)
        assert result == "degrees"

    def test_outlier_handling(self) -> None:
        """Test unit detection with outliers."""
        loader = MotionLoader()

        # Mostly in degree range with one outlier
        mostly_degrees = [45.0, 90.0, 180.0, -45.0, -90.0, 1000.0]
        result = loader._detect_data_units(mostly_degrees)
        assert result == "degrees"

    def test_near_boundary_radian_values(self) -> None:
        """Test unit detection near π boundary."""
        loader = MotionLoader()

        # Values near ±π should be detected as radians
        values = [3.0, -3.0]  # Close to π
        result = loader._detect_data_units(values)
        assert result == "radians"

    def test_near_boundary_degree_values(self) -> None:
        """Test unit detection near 180/360 boundary."""
        loader = MotionLoader()

        # Values in degree range
        values = [175.0, 185.0, -175.0, -185.0]
        result = loader._detect_data_units(values)
        assert result == "degrees"


class TestMotionLoaderWithUnits:
    """Integration tests for motion loader with unit conversion."""

    def test_motion_loader_initialization(self) -> None:
        """Test that motion loader initializes properly."""
        loader = MotionLoader()
        assert loader is not None

    def test_conversion_methods_exist(self) -> None:
        """Test that all conversion methods exist."""
        loader = MotionLoader()
        assert hasattr(loader, "_convert_coordinate_value")
        assert hasattr(loader, "_detect_data_units")
        assert hasattr(loader, "_detect_coordinate_units")
        assert hasattr(loader, "_extract_coord_name")
        assert callable(loader._convert_coordinate_value)
        assert callable(loader._detect_data_units)
