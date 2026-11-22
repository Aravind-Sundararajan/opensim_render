"""Scene management for OpenSim model visualization.

Renders bodies positioned according to model state from motion data.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Union, Optional

if TYPE_CHECKING:
    from osim_render.api.animation.value_types import CameraState

import vtkmodules.all as vtk

import opensim

from osim_render.api.rendering.render_scene import RenderScene as RenderScene
from osim_render.api.rendering.scene_builder import SceneBuilder
from osim_render.api.rendering.scene_camera_controller import SceneCameraController
from osim_render.api.rendering.actor_property_applier import ActorPropertyApplier
from osim_render.api.rendering.actor_transforms import (
    update_body_position,
    update_mass_center_position,
)
from osim_render.api.rendering.body_visualizer import BodyVisualizer
from osim_render.api.rendering.frame_visualizer import FrameVisualizer
from osim_render.api.rendering.joint_visualizer import JointVisualizer
from osim_render.api.rendering.contact_visualizer import ContactVisualizer
from osim_render.api.rendering.contact_force_visualizer import ContactForceVisualizer
from osim_render.api.rendering.marker_visualizer import MarkerVisualizer
from osim_render.api.rendering.muscle_visualizer import MuscleVisualizer
from osim_render.api.rendering.wrap_visualizer import WrapVisualizer
from osim_render.api.loaders.motion_loader import MotionFrame
from osim_render.api.loaders.grf_loader import load_ground_reactions
from osim_render.api.logging import get_logger_for
from osim_render.api.rendering.grf_visualizer import GroundReactionVisualizer
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.animation.animation import AnimationState

logger = get_logger_for(__name__)

__all__ = ["SceneManager", "RenderScene"]


class SceneManager:
    """Manage 3D visualization scene for OpenSim models.

    Renders bodies positioned according to motion data or current state.
    """

    def __init__(
        self,
        model_manager: ModelManager,
        model_path: str | Path,
        geometry_search_paths: tuple[str, ...] | None = None,
    ):
        """Initialize scene manager.

        Args:
            model_manager: Singleton ModelManager with shared model and state
            model_path: Path to OSIM file
            geometry_search_paths: Custom geometry search paths
        """
        self.model_manager = model_manager
        self.model_path = Path(model_path)
        # Use model and state from ModelManager (shared singleton)
        self.opensim_model: Any = model_manager.get_opensim_model()
        self.state: Any = model_manager.get_opensim_state()
        self.visualizer = BodyVisualizer(model_path, geometry_search_paths)
        self.frame_visualizer = FrameVisualizer(self.opensim_model, self.state)
        self.joint_visualizer = JointVisualizer(self.opensim_model, self.state)
        self.contact_visualizer = ContactVisualizer(
            self.opensim_model, self.state, model_path
        )
        self.contact_force_visualizer = ContactForceVisualizer(
            self.opensim_model, self.state, model_path
        )
        self.marker_visualizer = MarkerVisualizer(
            self.opensim_model, self.state, model_path
        )
        self.muscle_visualizer = MuscleVisualizer(self.opensim_model, self.state)
        self.wrap_visualizer = WrapVisualizer(self.opensim_model, self.state)
        self.grf_visualizer = GroundReactionVisualizer(self.opensim_model, self.state)
        # Playback time, needed by anything driven by recorded data rather
        # than by the model state.
        self.current_time = 0.0
        self.scene: Optional[RenderScene] = None
        # Track whether position stage has been realized for current state
        self._position_realized = False
        # Property control manager (will be set by main window)
        self.property_manager: Optional[Any] = None
        # Visibility state, attached by the main window. Per-frame updates that
        # own an actor's visibility must consult this so they do not override
        # the user's toggles.
        self.visualization_state: Optional[Any] = None

        # Extracted collaborators
        self._builder = SceneBuilder(
            self.opensim_model,
            self.state,
            self.visualizer,
            self.frame_visualizer,
            self.joint_visualizer,
            self.contact_visualizer,
            self.contact_force_visualizer,
            self.marker_visualizer,
            self.muscle_visualizer,
            self.wrap_visualizer,
        )
        self._camera = SceneCameraController()
        self._property_applier = ActorPropertyApplier()

    def set_current_time(self, time: float) -> None:
        """Record the playback time the scene is showing.

        Also stamped onto the OpenSim state so any consumer reading
        state.getTime() sees the frame being rendered rather than zero.

        Args:
            time: Playback time in seconds
        """
        self.current_time = time
        if self.state is not None:
            self.state.setTime(time)

    def load_ground_reactions(self, path: str | Path) -> tuple[str, ...]:
        """Load ground reaction data and add its arrows to the scene.

        Ground reactions arrive separately from the model, so the arrows are
        created here rather than during scene construction.

        Args:
            path: ExternalLoads XML, or a .mot/.sto data file

        Returns:
            Names of the loaded sources

        Raises:
            RuntimeError: If no scene has been created yet
        """
        if self.scene is None:
            raise RuntimeError("Cannot load ground reactions before a scene exists")

        data = load_ground_reactions(path)
        self.grf_visualizer.set_data(data)
        self._replace_ground_reaction_actors(self.grf_visualizer.create_actors())

        logger.info(
            f"Ground reactions loaded: {[s.name for s in data.sources]} "
            f"covering t=[{data.start_time:.3f}, {data.end_time:.3f}]"
        )
        return tuple(source.name for source in data.sources)

    def clear_ground_reactions(self) -> None:
        """Remove any loaded ground reaction arrows from the scene."""
        self.grf_visualizer.set_data(None)
        self._replace_ground_reaction_actors({})

    def _replace_ground_reaction_actors(
        self, actors: dict[str, vtk.vtkActor]
    ) -> None:
        """Swap the scene's ground reaction arrows for a new set.

        Args:
            actors: New arrows, keyed by source name
        """
        if self.scene is None or self.scene.ground_reaction_actors is None:
            return

        existing = self.scene.ground_reaction_actors
        for actor in existing.values():
            self.scene.renderer.RemoveActor(actor)
        existing.clear()

        for name, actor in actors.items():
            actor.SetVisibility(False)  # Default: hidden, like other overlays
            self.scene.renderer.AddActor(actor)
            existing[name] = actor

    def set_visualization_state(self, visualization_state: Any) -> None:
        """Attach the visibility state that per-frame updates must respect.

        Args:
            visualization_state: VisualizationStateManager holding user toggles
        """
        self.visualization_state = visualization_state

    def create_scene(self, renderer: vtk.vtkRenderer | None = None) -> RenderScene:
        """Create VTK scene with all bodies positioned by current state.

        Args:
            renderer: Optional existing VTK renderer. If None, creates a new one.

        Returns:
            RenderScene with actors and VTK components
        """
        self.scene = self._builder.build(renderer)
        return self.scene

    def _realize_position(self) -> None:
        """Realize the position stage of the model state.

        This updates all body positions based on current coordinate values.
        Sets flag to track that position stage has been realized.

        MUST be called after setting coordinate values and before
        calling update_muscle_paths() or update_wrap_positions().
        """
        if self.opensim_model is None:
            raise ValueError("opensim_model is None, cannot realize position")

        self.opensim_model.realizePosition(self.state)
        self._position_realized = True

    def _invalidate_position(self) -> None:
        """Mark position stage as invalid after coordinate changes.

        Called when coordinate values are set to indicate that
        position must be re-realized before using path information.
        """
        self._position_realized = False

    def update_frame(self, frame: Union[MotionFrame, AnimationState]) -> None:
        """Update visualization for a motion frame or animation state.

        Args:
            frame: MotionFrame or AnimationState to render
        """
        # Extract coordinate values (works for both types)
        coordinate_values = frame.coordinate_values

        self.set_current_time(frame.time)

        # Mark position as needing realization since we're changing coordinates
        self._invalidate_position()

        for coord_name, coord_value in coordinate_values.items():
            if self.opensim_model is None:
                raise ValueError("opensim_model is None, cannot update frame")

            coord = self.opensim_model.getCoordinateSet().get(coord_name)
            if not coord:
                logger.warning(f"Coordinate not found: {coord_name}")
                continue

            coord.setValue(self.state, coord_value)

        # Realize position stage for current coordinate configuration
        self._realize_position()

        if self.scene:
            self.update_all_actor_positions()

        # Handle AnimationState-specific features
        if isinstance(frame, AnimationState):
            # Update camera if present
            if frame.camera_state:
                self._apply_camera_state(frame.camera_state)

            # Update actor properties if present
            if frame.actor_properties:
                self._apply_actor_properties(frame.actor_properties)

        # Apply camera follow-body offset on top of any tween camera state
        if self._camera.is_following:
            tween_set_camera = bool(
                isinstance(frame, AnimationState) and frame.camera_state
            )
            self._apply_camera_follow(base_was_set=tween_set_camera)

        # Always reset clipping range after body positions change so moving
        # actors never get clipped regardless of whether the camera animated
        if self.scene and self.scene.renderer:
            self.scene.renderer.ResetCameraClippingRange()

        # Trigger render if we have a render window
        if self.scene and self.scene.render_window:
            self.scene.render_window.Render()

    def update_all_actor_positions(self) -> None:
        """Update all scene actors to match the current realized position.

        Single authoritative update sequence. Call after _realize_position().
        """
        if not self.scene:
            return

        for body_name, actor in self.scene.actors.items():
            update_body_position(actor, body_name, self.opensim_model, self.state)

        self.update_body_origins()
        self.update_body_mass_centers()
        self.update_joint_parent_positions()
        self.update_joint_child_positions()
        self.update_muscle_paths()
        self.update_wrap_positions()
        self.update_contact_positions()
        self.update_contact_forces()
        self.update_ground_reactions()
        self.update_marker_positions()

    def update_body_origins(self) -> None:
        """Update body origin frame positions."""
        if not self.scene or not self.scene.body_origin_actors:
            return

        for body_name, actor in self.scene.body_origin_actors.items():
            self.frame_visualizer.update_frame_position(actor, body_name)

    def update_body_mass_centers(self) -> None:
        """Update body mass center positions."""
        if not self.scene or not self.scene.body_mass_center_actors:
            return

        for body_name, actor in self.scene.body_mass_center_actors.items():
            update_mass_center_position(
                actor, body_name, self.opensim_model, self.state
            )

    def update_joint_parent_positions(self) -> None:
        """Update joint parent frame positions.

        Raises:
            AttributeError: If model or joint set operations fail
            ValueError: If joint not found
            RuntimeError: If position update fails
        """
        if not self.scene or not self.scene.joint_parent_actors:
            return

        for joint_name, parent_actor in self.scene.joint_parent_actors.items():
            self._update_single_joint_position(joint_name, parent_actor)

    def _update_single_joint_position(self, joint_name: str, parent_actor: Any) -> None:
        """Update position for a single joint's parent and child actors."""
        joint = self.opensim_model.getJointSet().get(joint_name)
        if joint is None:
            return

        if self.scene is None or self.scene.joint_child_actors is None:
            return

        child_actor = self.scene.joint_child_actors.get(joint_name)
        if child_actor is None:
            return

        self.joint_visualizer.update_joint_positions(parent_actor, child_actor, joint)

    def update_joint_child_positions(self) -> None:
        """Update joint child frame positions (handled with parent)."""
        # Child positions are updated together with parent in update_joint_parent_positions
        pass

    def update_muscle_paths(self) -> None:
        """Rebuild muscle path geometry (wrapping points change with joint angles).

        PRECONDITION: _realize_position() must have been called first
        to ensure position stage is up-to-date before recomputing paths.
        """
        assert self._position_realized, (
            "Position stage must be realized before updating muscle paths. "
            "Call _realize_position() after setting coordinate values."
        )

        if not self.scene or not self.scene.muscle_actors:
            return

        self.muscle_visualizer.update_muscle_paths(self.scene.muscle_actors)

    def update_wrap_positions(self) -> None:
        """Update wrap object positions when body poses change.

        Called when joint angles change to reposition wrap objects relative to
        their parent bodies.

        PRECONDITION: _realize_position() must have been called first
        to ensure body transforms are up-to-date.
        """
        assert self._position_realized, (
            "Position stage must be realized before updating wrap positions. "
            "Call _realize_position() after setting coordinate values."
        )

        if not self.scene or not self.scene.wrap_actors:
            return

        self.wrap_visualizer.update_wrap_positions(self.scene.wrap_actors)

    def update_contact_positions(self) -> None:
        """Update contact geometry positions when body poses change.

        Called when joint angles change to reposition contact geometries relative to
        their parent bodies.

        PRECONDITION: _realize_position() must have been called first
        to ensure body transforms are up-to-date.
        """
        assert self._position_realized, (
            "Position stage must be realized before updating contact positions. "
            "Call _realize_position() after setting coordinate values."
        )

        if (
            not self.scene
            or not self.scene.contact_actors
            or not self.scene.contact_metadata
        ):
            return

        self.contact_visualizer.update_contact_positions(
            self.scene.contact_actors, self.scene.contact_metadata
        )

    def update_marker_positions(self) -> None:
        """Update marker positions when body poses change.

        Markers are attached to bodies/frames and move with them.

        PRECONDITION: _realize_position() must have been called first
        to ensure frame transforms are up-to-date.
        """
        assert self._position_realized, (
            "Position stage must be realized before updating marker positions. "
            "Call _realize_position() after setting coordinate values."
        )

        if not self.scene or not self.scene.marker_actors:
            return

        self.marker_visualizer.update_marker_positions(self.scene.marker_actors)

    def update_contact_forces(self) -> None:
        """Update contact force arrow positions and magnitudes.

        Contact forces are computed based on current state (body positions,
        velocities, etc.). Arrows are repositioned and scaled by force magnitude.

        PRECONDITION: _realize_position() must have been called first
        to ensure body transforms are up-to-date.
        """
        assert self._position_realized, (
            "Position stage must be realized before updating contact forces. "
            "Call _realize_position() after setting coordinate values."
        )

        if (
            not self.scene
            or not self.scene.contact_force_actors
            or not self.scene.contact_force_metadata
        ):
            return

        self.contact_force_visualizer.update_contact_forces(
            self.scene.contact_force_actors,
            self.scene.contact_force_metadata,
            visible_forces=self._visible_contact_forces(),
        )

    def update_ground_reactions(self) -> None:
        """Place ground reaction arrows for the current playback time.

        Unlike contact forces these come from recorded data, so they follow
        the playback time rather than the model state.
        """
        if not self.scene or not self.scene.ground_reaction_actors:
            return

        self.grf_visualizer.update(
            self.scene.ground_reaction_actors,
            self.current_time,
            visible_sources=self._visible_category("ground_reactions"),
        )

    def _visible_contact_forces(self) -> set[str] | None:
        """Contact point keys the user currently wants displayed.

        A force acting through several spheres contributes one key per body,
        so these are contact point keys rather than force names.

        Returns:
            The visible keys, or None when the physics alone should decide
        """
        return self._visible_category("contact_forces")

    def _visible_category(self, category: str) -> set[str] | None:
        """Names in a visibility category the user currently wants displayed.

        Per-frame updates that own an actor's visibility must consult this,
        otherwise they silently override the user's toggles.

        Args:
            category: Visibility category name

        Returns:
            The visible names, or None when no visualization state is attached
        """
        if self.visualization_state is None:
            return None

        items = self.visualization_state.get_all_items(category)
        return {name for name, visible in items.items() if visible}

    def get_camera_state(self) -> "CameraState":
        """Return the current VTK camera state as a CameraState.

        Returns:
            CameraState reflecting the current camera position, focal point,
            view-up vector, zoom, and projection mode.
        """
        return self._camera.get_camera_state(self.scene)

    def set_camera_follow_body(self, body_name: str) -> None:
        """Configure the camera to follow a body during animation.

        The camera tracks the body's world position, maintaining whatever
        relative offset exists at the first frame. Camera tweens still apply
        on top — the follow offset is added after each tween is evaluated.

        Args:
            body_name: Name of the OpenSim body to follow (e.g. "pelvis")
        """
        self._camera.set_camera_follow_body(body_name)

    def clear_camera_follow(self) -> None:
        """Stop following a body, leaving the camera where it is."""
        self._camera.clear_camera_follow()

    def get_followed_body(self) -> Optional[str]:
        """Name of the body the camera is following, or None.

        Returns:
            The followed body name, or None when not following
        """
        return self._camera.followed_body

    def _apply_camera_follow(self, base_was_set: bool = False) -> None:
        """Offset camera by how far the tracked body has moved since frame 0.

        Args:
            base_was_set: True when a camera tween has just written the pose
        """
        self._camera.apply_camera_follow(
            self.scene, self.opensim_model, self.state, base_was_set=base_was_set
        )

    def _apply_camera_state(self, camera_state: Any) -> None:
        """Apply CameraState to VTK camera.

        Args:
            camera_state: CameraState with position, focal_point, view_up, zoom, etc.

        Raises:
            AttributeError: If camera_state lacks required attributes
            RuntimeError: If camera operations fail
        """
        self._camera.apply_camera_state(self.scene, camera_state)

    def _apply_actor_properties(
        self, actor_properties: dict[str, dict[str, Any]]
    ) -> None:
        """Apply visual properties to actors.

        Uses unified PropertyControlManager if available, otherwise applies directly.

        Args:
            actor_properties: Dict mapping actor names to property dicts
                             e.g. {"pelvis": {"color": ColorValue(...), "opacity": 0.5}}
        """
        self._property_applier.apply_actor_properties(
            self.scene, actor_properties, self.property_manager
        )

    def _find_actor_by_name(self, actor_name: str) -> Any | None:
        """Find actor in render scene by name.

        Args:
            actor_name: Actor name, optionally prefixed with "category:"

        Returns:
            vtkActor/vtkAssembly or None if not found
        """
        return self._property_applier.find_actor_by_name(self.scene, actor_name)

    def get_scene(self) -> RenderScene | None:
        """Get the current render scene."""
        return self.scene

    def get_model(self) -> Any:
        """Get the OpenSim model."""
        return self.opensim_model

    def get_state(self) -> Any:
        """Get the current model state."""
        return self.state


