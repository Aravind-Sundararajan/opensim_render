"""Outliner panel for model hierarchy display."""

from typing import Optional, TypedDict

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
)


class _ModelHierarchyData(TypedDict, total=False):
    name: str
    bodies: list[str]
    joints: list[str]


class OutlinerPanel(QWidget):
    """Outliner panel showing model hierarchy tree.

    Displays the structure of loaded OpenSim models in a tree view.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize outliner panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Component"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.tree)
        self.setLayout(layout)

    def set_model_hierarchy(self, model_data: _ModelHierarchyData) -> None:
        """Set model hierarchy from data.

        Args:
            model_data: Dictionary representing model structure
        """
        self.tree.clear()

        if "name" not in model_data:
            return

        root = QTreeWidgetItem([model_data["name"]])
        self.tree.addTopLevelItem(root)

        if "bodies" in model_data:
            bodies_item = QTreeWidgetItem(["Bodies"])
            root.addChild(bodies_item)

            for body in model_data["bodies"]:
                body_item = QTreeWidgetItem([body])
                bodies_item.addChild(body_item)

        if "joints" in model_data:
            joints_item = QTreeWidgetItem(["Joints"])
            root.addChild(joints_item)

            for joint in model_data["joints"]:
                joint_item = QTreeWidgetItem([joint])
                joints_item.addChild(joint_item)

        root.setExpanded(True)

    def clear_hierarchy(self) -> None:
        """Clear the hierarchy tree."""
        self.tree.clear()


if __name__ == "__main__":
    """Smoke test for outliner panel."""
    from PySide6.QtWidgets import QApplication

    print("OutlinerPanel smoke test")

    app = QApplication([])

    panel = OutlinerPanel()
    panel.setWindowTitle("Outliner Panel Test")
    panel.resize(300, 400)

    model_data: _ModelHierarchyData = {
        "name": "TestModel",
        "bodies": ["Ground", "Pelvis", "Femur_L", "Femur_R"],
        "joints": ["hip_flex_l", "hip_flex_r", "knee_l", "knee_r"],
    }

    panel.set_model_hierarchy(model_data)

    print("[OK] Outliner panel created")
    print("[OK] Model hierarchy set")

    print("\n[OK] Smoke test passed!")
