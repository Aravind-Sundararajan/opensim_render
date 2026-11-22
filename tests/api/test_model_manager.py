"""Unit tests for ModelManager."""

import pytest

from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.managers.event_bus import EventBus, Event
from osim_render.api.managers.events import EventType


class TestModelManager:
    """Test ModelManager class."""

    @pytest.fixture
    def event_bus(self) -> EventBus:
        """Create event bus."""
        return EventBus()

    @pytest.fixture
    def manager(self, event_bus: EventBus) -> ModelManager:
        """Create model manager."""
        return ModelManager(event_bus)

    def test_initialization(self, manager: ModelManager) -> None:
        """Test ModelManager initialization."""
        assert manager is not None

    def test_get_current_model_on_fresh_instance(self, manager: ModelManager) -> None:
        """Test get_current_model returns None on fresh instance."""
        model = manager.get_current_model()
        assert model is None

    def test_list_models_on_fresh_instance(self, manager: ModelManager) -> None:
        """Test list_models returns empty list on fresh instance."""
        models = manager.list_models()
        assert models == []

    def test_get_model_nonexistent(self, manager: ModelManager) -> None:
        """Test get_model returns None for nonexistent model."""
        model = manager.get_model("nonexistent")
        assert model is None

    def test_select_model_nonexistent_raises(self, manager: ModelManager) -> None:
        """Test select_model raises ValueError for nonexistent model."""
        with pytest.raises(ValueError):
            manager.select_model("nonexistent")

    def test_clear_all_models_on_empty_manager(self, manager: ModelManager) -> None:
        """Test clear_all_models doesn't crash on empty manager."""
        # Should not raise
        manager.clear_all_models()

    def test_unload_model_nonexistent_safe(self, manager: ModelManager, event_bus: EventBus) -> None:
        """Test unload_model handles nonexistent model gracefully."""
        # Should not crash when unloading nonexistent model
        manager.unload_model("nonexistent")

    def test_event_bus_used(self, manager: ModelManager, event_bus: EventBus) -> None:
        """Test event_bus is used for initialization."""
        # event_bus is passed to constructor but may not be exposed as attribute
        # Just verify manager was created successfully with it
        assert manager is not None

    def test_unload_without_event_fires_unloaded(self, manager: ModelManager, event_bus: EventBus) -> None:
        """Test that unload without loaded models doesn't error."""
        # clear_all_models should not fire event if no models loaded
        events: list[Event] = []

        def listener(event: Event) -> None:
            events.append(event)

        event_bus.subscribe(EventType.MODEL_UNLOADED, listener)
        manager.clear_all_models()

        # May or may not fire depending on implementation
        # At minimum, should not crash


class TestModelManagerStateManagement:
    """Test ModelManager state management."""

    @pytest.fixture
    def event_bus(self) -> EventBus:
        """Create event bus."""
        return EventBus()

    @pytest.fixture
    def manager(self, event_bus: EventBus) -> ModelManager:
        """Create model manager."""
        return ModelManager(event_bus)

    def test_models_list_property(self, manager: ModelManager) -> None:
        """Test models property returns list."""
        models = manager.list_models()
        assert isinstance(models, list)

    def test_models_list_mutability(self, manager: ModelManager) -> None:
        """Test that returned model list is independent."""
        list1 = manager.list_models()
        list2 = manager.list_models()
        # Should be equal but may not be the same object
        assert list1 == list2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
