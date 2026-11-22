"""Load ground reaction force data for visualization.

GRF reaches OpenSim two ways: an ExternalLoads XML naming a data file and the
column identifiers within it, or a bare .mot/.sto whose columns follow one of
several naming conventions. Both are read here as plain data.

Deliberately independent of the model. OpenSim's own ExternalForce only yields
values once connected to a model, which would mean rebuilding the multibody
system and actually applying the loads — neither of which a visualizer wants.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import opensim

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)

GROUND_FRAME = "ground"

# Every GRF convention seen in the wild ends its force columns in v{x,y,z} and
# its point columns in p{x,y,z}: "ground_force_vx", "ground_force_r_vx",
# "R_ground_force_vx", "1_ground_force_vx". Matching the suffix covers them all.
_FORCE_COLUMN = re.compile(r"^(?P<prefix>.*)v(?P<axis>[xyz])$")

_AXES = ("x", "y", "z")


def _triplet(prefix: str) -> tuple[str, str, str]:
    """Build the x/y/z column names for an identifier prefix.

    Args:
        prefix: Column prefix, e.g. "ground_force_v"

    Returns:
        The three column names
    """
    return (f"{prefix}x", f"{prefix}y", f"{prefix}z")


@dataclass(frozen=True)
class GroundReactionSample:
    """One ground reaction reading, in ground coordinates."""

    point: tuple[float, float, float]
    force: tuple[float, float, float]
    torque: Optional[tuple[float, float, float]] = None

    @property
    def magnitude(self) -> float:
        """Magnitude of the force in newtons."""
        total = sum(component * component for component in self.force)
        return float(total**0.5)


@dataclass(frozen=True)
class GroundReactionSource:
    """One force plate or limb within a ground reaction data file."""

    name: str
    force_columns: tuple[str, str, str]
    point_columns: tuple[str, str, str]
    torque_columns: Optional[tuple[str, str, str]] = None
    applied_to_body: Optional[str] = None
    point_expressed_in: str = GROUND_FRAME
    force_expressed_in: str = GROUND_FRAME

    @property
    def is_in_ground(self) -> bool:
        """Whether both force and point are already in ground coordinates."""
        return (
            self.point_expressed_in == GROUND_FRAME
            and self.force_expressed_in == GROUND_FRAME
        )


@dataclass(frozen=True)
class GroundReactionData:
    """Ground reaction traces for one trial."""

    path: Path
    sources: tuple[GroundReactionSource, ...]
    times: tuple[float, ...]
    columns: dict[str, tuple[float, ...]]

    @property
    def start_time(self) -> float:
        """First sample time in the file."""
        return self.times[0]

    @property
    def end_time(self) -> float:
        """Last sample time in the file."""
        return self.times[-1]

    def covers(self, time: float) -> bool:
        """Whether the file has data at a time.

        Args:
            time: Time in seconds

        Returns:
            True if the time falls inside the recorded range
        """
        return self.start_time <= time <= self.end_time

    def sample(
        self, source: GroundReactionSource, time: float
    ) -> Optional[GroundReactionSample]:
        """Read one source at a time, interpolating between rows.

        GRF is typically recorded an order of magnitude faster than motion is
        rendered, so interpolating keeps the arrow smooth instead of stepping
        between samples.

        Args:
            source: Which plate or limb to read
            time: Time in seconds

        Returns:
            The reading, or None when the time is outside the recorded range
        """
        if not self.covers(time):
            return None

        lower, upper, blend = self._bracket(time)
        return GroundReactionSample(
            point=self._read(source.point_columns, lower, upper, blend),
            force=self._read(source.force_columns, lower, upper, blend),
            torque=(
                self._read(source.torque_columns, lower, upper, blend)
                if source.torque_columns
                else None
            ),
        )

    def _bracket(self, time: float) -> tuple[int, int, float]:
        """Find the rows either side of a time and the blend between them.

        Args:
            time: Time in seconds, known to be in range

        Returns:
            Tuple of (lower row, upper row, blend factor in 0..1)
        """
        index = bisect_left(self.times, time)

        if index == 0:
            return (0, 0, 0.0)

        lower, upper = index - 1, min(index, len(self.times) - 1)
        span = self.times[upper] - self.times[lower]

        if span <= 0.0:
            return (lower, upper, 0.0)

        return (lower, upper, (time - self.times[lower]) / span)

    def _read(
        self, names: tuple[str, str, str], lower: int, upper: int, blend: float
    ) -> tuple[float, float, float]:
        """Interpolate a three-column triplet between two rows.

        Args:
            names: Column names for x, y and z
            lower: Lower row index
            upper: Upper row index
            blend: Blend factor between the rows

        Returns:
            The interpolated vector
        """
        values = []
        for name in names:
            column = self.columns[name]
            values.append(column[lower] + (column[upper] - column[lower]) * blend)

        return (values[0], values[1], values[2])


def load_ground_reactions(path: str | Path) -> GroundReactionData:
    """Load ground reaction data from an ExternalLoads XML or a data file.

    Args:
        path: Path to a .xml ExternalLoads file, or a .mot/.sto data file

    Returns:
        The loaded traces

    Raises:
        FileNotFoundError: If the path does not exist
        ValueError: If no ground reaction sources can be identified
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Ground reaction file not found: {path}")

    if path.suffix.lower() == ".xml":
        return load_external_loads(path)

    return load_data_file(path)


