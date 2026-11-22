"""Resolve local asset paths for development tooling."""

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from dotenv import load_dotenv


MODELS_DIR_ENV_VAR: Final[str] = "OSIM_RENDER_MODELS_DIR"
OPENSIM_GEOMETRY_DIR_ENV_VAR: Final[str] = "OSIM_RENDER_OPENSIM_GEOMETRY_DIR"


def get_project_root() -> Path:
    """Return the repository root for the current workspace."""
    return Path(__file__).resolve().parents[2]


def load_tooling_environment() -> None:
    """Load local dotenv files used by development tooling."""
    project_root = get_project_root()
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / ".env.local", override=True)


def get_models_root() -> Path:
    """Return the configured local models root directory."""
    load_tooling_environment()
    configured_root = os.environ.get(MODELS_DIR_ENV_VAR)
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return (get_project_root() / "models").resolve()


def get_opensim_geometry_root() -> Path:
    """Return the configured OpenSim shared geometry directory."""
    load_tooling_environment()
    configured_root = os.environ.get(OPENSIM_GEOMETRY_DIR_ENV_VAR)
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return (get_project_root() / "vendor" / "opensim-gui" / "opensim-models" / "Geometry").resolve()


def resolve_tool_path(path_value: str | Path) -> Path:
    """Resolve a tool path against either the models root or repository root."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "models":
        return get_models_root().joinpath(*path.parts[1:]).resolve()
    return (get_project_root() / path).resolve()


def resolve_tool_paths(path_values: Iterable[str | Path]) -> tuple[Path, ...]:
    """Resolve a collection of tool paths to absolute paths."""
    return tuple(resolve_tool_path(path_value) for path_value in path_values)


if __name__ == "__main__":
    print(f"project_root={get_project_root()}")
    print(f"models_root={get_models_root()}")
    print(f"opensim_geometry_root={get_opensim_geometry_root()}")
