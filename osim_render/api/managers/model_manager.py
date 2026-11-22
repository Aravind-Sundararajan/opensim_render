"""Application model state management."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from osim_render.api.managers.event_bus import EventBus, Event
from osim_render.api.managers.events import EventType
from osim_render.api.loaders.opensim_model_loader import (
    OpenSimModelLoader,
    OpenSimModelStructure,
)
from osim_render.api.logging import get_logger_for
from osim_render.api.posing.drag_marker_rig import DragMarkerRig

logger = get_logger_for(__name__)


@dataclass(frozen=True)
class LoadedModel:
    """Immutable loaded model information.

    Tracks metadata about a loaded OpenSim model with full structure.

    Attributes:
        filepath: Path to the model file
        name: Human-readable model name
        structure: OpenSimModelStructure with bodies, joints, coordinates
        opensim_model: The actual OpenSim Model instance
        metadata: Additional model metadata
    """

    filepath: Path
    name: str
    structure: OpenSimModelStructure
    opensim_model: Any  # opensim.Model instance
    metadata: dict[str, Any]


class ModelManager:
    """Manages loaded OpenSim models and current selection.

    Loads models using OpenSim 4.5+ Python API.
    Emits events when models are loaded, unloaded, or selected.
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Initialize model manager.

        Args:
            event_bus: Event bus for publishing model events
        """
        self._event_bus = event_bus
        self._loader = OpenSimModelLoader()
        self._loaded_models: dict[str, LoadedModel] = {}
        self._current_model: LoadedModel | None = None
        self._opensim_model: Any | None = None  # Current opensim.Model instance
        self._opensim_state: Any | None = None  # Current working state
        self._drag_rig: DragMarkerRig | None = None  # Drag handles for IK posing

    def load_model(self, filepath: str | Path, name: str | None = None) -> None:
        """Load a new OpenSim model using OpenSim Python API.

        Args:
            filepath: Path to .osim model file
            name: Optional human-readable name (default: filename)

        Raises:
            FileNotFoundError: If file does not exist
            RuntimeError: If model loading fails
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")

        if name is None:
            name = filepath.stem

        # Emit loading event
        self._event_bus.publish_event(
            EventType.MODEL_LOADING_STARTED,
            data={"filepath": str(filepath), "name": name},
        )

        logger.info(f"Loading model: {filepath}")
        structure = self._loader.load(filepath)
        logger.info(f"Model loaded: {structure.name}")
        logger.info(
            f"Bodies: {len(structure.bodies)}, Joints: {len(structure.joints)}, Coordinates: {len(structure.coordinates)}"
        )

        import opensim

        opensim_model = opensim.Model(str(filepath))

        # Drag handles must exist before initSystem(); adding markers later
        # would rebuild the multibody system mid-interaction.
        opensim_model.initSystem()
        self._drag_rig = DragMarkerRig.install(opensim_model)

        model = LoadedModel(
            filepath=filepath,
            name=name,
            structure=structure,
            opensim_model=opensim_model,
            metadata={
                "loaded_at": __import__("datetime").datetime.now().isoformat(),
                "body_count": len(structure.bodies),
                "joint_count": len(structure.joints),
                "coordinate_count": len(structure.coordinates),
            },
        )

        self._loaded_models[name] = model

        self._opensim_model = opensim_model
        self._opensim_state = opensim_model.initSystem()

        # Emit loaded event
        self._event_bus.publish_event(
            EventType.MODEL_LOADED,
            data={"filepath": str(filepath), "name": name, "model": model},
        )

        # Auto-select first loaded model
        if self._current_model is None:
            self.select_model(name)

    def unload_model(self, name: str) -> None:
        """Unload a previously loaded model.

        Args:
            name: Name of model to unload
        """
        if name not in self._loaded_models:
            return

        del self._loaded_models[name]

        self._event_bus.publish_event(
            EventType.MODEL_UNLOADED,
            data={"name": name},
        )

        if self._current_model and self._current_model.name == name:
            self._current_model = None
            self._opensim_model = None
            self._opensim_state = None

    def select_model(self, name: str) -> None:
        """Select a loaded model as current.

        Args:
            name: Name of model to select

        Raises:
            ValueError: If model is not loaded
        """
        if name not in self._loaded_models:
            raise ValueError(f"Model not loaded: {name}")

        self._current_model = self._loaded_models[name]

        self._event_bus.publish_event(
            EventType.MODEL_SELECTION_CHANGED,
            data={"name": name, "model": self._current_model},
        )

    def get_current_model(self) -> LoadedModel | None:
        """Get the currently selected model.

        Returns:
            Current LoadedModel or None if no model selected
        """
        return self._current_model

    def get_model(self, name: str) -> LoadedModel | None:
        """Get a model by name.

        Args:
            name: Name of model to retrieve

        Returns:
            LoadedModel or None if not found
        """
        return self._loaded_models.get(name)

    def get_opensim_model(self) -> Any | None:
        """Get the current OpenSim Model instance.

        Returns:
            opensim.Model instance or None if no model loaded
        """
        return self._opensim_model

    def get_opensim_state(self) -> Any | None:
        """Get the current working state.

        Returns:
            opensim.State instance or None if no model loaded
        """
        return self._opensim_state

    def get_drag_rig(self) -> DragMarkerRig | None:
        """Get the drag marker rig for interactive IK posing.

        Returns:
            DragMarkerRig for the current model, or None if no model loaded
        """
        return self._drag_rig

    def list_models(self) -> list[LoadedModel]:
        """Get list of all loaded models.

        Returns:
            List of LoadedModel objects
        """
        return list(self._loaded_models.values())

    def clear_all_models(self) -> None:
        """Unload all models."""
        for name in list(self._loaded_models.keys()):
            self.unload_model(name)


if __name__ == "__main__":
    """Smoke test for model manager."""
    from pathlib import Path

    print("ModelManager smoke test")

    bus = EventBus()
    manager = ModelManager(bus)

    events_received = []

    def test_listener(event: Event) -> None:
        """Record events."""
        events_received.append(event)

    bus.subscribe(EventType.MODEL_LOADED, test_listener)
    bus.subscribe(EventType.MODEL_SELECTION_CHANGED, test_listener)

    # Try to load a real model
    model_path = Path("models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim")

    if model_path.exists():
        print(f"[INFO] Loading real model: {model_path}")
        manager.load_model(model_path)
        assert len(events_received) >= 1
        print("[OK] Model loaded and events fired")

        # Verify current model
        current = manager.get_current_model()
        assert current is not None
        print(f"[OK] Current model: {current.name}")
        print(f"[OK] Bodies: {len(current.structure.bodies)}")
        print(f"[OK] Joints: {len(current.structure.joints)}")
        print(f"[OK] Coordinates: {len(current.structure.coordinates)}")

        # List models
        models = manager.list_models()
        assert len(models) == 1
        print("[OK] Model listing works")

        # Unload model
        manager.unload_model(current.name)
        assert manager.get_current_model() is None
        print("[OK] Model unloaded")

        print("\n[OK] All smoke tests passed!")
    else:
        print(f"[SKIP] Model not found: {model_path}")
        print("Run from project root directory to use real models")