def load_external_loads(xml_path: str | Path) -> GroundReactionData:
    """Load GRF described by an ExternalLoads XML.

    The XML names the data file and the column identifiers, so no guessing is
    needed. Its datafile path is resolved relative to the XML.

    Args:
        xml_path: Path to the ExternalLoads XML

    Returns:
        The loaded traces

    Raises:
        FileNotFoundError: If the XML or its data file is missing
        ValueError: If the XML declares no usable external forces
    """
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(f"ExternalLoads file not found: {xml_path}")

    loads = opensim.ExternalLoads(str(xml_path), True)
    data_path = _resolve_data_file(xml_path, loads.getDataFileName())
    times, columns = _read_table(data_path)

    sources = tuple(
        source
        for source in (
            _source_from_external_force(loads.get(index), columns)
            for index in range(loads.getSize())
        )
        if source is not None
    )

    if not sources:
        raise ValueError(f"No usable external forces declared in {xml_path}")

    logger.info(f"Loaded {len(sources)} ground reaction sources from {xml_path.name}")
    return GroundReactionData(
        path=data_path, sources=sources, times=times, columns=columns
    )


def load_data_file(data_path: str | Path) -> GroundReactionData:
    """Load GRF straight from a .mot/.sto, detecting columns by convention.

    Args:
        data_path: Path to the data file

    Returns:
        The loaded traces

    Raises:
        FileNotFoundError: If the file is missing
        ValueError: If no force/point column pairs can be found
    """
    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Ground reaction file not found: {data_path}")

    times, columns = _read_table(data_path)
    sources = detect_sources(tuple(columns))

    if not sources:
        raise ValueError(
            f"No ground reaction columns found in {data_path.name}. Expected "
            "force columns ending in vx/vy/vz with matching px/py/pz."
        )

    logger.info(f"Detected {len(sources)} ground reaction sources in {data_path.name}")
    return GroundReactionData(
        path=data_path, sources=sources, times=times, columns=columns
    )


def detect_sources(labels: tuple[str, ...]) -> tuple[GroundReactionSource, ...]:
    """Find force/point column groups by their naming convention.

    Args:
        labels: Column labels from the data file

    Returns:
        One source per prefix that has a full force and point triplet
    """
    available = set(labels)
    prefixes = _force_prefixes(labels)

    sources = []
    for prefix in prefixes:
        force = _triplet(f"{prefix}v")
        point = _triplet(f"{prefix}p")

        if not available.issuperset(force) or not available.issuperset(point):
            continue

        sources.append(
            GroundReactionSource(
                name=prefix.rstrip("_") or "ground_force",
                force_columns=force,
                point_columns=point,
                torque_columns=_torque_columns(prefix, available),
            )
        )

    return tuple(sources)


def _force_prefixes(labels: tuple[str, ...]) -> list[str]:
    """Collect distinct prefixes of force columns, in file order.

    Args:
        labels: Column labels from the data file

    Returns:
        Prefixes such as "ground_force_" or "1_ground_force_"
    """
    prefixes: list[str] = []
    for label in labels:
        match = _FORCE_COLUMN.match(label)
        if match is None:
            continue

        prefix = match.group("prefix")
        if prefix not in prefixes:
            prefixes.append(prefix)

    return prefixes


def _torque_columns(
    prefix: str, available: set[str]
) -> Optional[tuple[str, str, str]]:
    """Find the torque triplet matching a force prefix, if present.

    Force columns read "<prefix>vx" while torque columns replace the "force"
    stem with "torque", e.g. "ground_force_" -> "ground_torque_".

    Args:
        prefix: Force column prefix
        available: All column labels in the file

    Returns:
        The torque columns, or None when absent
    """
    columns = _triplet(prefix.replace("force", "torque"))

    return columns if available.issuperset(columns) else None


