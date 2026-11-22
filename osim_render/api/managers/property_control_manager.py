"""Unified property control service for actor properties.

Provides a single API for all property changes (instant + animated) across all actor
categories. Eliminates bespoke VTK calls from GUI and provides scripting API with
explicit instant methods alongside animated tweens.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union

from osim_render.api.animation.value_types import ColorValue
from osim_render.api.logging import get_logger_for

if TYPE_CHECKING:
    from osim_render.api.rendering.scene import SceneManager
    from osim_render.api.managers.visualization_state_manager import VisualizationStateManager
    from osim_render.api.managers.event_bus import EventBus

logger = get_logger_for(__name__)


class PropertyControlManager:
    """Unified API for actor property control.

    Provides single API for setting properties on actors across all 9 categories:
    - bodies, body_origins, body_mass_centers
    - joint_parents, joint_children
    - contacts, contact_forces, markers
    - muscles, wrap_actors

    Supports both instant changes (for GUI) and animated changes (for scripting).
    """

    def __init__(
        self,
        scene_manager: SceneManager,
        vis_state_manager: VisualizationStateManager,
        event_bus: EventBus,
    ) -> None:
        """Initialize property control manager.

        Args:
            scene_manager: SceneManager instance providing access to actors
            vis_state_manager: VisualizationStateManager for state synchronization
            event_bus: EventBus for publishing property change events
        """
        self.scene_manager = scene_manager
        self.vis_state_manager = vis_state_manager
        self.event_bus = event_bus
        # actor_name -> list of (category, actor); multiple categories can share a name
        self._actor_registry: dict[str, list[tuple[str, Any]]] = {}

    def rebuild_actor_registry(self) -> None:
        """Rebuild the actor registry after the scene gains or loses actors.

        Ground reactions are added to a live scene when their data file is
        loaded, so the registry has to be refreshed for them to be findable.
        """
        self._rebuild_actor_registry()

    def _rebuild_actor_registry(self) -> None:
        """Rebuild the complete actor registry from current scene.

        Maps actor names to (category, actor) tuples for quick lookup.
        Called whenever the scene changes.
        """
        self._actor_registry.clear()
        scene = self.scene_manager.get_scene()

        if scene is None:
            logger.debug("No scene available for actor registry rebuild")
            return

        # Map of category names to actor dictionaries
        actor_sources = [
            ("bodies", scene.actors),
            ("body_origins", scene.body_origin_actors),
            ("body_mass_centers", scene.body_mass_center_actors),
            ("joint_parents", scene.joint_parent_actors),
            ("joint_children", scene.joint_child_actors),
            ("contacts", scene.contact_actors),
            ("contact_forces", scene.contact_force_actors),
            ("ground_reactions", scene.ground_reaction_actors),
            ("markers", scene.marker_actors),
            ("muscles", scene.muscle_actors),
            ("wrap_actors", scene.wrap_actors),
        ]

        for category, actor_dict in actor_sources:
            if actor_dict:
                for name, actor in actor_dict.items():
                    if name not in self._actor_registry:
                        self._actor_registry[name] = []
                    self._actor_registry[name].append((category, actor))

        logger.debug(f"Rebuilt actor registry with {len(self._actor_registry)} actors")

    def find_actor(
        self,
        actor_name: str,
        category: Optional[str] = None,
    ) -> Optional[Any]:
        """Find an actor by name, optionally filtering by category.

        Args:
            actor_name: Name of the actor to find
            category: Optional category to restrict search (for disambiguation)

        Returns:
            VTK actor if found, None otherwise
        """
        if not self._actor_registry:
            self._rebuild_actor_registry()

        if actor_name not in self._actor_registry:
            logger.warning(f"Actor not found: {actor_name}")
            return None

        matches = self._actor_registry[actor_name]

        if category is not None:
            for found_category, actor in matches:
                if found_category == category:
                    return actor
            logger.warning(
                f"Actor '{actor_name}' not found in category '{category}'"
            )
            return None

        # No category filter — return the first match (categories are in priority order)
        return matches[0][1]

    def set_property(
        self,
        actor_name: str,
        property_name: str,
        value: Any,
        category: Optional[str] = None,
    ) -> bool:
        """Set a property on an actor instantly (no animation).

        Supports common properties:
        - 'visibility': bool
        - 'opacity': float (0.0-1.0)
        - 'color': ColorValue or (r, g, b) tuple

        Args:
            actor_name: Name of the actor
            property_name: Name of property to set
            value: Value to set
            category: Optional category for disambiguation

        Returns:
            True if property was set, False if actor not found or property unsupported
        """
        actor = self.find_actor(actor_name, category)
        if actor is None:
            return False

        self._apply_property_to_actor(actor, property_name, value)
        logger.debug(f"Set {property_name} on {actor_name} to {value}")
        return True

    def set_visibility(
        self,
        actor_name: str,
        visible: bool,
        category: Optional[str] = None,
    ) -> bool:
        """Set visibility on an actor instantly.

        Convenience method for setting the 'visibility' property.

        Args:
            actor_name: Name of the actor
            visible: Whether actor should be visible
            category: Optional category for disambiguation

        Returns:
            True if visibility was set, False if actor not found
        """
        actor = self.find_actor(actor_name, category)
        if actor is None:
            return False

        actor.SetVisibility(1 if visible else 0)
        self._sync_visibility_state(actor_name, visible, category)
        logger.debug(f"Set visibility on {actor_name} to {visible}")
        return True

    def set_opacity(
        self,
        actor_name: str,
        opacity: float,
        category: Optional[str] = None,
    ) -> bool:
        """Set opacity on an actor instantly.

        Convenience method for setting the 'opacity' property.

        Args:
            actor_name: Name of the actor
            opacity: Opacity value (0.0-1.0)
            category: Optional category for disambiguation

        Returns:
            True if opacity was set, False if actor not found
        """
        if not (0.0 <= opacity <= 1.0):
            logger.warning(f"Opacity {opacity} out of range [0.0, 1.0]")
            opacity = max(0.0, min(1.0, opacity))

        return self.set_property(actor_name, "opacity", opacity, category)

    def set_color(
        self,
        actor_name: str,
        color: Union[tuple[float, float, float], Any],
        category: Optional[str] = None,
    ) -> bool:
        """Set color on an actor instantly.

        Convenience method for setting the 'color' property.

        Args:
            actor_name: Name of the actor
            color: Color as (r, g, b) tuple or ColorValue object
            category: Optional category for disambiguation

        Returns:
            True if color was set, False if actor not found
        """
        return self.set_property(actor_name, "color", color, category)

    def set_category_visibility(self, category: str, visible: bool) -> None:
        """Set visibility for all actors in a category.

        Batch operation for convenience (e.g., "Show All" button).

        Args:
            category: Category name (e.g., 'muscles', 'bodies')
            visible: Whether all actors in category should be visible
        """
        scene = self.scene_manager.get_scene()
        if scene is None:
            return

        # Map category to actor dictionary
        category_map = {
            "bodies": scene.actors,
            "body_origins": scene.body_origin_actors,
            "body_mass_centers": scene.body_mass_center_actors,
            "joint_parents": scene.joint_parent_actors,
            "joint_children": scene.joint_child_actors,
            "contacts": scene.contact_actors,
            "contact_forces": scene.contact_force_actors,
            "ground_reactions": scene.ground_reaction_actors,
            "markers": scene.marker_actors,
            "muscles": scene.muscle_actors,
            "wrap_actors": scene.wrap_actors,
        }

        actor_dict = category_map.get(category)
        if not actor_dict:
            logger.warning(f"Unknown category: {category}")
            return

        for actor_name, actor in actor_dict.items():
            actor.SetVisibility(1 if visible else 0)
            self.vis_state_manager.set_visibility(category, actor_name, visible)

        logger.debug(f"Set {category} visibility to {visible} ({len(actor_dict)} actors)")

    def _apply_property_to_actor(self, actor: Any, property_name: str, value: Any) -> None:
        """Apply a property value to a VTK actor.

        Args:
            actor: VTK actor to modify
            property_name: Name of property
            value: Value to apply

        Raises:
            ValueError: If property name is not recognized
        """
        if property_name == "visibility":
            actor.SetVisibility(1 if value else 0)
        elif property_name == "opacity":
            actor.GetProperty().SetOpacity(float(value))
        elif property_name == "color":
            r, g, b, a = self._normalize_color_value(value)
            actor.GetProperty().SetColor(float(r), float(g), float(b))
            if a < 1.0:
                actor.GetProperty().SetOpacity(float(a))
        else:
            raise ValueError(f"Unsupported property: {property_name}")

    def _normalize_color_value(self, value: Any) -> tuple[float, float, float, float]:
        """Normalize color value to (r, g, b, a) tuple.

        Accepts ColorValue objects or RGB/RGBA tuples.
        """
        if isinstance(value, ColorValue):
            return (value.r, value.g, value.b, value.a)

        if len(value) == 4:
            return tuple(value)

        return (*value, 1.0)

    def _sync_visibility_state(
        self, actor_name: str, visible: bool, category: Optional[str]
    ) -> None:
        """Synchronize visibility state with VisualizationStateManager."""
        if category is None and actor_name in self._actor_registry:
            category = self._actor_registry[actor_name][0][0]

        if category is not None:
            self.vis_state_manager.set_visibility(category, actor_name, visible)

    def get_scene(self) -> Optional[Any]:
        """Get the current rendering scene.

        Returns:
            RenderScene if available, None otherwise
        """
        return self.scene_manager.get_scene()

    def on_scene_created(self) -> None:
        """Called when a new scene is created.

        Rebuilds the actor registry so find_actor() works with the new scene.
        """
        self._rebuild_actor_registry()
