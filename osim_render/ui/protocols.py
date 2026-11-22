"""Type protocols for UI mixins.

Defines comprehensive protocol interfaces for all MainWindow capabilities.
Allows mixins to properly type-check self parameter without full inheritance.
"""

from typing import Any, Optional, Protocol, runtime_checkable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar, QStatusBar, QToolBar

from osim_render.ui.vtk_widget import VTKWidget
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.managers.settings_manager import SettingsManager


# =============================================================================
# CAPABILITY PROTOCOLS - Mixin-specific requirements
# =============================================================================


class CanManageMenuBar(Protocol):
    """Protocol for menu bar management (QMainWindow capability)."""

    def menuBar(self) -> QMenuBar:
        ...


class CanAddToolBar(Protocol):
    """Protocol for toolbar management (QMainWindow capability)."""

    def addToolBar(self, text: str) -> QToolBar:
        ...

    def addToolBarBreak(self) -> None:
        ...


class CanShowStatus(Protocol):
    """Protocol for status bar and window management (QMainWindow capability)."""

    def statusBar(self) -> QStatusBar:
        ...

    def close(self) -> bool:
        ...


class HasVTKWidget(Protocol):
    """Protocol for classes that have a VTK widget."""

    vtk_widget: VTKWidget


class HasSceneManager(Protocol):
    """Protocol for classes that have a scene manager."""

    scene_manager: Optional[SceneManager]


class HasSettingsManager(Protocol):
    """Protocol for classes that have a settings manager."""

    settings_manager: SettingsManager


class HasEventHandlers(Protocol):
    """Protocol for event handler methods that mixins call."""

    def _on_open_model(self) -> None:
        ...

    def _on_open_motion(self) -> None:
        ...

    def _on_set_geometry_path(self) -> None:
        ...

    def _on_reset_camera(self) -> None:
        ...

    def _on_toggle_scripting_panel(self, checked: bool) -> None:
        ...

    def _on_toggle_projection(self) -> None:
        ...

    def _on_camera_front(self) -> None:
        ...

    def _on_camera_back(self) -> None:
        ...

    def _on_camera_top(self) -> None:
        ...

    def _on_camera_bottom(self) -> None:
        ...

    def _on_camera_left(self) -> None:
        ...

    def _on_camera_right(self) -> None:
        ...

    def _on_preset_selected(self, index: int) -> None:
        ...

    def _on_play(self) -> None:
        ...

    def _on_pause(self) -> None:
        ...

    def _on_speed_changed(self, speed: float) -> None:
        ...

    def _on_frame_slider_moved(self, value: int) -> None:
        ...

    def _on_body_item_toggled(self, body_name: str, visible: bool) -> None:
        ...

    def _on_body_origin_item_toggled(self, body_name: str, visible: bool) -> None:
        ...

    def _on_body_mass_center_item_toggled(self, body_name: str, visible: bool) -> None:
        ...

    def _on_joint_parent_item_toggled(self, joint_name: str, visible: bool) -> None:
        ...

    def _on_joint_child_item_toggled(self, joint_name: str, visible: bool) -> None:
        ...

    def _on_contact_force_item_toggled(self, force_name: str, visible: bool) -> None:
        ...

    def _on_contact_item_toggled(self, contact_name: str, visible: bool) -> None:
        ...

    def _on_muscle_item_toggled(self, muscle_name: str, visible: bool) -> None:
        ...

    def _on_wrap_actor_item_toggled(self, wrap_name: str, visible: bool) -> None:
        ...

    def _on_ground_reaction_item_toggled(self, source_name: str, visible: bool) -> None:
        ...

    def _populate_ground_reaction_menu(self, source_names: list[str]) -> None:
        ...

    def _on_category_show_all(self, category: str) -> None:
        ...

    def _on_category_hide_all(self, category: str) -> None:
        ...

    def _on_follow_body_changed(self, body_name: str) -> None:
        ...

    def _populate_follow_bodies(self, body_names: list[str]) -> None:
        ...

    def _load_saved_presets(self) -> None:
        ...

    def _populate_recent_models_menu(self) -> None:
        ...

    def _populate_recent_motions_menu(self) -> None:
        ...

    def _populate_recent_scripts_menu(self) -> None:
        ...

    def _on_open_recent_model(self, filepath: str) -> None:
        ...

    def _on_open_recent_motion(self, filepath: str) -> None:
        ...

    def _on_open_recent_script(self, filepath: str) -> None:
        ...


class HasUIAttributes(Protocol):
    """Protocol for UI attributes that mixins set."""

    scripting_panel_action: QAction
    play_action: QAction
    pause_action: QAction
    projection_action: QAction
    presets_combo: Any
    speed_control: Any
    frame_slider: Any
    frame_label: Any
    vis_state_manager: Any
    property_manager: Any
    bodies_button: Any
    body_origins_button: Any
    body_mass_centers_button: Any
    joint_parents_button: Any
    joint_children_button: Any
    contacts_button: Any
    muscles_button: Any
    contact_forces_button: Any
    ground_reactions_button: Any
    follow_body_combo: Any
    wrap_actors_button: Any
    recent_models_menu: Any
    recent_motions_menu: Any
    recent_scripts_menu: Any


# =============================================================================
# MIXIN-SPECIFIC PROTOCOLS
# =============================================================================


class MenubarMixinProtocol(
    CanManageMenuBar,
    CanShowStatus,
    HasEventHandlers,
    HasUIAttributes,
    Protocol,
):
    """Protocol for MenubarMixin requirements."""

    pass


class ToolbarMixinProtocol(
    CanAddToolBar,
    HasEventHandlers,
    HasUIAttributes,
    Protocol,
):
    """Protocol for ToolbarMixin requirements."""

    pose_mode_action: QAction
    pin_root_action: QAction
    root_gizmo_action: QAction
    open_grf_action: QAction

    def _on_pose_mode_toggled(self, enabled: bool) -> None:
        """Handle the drag-to-pose toolbar toggle."""
        ...

    def _on_pin_root_toggled(self, pinned: bool) -> None:
        """Handle the pin-root toolbar toggle."""
        ...

    def _on_root_gizmo_toggled(self, shown: bool) -> None:
        """Handle the base gizmo toolbar toggle."""
        ...

    def _on_open_grf(self) -> None:
        """Handle the open ground reactions action."""
        ...


class CameraToolbarMixinProtocol(
    CanAddToolBar,
    CanShowStatus,
    HasVTKWidget,
    HasSceneManager,
    HasSettingsManager,
    HasEventHandlers,
    HasUIAttributes,
    Protocol,
):
    """Protocol for CameraToolbarMixin requirements."""

    pass


class VisualizationToolbarMixinProtocol(
    CanAddToolBar,
    HasVTKWidget,
    HasSceneManager,
    HasEventHandlers,
    HasUIAttributes,
    Protocol,
):
    """Protocol for VisualizationToolbarMixin requirements."""

    pass


# =============================================================================
# MAIN WINDOW PROTOCOL - Full capability definition
# =============================================================================


@runtime_checkable
class MainWindowProtocol(
    CanManageMenuBar,
    CanAddToolBar,
    CanShowStatus,
    HasVTKWidget,
    HasSceneManager,
    HasSettingsManager,
    HasEventHandlers,
    HasUIAttributes,
    Protocol,
):
    """Complete protocol for MainWindow.

    Describes the full interface that MainWindow implements,
    allowing all mixins to properly type-check their self parameter.
    This ensures:
    - All required methods are declared
    - All required attributes are declared
    - Mixins can safely call these methods/access these attributes
    - Type checker verifies correctness at definition time
    """

    pass
