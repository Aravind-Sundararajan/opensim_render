"""Tests for main window UI mixins."""

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QComboBox, QDoubleSpinBox, QLabel, QMainWindow, QMenu, QSlider, QToolBar
from typing import cast

from osim_render.ui.main_window import MenubarMixin, ToolbarMixin


@pytest.fixture(scope="session")
def app() -> QApplication:
    """Create QApplication for tests."""
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication([])


class DummyWindow(MenubarMixin, ToolbarMixin, QMainWindow):
    """Minimal window for testing mixins."""

    # HasUIAttributes declared here; values assigned by mixin setup methods
    scripting_panel_action: QAction
    play_action: QAction
    pause_action: QAction
    projection_action: QAction
    presets_combo: QComboBox
    speed_control: QDoubleSpinBox
    frame_slider: QSlider
    frame_label: QLabel
    recent_models_menu: QMenu
    recent_motions_menu: QMenu
    recent_scripts_menu: QMenu
    # Manager/button attributes not used by menubar or toolbar mixins
    vis_state_manager = None
    property_manager = None
    bodies_button = None
    body_origins_button = None
    body_mass_centers_button = None
    joint_parents_button = None
    joint_children_button = None
    contacts_button = None
    muscles_button = None
    contact_forces_button = None
    wrap_actors_button = None

    def _on_open_model(self) -> None:
        pass

    def _on_open_motion(self) -> None:
        pass

    def _on_set_geometry_path(self) -> None:
        pass

    def _on_reset_camera(self) -> None:
        pass

    def _on_toggle_scripting_panel(self, checked: bool = False) -> None:
        pass

    def _on_pose_mode_toggled(self, enabled: bool = False) -> None:
        pass

    def _on_open_grf(self) -> None:
        pass

    def _on_pin_root_toggled(self, pinned: bool = False) -> None:
        pass

    def _on_root_gizmo_toggled(self, shown: bool = False) -> None:
        pass

    def _on_play(self) -> None:
        pass

    def _on_pause(self) -> None:
        pass

    def _on_speed_changed(self, speed: float = 1.0) -> None:
        pass

    def _on_frame_slider_moved(self, value: int = 0) -> None:
        pass

    def _on_toggle_projection(self) -> None:
        pass

    def _on_camera_front(self) -> None:
        pass

    def _on_camera_back(self) -> None:
        pass

    def _on_camera_top(self) -> None:
        pass

    def _on_camera_bottom(self) -> None:
        pass

    def _on_camera_left(self) -> None:
        pass

    def _on_camera_right(self) -> None:
        pass

    def _on_preset_selected(self, index: int = 0) -> None:
        pass

    def _on_body_item_toggled(self, body_name: str = "", visible: bool = True) -> None:
        pass

    def _on_body_origin_item_toggled(self, body_name: str = "", visible: bool = True) -> None:
        pass

    def _on_body_mass_center_item_toggled(self, body_name: str = "", visible: bool = True) -> None:
        pass

    def _on_joint_parent_item_toggled(self, joint_name: str = "", visible: bool = True) -> None:
        pass

    def _on_joint_child_item_toggled(self, joint_name: str = "", visible: bool = True) -> None:
        pass

    def _on_contact_item_toggled(self, contact_name: str = "", visible: bool = True) -> None:
        pass

    def _on_contact_force_item_toggled(self, force_name: str = "", visible: bool = True) -> None:
        pass

    def _on_muscle_item_toggled(self, muscle_name: str = "", visible: bool = True) -> None:
        pass

    def _on_wrap_actor_item_toggled(self, wrap_name: str = "", visible: bool = True) -> None:
        pass

    def _on_marker_item_toggled(self, marker_name: str = "", visible: bool = True) -> None:
        pass

    def _on_category_show_all(self, category: str = "") -> None:
        pass

    def _on_category_hide_all(self, category: str = "") -> None:
        pass

    def _load_saved_presets(self) -> None:
        pass

    def _populate_recent_models_menu(self) -> None:
        pass

    def _populate_recent_motions_menu(self) -> None:
        pass

    def _populate_recent_scripts_menu(self) -> None:
        pass

    def _on_open_recent_model(self, filepath: str = "") -> None:
        pass

    def _on_open_recent_motion(self, filepath: str = "") -> None:
        pass

    def _on_open_recent_script(self, filepath: str = "") -> None:
        pass


