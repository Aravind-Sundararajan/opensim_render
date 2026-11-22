"""Application settings management."""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path


def _get_default_geometry_paths() -> tuple[str, ...]:
    """Get default geometry search paths.

    Returns:
        Tuple of default geometry paths to search
    """
    paths = []

    # Windows OpenSim paths
    if os.name == "nt":
        opensim_root = Path("C:/OpenSim 4.5")
        if opensim_root.exists():
            paths.append(str(opensim_root / "Geometry"))

        program_files = Path("C:/Program Files")
        if program_files.exists():
            for opensim_dir in program_files.glob("OpenSim*"):
                geom_path = opensim_dir / "Geometry"
                if geom_path.exists():
                    paths.append(str(geom_path))

    # Linux/Mac OpenSim paths
    else:
        common_paths = [
            Path("/usr/local/opensim/Geometry"),
            Path("/opt/opensim/Geometry"),
            Path.home() / "opensim" / "geometry",
        ]
        for path in common_paths:
            if path.exists():
                paths.append(str(path))

    return tuple(paths)


@dataclass(frozen=True)
class CameraPreset:
    """Immutable camera view preset.

    Stores camera position, focal point, and up vector for reproducible views.
    """

    name: str
    position: tuple[float, float, float]
    focal_point: tuple[float, float, float]
    up_vector: tuple[float, float, float]
    parallel_projection: bool = False