def _source_from_external_force(
    force: Any, columns: dict[str, tuple[float, ...]]
) -> Optional[GroundReactionSource]:
    """Build a source from one ExternalForce declaration.

    Args:
        force: OpenSim ExternalForce read from the XML
        columns: Available data columns

    Returns:
        The source, or None if its columns are absent from the data file
    """
    force_columns = _triplet(force.getForceIdentifier())
    point_columns = _triplet(force.getPointIdentifier())

    missing = [name for name in force_columns + point_columns if name not in columns]
    if missing:
        logger.warning(
            f"External force {force.getName()} references missing columns: {missing}"
        )
        return None

    declared_torque = _triplet(force.getTorqueIdentifier())
    torque_columns = (
        declared_torque
        if all(name in columns for name in declared_torque)
        else None
    )

    return GroundReactionSource(
        name=force.getName(),
        force_columns=force_columns,
        point_columns=point_columns,
        torque_columns=torque_columns,
        applied_to_body=force.getAppliedToBodyName(),
        point_expressed_in=force.getPointExpressedInBodyName() or GROUND_FRAME,
        force_expressed_in=force.getForceExpressedInBodyName() or GROUND_FRAME,
    )


def _resolve_data_file(xml_path: Path, declared: str) -> Path:
    """Resolve an ExternalLoads datafile path, which is relative to the XML.

    Args:
        xml_path: Path to the ExternalLoads XML
        declared: The datafile entry from the XML

    Returns:
        The resolved data file path

    Raises:
        FileNotFoundError: If the declared file cannot be found
    """
    if not declared:
        raise FileNotFoundError(f"{xml_path.name} declares no datafile")

    candidate = Path(declared.replace("\\", "/"))
    if candidate.is_absolute() and candidate.exists():
        return candidate

    resolved = (xml_path.parent / candidate).resolve()
    if resolved.exists():
        return resolved

    raise FileNotFoundError(
        f"{xml_path.name} declares datafile {declared}, not found at {resolved}"
    )


def _read_table(
    data_path: Path,
) -> tuple[tuple[float, ...], dict[str, tuple[float, ...]]]:
    """Read a .mot/.sto into times and columns.

    Args:
        data_path: Path to the data file

    Returns:
        Tuple of (times, column name -> values)
    """
    table = opensim.TimeSeriesTable(str(data_path))
    labels = list(table.getColumnLabels())

    columns = {
        label: tuple(table.getDependentColumn(label)[row] for row in range(table.getNumRows()))
        for label in labels
    }

    return (tuple(table.getIndependentColumn()), columns)


if __name__ == "__main__":
    """Smoke test for the ground reaction loader."""
    import sys

    opensim.Model.setDebugLevel(-1)

    xml = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "resources/Models/Gait2354_Simbody/subject01_walk1_grf.xml"
    )
    print(f"grf_loader smoke test on {xml}")

    data = load_ground_reactions(xml)
    print(f"[OK] Data file {data.path.name}, t=[{data.start_time:.3f}, {data.end_time:.3f}]")
    print(f"[OK] {len(data.sources)} sources: {[s.name for s in data.sources]}")

    for source in data.sources:
        print(f"    {source.name}: body={source.applied_to_body} "
              f"force={source.force_columns[0]}.. torque={'yes' if source.torque_columns else 'no'}")

    print("\nSampling the right foot through the trial...")
    right = data.sources[0]
    for time in (0.0, 0.25, 0.5, 0.9, 1.2):
        sample = data.sample(right, time)
        assert sample is not None
        print(f"   t={time:.2f}  |F|={sample.magnitude:8.1f} N  "
              f"COP=({sample.point[0]:+.3f},{sample.point[1]:+.3f},{sample.point[2]:+.3f})")

    print("\nChecking interpolation lands between samples...")
    exact = data.sample(right, data.times[10])
    between = data.sample(right, (data.times[10] + data.times[11]) / 2.0)
    after = data.sample(right, data.times[11])
    assert exact is not None and between is not None and after is not None
    low, high = sorted((exact.force[1], after.force[1]))
    print(f"   Fy {exact.force[1]:.2f} -> {between.force[1]:.2f} -> {after.force[1]:.2f}")
    assert low <= between.force[1] <= high

    print("\nChecking out-of-range returns nothing...")
    assert data.sample(right, data.end_time + 1.0) is None
    assert data.sample(right, data.start_time - 1.0) is None
    print("   [OK] outside the recorded range yields None")

    print("\nChecking bare-file detection agrees with the XML...")
    bare = load_data_file(data.path)
    print(f"   detected {[s.name for s in bare.sources]}")
    assert len(bare.sources) == len(data.sources)

    print("\n[OK] Smoke test passed!")
