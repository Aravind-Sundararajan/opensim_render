"""Main application window."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QToolBar,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction

from osim_render.api.managers.event_bus import (
    EventBus,
    Event,
    event_handler,
    auto_subscribe_all_events,
)
from osim_render.api.managers.events import EventType
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.managers.settings_manager import (
    SettingsManager,
)
from osim_render.api.managers.visualization_state_manager import (
    VisualizationStateManager,
)
from osim_render.api.managers.property_control_manager import (
    PropertyControlManager,
)
from osim_render.ui.vtk_widget import VTKWidget
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.posing.pose_controller import DragPoseController
from osim_render.ui.interaction.root_gizmo import RootGizmo
from osim_render.api.loaders.motion_loader import MotionLoader, MotionData
from osim_render.ui.panels.coordinate_slider_panel import CoordinateSliderPanel
from osim_render.ui.widgets.visualization_toolbutton import VisualizationToolButton
from osim_render.api.logging import get_logger_for
from osim_render.api.animation.integration import AnimationManager
from osim_render.api.animation.script_executor import ScriptExecutor
from osim_render.ui.panels.scripting_panel import ScriptingPanel
from osim_render.api.rendering.animation_renderer import (
    AnimationRenderer,
    RenderConfig,
)
from osim_render.api.animation.timeline import Timeline
from osim_render.ui.main_window.menubar import MenubarMixin
from osim_render.ui.main_window.toolbar import ToolbarMixin
from osim_render.ui.main_window.camera_toolbar import CameraToolbarMixin
from osim_render.ui.main_window.visualization_toolbar import (
    VisualizationToolbarMixin,
)

logger = get_logger_for(__name__)


class MainWindow(
    MenubarMixin,
    ToolbarMixin,
    CameraToolbarMixin,
    VisualizationToolbarMixin,
    QMainWindow,
):
    """Main application window.

    Provides 3D viewport and docking panels for model interaction.
    Uses mixin classes for menu bar and toolbar setup.
    """

    if TYPE_CHECKING:
        # UI elements created by mixin setup methods - declared for type checking
        scripting_panel_action: QAction
        play_action: QAction
        pause_action: QAction
        projection_action: QAction
        presets_combo: Any
        speed_control: Any
        frame_slider: Any
        frame_label: Any
        vis_state_manager: VisualizationStateManager
        bodies_button: "VisualizationToolButton"
        body_origins_button: "VisualizationToolButton"
        body_mass_centers_button: "VisualizationToolButton"
        joint_parents_button: "VisualizationToolButton"
        joint_children_button: "VisualizationToolButton"
        contacts_button: "VisualizationToolButton"
        muscles_button: "VisualizationToolButton"
        wrap_actors_button: "VisualizationToolButton"

    def __init__(
        self,
        event_bus: EventBus,
        model_manager: ModelManager,
        settings_manager: SettingsManager,
    ):
        """Initialize main window.

        Args:
            event_bus: Application event bus
            model_manager: Model state manager
            settings_manager: Settings manager
        """
        super().__init__()

        _self = cast(Any, self)
        del _self  # Only used for type declaration

        self.event_bus = event_bus
        self.model_manager = model_manager
        self.settings_manager = settings_manager

        # Visualization state
        self.scene_manager: SceneManager | None = None
        self.motion_data: MotionData | None = None
        self.pose_controller: DragPoseController | None = None
        self.root_gizmo: RootGizmo | None = None

        # Unified animation renderer for all playback (motion data + scripts)
        self.renderer: AnimationRenderer | None = None
        self.playback_timer = QTimer()

        self.setWindowTitle("OpenSim Renderer")
        self.resize(1200, 800)

        self.vtk_widget = VTKWidget()
        self.setCentralWidget(self.vtk_widget)

        mw = cast(Any, self)
        MenubarMixin._setup_menubar(mw)
        ToolbarMixin._setup_toolbar(mw)
        CameraToolbarMixin._setup_camera_toolbar(mw)
        VisualizationToolbarMixin._setup_visualization_toolbar(mw)

        from osim_render.api.ui.coordinate_panel.controller import (
            CoordinatePanelController,
        )

        self.coord_panel = CoordinateSliderPanel(
            self.event_bus, self.model_manager, self
        )
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.coord_panel)

        self.coord_controller = CoordinatePanelController(
            self.model_manager, self.event_bus
        )

        # Animation system integration
        self.animation_manager = AnimationManager(
            self.model_manager,
            self.scene_manager,
            self.event_bus,
        )
        # Script executor for animation scripting
        self.script_executor = ScriptExecutor(
            self.model_manager,
            self.scene_manager,
            self.event_bus,
            vis_state_manager=self.vis_state_manager,
        )
        self.scripting_panel = ScriptingPanel(
            self.script_executor,
            self,
        )
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.scripting_panel)
        self.scripting_panel.hide()  # Initially hidden

        # Auto-subscribe all @event_handler decorated methods
        auto_subscribe_all_events(self, self.event_bus)

    def _init_unified_renderer(self, timeline: Timeline) -> None:
        """Initialize or update the unified animation renderer.

        Args:
            timeline: Timeline to load into renderer
        """
        if not self.scene_manager:
            logger.warning("Cannot initialize renderer: no scene manager")
            return

        # Verify timeline has data
        if not timeline.animations:
            logger.warning("Timeline has no animations")
            return

        if self.renderer is None:
            config = RenderConfig(fps=30)
            self.renderer = AnimationRenderer(
                self.scene_manager,
                timer=cast(Any, self.playback_timer),
                config=config,
                timeline=timeline,
            )
            self.renderer.set_frame_callback(self._on_renderer_frame_update)
        else:
            self.renderer.set_timeline(timeline)

    def _on_renderer_frame_update(self, current_frame: int, total_frames: int) -> None:
        """Handle frame update from renderer.

        Args:
            current_frame: Current frame index
            total_frames: Total number of frames
        """
        if not self.renderer or not self.frame_slider or not self.renderer.timeline:
            return

        self.frame_slider.blockSignals(True)
        # Convert time to slider position
        current_time = self.renderer._current_time
        slider_value = int(
            (current_time / self.renderer.timeline.duration) * 1000
            if self.renderer.timeline.duration > 0
            else 0
        )
        self.frame_slider.setValue(slider_value)
        self.frame_slider.blockSignals(False)

        current_time = self.renderer._current_time
        total_time = self.renderer.timeline.duration
        self.frame_label.setText(f"{current_time:.1f}s / {total_time:.1f}s")

        if self.coord_panel:
            animation_state = self.renderer.timeline.get_state_at_time(
                current_time)
            self.coord_panel.update_sliders_from_motion_frame(animation_state)

        # Render the VTK widget to display the updated animation frame
        self.vtk_widget.render()

    def _on_open_model(self) -> None:
        """Handle open model action."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open OpenSim Model",
            "",
            "OpenSim Files (*.osim);;All Files (*)",
        )

        if filepath:
            model_name = Path(filepath).stem
            self.model_manager.load_model(filepath, model_name)

            settings = self.settings_manager.get_settings()
            settings = settings.with_recent_model(filepath)
            self.settings_manager.update_settings(settings)

    def _on_reset_camera(self) -> None:
        """Handle reset camera action."""
        self.vtk_widget.reset_camera()

    def _setup_drag_posing(self) -> None:
        """Wire drag-to-pose to the freshly loaded model and scene."""
        rig = self.model_manager.get_drag_rig()
        if rig is None:
            logger.warning("No drag rig available, posing disabled")
            return

        self.pose_controller = DragPoseController(
            self.scene_manager, rig, self.event_bus
        )
        self.vtk_widget.set_pose_controller(self.pose_controller)
        self.pose_mode_action.setEnabled(True)

        self._setup_root_controls()

    def _model_body_names(self) -> list[str]:
        """Names of the loaded model's bodies, in model order.

        Returns:
            Body names, or empty when no model is loaded
        """
        model = self.model_manager.get_opensim_model()
        if model is None:
            return []

        return [body.getName() for body in model.getBodySet()]

    def _setup_root_controls(self) -> None:
        """Enable root pinning and the base gizmo when the model supports them."""
        controller = self.pose_controller
        if controller is None:
            return

        can_pin = controller.can_pin_root
        self.pin_root_action.setEnabled(can_pin)
        self.pin_root_action.blockSignals(True)
        self.pin_root_action.setChecked(controller.pin_root)
        self.pin_root_action.blockSignals(False)

        self.root_gizmo = self._build_root_gizmo()
        self.root_gizmo_action.setEnabled(self.root_gizmo is not None)
        self.root_gizmo_action.blockSignals(True)
        self.root_gizmo_action.setChecked(False)
        self.root_gizmo_action.blockSignals(False)

    def _build_root_gizmo(self) -> RootGizmo | None:
        """Create a base gizmo if the root joint can be driven by one.

        Returns:
            RootGizmo, or None when the root is not a six-axis base
        """
        controller = self.pose_controller
        if controller is None or controller.root is None:
            return None

        if not controller.root.supports_gizmo:
            logger.info("Root joint does not support a transform gizmo")
            return None

        return RootGizmo(
            self.scene_manager,
            controller.root,
            controller.applier,
            self.vtk_widget.renderer,
            self.vtk_widget.iren,
        )

    def _on_pin_root_toggled(self, pinned: bool) -> None:
        """Handle the pin-root toolbar toggle.

        Args:
            pinned: True to hold the floating base still while posing
        """
        if self.pose_controller is None:
            return

        self.pose_controller.set_pin_root(pinned)
        message = (
            "Root pinned - dragging articulates joints"
            if pinned
            else "Root free - dragging may move the whole model"
        )
        self.statusBar().showMessage(message, 3000)

    def _on_root_gizmo_toggled(self, shown: bool) -> None:
        """Handle the base gizmo toolbar toggle.

        Args:
            shown: True to display the gizmo
        """
        if self.root_gizmo is None:
            return

        self.root_gizmo.set_enabled(shown)
        self.vtk_widget.render()

    @event_handler(EventType.POSE_DRAG_ENDED)
    def _on_pose_drag_ended(self, event: Event) -> None:
        """Keep the base gizmo aligned after a drag moved the model.

        Args:
            event: Event describing the finished drag
        """
        if self.root_gizmo is None or not self.root_gizmo.is_enabled:
            return

        self.root_gizmo.sync_from_model()
        self.vtk_widget.render()

    def _on_pose_mode_toggled(self, enabled: bool) -> None:
        """Handle the pose mode toolbar toggle.

        Args:
            enabled: True when posing should respond to plain left-drag
        """
        self.vtk_widget.set_pose_mode_enabled(enabled)
        message = (
            "Pose mode ON - drag bodies to pose with IK"
            if enabled
            else "Pose mode OFF - hold Ctrl and drag to pose"
        )
        self.statusBar().showMessage(message, 3000)

    @event_handler(EventType.MODEL_LOADED)
    def _on_model_loaded(self, event: Event) -> None:
        """Handle model loaded event.

        Args:
            event: Event object with model data
        """
        name = event.data.get("name", "Unknown")
        filepath = event.data.get("filepath", "")

        if filepath:
            self.scene_manager = SceneManager(
                self.model_manager,
                filepath,
                geometry_search_paths=self.settings_manager.get_settings().geometry_search_paths,
            )

            self.vtk_widget.renderer.RemoveAllViewProps()

            self.scene_manager.set_visualization_state(self.vis_state_manager)
            self.scene_manager.create_scene(renderer=self.vtk_widget.renderer)

            self.property_manager = PropertyControlManager(
                self.scene_manager,
                self.vis_state_manager,
                self.event_bus,
            )
            self.scene_manager.property_manager = self.property_manager

            self.vtk_widget.renderer.ResetCamera()
            self.vtk_widget.render()

            self._setup_drag_posing()

            self.coord_panel.set_scene_manager(self.scene_manager)

            self.animation_manager.scene_manager = self.scene_manager

            # Populate visualization menus and enable buttons
            self._populate_visualization_menus()
            self.bodies_button.setEnabled(True)
            self.body_origins_button.setEnabled(True)
            self.body_mass_centers_button.setEnabled(True)
            self.joint_parents_button.setEnabled(True)
            self.joint_children_button.setEnabled(True)
            self.contacts_button.setEnabled(True)
            self.muscles_button.setEnabled(True)
            self.wrap_actors_button.setEnabled(True)
            self.open_grf_action.setEnabled(True)
            self._populate_follow_bodies(self._model_body_names())

            self.statusBar().showMessage(
                f"Loaded model: {name} (Ready for motion data)"
            )
        else:
            self.statusBar().showMessage(f"Loaded model: {name}")

    @event_handler(EventType.MODEL_LOADING_FAILED)
    def _on_model_load_failed(self, event: Event) -> None:
        """Handle model load failed event.

        Args:
            event: Event object with error data
        """
        error = event.data.get("error", "Unknown error")
        QMessageBox.critical(self, "Load Failed",
                             f"Failed to load model: {error}")

    @event_handler(EventType.MODEL_UNLOADED)
    def _on_model_unloaded(self, event: Event) -> None:
        """Handle model unload event.

        Args:
            event: Event object
        """
        self._clear_visualization_menus()
        self.scene_manager = None

    def _on_open_grf(self) -> None:
        """Handle open ground reaction forces action."""
        if not self.scene_manager:
            QMessageBox.warning(self, "No Model", "Please load a model first")
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Ground Reaction Forces",
            "",
            "Ground Reactions (*.xml *.mot *.sto);;All Files (*)",
        )

        if not filepath:
            return

        self._load_ground_reactions(Path(filepath), announce=True)

    def _try_auto_load_ground_reactions(self, motion_path: Path) -> None:
        """Load ground reactions sitting alongside a motion file, if any.

        Trials are usually distributed as a motion plus a matching *_grf file,
        so finding one saves a second trip through the file dialog.

        Args:
            motion_path: Path of the motion file just opened
        """
        candidate = self._find_sibling_ground_reactions(motion_path)
        if candidate is None:
            return

        logger.info(f"Found ground reactions alongside the motion: {candidate.name}")
        self._load_ground_reactions(candidate, announce=True)

    def _find_sibling_ground_reactions(self, motion_path: Path) -> Path | None:
        """Look for a ground reaction file next to a motion file.

        Args:
            motion_path: Path of the motion file

        Returns:
            The GRF file to load, preferring an ExternalLoads XML, or None
        """
        matches = sorted(
            path
            for pattern in ("*grf*.xml", "*GRF*.xml", "*grf*.mot", "*grf*.sto")
            for path in motion_path.parent.glob(pattern)
        )
        if not matches:
            return None

        # An ExternalLoads XML names its own columns, so prefer it over raw data.
        for path in matches:
            if path.suffix.lower() == ".xml":
                return path

        return matches[0]

    def _load_ground_reactions(self, path: Path, announce: bool) -> None:
        """Load a ground reaction file into the scene and wire up its menu.

        Args:
            path: ExternalLoads XML or .mot/.sto data file
            announce: Whether to report the outcome in the status bar
        """
        if self.scene_manager is None:
            return

        try:
            source_names = self.scene_manager.load_ground_reactions(path)
        except (FileNotFoundError, ValueError, RuntimeError) as error:
            logger.warning(f"Could not load ground reactions from {path}: {error}")
            QMessageBox.warning(self, "Ground Reactions", str(error))
            return

        self._populate_ground_reaction_menu(list(source_names))
        self.vtk_widget.render()

        if announce:
            self.statusBar().showMessage(
                f"Loaded {len(source_names)} ground reaction sources from {path.name}",
                5000,
            )

    def _on_open_motion(self) -> None:
        """Handle open motion file action."""
        if not self.scene_manager:
            QMessageBox.warning(self, "No Model", "Please load a model first")
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Motion File",
            "",
            "Motion Files (*.sto *.mot);;All Files (*)",
        )

        if not filepath:
            return

        model = self.model_manager.get_opensim_model()

        motion_loader = MotionLoader()
        self.motion_data = motion_loader.load(filepath, model=model)

        self._try_auto_load_ground_reactions(Path(filepath))

        # Make motion data available to scripts
        self.script_executor.motion_data = self.motion_data

        validation = motion_loader.validate_motion(self.motion_data, model)

        # Log validation warnings if any
        if validation.warnings:
            for warning in validation.warnings:
                logger.warning(f"Motion validation: {warning}")

        animation = self.animation_manager.create_animation_from_motion(
            self.motion_data, name=Path(filepath).stem
        )
        timeline = Timeline(animations=(animation,))

        self._init_unified_renderer(timeline)

        self.frame_slider.setMaximum(1000)  # 0-1000 for time-based scrubbing
        self.frame_slider.setValue(0)

        # Enable playback controls
        self.play_action.setEnabled(True)
        self.pause_action.setEnabled(True)

        # Re-enable contact forces button if actors exist (may have been missed at model load)
        if self.scene_manager:
            scene = self.scene_manager.get_scene()
            if scene and scene.contact_force_actors:
                self.contact_forces_button.setEnabled(True)

        settings = self.settings_manager.get_settings()
        settings = settings.with_recent_motion(filepath)
        self.settings_manager.update_settings(settings)

        self.event_bus.publish_event(
            EventType.ANIMATION_TIMELINE_LOADED,
            data={"timeline": timeline, "source": "motion_file"},
        )

        # Show motion info in status bar
        motion_duration = self.motion_data.end_time - self.motion_data.start_time
        status = (
            f"Loaded motion: {Path(filepath).name} | "
            f"{self.motion_data.num_frames} frames | "
            f"{motion_duration:.2f}s | "
            f"Valid: {validation.is_valid}"
        )
        self.statusBar().showMessage(status)

    def _on_set_geometry_path(self) -> None:
        """Handle set geometry path action."""
        geometry_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Geometry Directory",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if not geometry_dir:
            return

        new_settings = self.settings_manager.get_settings().add_geometry_search_path(
            geometry_dir
        )
        self.settings_manager.update_settings(new_settings)

        self.statusBar().showMessage(f"Added geometry path: {geometry_dir}")

        # Reload current model if one is loaded
        if self.scene_manager:
            # Recreate scene manager with updated search paths
            from osim_render.api.rendering.scene import SceneManager

            self.scene_manager = SceneManager(
                self.model_manager,
                self.scene_manager.model_path,
                geometry_search_paths=new_settings.geometry_search_paths,
            )

            self.vtk_widget.renderer.RemoveAllViewProps()
            self.scene_manager.create_scene(renderer=self.vtk_widget.renderer)

            self.vtk_widget.renderer.ResetCamera()
            self.vtk_widget.render()

            self.coord_panel.set_scene_manager(self.scene_manager)

            self.statusBar().showMessage(
                f"Reloaded model with new geometry path: {geometry_dir}"
            )

    def _on_toggle_scripting_panel(self, checked: bool) -> None:
        """Handle scripting panel toggle.

        Args:
            checked: Whether panel should be shown
        """
        if checked:
            self.scripting_panel.show()
        else:
            self.scripting_panel.hide()

    def _populate_recent_models_menu(self) -> None:
        """Dynamically populate recent models menu."""
        self.recent_models_menu.clear()
        settings = self.settings_manager.get_settings()

        if not settings.recent_models:
            action = self.recent_models_menu.addAction("(no recent models)")
            action.setEnabled(False)
            return

        for filepath in settings.recent_models:
            action = self.recent_models_menu.addAction(Path(filepath).name)
            action.setStatusTip(filepath)
            action.triggered.connect(
                lambda checked=False, path=filepath: self._on_open_recent_model(
                    path)
            )

    def _populate_recent_motions_menu(self) -> None:
        """Dynamically populate recent motions menu."""
        self.recent_motions_menu.clear()
        settings = self.settings_manager.get_settings()

        if not settings.recent_motions:
            action = self.recent_motions_menu.addAction("(no recent motions)")
            action.setEnabled(False)
            return

        for filepath in settings.recent_motions:
            action = self.recent_motions_menu.addAction(Path(filepath).name)
            action.setStatusTip(filepath)
            action.triggered.connect(
                lambda checked=False, path=filepath: self._on_open_recent_motion(
                    path)
            )

    def _populate_recent_scripts_menu(self) -> None:
        """Dynamically populate recent scripts menu."""
        self.recent_scripts_menu.clear()
        settings = self.settings_manager.get_settings()

        if not settings.recent_scripts:
            action = self.recent_scripts_menu.addAction("(no recent scripts)")
            action.setEnabled(False)
            return

        for filepath in settings.recent_scripts:
            action = self.recent_scripts_menu.addAction(Path(filepath).name)
            action.setStatusTip(filepath)
            action.triggered.connect(
                lambda checked=False, path=filepath: self._on_open_recent_script(
                    path)
            )

    def _on_open_recent_model(self, filepath: str) -> None:
        """Open a recent model file.

        Args:
            filepath: Path to model file
        """
        model_name = Path(filepath).stem
        self.model_manager.load_model(filepath, model_name)

        settings = self.settings_manager.get_settings()
        settings = settings.with_recent_model(filepath)
        self.settings_manager.update_settings(settings)

    def _on_open_recent_motion(self, filepath: str) -> None:
        """Open a recent motion file.

        Args:
            filepath: Path to motion file
        """
        if not Path(filepath).exists():
            QMessageBox.warning(
                self, "File Not Found", f"Motion file not found:\n{filepath}"
            )
            return

        if not self.scene_manager:
            QMessageBox.warning(self, "No Model", "Please load a model first")
            return

        model = self.model_manager.get_opensim_model()

        motion_loader = MotionLoader()
        self.motion_data = motion_loader.load(filepath, model=model)
        self.script_executor.motion_data = self.motion_data

        # Ensure animation manager has current scene manager
        self.animation_manager.scene_manager = self.scene_manager

        animation = self.animation_manager.create_animation_from_motion(
            self.motion_data, name=Path(filepath).stem
        )

        timeline = Timeline(animations=(animation,))

        self._init_unified_renderer(timeline)

        self.frame_slider.setMaximum(1000)
        self.frame_slider.setValue(0)

        # Enable playback
        self.play_action.setEnabled(True)
        self.pause_action.setEnabled(True)

        settings = self.settings_manager.get_settings()
        settings = settings.with_recent_motion(filepath)
        self.settings_manager.update_settings(settings)

        # Show status
        self.statusBar().showMessage(f"Loaded: {Path(filepath).name}")

    def _on_open_recent_script(self, filepath: str) -> None:
        """Open a recent script file.

        Args:
            filepath: Path to script file
        """
        if not Path(filepath).exists():
            QMessageBox.warning(
                self, "File Not Found", f"Script file not found:\n{filepath}"
            )
            return

        with open(filepath, "r") as f:
            code = f.read()

        self.scripting_panel.code_editor.setPlainText(code)
        self.scripting_panel.current_script_path = Path(filepath)
        self.scripting_panel.output_console.clear()
        self.scripting_panel.status_label.setText(
            f"Loaded: {Path(filepath).name}")
        self.scripting_panel.status_label.setStyleSheet("color: blue;")

        # Show scripting panel
        self.scripting_panel_action.setChecked(True)
        self.scripting_panel.show()

        settings = self.settings_manager.get_settings()
        settings = settings.with_recent_script(filepath)
        self.settings_manager.update_settings(settings)

    def _on_play(self) -> None:
        """Handle play button press."""
        if not self.renderer:
            QMessageBox.warning(
                self, "No Animation", "Load motion data or execute a script first"
            )
            return

        self.renderer.play()
        self.play_action.setEnabled(False)
        self.pause_action.setEnabled(True)

    def _on_pause(self) -> None:
        """Handle pause button press."""
        if self.renderer:
            self.renderer.pause()
        self.play_action.setEnabled(True)
        self.pause_action.setEnabled(False)

    def _on_speed_changed(self, speed: float) -> None:
        """Handle playback speed change.

        Args:
            speed: Speed multiplier (1.0 = normal)

        Raises:
            ValueError: If speed is invalid
            AttributeError: If renderer lacks set_playback_speed method
        """
        if not self.renderer:
            return

        self.renderer.set_playback_speed(speed)

    def _on_frame_slider_moved(self, value: int) -> None:
        """Handle frame slider movement."""
        if not self.renderer or not self.renderer.timeline:
            return

        # Convert slider value (0-1000) to time
        time = (value / 1000.0) * self.renderer.timeline.duration
        self.renderer.seek(time)


