"""Scene construction for OpenSim model visualization.

Builds a RenderScene with all bodies and VTK components positioned by the
current model state, delegating per-actor positioning to actor_transforms.
"""

from __future__ import annotations

from typing import Any

import vtkmodules.all as vtk

from osim_render.api.rendering.render_scene import RenderScene
from osim_render.api.rendering.actor_transforms import (
    update_body_position,
    create_mass_center_actor,
)
from osim_render.api.rendering.body_visualizer import BodyVisualizer
from osim_render.api.rendering.frame_visualizer import FrameVisualizer
from osim_render.api.rendering.joint_visualizer import JointVisualizer
from osim_render.api.rendering.contact_visualizer import ContactVisualizer
from osim_render.api.rendering.contact_force_visualizer import ContactForceVisualizer
from osim_render.api.rendering.marker_visualizer import MarkerVisualizer
from osim_render.api.rendering.muscle_visualizer import MuscleVisualizer
from osim_render.api.rendering.wrap_visualizer import WrapVisualizer
from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


class SceneBuilder:
    """Build a RenderScene from an OpenSim model and its visualizers."""

    def __init__(
        self,
        opensim_model: Any,
        state: Any,
        visualizer: BodyVisualizer,
        frame_visualizer: FrameVisualizer,
        joint_visualizer: JointVisualizer,
        contact_visualizer: ContactVisualizer,
        contact_force_visualizer: ContactForceVisualizer,
        marker_visualizer: MarkerVisualizer,
        muscle_visualizer: MuscleVisualizer,
        wrap_visualizer: WrapVisualizer,
    ):
        """Initialize scene builder.

        Args:
            opensim_model: Shared OpenSim model
            state: Shared OpenSim model state
            visualizer: Body geometry visualizer
            frame_visualizer: Body origin frame visualizer
            joint_visualizer: Joint frame visualizer
            contact_visualizer: Contact geometry visualizer
            contact_force_visualizer: Contact force arrow visualizer
            marker_visualizer: Marker visualizer
            muscle_visualizer: Muscle path visualizer
            wrap_visualizer: Wrap object visualizer
        """
        self.opensim_model = opensim_model
        self.state = state
        self.visualizer = visualizer
        self.frame_visualizer = frame_visualizer
        self.joint_visualizer = joint_visualizer
        self.contact_visualizer = contact_visualizer
        self.contact_force_visualizer = contact_force_visualizer
        self.marker_visualizer = marker_visualizer
        self.muscle_visualizer = muscle_visualizer
        self.wrap_visualizer = wrap_visualizer

    def build(self, renderer: vtk.vtkRenderer | None = None) -> RenderScene:
        """Create VTK scene with all bodies positioned by current state.

        Args:
            renderer: Optional existing VTK renderer. If None, creates a new one.

        Returns:
            RenderScene with actors and VTK components
        """
        if renderer is None:
            renderer = vtk.vtkRenderer()
            render_window = vtk.vtkRenderWindow()
            render_window.AddRenderer(renderer)
            interactor = vtk.vtkRenderWindowInteractor()
            interactor.SetRenderWindow(render_window)
            renderer.SetBackground(0.2, 0.2, 0.2)
        else:
            render_window = renderer.GetRenderWindow()
            interactor = render_window.GetInteractor()

        # 15% expansion for safety margin when bodies move toward/away from camera
        renderer.SetClippingRangeExpansion(0.15)

        actors = {}
        if self.opensim_model is not None:
            bodies_with_geometry = 0
            bodies_skipped = 0

            for body in self.opensim_model.getBodyList():
                body_name = body.getName()
                body_visuals = self.visualizer.create_body_actor(body_name)
                if not body_visuals:
                    bodies_skipped += 1
                    logger.debug(f"Body '{body_name}' has no geometry")
                    continue

                bodies_with_geometry += 1
                actor = body_visuals.actor
                update_body_position(
                    actor, body_name, self.opensim_model, self.state
                )
                renderer.AddActor(actor)
                actors[body_name] = actor

            if bodies_skipped > 0:
                logger.info(
                    f"Created {bodies_with_geometry} body actors, {bodies_skipped} bodies have no geometry"
                )

        body_origin_actors = self.frame_visualizer.create_all_frame_actors()
        for body_name, frame_actor in body_origin_actors.items():
            self.frame_visualizer.update_frame_position(frame_actor, body_name)
            frame_actor.SetVisibility(False)  # Default: hidden
            renderer.AddActor(frame_actor)

        body_mass_center_actors = {}
        if self.opensim_model is not None:
            ground_name = self.opensim_model.getGround().getName()
            for body in self.opensim_model.getBodyList():
                body_name = body.getName()
                # Skip ground body
                if body_name == ground_name:
                    continue
                mass_actor = create_mass_center_actor(
                    body_name, self.opensim_model, self.state
                )
                if mass_actor:
                    mass_actor.SetVisibility(False)  # Default: hidden
                    renderer.AddActor(mass_actor)
                    body_mass_center_actors[body_name] = mass_actor

        joint_parent_actors = {}
        joint_child_actors = {}
        joint_all_actors = self.joint_visualizer.create_all_joint_actors()
        for joint_name, (parent_actor, child_actor) in joint_all_actors.items():
            # Get joint for position updates
            if self.opensim_model is not None:
                joint = self.opensim_model.getJointSet().get(joint_name)
                if joint is not None:
                    self.joint_visualizer.update_joint_positions(
                        parent_actor, child_actor, joint
                    )

            parent_actor.SetVisibility(False)  # Default: hidden
            child_actor.SetVisibility(False)
            renderer.AddActor(parent_actor)
            renderer.AddActor(child_actor)

            joint_parent_actors[joint_name] = parent_actor
            joint_child_actors[joint_name] = child_actor

        (
            contact_actors,
            contact_metadata,
        ) = self.contact_visualizer.create_all_contact_actors()
        for contact_actor in contact_actors.values():
            contact_actor.SetVisibility(False)  # Default: hidden
            renderer.AddActor(contact_actor)

        if contact_actors and contact_metadata:
            self.contact_visualizer.update_contact_positions(
                contact_actors, contact_metadata
            )

        (
            contact_force_actors,
            contact_force_metadata,
        ) = self.contact_force_visualizer.create_all_contact_force_actors()
        for force_actor in contact_force_actors.values():
            force_actor.SetVisibility(False)  # Default: hidden
            renderer.AddActor(force_actor)

        (
            marker_actors,
            marker_metadata,
        ) = self.marker_visualizer.create_all_marker_actors()
        for marker_actor in marker_actors.values():
            marker_actor.SetVisibility(False)  # Default: hidden
            renderer.AddActor(marker_actor)

        muscle_actors = self.muscle_visualizer.create_all_muscle_actors()
        for muscle_actor in muscle_actors.values():
            muscle_actor.SetVisibility(False)  # Default: hidden
            renderer.AddActor(muscle_actor)

        wrap_actors = self.wrap_visualizer.create_all_wrap_actors()
        for wrap_actor in wrap_actors.values():
            wrap_actor.SetVisibility(False)  # Default: hidden
            renderer.AddActor(wrap_actor)

        renderer.ResetCamera()

        model_name = (
            self.opensim_model.getName()
            if self.opensim_model is not None
            else "Unknown"
        )
        return RenderScene(
            model_name=model_name,
            renderer=renderer,
            render_window=render_window,
            interactor=interactor,
            actors=actors,
            body_origin_actors=body_origin_actors,
            body_mass_center_actors=body_mass_center_actors,
            joint_parent_actors=joint_parent_actors,
            joint_child_actors=joint_child_actors,
            contact_actors=contact_actors,
            contact_metadata=contact_metadata,
            contact_force_actors=contact_force_actors,
            contact_force_metadata=contact_force_metadata,
            # Ground reactions arrive with a data file rather than the model,
            # so the scene starts with an empty slot the SceneManager fills in.
            ground_reaction_actors={},
            marker_actors=marker_actors,
            marker_metadata=marker_metadata,
            muscle_actors=muscle_actors,
            wrap_actors=wrap_actors,
        )


if __name__ == "__main__":
    print("[OK] scene_builder imports cleanly")
