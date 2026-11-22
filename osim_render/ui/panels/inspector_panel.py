"""Inspector panel for displaying object properties."""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt


class InspectorPanel(QWidget):
    """Inspector panel displaying properties of selected objects.

    Shows editable properties of selected model components.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize inspector panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)

        self.properties_table = QTableWidget()
        self.properties_table.setColumnCount(2)
        self.properties_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.properties_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.properties_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )

        layout.addWidget(self.properties_table)
        self.setLayout(layout)

    def set_properties(self, properties: dict[str, str]) -> None:
        """Set properties to display.

        Args:
            properties: Dictionary of property name to value
        """
        self.properties_table.setRowCount(len(properties))

        for i, (name, value) in enumerate(properties.items()):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.properties_table.setItem(i, 0, name_item)

            value_item = QTableWidgetItem(str(value))
            self.properties_table.setItem(i, 1, value_item)

    def clear_properties(self) -> None:
        """Clear all properties."""
        self.properties_table.setRowCount(0)


if __name__ == "__main__":
    """Smoke test for inspector panel."""
    from PySide6.QtWidgets import QApplication

    print("InspectorPanel smoke test")

    app = QApplication([])

    panel = InspectorPanel()
    panel.setWindowTitle("Inspector Panel Test")
    panel.resize(400, 300)

    # Set test properties
    panel.set_properties(
        {
            "name": "TestObject",
            "type": "Body",
            "mass": "75.0",
            "position": "0.0 0.0 0.0",
        }
    )

    print("[OK] Inspector panel created")
    print("[OK] Properties set")

    print("\n[OK] Smoke test passed!")