if __name__ == "__main__":
    """Smoke test for main window."""
    from PySide6.QtWidgets import QApplication

    print("MainWindow smoke test")

    app = QApplication([])

    bus = EventBus()
    model_manager = ModelManager(bus)
    settings_manager = SettingsManager()

    window = MainWindow(bus, model_manager, settings_manager)

    print("[OK] Main window created")
    print("[OK] Menu bar created")
    print("[OK] Main toolbar created")
    print("[OK] Camera toolbar created with view controls")
    print("[OK] Visualization toolbar created with element toggles")
    print("[OK] VTK widget initialized")

    # Verify all toolbars
    assert window.menuBar() is not None, "Menu bar not created"
    toolbars = window.findChildren(QToolBar)
    assert len(toolbars) >= 3, "Should have at least 3 toolbars"

    toolbar_names = [tb.objectName() for tb in toolbars]
    assert "MainToolbar" in toolbar_names, "Main toolbar not found"
    assert "CameraToolbar" in toolbar_names, "Camera toolbar not found"
    assert "VisualizationToolbar" in toolbar_names, "Visualization toolbar not found"

    # Verify visualization buttons exist (AttributeError if missing)
    _ = window.bodies_button
    _ = window.body_origins_button
    _ = window.body_mass_centers_button
    _ = window.joint_parents_button
    _ = window.joint_children_button
    _ = window.contacts_button
    _ = window.muscles_button
    _ = window.wrap_actors_button
    _sm = window.vis_state_manager

    print("\n[OK] Smoke test passed!")
