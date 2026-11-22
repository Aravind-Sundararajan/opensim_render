"""3D viewport display panel."""

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout
from osim_render.ui.vtk_widget import VTKWidget


class ViewportPanel(QWidget):
    """3D viewport panel for displaying models.

    Contains the main VTK rendering area for 3D visualization.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize viewport panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.vtk_widget: VTKWidget = VTKWidget()
        layout.addWidget(self.vtk_widget)

        self.setLayout(layout)

    def get_vtk_widget(self) -> VTKWidget:
        """Get the VTK widget.

        Returns:
            VTKWidget for rendering
        """
        return self.vtk_widget


if __name__ == "__main__":
    """Smoke test for viewport panel."""
    from PySide6.QtWidgets import QApplication

    print("ViewportPanel smoke test")

    app = QApplication([])

    panel = ViewportPanel()
    panel.setWindowTitle("Viewport Panel Test")
    panel.resize(800, 600)

    print("[OK] Viewport panel created")

    print("\n[OK] Smoke test passed!")
