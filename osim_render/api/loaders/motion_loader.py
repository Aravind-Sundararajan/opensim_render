"""Load motion data from .sto and .mot files.

Reads time-series kinematic or dynamics data for model visualization.
Handles automatic unit detection and conversion for coordinate data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import opensim


class CoordinateProtocol(Protocol):
    """Protocol for OpenSim Coordinate objects."""

    def getName(self) -> str:
        """Get coordinate name."""
        ...

    def getMotionType(self) -> int:
        """Get motion type (0=undefined, 1=rotational, 2=translational)."""
        ...


@dataclass(frozen=True)
class MotionFrame:
    """Single frame of motion data at a specific time.

    Attributes:
        time: Time in seconds
        coordinate_values: Mapping of coordinate name to value
    """

    time: float
    coordinate_values: dict[str, float]


@dataclass(frozen=True)
class MotionValidationResult:
    """Result of validating motion against model.

    Attributes:
        is_valid: True if motion matches model exactly
        missing_coordinates: Coordinates in motion but not in model
        unused_coordinates: Coordinates in model but not in motion
        warnings: Non-fatal issues found
    """

    is_valid: bool
    missing_coordinates: tuple[str, ...]
    unused_coordinates: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class MotionData:
    """Complete motion file data.

    Attributes:
        filepath: Path to the motion file
        num_frames: Total number of frames
        start_time: Time of first frame
        end_time: Time of last frame
        frames: All motion frames
        validation_result: Optional validation results
    """

    filepath: Path
    num_frames: int
    start_time: float
    end_time: float
    frames: tuple[MotionFrame, ...]
    validation_result: MotionValidationResult | None = None


class MotionLoader:
    """Load motion data from OpenSim motion files (.sto, .mot).

    Automatically detects and converts coordinate units (radians/degrees)
    based on model coordinate definitions or data range analysis.
    """

    def _extract_coord_name(self, label: str) -> str | None:
        """Extract the bare coordinate name from a column label.

        OpenSim Moco .sto files use full component paths as column headers,
        e.g. /jointset/ground_pelvis/pelvis_rotation/value. Only /value
        columns represent coordinate positions; /speed and all other suffixes
        are skipped by returning None.

        Old-style .mot files use bare names (e.g. pelvis_rotation) which are
        returned unchanged.

        Args:
            label: Raw column label from the motion file

        Returns:
            Bare coordinate name, or None if the column is not a coordinate position
        """
        if not label.startswith("/"):
            return label

        parts = label.split("/")
        if parts[-1] == "value":
            return parts[-2]

        return None  # /speed, /activation, GRF columns, etc.

    def _detect_coordinate_units(self, model: Any, coord_name: str) -> str | None:
        """Detect if a coordinate is expected to be in radians or degrees.

        Queries the model's coordinate set to find the named coordinate,
        then determines its expected units based on its motion type:
        - Rotational coordinates default to degrees in motion files
        - Translational coordinates use radians/meters (no conversion needed)

        Args:
            model: OpenSim model
            coord_name: Bare coordinate name (not a full path)

        Returns:
            "radians", "degrees", or None if the coordinate is not in the model
        """
        coord_set = model.getCoordinateSet()

        for i in range(coord_set.getSize()):
            coord = coord_set.get(i)

            if coord.getName() == coord_name:
                motion_type = coord.getMotionType()
                return "degrees" if motion_type == 1 else "radians"

        return None

    def _detect_data_units(self, coord_values: list[float]) -> str:
        """Detect if coordinate data is in radians or degrees based on value range.

        Uses heuristic analysis of value ranges:
        - Radians: typically [-π, π] or [-2π, 2π]
        - Degrees: typically [-180, 180] or [-360, 360]

        Args:
            coord_values: List of coordinate values from motion data

        Returns:
            "radians" or "degrees" (defaults to "radians" for empty list)
        """
        if not coord_values:
            return "radians"

        min_val = min(coord_values)
        max_val = max(coord_values)

        if abs(min_val) > 2 * math.pi + 0.1 or abs(max_val) > 2 * math.pi + 0.1:
            return "degrees"

        if min_val >= -math.pi - 0.1 and max_val <= math.pi + 0.1:
            return "radians"

        spread = max_val - min_val

        if abs(spread - 2 * math.pi) < math.pi:
            return "radians"

        if abs(spread - 360) < 90:
            return "degrees"

        max_abs = max(abs(min_val), abs(max_val))
        if max_abs > math.pi:
            return "degrees"

        return "radians"

    def _convert_coordinate_value(
        self, value: float, from_unit: str, to_unit: str
    ) -> float:
        """Convert a coordinate value between units.

        Args:
            value: The value to convert
            from_unit: Source unit ("radians" or "degrees")
            to_unit: Target unit ("radians" or "degrees")

        Returns:
            Converted value

        Raises:
            ValueError: If units are invalid
        """
        if from_unit == to_unit:
            return value

        if from_unit == "degrees" and to_unit == "radians":
            return math.radians(value)

        if from_unit == "radians" and to_unit == "degrees":
            return math.degrees(value)

        raise ValueError(f"Invalid unit conversion: {from_unit} to {to_unit}")

    def load(self, filepath: str | Path, model: Any | None = None) -> MotionData:
        """Load motion data from file with automatic unit conversion.

        Detects if coordinate data is in radians or degrees and converts
        to radians (OpenSim's internal unit) if needed.

        Args:
            filepath: Path to .sto or .mot file
            model: OpenSim model (optional, for more accurate unit detection)

        Returns:
            MotionData with all frames, coordinate values in radians

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If file cannot be parsed
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Motion file not found: {filepath}")

        table = opensim.TimeSeriesTable(str(filepath))

        time_col = table.getIndependentColumn()
        times = list(time_col)

        labels = table.getColumnLabels()

        # Normalise every label to a bare coordinate name.  Labels that are not
        # coordinate-position columns (e.g. /speed, GRF) map to None and are
        # excluded from coord_values entirely.
        label_to_coord: dict[str, str | None] = {
            label: self._extract_coord_name(label) for label in labels
        }

        # Read the authoritative inDegrees flag from the file header.
        # TimeSeriesTable exposes header key-value pairs via getTableMetaDataString.
        # Returns True (degrees), False (radians), or None (header absent).
        try:
            in_degrees: bool | None = (
                table.getTableMetaDataString("inDegrees").strip().lower() == "yes"
            )
        except Exception:
            in_degrees = None

        coord_conversion: dict[str, bool] = {}  # label -> needs_deg_to_rad

        if in_degrees is False:
            # Header explicitly says radians — no conversion needed for any column.
            pass
        elif in_degrees is True and model is not None:
            # Header says degrees; use the model to identify which columns are
            # rotational (only those need deg→rad conversion).
            for label, coord_name in label_to_coord.items():
                if coord_name is None:
                    continue
                unit = self._detect_coordinate_units(model, coord_name)
                coord_conversion[label] = unit == "degrees"
        else:
            # Header absent, or degrees flag set but no model to classify columns.
            # Fall back to per-column data range heuristic.
            coord_data_samples: dict[str, list[float]] = {
                label: [] for label, name in label_to_coord.items() if name is not None
            }
            for i in range(table.getNumRows()):
                row = table.getRowAtIndex(i)
                for j, label in enumerate(labels):
                    if label_to_coord[label] is not None:
                        coord_data_samples[label].append(row[j])

            for label in coord_data_samples:
                detected_unit = self._detect_data_units(coord_data_samples[label])
                coord_conversion[label] = detected_unit == "degrees"

        frames = []
        for i in range(table.getNumRows()):
            row = table.getRowAtIndex(i)
            time = times[i]

            coord_values: dict[str, float] = {}
            for j, label in enumerate(labels):
                coord_name = label_to_coord[label]
                if coord_name is None:
                    continue

                value = row[j]
                if coord_conversion.get(label, False):
                    value = self._convert_coordinate_value(value, "degrees", "radians")

                coord_values[coord_name] = value

            frames.append(
                MotionFrame(
                    time=time,
                    coordinate_values=coord_values,
                )
            )

        return MotionData(
            filepath=filepath,
            num_frames=len(frames),
            start_time=times[0] if times else 0.0,
            end_time=times[-1] if times else 0.0,
            frames=tuple(frames),
        )

    def get_frame(self, motion_data: MotionData, frame_index: int) -> MotionFrame:
        """Get a specific frame from motion data.

        Args:
            motion_data: Loaded MotionData
            frame_index: Index of frame to retrieve

        Returns:
            MotionFrame at the specified index

        Raises:
            IndexError: If frame_index is out of range
        """
        if not (0 <= frame_index < len(motion_data.frames)):
            raise IndexError(
                f"Frame index {frame_index} out of range "
                f"[0, {len(motion_data.frames)})"
            )

        return motion_data.frames[frame_index]

    def get_frame_at_time(self, motion_data: MotionData, time: float) -> MotionFrame:
        """Get frame at or nearest to given time.

        Args:
            motion_data: Loaded MotionData
            time: Time in seconds

        Returns:
            MotionFrame nearest to the specified time

        Raises:
            ValueError: If motion has no frames
        """
        if not motion_data.frames:
            raise ValueError("Motion data has no frames")

        nearest_frame = motion_data.frames[0]
        min_diff = abs(nearest_frame.time - time)

        for frame in motion_data.frames[1:]:
            diff = abs(frame.time - time)
            if diff < min_diff:
                nearest_frame = frame
                min_diff = diff
            elif diff > min_diff:
                break

        return nearest_frame

    def validate_motion(
        self, motion_data: MotionData, model: Any
    ) -> MotionValidationResult:
        """Validate motion coordinates against model.

        Checks that all coordinates in the motion file exist in the model
        and that all model coordinates have values in the motion.

        Args:
            motion_data: Loaded MotionData
            model: OpenSim model

        Returns:
            MotionValidationResult with validation status and details

        Raises:
            ValueError: If motion data has no frames
        """
        if not motion_data.frames:
            raise ValueError("Cannot validate motion with no frames")

        coord_set = model.getCoordinateSet()
        model_coords = set()
        for i in range(coord_set.getSize()):
            coord = coord_set.get(i)
            model_coords.add(coord.getName())

        motion_coords = set(motion_data.frames[0].coordinate_values.keys())

        missing = motion_coords - model_coords
        unused = model_coords - motion_coords

        warnings = []
        if missing:
            warnings.append(
                f"Motion has {len(missing)} coordinate(s) not in model: "
                f"{', '.join(sorted(missing)[:3])}..."
            )
        if unused:
            warnings.append(
                f"Model has {len(unused)} coordinate(s) not in motion: "
                f"{', '.join(sorted(unused)[:3])}..."
            )

        is_valid = len(missing) == 0 and len(unused) == 0

        return MotionValidationResult(
            is_valid=is_valid,
            missing_coordinates=tuple(sorted(missing)),
            unused_coordinates=tuple(sorted(unused)),
            warnings=tuple(warnings),
        )


if __name__ == "__main__":
    """Smoke test for motion loading."""
    model_dir = Path("models/lowerExtremity/Gait2392_Simbody")
    motion_files = list(model_dir.glob("*.sto")) + list(model_dir.glob("*.mot"))

    loader = MotionLoader()

    if motion_files:
        motion_file = motion_files[0]
        print(f"[INFO] Loading motion file: {motion_file.name}")

        motion_data = loader.load(motion_file)
        print(f"[OK] Loaded motion data: {motion_data.num_frames} frames")
        print(
            f"[OK] Time range: {motion_data.start_time:.3f} - "
            f"{motion_data.end_time:.3f} seconds"
        )

        if motion_data.frames:
            first_frame = motion_data.frames[0]
            print(
                f"[OK] First frame coordinates: "
                f"{len(first_frame.coordinate_values)} values"
            )

        print("\n[OK] Motion loading smoke test passed!")
    else:
        print(f"[SKIP] No motion files found in {model_dir}")
