"""Reusable toolbar button for visualization element controls with dropdown menu."""

import re
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QToolButton,
    QMenu,
    QLineEdit,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)


def natural_sort_key(text: str) -> tuple[tuple[int, int] | tuple[int, str], ...]:
    """Generate a sort key for natural ordering of strings with numbers.

    Examples:
        "muscle2" < "muscle10"
        "body1" < "body20"

    Args:
        text: String to generate sort key for

    Returns:
        Tuple of alternating strings and integers for natural ordering
    """
    result: list[tuple[int, int] | tuple[int, str]] = []
    for match in re.finditer(r"(\d+|\D+)", text):
        part = match.group(0)
        if part.isdigit():
            result.append((0, int(part)))
        else:
            result.append((1, part.lower()))
    return tuple(result)


class VisualizationToolButton(QToolButton):
    """Tri-state toolbar button with dropdown menu for individual item visibility.

    Features:
    - Tri-state visual feedback (all/some/none visible)
    - Dropdown menu with "Show All" / "Hide All" actions
    - Alphabetically sorted checkable items
    - Search box for large lists (>50 items)
    - Natural sort for items with numbers (e.g., "muscle2" < "muscle10")

    Signals:
    - item_toggled(item_name: str, visible: bool): Individual checkbox changed
    - show_all_clicked(): Show All action activated
    - hide_all_clicked(): Hide All action activated
    """

    item_toggled = Signal(str, bool)
    show_all_clicked = Signal()
    hide_all_clicked = Signal()

    def __init__(self, name: str, parent: Optional[QWidget] = None) -> None:
        """Initialize the visualization tool button.

        Args:
            name: Display name for the button (e.g., "Bodies", "Muscles")
            parent: Parent widget
        """
        super().__init__(parent)
        self.name = name
        self.setText(name)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.setCheckable(True)

        self._popup_menu: QMenu = QMenu(self)
        self.setMenu(self._popup_menu)

        # Menu items (checkable actions)
        self._menu_items: dict[str, QAction] = {}

        # For managing "Show All" / "Hide All" actions
        self._show_all_action: Optional[QAction] = None
        self._hide_all_action: Optional[QAction] = None
        self._separator_action: Optional[QAction] = None

        # Search box (created on demand for large lists)
        self._search_box: Optional[QLineEdit] = None
        self._has_search_box = False

        # Tri-state tracking
        self._tri_state = Qt.CheckState.Unchecked

        # Connect button click to toggle show/hide
        self.clicked.connect(self._on_button_clicked)

    def populate_menu(
        self, item_names: list[str], default_visible: bool = True
    ) -> None:
        """Populate the menu with individual item checkboxes.

        Args:
            item_names: List of item names to display in menu
            default_visible: Default visibility state for all items
        """
        self._popup_menu.clear()
        self._menu_items.clear()
        self._search_box = None
        self._has_search_box = False

        if not item_names:
            # Empty menu
            no_items_action = self._popup_menu.addAction("No items")
            no_items_action.setEnabled(False)
            self.setEnabled(False)
            return

        self.setEnabled(True)

        # Add "Show All" / "Hide All" actions
        self._show_all_action = self._popup_menu.addAction("Show All")
        self._show_all_action.triggered.connect(self.show_all_clicked.emit)

        self._hide_all_action = self._popup_menu.addAction("Hide All")
        self._hide_all_action.triggered.connect(self.hide_all_clicked.emit)

        self._separator_action = self._popup_menu.addSeparator()

        if len(item_names) > 50:
            self._add_search_box()

        # Sort items naturally
        sorted_items = sorted(item_names, key=natural_sort_key)

        for item_name in sorted_items:
            action = self._popup_menu.addAction(item_name)
            action.setCheckable(True)
            action.setChecked(default_visible)
            action.triggered.connect(
                lambda checked=False, name=item_name: self._on_item_toggled(
                    name, checked
                )
            )
            self._menu_items[item_name] = action

        self._update_button_state()

    def update_item_visibility(self, item_name: str, visible: bool) -> None:
        """Update the visibility state of a menu item (for external state sync).

        Args:
            item_name: Name of the item to update
            visible: New visibility state
        """
        if item_name in self._menu_items:
            action = self._menu_items[item_name]
            action.blockSignals(True)
            action.setChecked(visible)
            action.blockSignals(False)
            self._update_button_state()

    def set_all_visible(self) -> None:
        """Check all items in the menu."""
        for action in self._menu_items.values():
            action.blockSignals(True)
            action.setChecked(True)
            action.blockSignals(False)
        self._update_button_state()

    def set_all_hidden(self) -> None:
        """Uncheck all items in the menu."""
        for action in self._menu_items.values():
            action.blockSignals(True)
            action.setChecked(False)
            action.blockSignals(False)
        self._update_button_state()

    def _add_search_box(self) -> None:
        """Add a search box to the top of the menu."""
        if self._has_search_box:
            return

        search_widget = QWidget()
        layout = QVBoxLayout(search_widget)
        layout.setContentsMargins(4, 4, 4, 4)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search...")
        self._search_box.textChanged.connect(self._filter_menu_items)
        layout.addWidget(self._search_box)

        search_action = QWidgetAction(self._popup_menu)
        search_action.setDefaultWidget(search_widget)

        # Insert at beginning of menu, before Show All
        if self._show_all_action:
            self._popup_menu.insertAction(self._show_all_action, search_action)
        else:
            self._popup_menu.addAction(search_action)

        self._has_search_box = True

    def _filter_menu_items(self, search_text: str) -> None:
        """Filter menu items based on search text.

        Args:
            search_text: Text to search for in item names
        """
        if not self._has_search_box:
            return

        search_lower = search_text.lower()
        for item_name, action in self._menu_items.items():
            action.setVisible(search_lower in item_name.lower())

    def _on_item_toggled(self, item_name: str, _checked: bool = False) -> None:
        """Handle when a menu item's checkbox is toggled.

        Args:
            item_name: Name of the toggled item
            _checked: Unused (passed by Qt but not reliable)
        """
        if item_name in self._menu_items:
            action = self._menu_items[item_name]
            visible = action.isChecked()
            # Emit signal before updating button state so handlers can process the change
            self.item_toggled.emit(item_name, visible)
            self._update_button_state()

    def checkState(self) -> Qt.CheckState:
        """Get the current tri-state of the button.

        Returns:
            Qt.CheckState representing all/some/none visible
        """
        return self._tri_state

    def _on_button_clicked(self) -> None:
        """Handle button click to toggle show all/hide all."""
        if not self._menu_items:
            return

        visible_count = sum(
            1 for action in self._menu_items.values() if action.isChecked()
        )
        total_count = len(self._menu_items)

        # If all visible, hide all. Otherwise, show all.
        if visible_count == total_count:
            # Hide all: uncheck all items
            for action in self._menu_items.values():
                action.blockSignals(True)
                action.setChecked(False)
                action.blockSignals(False)
            self._update_button_state()
            self.hide_all_clicked.emit()
        else:
            # Show all: check all items
            for action in self._menu_items.values():
                action.blockSignals(True)
                action.setChecked(True)
                action.blockSignals(False)
            self._update_button_state()
            self.show_all_clicked.emit()

    def _update_button_state(self) -> None:
        """Recalculate and update the button's tri-state appearance.

        Updates the button's checkable state based on how many items are visible:
        - All visible: checked ()
        - Some visible: partially checked ()
        - None visible: unchecked ()
        """
        if not self._menu_items:
            return

        visible_count = sum(
            1 for action in self._menu_items.values() if action.isChecked()
        )
        total_count = len(self._menu_items)

        self.blockSignals(True)
        if visible_count == 0:
            # None visible: unchecked
            self._tri_state = Qt.CheckState.Unchecked
            self.setChecked(False)
        elif visible_count == total_count:
            # All visible: checked
            self._tri_state = Qt.CheckState.Checked
            self.setChecked(True)
        else:
            # Some visible: partially checked
            self._tri_state = Qt.CheckState.PartiallyChecked
            # For visual feedback, keep checked but update internal state
            self.setChecked(True)
        self.blockSignals(False)