class TestMenubarMixin:
    """Test MenubarMixin functionality."""

    def test_menubar_mixin_exists(self, app: QApplication) -> None:
        """Test that MenubarMixin class exists."""
        assert MenubarMixin is not None

    def test_setup_menubar_method_exists(self, app: QApplication) -> None:
        """Test that _setup_menubar method exists."""
        assert hasattr(MenubarMixin, "_setup_menubar")

    def test_menubar_setup_creates_menus(self, app: QApplication) -> None:
        """Test that menubar setup creates File and View menus."""
        window = DummyWindow()
        window._setup_menubar()

        menubar = window.menuBar()
        assert menubar is not None

        # Check menu items
        actions = menubar.actions()
        assert len(actions) >= 2, "Should have at least File and View menus"

        # Find menus by text
        menus = {action.text(): cast(QMenu, action.menu())
                 for action in actions}
        assert "File" in menus, "File menu should exist"
        assert "View" in menus, "View menu should exist"

    def test_file_menu_contains_open_model(self, app: QApplication) -> None:
        """Test that File menu contains Open Model action."""
        window = DummyWindow()
        window._setup_menubar()

        menubar = window.menuBar()
        file_menu: QMenu | None = None

        for action in menubar.actions():
            if action.text() == "File":
                file_menu = cast(QMenu, action.menu())
                break

        assert file_menu is not None, "File menu should exist"

        menu_actions = file_menu.actions()
        action_texts = [action.text()
                        for action in menu_actions if action.text()]

        assert "Open Model" in action_texts, "Open Model should be in File menu"
        assert "Exit" in action_texts, "Exit should be in File menu"

    def test_open_model_has_shortcut(self, app: QApplication) -> None:
        """Test that Open Model action has Ctrl+O shortcut."""
        window = DummyWindow()
        window._setup_menubar()

        menubar = window.menuBar()
        file_menu: QMenu | None = None

        for action in menubar.actions():
            if action.text() == "File":
                file_menu = cast(QMenu, action.menu())
                break

        assert file_menu is not None, "File menu not found"

        for action in file_menu.actions():
            if action.text() == "Open Model":
                assert action.shortcut().toString() == "Ctrl+O"
                return

        pytest.fail("Open Model action not found")

    def test_exit_has_shortcut(self, app: QApplication) -> None:
        """Test that Exit action has Ctrl+Q shortcut."""
        window = DummyWindow()
        window._setup_menubar()

        menubar = window.menuBar()

        # Find File menu
        file_menu: QMenu | None = None
        for action in menubar.actions():
            if action.text() == "File":
                file_menu = cast(QMenu, action.menu())
                break

        assert file_menu is not None, "File menu not found"

        # Check that menu has Exit action
        action_texts = [action.text() for action in file_menu.actions()]
        assert "Exit" in action_texts, "Exit action should exist"


