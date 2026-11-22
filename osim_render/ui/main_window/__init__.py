"""Main application window package.

Re-exports the window class and its mixins so existing imports such as
``from osim_render.ui.main_window import MainWindow`` keep working after the
module was split into a package.
"""

from osim_render.ui.main_window.menubar import MenubarMixin
from osim_render.ui.main_window.toolbar import ToolbarMixin
from osim_render.ui.main_window.camera_toolbar import CameraToolbarMixin
from osim_render.ui.main_window.visualization_toolbar import (
    VisualizationToolbarMixin,
)
from osim_render.ui.main_window.window import MainWindow

__all__ = [
    "MainWindow",
    "MenubarMixin",
    "ToolbarMixin",
    "CameraToolbarMixin",
    "VisualizationToolbarMixin",
]