if __name__ == "__main__":
    """Smoke test for scene management."""
    opensim.Model.setDebugLevel(0)

    model_path = Path("models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim")

    if model_path.exists():
        # Create model manager first
        from osim_render.api.managers.model_manager import ModelManager
        from osim_render.api.managers.event_bus import EventBus

        event_bus = EventBus()
        model_manager = ModelManager(event_bus)
        model_manager.load_model(str(model_path), "Gait2392")

        manager = SceneManager(model_manager, model_path)
        scene = manager.create_scene()

        print(f"[OK] Created scene for model: {scene.model_name}")
        print(f"[OK] Added {len(scene.actors)} body actors to scene")
        print(
            f"[OK] Added {len(scene.body_origin_actors or {})} body origin actors to scene"
        )
        print(
            f"[OK] Added {len(scene.body_mass_center_actors or {})} body mass center actors to scene"
        )
        print(
            f"[OK] Added {len(scene.joint_parent_actors or {})} joint parent actors to scene"
        )
        print(
            f"[OK] Added {len(scene.joint_child_actors or {})} joint child actors to scene"
        )
        print(f"[OK] Added {len(scene.contact_actors or {})} contact actors to scene")
        print(f"[OK] Added {len(scene.muscle_actors or {})} muscle actors to scene")
        print(f"[OK] Scene has renderer: {scene.renderer is not None}")
        print(f"[OK] Scene has render window: {scene.render_window is not None}")

        print("\n[OK] Scene management smoke test passed!")
    else:
        print(f"[SKIP] Model not found: {model_path}")