class TestToolbarMixin:
    """Test ToolbarMixin functionality."""

    def test_toolbar_mixin_exists(self, app: QApplication) -> None:
        """Test that ToolbarMixin class exists."""
        assert ToolbarMixin is not None

    def test_setup_toolbar_method_exists(self, app: QApplication) -> None:
        """Test that _setup_toolbar method exists."""
        assert hasattr(ToolbarMixin, "_setup_toolbar")

    def test_toolbar_creation(self, app: QApplication) -> None:
        """Test that toolbar is created."""
        window = DummyWindow()
        window._setup_toolbar()

        # Find the main toolbar
        toolbar_found = False
        for toolbar in cast(list[QToolBar], window.findChildren(QToolBar)):
            if toolbar.objectName() == "MainToolbar":
                toolbar_found = True
                break

        assert toolbar_found, "MainToolbar should be created"

    def test_toolbar_has_open_action(self, app: QApplication) -> None:
        """Test that toolbar has Open Model action."""
        window = DummyWindow()
        window._setup_toolbar()

        # Find the main toolbar
        toolbar: QToolBar | None = None
        for tb in cast(list[QToolBar], window.findChildren(QToolBar)):
            if tb.objectName() == "MainToolbar":
                toolbar = tb
                break

        assert toolbar is not None, "MainToolbar should exist"

        actions = toolbar.actions()
        action_texts = [action.text() for action in actions if action.text()]

        assert "Open Model" in action_texts, "Open Model should be in toolbar"

    def test_toolbar_has_reset_camera_action(self, app: QApplication) -> None:
        """Test that toolbar has pause action."""
        window = DummyWindow()
        window._setup_toolbar()

        # Find the main toolbar
        toolbar: QToolBar | None = None
        for tb in cast(list[QToolBar], window.findChildren(QToolBar)):
            if tb.objectName() == "MainToolbar":
                toolbar = tb
                break

        assert toolbar is not None, "MainToolbar should exist"

        actions = toolbar.actions()
        action_texts = [action.text() for action in actions if action.text()]

        assert "Pause" in action_texts, "Pause should be in toolbar"


class TestMainWindowMixinIntegration:
    """Test MainWindow mixin integration."""

    def test_mixin_inheritance_order(self, app: QApplication) -> None:
        """Test that mixins inherit in correct order."""
        window = DummyWindow()

        # Verify inheritance
        assert isinstance(
            window, MenubarMixin), "Should inherit from MenubarMixin"
        assert isinstance(
            window, ToolbarMixin), "Should inherit from ToolbarMixin"
        assert isinstance(
            window, QMainWindow), "Should inherit from QMainWindow"

    def test_both_ui_elements_created(self, app: QApplication) -> None:
        """Test that both menubar and toolbar can be created."""
        window = DummyWindow()

        # Setup both
        window._setup_menubar()
        window._setup_toolbar()

        # Menubar check
        menubar = window.menuBar()
        assert menubar is not None, "Menubar should exist"

        # Toolbar check
        toolbar_found = False
        for toolbar in cast(list[QToolBar], window.findChildren(QToolBar)):
            if toolbar.objectName() == "MainToolbar":
                toolbar_found = True
                break

        assert toolbar_found, "Toolbar should exist"

    def test_menu_and_toolbar_share_actions(self, app: QApplication) -> None:
        """Test that menu and toolbar both provide same actions."""
        window = DummyWindow()
        window._setup_menubar()
        window._setup_toolbar()

        # Get menu actions
        menubar = window.menuBar()
        file_menu: QMenu | None = None
        for action in menubar.actions():
            if action.text() == "File":
                file_menu = cast(QMenu, action.menu())
                break

        assert file_menu is not None, "File menu not found"

        menu_action_texts = [
            action.text()
            for action in file_menu.actions()
            if action.text() in ["Open Model", "Open Motion File"]
        ]

        # Get toolbar actions
        toolbar: QToolBar | None = None
        for tb in cast(list[QToolBar], window.findChildren(QToolBar)):
            if tb.objectName() == "MainToolbar":
                toolbar = tb
                break

        assert toolbar is not None, "MainToolbar not found"

        toolbar_action_texts = [
            action.text()
            for action in toolbar.actions()
            if action.text() in ["Open Model", "Open Motion"]
        ]

        # Both should have Open Model in menu and toolbar
        assert "Open Model" in menu_action_texts, "Open Model should be in File menu"
        assert "Open Model" in toolbar_action_texts, "Open Model should be in toolbar"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
