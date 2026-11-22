"""Unit tests for EventBus and event system."""

import pytest

from osim_render.api.managers.event_bus import (
    EventBus,
    Event,
    event_handler,
    auto_subscribe_all_events,
    auto_unsubscribe_all_events,
)
from osim_render.api.managers.events import EventType


class TestEventType:
    """Test EventType enum."""

    def test_event_types_defined(self) -> None:
        """Test that common event types are defined."""
        assert hasattr(EventType, "MODEL_LOADED")
        assert hasattr(EventType, "MODEL_UNLOADED")


class TestEvent:
    """Test Event class."""

    def test_event_creation(self) -> None:
        """Test creating an event."""
        event = Event(event_type=EventType.MODEL_LOADED, data={"model": "test"})
        assert event.event_type == EventType.MODEL_LOADED
        assert event.data == {"model": "test"}

    def test_event_with_none_data(self) -> None:
        """Test creating event with None data."""
        event = Event(event_type=EventType.MODEL_LOADED, data=None)
        assert event.data is None


class TestEventBus:
    """Test suite for EventBus."""

    @pytest.fixture
    def bus(self) -> EventBus:
        """Create a fresh EventBus for each test."""
        return EventBus()

    def test_subscribe_and_publish(self, bus: EventBus) -> None:
        """Test basic subscribe and publish."""
        received: list[Event] = []

        def listener(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.MODEL_LOADED, listener)
        bus.publish_event(EventType.MODEL_LOADED, data={"name": "test"})

        assert len(received) == 1
        assert received[0].event_type == EventType.MODEL_LOADED
        assert received[0].data == {"name": "test"}

    def test_unsubscribe_stops_delivery(self, bus: EventBus) -> None:
        """Test that unsubscribe stops event delivery."""
        received: list[Event] = []

        def listener(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.MODEL_LOADED, listener)
        bus.unsubscribe(EventType.MODEL_LOADED, listener)
        bus.publish_event(EventType.MODEL_LOADED)

        assert len(received) == 0

    def test_multiple_listeners_same_event(self, bus: EventBus) -> None:
        """Test multiple listeners on same event type."""
        received1: list[Event] = []
        received2: list[Event] = []

        def listener1(event: Event) -> None:
            received1.append(event)

        def listener2(event: Event) -> None:
            received2.append(event)

        bus.subscribe(EventType.MODEL_LOADED, listener1)
        bus.subscribe(EventType.MODEL_LOADED, listener2)
        bus.publish_event(EventType.MODEL_LOADED, data={"id": 1})

        assert len(received1) == 1
        assert len(received2) == 1

    def test_listener_not_called_for_other_events(self, bus: EventBus) -> None:
        """Test listener not called for different event types."""
        received: list[Event] = []

        def listener(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.MODEL_LOADED, listener)
        bus.publish_event(EventType.MODEL_UNLOADED)

        assert len(received) == 0

    def test_publish_event_convenience(self, bus: EventBus) -> None:
        """Test publish_event convenience method."""
        received: list[Event] = []

        def listener(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.MODEL_LOADED, listener)
        bus.publish_event(EventType.MODEL_LOADED, data={"test": True})

        assert len(received) == 1
        assert received[0].data == {"test": True}

    def test_clear_removes_all_subscribers(self, bus: EventBus) -> None:
        """Test clear removes all subscribers."""
        received1: list[Event] = []
        received2: list[Event] = []

        def listener1(event: Event) -> None:
            received1.append(event)

        def listener2(event: Event) -> None:
            received2.append(event)

        bus.subscribe(EventType.MODEL_LOADED, listener1)
        bus.subscribe(EventType.MODEL_UNLOADED, listener2)
        bus.clear()
        bus.publish_event(EventType.MODEL_LOADED)
        bus.publish_event(EventType.MODEL_UNLOADED)

        assert len(received1) == 0
        assert len(received2) == 0

    def test_event_handler_decorator_registers_method(self) -> None:
        """Test event_handler decorator registers method."""
        events_seen: list[Event] = []

        class Handler:
            @event_handler(EventType.MODEL_LOADED)
            def on_model_loaded(self, event: Event) -> None:
                events_seen.append(event)

        handler = Handler()
        bus = EventBus()
        bus.subscribe(EventType.MODEL_LOADED, handler.on_model_loaded)
        bus.publish_event(EventType.MODEL_LOADED, data={"model": "test"})

        assert len(events_seen) == 1

    def test_auto_subscribe_all_events(self) -> None:
        """Test auto_subscribe_all_events wires all decorated methods."""
        events: list[tuple[str, Event]] = []

        class Handler:
            @event_handler(EventType.MODEL_LOADED)
            def on_model_loaded(self, event: Event) -> None:
                events.append(("loaded", event))

            @event_handler(EventType.MODEL_UNLOADED)
            def on_model_unloaded(self, event: Event) -> None:
                events.append(("unloaded", event))

        handler = Handler()
        bus = EventBus()
        auto_subscribe_all_events(handler, bus)
        bus.publish_event(EventType.MODEL_LOADED, data={"id": 1})
        bus.publish_event(EventType.MODEL_UNLOADED, data={"id": 1})

        assert len(events) == 2
        assert events[0][0] == "loaded"
        assert events[1][0] == "unloaded"

    def test_auto_unsubscribe_all_events(self) -> None:
        """Test auto_unsubscribe_all_events unwires all decorated methods."""
        events: list[Event] = []

        class Handler:
            @event_handler(EventType.MODEL_LOADED)
            def on_model_loaded(self, event: Event) -> None:
                events.append(event)

        handler = Handler()
        bus = EventBus()
        auto_subscribe_all_events(handler, bus)
        auto_unsubscribe_all_events(handler, bus)
        bus.publish_event(EventType.MODEL_LOADED)

        assert len(events) == 0

    def test_subscribe_with_publish_directly(self, bus: EventBus) -> None:
        """Test subscribe/publish using publish directly."""
        received: list[Event] = []

        def listener(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.MODEL_LOADED, listener)
        event = Event(event_type=EventType.MODEL_LOADED, data={"test": True})
        bus.publish(event)

        assert len(received) == 1
        assert received[0].data == {"test": True}

    def test_multiple_subscriptions_from_same_listener(self, bus: EventBus) -> None:
        """Test same listener subscribed to multiple event types."""
        events: list[EventType] = []

        def listener(event: Event) -> None:
            events.append(event.event_type)

        bus.subscribe(EventType.MODEL_LOADED, listener)
        bus.subscribe(EventType.MODEL_UNLOADED, listener)
        bus.publish_event(EventType.MODEL_LOADED)
        bus.publish_event(EventType.MODEL_UNLOADED)

        assert len(events) == 2
        assert EventType.MODEL_LOADED in events
        assert EventType.MODEL_UNLOADED in events


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
