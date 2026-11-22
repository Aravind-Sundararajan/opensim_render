"""Main toolbar mixin for the main application window."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtWidgets import (
    QLabel,
    QDoubleSpinBox,
    QSlider,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

if TYPE_CHECKING:
    from osim_render.ui.protocols import ToolbarMixinProtocol


class ToolbarMixin:
    """Mixin for main toolbar with file operations and playback controls."""

    def _setup_toolbar(self: "ToolbarMixinProtocol") -> None:
        """Create main toolbar."""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setObjectName("MainToolbar")

        open_model_action = QAction("Open Model", cast(QWidget, self))
        open_model_action.setStatusTip("Open an OpenSim model")
        open_model_action.triggered.connect(self._on_open_model)
        toolbar.addAction(open_model_action)

        open_motion_action = QAction("Open Motion", cast(QWidget, self))
        open_motion_action.setStatusTip("Open a motion file (.sto/.mot)")
        open_motion_action.triggered.connect(self._on_open_motion)
        toolbar.addAction(open_motion_action)

        self.open_grf_action = QAction("Open GRF", cast(QWidget, self))
        self.open_grf_action.setStatusTip(
            "Open ground reaction forces (ExternalLoads .xml, or .mot/.sto)"
        )
        self.open_grf_action.setEnabled(False)
        self.open_grf_action.triggered.connect(self._on_open_grf)
        toolbar.addAction(self.open_grf_action)

        toolbar.addSeparator()

        # Drag-to-pose toggle (Ctrl+drag works without enabling this)
        self.pose_mode_action = QAction("Pose", cast(QWidget, self))
        self.pose_mode_action.setStatusTip(
            "Drag bodies to pose the model with OpenSim IK (or hold Ctrl and drag)"
        )
        self.pose_mode_action.setCheckable(True)
        self.pose_mode_action.setEnabled(False)
        self.pose_mode_action.toggled.connect(self._on_pose_mode_toggled)
        toolbar.addAction(self.pose_mode_action)

        self.pin_root_action = QAction("Pin Root", cast(QWidget, self))
        self.pin_root_action.setStatusTip(
            "Hold the model's floating base still while posing, so dragging "
            "articulates joints instead of moving the whole model"
        )
        self.pin_root_action.setCheckable(True)
        self.pin_root_action.setEnabled(False)
        self.pin_root_action.toggled.connect(self._on_pin_root_toggled)
        toolbar.addAction(self.pin_root_action)

        self.root_gizmo_action = QAction("Base Gizmo", cast(QWidget, self))
        self.root_gizmo_action.setStatusTip(
            "Show a transform gizmo for placing and orienting the multibody tree base"
        )
        self.root_gizmo_action.setCheckable(True)
        self.root_gizmo_action.setEnabled(False)
        self.root_gizmo_action.toggled.connect(self._on_root_gizmo_toggled)
        toolbar.addAction(self.root_gizmo_action)

        toolbar.addSeparator()

        # Playback controls
        self.play_action = QAction("Play", cast(QWidget, self))
        self.play_action.setStatusTip("Play motion")
        self.play_action.triggered.connect(self._on_play)
        self.play_action.setEnabled(False)
        toolbar.addAction(self.play_action)

        self.pause_action = QAction("Pause", cast(QWidget, self))
        self.pause_action.setStatusTip("Pause motion")
        self.pause_action.triggered.connect(self._on_pause)
        self.pause_action.setEnabled(False)
        toolbar.addAction(self.pause_action)

        toolbar.addSeparator()

        # Playback speed control
        toolbar.addWidget(QLabel("Speed:"))
        self.speed_control = QDoubleSpinBox()
        self.speed_control.setRange(0.1, 5.0)
        self.speed_control.setValue(1.0)
        self.speed_control.setSingleStep(0.1)
        self.speed_control.setDecimals(1)
        self.speed_control.setSuffix("x")
        self.speed_control.setMaximumWidth(60)
        self.speed_control.setStatusTip("Playback speed (0.1x to 5.0x)")
        self.speed_control.valueChanged.connect(self._on_speed_changed)
        toolbar.addWidget(self.speed_control)

        toolbar.addSeparator()

        # Frame slider
        toolbar.addWidget(QLabel("Frame:"))
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMaximum(0)
        self.frame_slider.setMaximumWidth(200)
        self.frame_slider.sliderMoved.connect(self._on_frame_slider_moved)
        toolbar.addWidget(self.frame_slider)

        self.frame_label = QLabel("0/0")
        self.frame_label.setMaximumWidth(50)
        toolbar.addWidget(self.frame_label)


if __name__ == "__main__":
    print(f"[OK] {ToolbarMixin.__name__} imports cleanly")
