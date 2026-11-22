"""Event type definitions for application event bus."""

from enum import Enum, auto


class EventType(Enum):
    """Enumeration of all application event types.

    Events are emitted by managers and UI components to signal
    changes in application state.
    """

    # Model loading and management
    MODEL_LOADING_STARTED = auto()
    MODEL_LOADED = auto()
    MODEL_LOADING_FAILED = auto()
    MODEL_UNLOADED = auto()
    MODEL_SELECTION_CHANGED = auto()

    # Model coordinates
    COORDINATE_CHANGED = auto()
    COORDINATE_CONSTRAINT_CHANGED = auto()

    # Animation playback
    ANIMATION_STARTED = auto()
    ANIMATION_STOPPED = auto()
    ANIMATION_PAUSED = auto()
    ANIMATION_RESUMED = auto()
    ANIMATION_FRAME_CHANGED = auto()
    ANIMATION_SPEED_CHANGED = auto()
    ANIMATION_TIMELINE_LOADED = auto()

    # Viewport and rendering
    VIEWPORT_CAMERA_CHANGED = auto()
    VIEWPORT_RESET = auto()
    VIEWPORT_REPAINT_NEEDED = auto()

    # Settings and configuration
    SETTINGS_CHANGED = auto()
    RENDER_QUALITY_CHANGED = auto()

    # Application lifecycle
    APPLICATION_CLOSING = auto()
    APPLICATION_READY = auto()

    # User interactions
    OBJECT_SELECTED = auto()
    OBJECT_PROPERTY_CHANGED = auto()

    # Interactive drag-to-pose
    POSE_DRAG_STARTED = auto()
    POSE_CHANGED = auto()
    POSE_DRAG_ENDED = auto()


if __name__ == "__main__":
    """Smoke test for event types."""
    print("EventType smoke test")
    print(f"\nDefined {len(EventType)} event types:")
    for event_type in EventType:
        print(f"  - {event_type.name}")
    print("\n[OK] Smoke test passed!")
