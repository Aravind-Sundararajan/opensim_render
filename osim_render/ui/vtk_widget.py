"""VTK rendering widget integrated with PySide6 Qt."""

from typing import Any, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout

from vtkmodules.vtkRenderingCore import (
    vtkRenderer,
    vtkActor,
    vtkPolyDataMapper,
)
from vtkmodules.vtkFiltersSources import vtkCubeSource
from vtkmodules.vtkInteractionWidgets import vtkCameraOrientationWidget

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from osim_render.ui.interaction.pose_interactor_style import PoseInteractorStyle


class VTKWidget(QWidget):
    """Qt widget for VTK rendering.

    Integrates VTK rendering into a PySide6 application with
    interactive camera controls.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize VTK widget.

        Args:
            parent: Parent Qt widget
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.interactor = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.interactor)
        self.setLayout(layout)

        # VTK scene basics
        self.renderer = vtkRenderer()
        self.render_window = self.interactor.GetRenderWindow()
        self.render_window.AddRenderer(self.renderer)

        # Interactor + trackball camera style extended with drag-to-pose
        self.iren = self.render_window.GetInteractor()
        self.pose_style = PoseInteractorStyle(self.renderer)
        self.iren.SetInteractorStyle(self.pose_style)

        camera = self.renderer.GetActiveCamera()
        if camera:
            camera.SetParallelScale(1.0)

        self.set_background_color(0.2, 0.2, 0.2)

        # proper event handling to avoid interfering with Qt buttons
        self.camera_orientation_widget = vtkCameraOrientationWidget()
        self.camera_orientation_widget.SetParentRenderer(self.renderer)
        self.camera_orientation_widget.SetInteractor(self.iren)
        self.camera_orientation_widget.SetAnimate(True)
        self.camera_orientation_widget.SetAnimatorTotalFrames(60)

        # Lower priority so Qt events take precedence
        self.camera_orientation_widget.SetPriority(0.5)
        self.camera_orientation_widget.ManagesCursorOff()

        self.camera_orientation_widget.On()

        self.interactor.Initialize()

    def set_pose_controller(self, controller: Optional[Any]) -> None:
        """Attach the drag-to-pose controller to the interactor style.

        Args:
            controller: DragPoseController, or None to disable posing
        """
        self.pose_style.set_controller(controller)

    def set_pose_mode_enabled(self, enabled: bool) -> None:
        """Enable or disable posing on plain left-drag.

        Args:
            enabled: True to pose without holding Ctrl
        """
        self.pose_style.set_pose_mode_enabled(enabled)

    def set_background_color(self, r: float, g: float, b: float) -> None:
        """Set viewport background color.

        Args:
            r: Red component (0.0-1.0)
            g: Green component (0.0-1.0)
            b: Blue component (0.0-1.0)
        """
        self.renderer.SetBackground(r, g, b)
        self.render_window.Render()

    def add_actor(self, actor: vtkActor) -> None:
        """Add an actor to the scene.

        Args:
            actor: VTK actor to add
        """
        self.renderer.AddActor(actor)
        self.reset_camera()
        self.render_window.Render()

    def remove_actor(self, actor: vtkActor) -> None:
        """Remove an actor from the scene.

        Args:
            actor: VTK actor to remove
        """
        self.renderer.RemoveActor(actor)
        self.render_window.Render()

    def reset_camera(self) -> None:
        """Reset camera to fit all visible actors."""
        self.renderer.ResetCamera()
        self.render_window.Render()

    def render(self, *args: Any, **kwargs: Any) -> None:
        """Trigger a render update."""
        # Override parent class render to trigger VTK render window update
        self.render_window.Render()

    def create_cube_actor(self) -> vtkActor:
        """Create a simple cube actor for testing.

        Returns:
            vtkActor with cube geometry
        """
        cube_source = vtkCubeSource()
        cube_source.SetXLength(2.0)
        cube_source.SetYLength(2.0)
        cube_source.SetZLength(2.0)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(cube_source.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1.0, 0.0, 0.0)

        return actor


if __name__ == "__main__":
    """Smoke test for VTK widget."""
    from PySide6.QtWidgets import QApplication

    print("VTKWidget smoke test")

    app = QApplication([])

    widget = VTKWidget()

    print("[OK] VTK widget created")
    print("[OK] Rendering window initialized")

    # Don't show in automated test
    # widget.show()
    # sys.exit(app.exec())

    print("\n[OK] Smoke test passed!")