@dataclass(frozen=True)
class ApplicationSettings:
    """Immutable application settings.

    Contains all configurable application parameters.
    Use the SettingsManager to create modified versions.

    Attributes:
        render_quality: Rendering quality level (0-3)
        background_color: RGB background color as tuple
        show_normals: Whether to show vertex normals
        auto_fit_camera: Auto-fit camera on model load
        recent_files: List of recently opened files (deprecated, use specific lists)
        recent_models: List of recently opened model files (.osim)
        recent_motions: List of recently opened motion files (.sto, .mot)
        recent_scripts: List of recently executed script files (.py)
        camera_presets: Saved camera view presets
        geometry_search_paths: Paths to search for geometry files (.vtp, .obj, .stl)
    """

    render_quality: int = 2  # 0=low, 1=medium, 2=high, 3=ultra
    background_color: tuple[float, float, float] = (0.2, 0.2, 0.2)
    show_normals: bool = False
    auto_fit_camera: bool = True
    recent_files: tuple[str, ...] = field(default_factory=tuple)
    recent_models: tuple[str, ...] = field(default_factory=tuple)
    recent_motions: tuple[str, ...] = field(default_factory=tuple)
    recent_scripts: tuple[str, ...] = field(default_factory=tuple)
    camera_presets: tuple[CameraPreset, ...] = field(default_factory=tuple)
    geometry_search_paths: tuple[str, ...] = field(
        default_factory=_get_default_geometry_paths
    )

    def with_render_quality(self, quality: int) -> "ApplicationSettings":
        """Create settings with different render quality.

        Args:
            quality: Quality level (0-3)

        Returns:
            New ApplicationSettings instance
        """
        if not 0 <= quality <= 3:
            raise ValueError("Render quality must be 0-3")

        return ApplicationSettings(
            render_quality=quality,
            background_color=self.background_color,
            show_normals=self.show_normals,
            auto_fit_camera=self.auto_fit_camera,
            recent_files=self.recent_files,
            recent_models=self.recent_models,
            recent_motions=self.recent_motions,
            recent_scripts=self.recent_scripts,
            camera_presets=self.camera_presets,
            geometry_search_paths=self.geometry_search_paths,
        )

    def with_background_color(
        self, r: float, g: float, b: float
    ) -> "ApplicationSettings":
        """Create settings with different background color.

        Args:
            r: Red component (0.0-1.0)
            g: Green component (0.0-1.0)
            b: Blue component (0.0-1.0)

        Returns:
            New ApplicationSettings instance
        """
        return ApplicationSettings(
            render_quality=self.render_quality,
            background_color=(r, g, b),
            show_normals=self.show_normals,
            auto_fit_camera=self.auto_fit_camera,
            recent_files=self.recent_files,
            recent_models=self.recent_models,
            recent_motions=self.recent_motions,
            recent_scripts=self.recent_scripts,
            camera_presets=self.camera_presets,
            geometry_search_paths=self.geometry_search_paths,
        )

    def with_recent_file(
        self, filepath: str | Path, max_count: int = 10
    ) -> "ApplicationSettings":
        """Create settings with file added to recent list.

        Args:
            filepath: Path to file to add
            max_count: Maximum number of recent files to keep

        Returns:
            New ApplicationSettings instance
        """
        filepath_str = str(filepath)

        recent = list(self.recent_files)
        if filepath_str in recent:
            recent.remove(filepath_str)

        recent.insert(0, filepath_str)

        # Keep only most recent
        recent = recent[:max_count]

        return ApplicationSettings(
            render_quality=self.render_quality,
            background_color=self.background_color,
            show_normals=self.show_normals,
            auto_fit_camera=self.auto_fit_camera,
            recent_files=tuple(recent),
            recent_models=self.recent_models,
            recent_motions=self.recent_motions,
            recent_scripts=self.recent_scripts,
            camera_presets=self.camera_presets,
            geometry_search_paths=self.geometry_search_paths,
        )

    def _update_recent_list(
        self, recent_list: tuple[str, ...], filepath: str | Path, max_count: int = 10
    ) -> tuple[str, ...]:
        """Helper to update a recent files list.

        Args:
            recent_list: Current recent list
            filepath: Path to add
            max_count: Maximum items to keep

        Returns:
            Updated recent list
        """
        filepath_str = str(filepath)
        recent = list(recent_list)

        if filepath_str in recent:
            recent.remove(filepath_str)

        recent.insert(0, filepath_str)

        # Keep only most recent
        return tuple(recent[:max_count])

    def with_recent_model(
        self, filepath: str | Path, max_count: int = 10
    ) -> "ApplicationSettings":
        """Create settings with model file added to recent list.

        Args:
            filepath: Path to model file (.osim)
            max_count: Maximum number of recent models to keep

        Returns:
            New ApplicationSettings instance
        """
        return ApplicationSettings(
            render_quality=self.render_quality,
            background_color=self.background_color,
            show_normals=self.show_normals,
            auto_fit_camera=self.auto_fit_camera,
            recent_files=self.recent_files,
            recent_models=self._update_recent_list(
                self.recent_models, filepath, max_count
            ),
            recent_motions=self.recent_motions,
            recent_scripts=self.recent_scripts,
            camera_presets=self.camera_presets,
            geometry_search_paths=self.geometry_search_paths,
        )

    def with_recent_motion(
        self, filepath: str | Path, max_count: int = 10
    ) -> "ApplicationSettings":
        """Create settings with motion file added to recent list.

        Args:
            filepath: Path to motion file (.sto, .mot)
            max_count: Maximum number of recent motions to keep

        Returns:
            New ApplicationSettings instance
        """
        return ApplicationSettings(
            render_quality=self.render_quality,
            background_color=self.background_color,
            show_normals=self.show_normals,
            auto_fit_camera=self.auto_fit_camera,
            recent_files=self.recent_files,
            recent_models=self.recent_models,
            recent_motions=self._update_recent_list(
                self.recent_motions, filepath, max_count
            ),
            recent_scripts=self.recent_scripts,
            camera_presets=self.camera_presets,
            geometry_search_paths=self.geometry_search_paths,
        )

    def with_recent_script(
        self, filepath: str | Path, max_count: int = 10
    ) -> "ApplicationSettings":
        """Create settings with script file added to recent list.

        Args:
            filepath: Path to script file (.py)
            max_count: Maximum number of recent scripts to keep

        Returns:
            New ApplicationSettings instance
        """
        return ApplicationSettings(
            render_quality=self.render_quality,
            background_color=self.background_color,
            show_normals=self.show_normals,
            auto_fit_camera=self.auto_fit_camera,
            recent_files=self.recent_files,
            recent_models=self.recent_models,
            recent_motions=self.recent_motions,
            recent_scripts=self._update_recent_list(
                self.recent_scripts, filepath, max_count
            ),
            camera_presets=self.camera_presets,
            geometry_search_paths=self.geometry_search_paths,
        )

    def with_camera_preset(self, preset: CameraPreset) -> "ApplicationSettings":
        """Create settings with camera preset added or updated.

        Args:
            preset: Camera preset to add or update

        Returns:
            New ApplicationSettings instance
        """
        presets = list(self.camera_presets)

        presets = [p for p in presets if p.name != preset.name]

        presets.append(preset)

        return ApplicationSettings(
            render_quality=self.render_quality,
            background_color=self.background_color,
            show_normals=self.show_normals,
            auto_fit_camera=self.auto_fit_camera,
            recent_files=self.recent_files,
            camera_presets=tuple(presets),
        )

    def get_camera_preset(self, name: str) -> CameraPreset | None:
        """Get camera preset by name.

        Args:
            name: Preset name

        Returns:
            CameraPreset if found, None otherwise
        """
        for preset in self.camera_presets:
            if preset.name == name:
                return preset
        return None

    def add_geometry_search_path(self, path: str | Path) -> "ApplicationSettings":
        """Create settings with additional geometry search path.

        Args:
            path: Path to add to geometry search paths

        Returns:
            New ApplicationSettings with path added
        """
        path_str = str(path)
        if path_str in self.geometry_search_paths:
            return self

        paths = list(self.geometry_search_paths)
        paths.insert(0, path_str)  # Add to front for priority

        return ApplicationSettings(
            render_quality=self.render_quality,
            background_color=self.background_color,
            show_normals=self.show_normals,
            auto_fit_camera=self.auto_fit_camera,
            recent_files=self.recent_files,
            camera_presets=self.camera_presets,
            geometry_search_paths=tuple(paths),
        )

    def remove_geometry_search_path(self, path: str | Path) -> "ApplicationSettings":
        """Create settings with geometry search path removed.

        Args:
            path: Path to remove from geometry search paths

        Returns:
            New ApplicationSettings with path removed
        """
        path_str = str(path)
        paths = tuple(p for p in self.geometry_search_paths if p != path_str)

        return ApplicationSettings(
            render_quality=self.render_quality,
            background_color=self.background_color,
            show_normals=self.show_normals,
            auto_fit_camera=self.auto_fit_camera,
            recent_files=self.recent_files,
            camera_presets=self.camera_presets,
            geometry_search_paths=paths,
        )

    def get_geometry_search_paths(self) -> list[Path]:
        """Get geometry search paths as Path objects.

        Returns:
            List of valid existing paths
        """
        from pathlib import Path

        valid_paths = []
        for path_str in self.geometry_search_paths:
            path = Path(path_str)
            if path.exists():
                valid_paths.append(path)
        return valid_paths


