"""Immutable state for coordinate slider panel."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CoordinateInfo:
    """Immutable information about a model coordinate."""

    name: str
    min_value: float
    max_value: float
    default_value: float


@dataclass(frozen=True)
class CoordinatePanelState:
    """Immutable state of coordinate slider panel."""

    model_loaded: bool
    model_path: Path | None
    coordinates: tuple[CoordinateInfo, ...] = ()
    current_values: dict[str, float] = field(default_factory=dict)
