"""Unit tests for VisualizationToolButton widget."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

from osim_render.ui.widgets.visualization_toolbutton import (
    VisualizationToolButton,
    natural_sort_key,
)


@pytest.fixture
def app() -> QCoreApplication:
    """Create QApplication for tests."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def button(app: QCoreApplication) -> VisualizationToolButton:
    """Create VisualizationToolButton instance."""
    return VisualizationToolButton("Test Button")


class TestNaturalSortKey:
    """Test natural sort key generation."""

    def test_simple_text_sort(self) -> None:
        """Test sorting simple text."""
        items = ["body", "alpha", "charlie", "bravo"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["alpha", "body", "bravo", "charlie"]

    def test_number_sort(self) -> None:
        """Test that numbers are sorted numerically."""
        items = ["muscle10", "muscle2", "muscle1", "muscle20"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["muscle1", "muscle2", "muscle10", "muscle20"]

    def test_mixed_alphanumeric_sort(self) -> None:
        """Test sorting mixed alphanumeric strings."""
        items = ["body2_origin", "body10_origin", "body1_origin"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["body1_origin", "body2_origin", "body10_origin"]

    def test_case_insensitive_sort(self) -> None:
        """Test that sort is case-insensitive."""
        items = ["Body", "alpha", "CHARLIE"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items[0].lower() == "alpha"


class TestVisualizationToolButton:
    """Test suite for VisualizationToolButton."""

    def test_initialization(self, button: VisualizationToolButton) -> None:
        """Test button initialization."""
        assert button.name == "Test Button"
        assert button.text() == "Test Button"
        assert button.isCheckable()

    def test_populate_menu_empty(self, button: VisualizationToolButton) -> None:
        """Test populating menu with empty list."""
        button.populate_menu([])

        assert not button.isEnabled()
        assert button.menu().actions()  # Should have "No items" action

    def test_populate_menu_single_item(self, button: VisualizationToolButton) -> None:
        """Test populating menu with single item."""
        button.populate_menu(["body1"], default_visible=True)

        assert button.isEnabled()
        assert "body1" in button._menu_items
        assert button._menu_items["body1"].isChecked()

    def test_populate_menu_multiple_items(self, button: VisualizationToolButton) -> None:
        """Test populating menu with multiple items."""
        items = ["body1", "body2", "body3"]
        button.populate_menu(items, default_visible=True)

        assert button.isEnabled()
        assert len(button._menu_items) == 3
        for item in items:
            assert item in button._menu_items
            assert button._menu_items[item].isChecked()

    def test_populate_menu_default_hidden(self, button: VisualizationToolButton) -> None:
        """Test populating menu with default_visible=False."""
        items = ["body1", "body2"]
        button.populate_menu(items, default_visible=False)

        for item in items:
            assert not button._menu_items[item].isChecked()

    def test_populate_menu_sorts_naturally(self, button: VisualizationToolButton) -> None:
        """Test that menu items are sorted naturally."""
        items = ["muscle10", "muscle2", "muscle1", "muscle20"]
        button.populate_menu(items)

        menu_items = [
            action.text() for action in button.menu().actions() if action.text() in items
        ]
        assert menu_items == ["muscle1", "muscle2", "muscle10", "muscle20"]

    def test_update_item_visibility(self, button: VisualizationToolButton) -> None:
        """Test updating item visibility externally."""
        button.populate_menu(["body1", "body2"], default_visible=True)

        button.update_item_visibility("body1", False)

        assert not button._menu_items["body1"].isChecked()
        assert button._menu_items["body2"].isChecked()

    def test_set_all_visible(self, button: VisualizationToolButton) -> None:
        """Test setting all items visible."""
        button.populate_menu(["body1", "body2", "body3"], default_visible=False)

        button.set_all_visible()

        for action in button._menu_items.values():
            assert action.isChecked()

    def test_set_all_hidden(self, button: VisualizationToolButton) -> None:
        """Test setting all items hidden."""
        button.populate_menu(["body1", "body2", "body3"], default_visible=True)

        button.set_all_hidden()

        for action in button._menu_items.values():
            assert not action.isChecked()

    def test_tri_state_all_visible(self, button: VisualizationToolButton) -> None:
        """Test tri-state when all items are visible."""
        button.populate_menu(["body1", "body2", "body3"], default_visible=True)

        assert button.checkState() == Qt.CheckState.Checked

    def test_tri_state_none_visible(self, button: VisualizationToolButton) -> None:
        """Test tri-state when no items are visible."""
        button.populate_menu(["body1", "body2", "body3"], default_visible=False)

        assert button.checkState() == Qt.CheckState.Unchecked

    def test_tri_state_some_visible(self, button: VisualizationToolButton) -> None:
        """Test tri-state when some items are visible."""
        button.populate_menu(["body1", "body2", "body3"], default_visible=True)
        button._menu_items["body1"].setChecked(False)
        button._menu_items["body2"].setChecked(False)
        button._update_button_state()  # Manually update state

        assert button.checkState() == Qt.CheckState.PartiallyChecked

    def test_show_all_action_exists(self, button: VisualizationToolButton) -> None:
        """Test that Show All action is added to menu."""
        button.populate_menu(["body1"], default_visible=False)

        assert button._show_all_action is not None
        assert button._show_all_action.text() == "Show All"

    def test_hide_all_action_exists(self, button: VisualizationToolButton) -> None:
        """Test that Hide All action is added to menu."""
        button.populate_menu(["body1"], default_visible=True)

        assert button._hide_all_action is not None
        assert button._hide_all_action.text() == "Hide All"

    def test_show_all_signal_emitted(self, button: VisualizationToolButton) -> None:
        """Test that show_all_clicked signal is emitted."""
        button.populate_menu(["body1"])
        signal_emitted = False

        def on_show_all() -> None:
            nonlocal signal_emitted
            signal_emitted = True

        button.show_all_clicked.connect(on_show_all)
        assert button._show_all_action is not None
        button._show_all_action.trigger()

        assert signal_emitted

    def test_hide_all_signal_emitted(self, button: VisualizationToolButton) -> None:
        """Test that hide_all_clicked signal is emitted."""
        button.populate_menu(["body1"])
        signal_emitted = False

        def on_hide_all() -> None:
            nonlocal signal_emitted
            signal_emitted = True

        button.hide_all_clicked.connect(on_hide_all)
        assert button._hide_all_action is not None
        button._hide_all_action.trigger()

        assert signal_emitted

    def test_item_toggled_signal_emitted(self, button: VisualizationToolButton) -> None:
        """Test that item_toggled signal is emitted."""
        button.populate_menu(["body1"])  # Starts checked=True
        signal_data: dict[str, object] = {}

        def on_item_toggled(item_name: str, visible: bool) -> None:
            signal_data["item"] = item_name
            signal_data["visible"] = visible

        button.item_toggled.connect(on_item_toggled)
        button._menu_items["body1"].trigger()  # Toggles to False

        assert signal_data.get("item") == "body1"
        # After trigger(), the action is toggled, so it should be False
        assert signal_data.get("visible") is False

    def test_search_box_added_for_large_list(self, button: VisualizationToolButton) -> None:
        """Test that search box is added for lists with >50 items."""
        items = [f"item_{i}" for i in range(51)]
        button.populate_menu(items)

        assert button._has_search_box is True
        assert button._search_box is not None

    def test_search_box_not_added_for_small_list(self, button: VisualizationToolButton) -> None:
        """Test that search box is not added for small lists."""
        items = [f"item_{i}" for i in range(10)]
        button.populate_menu(items)

        assert button._has_search_box is False

    def test_search_filter(self, button: VisualizationToolButton) -> None:
        """Test search filtering of menu items."""
        # Create list large enough to trigger search box
        items = [f"muscle_gastrocnemius_{i}" for i in range(26)]
        items.extend([f"muscle_soleus_{i}" for i in range(26)])
        button.populate_menu(items)

        # Need search box to be present
        assert button._has_search_box is True

        button._filter_menu_items("gastrocnemius")

        visible_items = [
            action for action in button._menu_items.values() if action.isVisible()
        ]
        assert len(visible_items) == 26

    def test_clear_and_repopulate(self, button: VisualizationToolButton) -> None:
        """Test clearing and repopulating the menu."""
        button.populate_menu(["body1", "body2"])
        button.populate_menu(["muscle1", "muscle2", "muscle3"])

        assert len(button._menu_items) == 3
        assert "body1" not in button._menu_items
        assert "muscle1" in button._menu_items

    def test_button_click_hide_all_when_all_visible(self, button: VisualizationToolButton) -> None:
        """Test that button click emits hide_all when all items are visible."""
        button.populate_menu(["body1", "body2"], default_visible=True)
        signal_emitted: bool | None = None

        def on_signal() -> None:
            nonlocal signal_emitted
            signal_emitted = True

        button.hide_all_clicked.connect(on_signal)
        button.clicked.emit()

        assert signal_emitted is True

    def test_button_click_show_all_when_some_visible(self, button: VisualizationToolButton) -> None:
        """Test that button click emits show_all when some items are visible."""
        button.populate_menu(["body1", "body2"], default_visible=True)
        button._menu_items["body1"].setChecked(False)
        signal_emitted: bool | None = None

        def on_signal() -> None:
            nonlocal signal_emitted
            signal_emitted = True

        button.show_all_clicked.connect(on_signal)
        button.clicked.emit()

        assert signal_emitted is True

    def test_button_click_show_all_when_none_visible(self, button: VisualizationToolButton) -> None:
        """Test that button click emits show_all when no items are visible."""
        button.populate_menu(["body1", "body2"], default_visible=False)
        signal_emitted: bool | None = None

        def on_signal() -> None:
            nonlocal signal_emitted
            signal_emitted = True

        button.show_all_clicked.connect(on_signal)
        button.clicked.emit()

        assert signal_emitted is True