class SettingsManager:
    """Manager for application settings persistence and access.

    Handles loading, saving, and updating application settings
    from/to a configuration file.
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        """Initialize settings manager.

        Args:
            config_path: Path to configuration file (default: AppData/Roaming/osim_render/settings.json on Windows)
        """
        if config_path is None:
            import os

            if "APPDATA" in os.environ:
                config_dir = Path(os.environ["APPDATA"]) / "osim_render"
            else:
                config_dir = Path.home() / ".osim_render"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "settings.json"

        self.config_path = Path(config_path)
        self._settings = self._load_settings()

    def get_settings(self) -> ApplicationSettings:
        """Get current settings.

        Returns:
            Current ApplicationSettings
        """
        return self._settings

    def update_settings(self, settings: ApplicationSettings) -> None:
        """Update and save settings.

        Args:
            settings: New ApplicationSettings to apply
        """
        self._settings = settings
        self._save_settings()

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self._settings = ApplicationSettings()
        self._save_settings()

    def _load_settings(self) -> ApplicationSettings:
        """Load settings from file.

        Returns:
            ApplicationSettings from file, or defaults if file doesn't exist

        Raises:
            json.JSONDecodeError: If file contains invalid JSON
            ValueError: If settings data is invalid
            KeyError: If required fields are missing
        """
        if not self.config_path.exists():
            return ApplicationSettings()

        with open(self.config_path) as f:
            data = json.load(f)

        # Convert recent_files list to tuple
        if "recent_files" in data:
            data["recent_files"] = tuple(data["recent_files"])

        # Convert background_color list to tuple
        if "background_color" in data:
            data["background_color"] = tuple(data["background_color"])

        # Convert camera_presets
        if "camera_presets" in data:
            presets = []
            for preset_data in data["camera_presets"]:
                preset = CameraPreset(
                    name=preset_data["name"],
                    position=tuple(preset_data["position"]),
                    focal_point=tuple(preset_data["focal_point"]),
                    up_vector=tuple(preset_data["up_vector"]),
                    parallel_projection=preset_data.get("parallel_projection", False),
                )
                presets.append(preset)
            data["camera_presets"] = tuple(presets)

        # Convert geometry_search_paths list to tuple
        if "geometry_search_paths" in data:
            data["geometry_search_paths"] = tuple(data["geometry_search_paths"])
        else:
            data["geometry_search_paths"] = _get_default_geometry_paths()

        return ApplicationSettings(**data)

    def _save_settings(self) -> None:
        """Save settings to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert dataclass to dict, handling tuples
        data = asdict(self._settings)
        data["background_color"] = list(data["background_color"])
        data["recent_files"] = list(data["recent_files"])
        data["geometry_search_paths"] = list(data["geometry_search_paths"])

        # Convert camera presets
        data["camera_presets"] = [
            {
                "name": preset.name,
                "position": list(preset.position),
                "focal_point": list(preset.focal_point),
                "up_vector": list(preset.up_vector),
                "parallel_projection": preset.parallel_projection,
            }
            for preset in self._settings.camera_presets
        ]

        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    """Smoke test for settings manager."""
    import tempfile

    print("SettingsManager smoke test")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "settings.json"

        manager = SettingsManager(config_path)
        print("[OK] Created SettingsManager")

        settings = manager.get_settings()
        assert settings.render_quality == 2
        print("[OK] Loaded default settings")

        new_settings = settings.with_render_quality(3)
        manager.update_settings(new_settings)
        print("[OK] Updated and saved settings")

        manager2 = SettingsManager(config_path)
        assert manager2.get_settings().render_quality == 3
        print("[OK] Persisted settings loaded correctly")

        # Test recent files
        settings = manager2.get_settings()
        settings = settings.with_recent_file("model1.osim")
        settings = settings.with_recent_file("model2.osim")
        assert settings.recent_files == ("model2.osim", "model1.osim")
        print("[OK] Recent files tracking works")

        # Test camera presets
        settings = manager2.get_settings()
        front_preset = CameraPreset(
            name="Front View",
            position=(0, 0, 1),
            focal_point=(0, 0, 0),
            up_vector=(0, 1, 0),
            parallel_projection=False,
        )
        settings = settings.with_camera_preset(front_preset)
        manager2.update_settings(settings)
        print("[OK] Added camera preset")

        manager3 = SettingsManager(config_path)
        loaded_preset = manager3.get_settings().get_camera_preset("Front View")
        assert loaded_preset is not None
        assert loaded_preset.position == (0, 0, 1)
        print("[OK] Camera preset saved and loaded correctly")

        # Test geometry search paths
        settings = manager3.get_settings()
        initial_paths = len(settings.geometry_search_paths)
        settings = settings.add_geometry_search_path("/test/geometry")
        assert len(settings.geometry_search_paths) == initial_paths + 1
        print("[OK] Geometry search path added")

        settings = settings.remove_geometry_search_path("/test/geometry")
        assert len(settings.geometry_search_paths) == initial_paths
        print("[OK] Geometry search path removed")

        # Verify paths persist
        manager3.update_settings(settings)
        manager4 = SettingsManager(config_path)
        assert len(manager4.get_settings().geometry_search_paths) == initial_paths
        print("[OK] Geometry paths persisted correctly")

    print("\n[OK] All smoke tests passed!")
