"""Camera toolbar mixin for the main application window."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from PySide6.QtWidgets import (
    QComboBox,
    QInputDialog,
    QLabel,
    QWidget,
)
from PySide6.QtGui import QAction

from osim_render.api.managers.settings_manager import CameraPreset

if TYPE_CHECKING:
    from PySide6.QtWidgets import QStatusBar

    from osim_render.ui.protocols import MainWindowProtocol
    from osim_render.ui.vtk_widget import VTKWidget
    from osim_render.api.managers.settings_manager import SettingsManager

# Shown when the camera is not tracking anything.
NO_FOLLOW_LABEL = "None"


class CameraToolbarMixin:
    """Mixin for camera toolbar with view controls."""

    if TYPE_CHECKING:
        vtk_widget: VTKWidget
        settings_manager: SettingsManager

        def statusBar(self) -> QStatusBar:
            ...

    def _setup_camera_toolbar(self: MainWindowProtocol) -> None:
        """Create camera toolbar with view controls."""
        toolbar = self.addToolBar("Camera Toolbar")
        toolbar.setObjectName("CameraToolbar")
        toolbar.setMovable(False)

        # Projection mode toggle
        projection_action = QAction("Perspective", cast(QWidget, self))
        projection_action.setCheckable(True)
        projection_action.setChecked(True)
        projection_action.setStatusTip(
            "Toggle between perspective and orthographic")
        projection_action.triggered.connect(self._on_toggle_projection)
        toolbar.addAction(projection_action)
        self.projection_action = projection_action

        toolbar.addSeparator()

        # Camera view buttons (6 standard views)
        views = [
            ("Front", "1", self._on_camera_front),
            ("Back", "Shift+1", self._on_camera_back),
            ("Top", "7", self._on_camera_top),
            ("Bottom", "Shift+7", self._on_camera_bottom),
            ("Left", "3", self._on_camera_left),
            ("Right", "Shift+3", self._on_camera_right),
        ]

        for label, shortcut, callback in views:
            action = QAction(label, cast(QWidget, self))
            action.setShortcut(shortcut)
            action.setStatusTip(f"View from {label.lower()}")
            action.triggered.connect(callback)
            toolbar.addAction(action)

        toolbar.addSeparator()

        # Camera presets dropdown
        self.presets_combo = QComboBox()
        self.presets_combo.addItem("Save Preset...")
        self.presets_combo.addItem("Load Preset...")
        self._load_saved_presets()
        self.presets_combo.setStatusTip("Save/load camera presets")
        self.presets_combo.currentIndexChanged.connect(
            self._on_preset_selected)
        toolbar.addWidget(self.presets_combo)

        toolbar.addSeparator()

        # Camera follow-body dropdown, the GUI counterpart to a script's
        # scene.track_body("pelvis").
        toolbar.addWidget(QLabel("Follow:"))
        self.follow_body_combo = QComboBox()
        self.follow_body_combo.addItem(NO_FOLLOW_LABEL)
        self.follow_body_combo.setStatusTip(
            "Keep a body in frame as the model moves, e.g. the pelvis during gait"
        )
        self.follow_body_combo.setEnabled(False)
        self.follow_body_combo.currentTextChanged.connect(
            self._on_follow_body_changed)
        toolbar.addWidget(self.follow_body_combo)

    def _populate_follow_bodies(
        self: MainWindowProtocol, body_names: list[str]
    ) -> None:
        """Fill the follow dropdown with the loaded model's bodies.

        Args:
            body_names: Names of the model's bodies
        """
        combo = self.follow_body_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(NO_FOLLOW_LABEL)
        combo.addItems(body_names)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)

        combo.setEnabled(bool(body_names))

    def _on_follow_body_changed(self: MainWindowProtocol, body_name: str) -> None:
        """Start or stop following a body.

        Args:
            body_name: Selected body, or the no-follow label
        """
        if self.scene_manager is None:
            return

        if not body_name or body_name == NO_FOLLOW_LABEL:
            self.scene_manager.clear_camera_follow()
            self.statusBar().showMessage("Camera follow off", 3000)
            return

        self.scene_manager.set_camera_follow_body(body_name)
        self.statusBar().showMessage(f"Camera following {body_name}", 3000)

    def _on_toggle_projection(self) -> None:
        """Toggle between perspective and orthographic projection."""
        is_perspective = self.projection_action.isChecked()
        camera = self.vtk_widget.renderer.GetActiveCamera()

        if is_perspective:
            camera.ParallelProjectionOff()
            self.projection_action.setText("Perspective")
        else:
            camera.ParallelProjectionOn()
            self.projection_action.setText("Orthographic")

        self.vtk_widget.render()

    def _set_camera_view(
        self,
        direction: tuple[float, float, float],
        up_vector: tuple[float, float, float],
    ) -> None:
        """Set camera to a specific view direction based on scene bounds.

        Args:
            direction: Normalized direction vector for camera position
            up_vector: Up vector for the view
        """
        renderer = self.vtk_widget.renderer
        camera = renderer.GetActiveCamera()

        bounds = renderer.ComputeVisiblePropBounds()

        focal_point = (
            (bounds[0] + bounds[1]) / 2.0,
            (bounds[2] + bounds[3]) / 2.0,
            (bounds[4] + bounds[5]) / 2.0,
        )

        # This gives us the same framing as the orientation widget
        camera.SetFocalPoint(*focal_point)
        camera.SetViewUp(*up_vector)
        camera.SetPosition(
            focal_point[0] + direction[0],
            focal_point[1] + direction[1],
            focal_point[2] + direction[2],
        )
        renderer.ResetCamera()

        # Now get the distance that ResetCamera calculated
        camera_pos = camera.GetPosition()
        dist_x = camera_pos[0] - focal_point[0]
        dist_y = camera_pos[1] - focal_point[1]
        dist_z = camera_pos[2] - focal_point[2]

        import math

        distance = math.sqrt(dist_x * dist_x + dist_y *
                             dist_y + dist_z * dist_z)

        position = (
            focal_point[0] + direction[0] * distance,
            focal_point[1] + direction[1] * distance,
            focal_point[2] + direction[2] * distance,
        )
        camera.SetPosition(*position)
        camera.SetViewUp(*up_vector)
        renderer.ResetCameraClippingRange()
        self.vtk_widget.render()

    def _on_camera_front(self) -> None:
        """Set camera to front view."""
        self._set_camera_view((0, 0, 1), (0, 1, 0))

    def _on_camera_back(self) -> None:
        """Set camera to back view."""
        self._set_camera_view((0, 0, -1), (0, 1, 0))

    def _on_camera_top(self) -> None:
        """Set camera to top view."""
        self._set_camera_view((0, 1, 0), (0, 0, -1))

    def _on_camera_bottom(self) -> None:
        """Set camera to bottom view."""
        self._set_camera_view((0, -1, 0), (0, 0, 1))

    def _on_camera_left(self) -> None:
        """Set camera to left view."""
        self._set_camera_view((-1, 0, 0), (0, 1, 0))

    def _on_camera_right(self) -> None:
        """Set camera to right view."""
        self._set_camera_view((1, 0, 0), (0, 1, 0))

    def _load_saved_presets(self) -> None:
        """Load saved presets from settings into combo box."""
        settings = self.settings_manager.get_settings()
        for preset in settings.camera_presets:
            self.presets_combo.addItem(preset.name)

    def _get_current_camera_state(self) -> tuple[Any, ...]:
        """Get current camera position, focal point, and up vector.

        Returns:
            Tuple of (position, focal_point, up_vector, parallel_projection)
        """
        camera = self.vtk_widget.renderer.GetActiveCamera()
        position = camera.GetPosition()
        focal_point = camera.GetFocalPoint()
        up_vector = camera.GetViewUp()
        is_parallel = camera.GetParallelProjection()
        return (position, focal_point, up_vector, bool(is_parallel))

    def _on_preset_selected(self, index: int) -> None:
        """Handle preset selection."""
        if index == 0:
            text, ok = QInputDialog.getText(
                cast(QWidget, self), "Save Preset", "Preset name:"
            )
            if ok and text:
                (
                    position,
                    focal_point,
                    up_vector,
                    is_parallel,
                ) = self._get_current_camera_state()
                preset = CameraPreset(
                    name=text,
                    position=position,
                    focal_point=focal_point,
                    up_vector=up_vector,
                    parallel_projection=is_parallel,
                )
                settings = self.settings_manager.get_settings()
                settings = settings.with_camera_preset(preset)
                self.settings_manager.update_settings(settings)

                if self.presets_combo.findText(text) == -1:
                    self.presets_combo.addItem(text)

                self.statusBar().showMessage(f"Saved preset: {text}")
        elif index > 1:
            preset_name = self.presets_combo.currentText()
            settings = self.settings_manager.get_settings()
            preset_opt = settings.get_camera_preset(preset_name)
            if preset_opt:
                camera = self.vtk_widget.renderer.GetActiveCamera()
                camera.SetPosition(*preset_opt.position)
                camera.SetFocalPoint(*preset_opt.focal_point)
                camera.SetViewUp(*preset_opt.up_vector)
                if preset_opt.parallel_projection:
                    camera.ParallelProjectionOn()
                    self.projection_action.setChecked(False)
                    self.projection_action.setText("Orthographic")
                else:
                    camera.ParallelProjectionOff()
                    self.projection_action.setChecked(True)
                    self.projection_action.setText("Perspective")
                self.vtk_widget.renderer.ResetCameraClippingRange()
                self.vtk_widget.render()
                self.statusBar().showMessage(f"Loaded preset: {preset_name}")

        self.presets_combo.setCurrentIndex(0)


if __name__ == "__main__":
    print(f"[OK] {CameraToolbarMixin.__name__} imports cleanly")
