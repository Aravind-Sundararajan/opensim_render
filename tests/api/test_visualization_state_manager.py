"""Unit tests for VisualizationStateManager."""


from osim_render.api.managers.visualization_state_manager import (
    VisualizationStateManager,
)


class TestVisualizationStateManager:
    """Test suite for VisualizationStateManager."""

    def test_initialize_category_default_visible(self) -> None:
        """Test initializing a category with default visible True."""
        manager = VisualizationStateManager()
        items = ["body1", "body2", "body3"]

        manager.initialize_category("bodies", items, default_visible=True)

        for item in items:
            assert manager.get_visibility("bodies", item) is True

    def test_initialize_category_default_hidden(self) -> None:
        """Test initializing a category with default visible False."""
        manager = VisualizationStateManager()
        items = ["muscle1", "muscle2"]

        manager.initialize_category("muscles", items, default_visible=False)

        for item in items:
            assert manager.get_visibility("muscles", item) is False

    def test_initialize_multiple_categories(self) -> None:
        """Test initializing multiple categories independently."""
        manager = VisualizationStateManager()
        bodies = ["body1", "body2"]
        muscles = ["muscle1", "muscle2"]

        manager.initialize_category("bodies", bodies, default_visible=True)
        manager.initialize_category("muscles", muscles, default_visible=False)

        assert manager.get_visibility("bodies", "body1") is True
        assert manager.get_visibility("muscles", "muscle1") is False

    def test_set_visibility_single_item(self) -> None:
        """Test setting visibility for a single item."""
        manager = VisualizationStateManager()
        manager.initialize_category(
            "bodies", ["body1", "body2"], default_visible=True)

        manager.set_visibility("bodies", "body1", False)

        assert manager.get_visibility("bodies", "body1") is False
        assert manager.get_visibility("bodies", "body2") is True

    def test_set_visibility_toggle(self) -> None:
        """Test toggling visibility multiple times."""
        manager = VisualizationStateManager()
        manager.initialize_category("bodies", ["body1"], default_visible=True)

        manager.set_visibility("bodies", "body1", False)
        assert manager.get_visibility("bodies", "body1") is False

        manager.set_visibility("bodies", "body1", True)
        assert manager.get_visibility("bodies", "body1") is True

    def test_set_all_visibility_show(self) -> None:
        """Test showing all items in a category."""
        manager = VisualizationStateManager()
        manager.initialize_category(
            "bodies", ["body1", "body2", "body3"], default_visible=False
        )

        manager.set_all_visibility("bodies", True)

        for item in ["body1", "body2", "body3"]:
            assert manager.get_visibility("bodies", item) is True

    def test_set_all_visibility_hide(self) -> None:
        """Test hiding all items in a category."""
        manager = VisualizationStateManager()
        manager.initialize_category(
            "bodies", ["body1", "body2", "body3"], default_visible=True
        )

        manager.set_all_visibility("bodies", False)

        for item in ["body1", "body2", "body3"]:
            assert manager.get_visibility("bodies", item) is False

    def test_get_summary_all_visible(self) -> None:
        """Test summary when all items are visible."""
        manager = VisualizationStateManager()
        items = ["body1", "body2", "body3"]
        manager.initialize_category("bodies", items, default_visible=True)

        total, visible = manager.get_summary("bodies")

        assert total == 3
        assert visible == 3

    def test_get_summary_none_visible(self) -> None:
        """Test summary when no items are visible."""
        manager = VisualizationStateManager()
        items = ["body1", "body2", "body3"]
        manager.initialize_category("bodies", items, default_visible=False)

        total, visible = manager.get_summary("bodies")

        assert total == 3
        assert visible == 0

    def test_get_summary_some_visible(self) -> None:
        """Test summary when some items are visible."""
        manager = VisualizationStateManager()
        items = ["body1", "body2", "body3"]
        manager.initialize_category("bodies", items, default_visible=True)
        manager.set_visibility("bodies", "body1", False)
        manager.set_visibility("bodies", "body2", False)

        total, visible = manager.get_summary("bodies")

        assert total == 3
        assert visible == 1

    def test_get_summary_empty_category(self) -> None:
        """Test summary for empty or uninitialized category."""
        manager = VisualizationStateManager()

        total, visible = manager.get_summary("bodies")

        assert total == 0
        assert visible == 0

    def test_get_all_items(self) -> None:
        """Test retrieving all items in a category."""
        manager = VisualizationStateManager()
        items = ["body1", "body2", "body3"]
        manager.initialize_category("bodies", items, default_visible=True)
        manager.set_visibility("bodies", "body1", False)

        all_items = manager.get_all_items("bodies")

        assert len(all_items) == 3
        assert all_items["body1"] is False
        assert all_items["body2"] is True
        assert all_items["body3"] is True

    def test_get_all_items_empty_category(self) -> None:
        """Test retrieving items from empty category."""
        manager = VisualizationStateManager()

        all_items = manager.get_all_items("bodies")

        assert all_items == {}

    def test_clear(self) -> None:
        """Test clearing all state."""
        manager = VisualizationStateManager()
        manager.initialize_category("bodies", ["body1"], default_visible=True)
        manager.initialize_category(
            "muscles", ["muscle1"], default_visible=False)

        manager.clear()

        assert manager.get_all_items("bodies") == {}
        assert manager.get_all_items("muscles") == {}

    def test_all_categories(self) -> None:
        """Test that all seven categories work."""
        manager = VisualizationStateManager()
        categories = [
            "bodies",
            "body_origins",
            "body_mass_centers",
            "joint_parents",
            "joint_children",
            "contacts",
            "muscles",
        ]

        for category in categories:
            manager.initialize_category(
                category, ["item1", "item2"], default_visible=True
            )

        for category in categories:
            total, visible = manager.get_summary(category)
            assert total == 2
            assert visible == 2

    def test_get_visibility_nonexistent_item(self) -> None:
        """Test getting visibility for nonexistent item."""
        manager = VisualizationStateManager()
        manager.initialize_category("bodies", ["body1"], default_visible=True)

        visibility = manager.get_visibility("bodies", "nonexistent")

        assert visibility is False

    def test_invalid_category(self) -> None:
        """Test operations with invalid category."""
        manager = VisualizationStateManager()

        # Should handle gracefully without crashing
        manager.set_visibility("invalid_category", "item", True)
        visibility = manager.get_visibility("invalid_category", "item")
        total, visible = manager.get_summary("invalid_category")
        all_items = manager.get_all_items("invalid_category")

        assert visibility is False
        assert total == 0
        assert visible == 0
        assert all_items == {}
