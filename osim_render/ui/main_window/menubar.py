"""Menu bar mixin for the main application window."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QAction

if TYPE_CHECKING:
    from osim_render.ui.protocols import MenubarMixinProtocol


class MenubarMixin:
    """Mixin for menu bar setup and event handling."""

    def _setup_menubar(self: "MenubarMixinProtocol") -> None:
        """Create application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_model_action = QAction("Open Model", cast(QWidget, self))
        open_model_action.setShortcut("Ctrl+O")
        open_model_action.triggered.connect(self._on_open_model)
        file_menu.addAction(open_model_action)

        open_motion_action = QAction("Open Motion File", cast(QWidget, self))
        open_motion_action.setShortcut("Ctrl+M")
        open_motion_action.triggered.connect(self._on_open_motion)
        file_menu.addAction(open_motion_action)

        # Recent models submenu
        self.recent_models_menu = file_menu.addMenu("Recent Models")
        self.recent_models_menu.aboutToShow.connect(
            self._populate_recent_models_menu)

        # Recent motions submenu
        self.recent_motions_menu = file_menu.addMenu("Recent Motions")
        self.recent_motions_menu.aboutToShow.connect(
            self._populate_recent_motions_menu)

        file_menu.addSeparator()

        set_geometry_path_action = QAction(
            "Set Geometry Path...", cast(QWidget, self))
        set_geometry_path_action.setStatusTip(
            "Add custom geometry search path")
        set_geometry_path_action.triggered.connect(self._on_set_geometry_path)
        file_menu.addAction(set_geometry_path_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", cast(QWidget, self))
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("View")

        reset_camera_action = QAction("Reset Camera", cast(QWidget, self))
        reset_camera_action.setShortcut("R")
        reset_camera_action.triggered.connect(self._on_reset_camera)
        view_menu.addAction(reset_camera_action)

        view_menu.addSeparator()

        self.scripting_panel_action = QAction(
            "Animation Scripts", cast(QWidget, self))
        self.scripting_panel_action.setCheckable(True)
        self.scripting_panel_action.setChecked(False)
        self.scripting_panel_action.triggered.connect(
            self._on_toggle_scripting_panel)
        view_menu.addAction(self.scripting_panel_action)

        view_menu.addSeparator()

        # Recent scripts submenu
        self.recent_scripts_menu = view_menu.addMenu("Recent Scripts")
        self.recent_scripts_menu.aboutToShow.connect(
            self._populate_recent_scripts_menu)


if __name__ == "__main__":
    print(f"[OK] {MenubarMixin.__name__} imports cleanly")
