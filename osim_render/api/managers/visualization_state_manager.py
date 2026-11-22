"""Manages visibility state for all visualization elements."""

from dataclasses import dataclass, field


@dataclass
class VisualizationStateManager:
    """Centralized visibility state tracking for all visualization elements.

    Manages the visibility state of bodies, body origins, body mass centers,
    joint parents, joint children, contacts, and muscles independently.
    """

    bodies: dict[str, bool] = field(default_factory=dict)
    body_origins: dict[str, bool] = field(default_factory=dict)
    body_mass_centers: dict[str, bool] = field(default_factory=dict)
    joint_parents: dict[str, bool] = field(default_factory=dict)
    joint_children: dict[str, bool] = field(default_factory=dict)
    contacts: dict[str, bool] = field(default_factory=dict)
    muscles: dict[str, bool] = field(default_factory=dict)
    contact_forces: dict[str, bool] = field(default_factory=dict)
    ground_reactions: dict[str, bool] = field(default_factory=dict)
    wrap_actors: dict[str, bool] = field(default_factory=dict)

    def initialize_category(
        self, category: str, item_names: list[str], default_visible: bool = True
    ) -> None:
        """Initialize a category with items and their default visibility.

        Args:
            category: Category name (e.g., 'bodies', 'muscles')
            item_names: List of item names in this category
            default_visible: Default visibility state for all items
        """
        category_dict = self._get_category_dict(category)
        if category_dict is not None:
            for item_name in item_names:
                category_dict[item_name] = default_visible

    def set_visibility(self, category: str, item_name: str, visible: bool) -> None:
        """Set visibility state for a single item.

        Args:
            category: Category name (e.g., 'bodies', 'muscles')
            item_name: Name of the item within the category
            visible: Desired visibility state
        """
        category_dict = self._get_category_dict(category)
        if category_dict is not None:
            category_dict[item_name] = visible

    def set_all_visibility(self, category: str, visible: bool) -> None:
        """Set visibility state for all items in a category.

        Args:
            category: Category name (e.g., 'bodies', 'muscles')
            visible: Desired visibility state for all items
        """
        category_dict = self._get_category_dict(category)
        if category_dict is not None:
            for item_name in category_dict:
                category_dict[item_name] = visible

    def get_visibility(self, category: str, item_name: str) -> bool:
        """Get visibility state for a single item.

        Args:
            category: Category name (e.g., 'bodies', 'muscles')
            item_name: Name of the item within the category

        Returns:
            Visibility state (True if visible, False if hidden)
        """
        category_dict = self._get_category_dict(category)
        if category_dict is not None:
            return category_dict.get(item_name, False)
        return False

    def get_summary(self, category: str) -> tuple[int, int]:
        """Get summary of visibility state for a category.

        Used to determine tri-state button appearance (all/some/none checked).

        Args:
            category: Category name (e.g., 'bodies', 'muscles')

        Returns:
            Tuple of (total_count, visible_count)
        """
        category_dict = self._get_category_dict(category)
        if category_dict is None:
            return (0, 0)
        total = len(category_dict)
        visible = sum(1 for v in category_dict.values() if v)
        return (total, visible)

    def get_all_items(self, category: str) -> dict[str, bool]:
        """Get all items and their visibility state for a category.

        Args:
            category: Category name (e.g., 'bodies', 'muscles')

        Returns:
            Dictionary mapping item names to visibility states
        """
        category_dict = self._get_category_dict(category)
        if category_dict is None:
            return {}
        return dict(category_dict)

    def clear(self) -> None:
        """Clear all visibility state (typically called on model unload)."""
        self.bodies.clear()
        self.body_origins.clear()
        self.body_mass_centers.clear()
        self.joint_parents.clear()
        self.joint_children.clear()
        self.contacts.clear()
        self.ground_reactions.clear()
        self.muscles.clear()
        self.contact_forces.clear()
        self.wrap_actors.clear()

    def _get_category_dict(self, category: str) -> dict[str, bool] | None:
        """Get the dictionary for a given category.

        Args:
            category: Category name

        Returns:
            Dictionary for the category, or None if invalid category
        """
        mapping = {
            "bodies": self.bodies,
            "body_origins": self.body_origins,
            "body_mass_centers": self.body_mass_centers,
            "joint_parents": self.joint_parents,
            "joint_children": self.joint_children,
            "contacts": self.contacts,
            "muscles": self.muscles,
            "contact_forces": self.contact_forces,
            "ground_reactions": self.ground_reactions,
            "wrap_actors": self.wrap_actors,
        }
        return mapping.get(category)
