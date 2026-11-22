"""Event bus for pub/sub application event handling."""

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from osim_render.api.managers.events import EventType
from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


@dataclass(frozen=True)
class Event:
    """Immutable event object.

    Contains event type and optional data payload.

    Attributes:
        event_type: Type of event that occurred
        data: Optional event data payload (immutable)
    """

    event_type: EventType
    data: Any = None


class EventListener(Protocol):
    """Protocol for event listener callbacks.

    Any callable matching this signature can subscribe to events.
    """

    def __call__(self, event: Event) -> None:
        """Handle an event.

        Args:
            event: Event object with type and data
        """
        ...


_event_handler_registry: dict[int, tuple[Callable[..., Any], tuple[EventType, ...]]] = {}


def event_handler(*event_types: EventType) -> Callable[..., Any]:
    """Decorator to mark a method as an event handler.

    Registers the method so it can be auto-subscribed to events.
    Use with auto_subscribe_all_events to register all decorated methods.

    Args:
        *event_types: EventType values this handler listens to

    Example:
        class MyController:
            @event_handler(EventType.MODEL_LOADED)
            def on_model_loaded(self, event: Event) -> None:
                pass

            @event_handler(EventType.MODEL_LOADED, EventType.MODEL_UNLOADED)
            def on_model_changed(self, event: Event) -> None:
                pass

        controller = MyController()
        auto_subscribe_all_events(controller, event_bus)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        _event_handler_registry[id(func)] = (func, event_types)
        return func

    return decorator


def auto_subscribe_all_events(obj: Any, event_bus: "EventBus") -> None:
    """Automatically subscribe all @event_handler decorated methods to event bus.

    Scans the object for methods decorated with @event_handler and subscribes
    them to their specified event types.

    Note: This function uses getattr to access decorated methods. This is
    intentional introspection to discover event handlers, not defensive
    error handling.

    Args:
        obj: Object with methods decorated with @event_handler
        event_bus: EventBus instance to subscribe to

    Raises:
        AttributeError: If event handler method is missing from object
        TypeError: If event handler is not callable
    """
    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)

        if not callable(attr):
            continue

        underlying = attr.__func__ if inspect.ismethod(attr) else attr
        if id(underlying) not in _event_handler_registry:
            continue

        _, registered_event_types = _event_handler_registry[id(underlying)]
        for event_type in registered_event_types:
            event_bus.subscribe(event_type, attr)
            logger.debug(f"Auto-subscribed {attr_name} to {event_type.name}")


def auto_unsubscribe_all_events(obj: Any, event_bus: "EventBus") -> None:
    """Automatically unsubscribe all @event_handler decorated methods from event bus.

    Note: This function uses getattr to access decorated methods. This is
    intentional introspection to discover event handlers, not defensive
    error handling.

    Args:
        obj: Object with methods decorated with @event_handler
        event_bus: EventBus instance to unsubscribe from

    Raises:
        AttributeError: If event handler method is missing from object
        TypeError: If event handler is not callable
    """
    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)

        if not callable(attr):
            continue

        underlying = attr.__func__ if inspect.ismethod(attr) else attr
        if id(underlying) not in _event_handler_registry:
            continue

        _, registered_event_types = _event_handler_registry[id(underlying)]
        for event_type in registered_event_types:
            event_bus.unsubscribe(event_type, attr)


class EventBus:
    """Publish-subscribe event bus for application events.

    Implements a simple pub/sub pattern where listeners can
    subscribe to specific event types and receive notifications
    when those events are published.
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._listeners: dict[EventType, list[EventListener]] = {}

    def subscribe(self, event_type: EventType, listener: EventListener) -> None:
        """Subscribe a listener to an event type.

        Args:
            event_type: Type of event to listen for
            listener: Callback function to invoke when event occurs
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []

        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)
            logger.info(
                f"Listener subscribed to {event_type.name} ({len(self._listeners[event_type])} total)"
            )

    def unsubscribe(self, event_type: EventType, listener: EventListener) -> None:
        """Unsubscribe a listener from an event type.

        Args:
            event_type: Type of event to stop listening for
            listener: Callback function to remove
        """
        if event_type in self._listeners and listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers.

        Args:
            event: Event object to publish
        """
        if event.event_type in self._listeners:
            for listener in self._listeners[event.event_type]:
                listener(event)

    def publish_event(self, event_type: EventType, data: Any = None) -> None:
        """Publish an event by type and optional data.

        Convenience method for publishing events without constructing
        Event object explicitly.

        Args:
            event_type: Type of event to publish
            data: Optional event data
        """
        listener_count = len(self._listeners.get(event_type, []))
        logger.info(f"Publishing {event_type.name} event to {listener_count} listeners")
        event = Event(event_type=event_type, data=data)
        self.publish(event)

    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()


if __name__ == "__main__":
    """Smoke test for event bus."""
    print("EventBus smoke test")

    bus = EventBus()

    received_events = []

    def test_listener(event: Event) -> None:
        """Test listener that records events."""
        received_events.append(event)

    # Subscribe to an event
    bus.subscribe(EventType.MODEL_LOADED, test_listener)
    print("[OK] Subscribed listener")

    # Publish an event
    bus.publish_event(EventType.MODEL_LOADED, data={"path": "test.osim"})
    print("[OK] Published event")

    # Check event was received
    assert len(received_events) == 1
    assert received_events[0].event_type == EventType.MODEL_LOADED
    assert received_events[0].data == {"path": "test.osim"}
    print("[OK] Event received correctly")

    # Unsubscribe
    bus.unsubscribe(EventType.MODEL_LOADED, test_listener)
    print("[OK] Unsubscribed listener")

    # Publish another event - should not be received
    bus.publish_event(EventType.MODEL_LOADED)
    assert len(received_events) == 1  # Still 1, not 2
    print("[OK] Unsubscribe worked correctly")

    print("\n[OK] All smoke tests passed!")
