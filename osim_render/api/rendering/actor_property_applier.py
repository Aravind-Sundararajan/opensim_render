"""Apply visual properties to actors in a RenderScene."""

from __future__ import annotations

from typing import Any

import vtkmodules.all as vtk

from osim_render.api.rendering.render_scene import RenderScene


class ActorPropertyApplier:
    """Apply visual properties to actors and look actors up by name."""

    def apply_actor_properties(
        self,
        scene: RenderScene | None,
        actor_properties: dict[str, dict[str, Any]],
        property_manager: Any,
    ) -> None:
        """Apply visual properties to actors.

        Uses unified PropertyControlManager if available, otherwise applies directly.

        Args:
            scene: Current RenderScene (or None)
            actor_properties: Dict mapping actor names to property dicts
                             e.g. {"pelvis": {"color": ColorValue(...), "opacity": 0.5}}
            property_manager: Optional PropertyControlManager
        """
        if not scene:
            return

        for actor_name, properties in actor_properties.items():
            if property_manager:
                for prop_name, prop_value in properties.items():
                    property_manager.set_property(actor_name, prop_name, prop_value)
            else:
                actor = self.find_actor_by_name(scene, actor_name)
                if actor is None:
                    continue

                if "color" in properties:
                    from osim_render.api.animation.value_types import ColorValue

                    color = properties["color"]
                    if isinstance(color, ColorValue):
                        actor.GetProperty().SetColor(color.r, color.g, color.b)
                        actor.GetProperty().SetOpacity(color.a)

                if "opacity" in properties:
                    opacity = properties["opacity"]
                    if isinstance(actor, vtk.vtkActor):
                        actor.GetProperty().SetOpacity(opacity)
                    else:
                        # vtkAssembly: propagate opacity to each child part so
                        # the assembly fades smoothly rather than popping in/out
                        parts = actor.GetParts()
                        parts.InitTraversal()
                        part = parts.GetNextProp3D()
                        while part is not None:
                            if isinstance(part, vtk.vtkActor):
                                part.GetProperty().SetOpacity(opacity)
                            part = parts.GetNextProp3D()
                    # Auto-show/hide based on opacity so fade_in/fade_out work on
                    # actors that start hidden (SetVisibility=0)
                    actor.SetVisibility(1 if opacity > 0 else 0)

                if "visibility" in properties:
                    actor.SetVisibility(1 if properties["visibility"] else 0)

    def find_actor_by_name(
        self, scene: RenderScene | None, actor_name: str
    ) -> Any | None:
        """Find actor in render scene by name.

        Supports an optional "category:name" prefix to target a specific actor
        category when names collide across categories (e.g. body names are reused
        for body frames and body mass centers).

        Prefixes:
            body_frame:   body origin frame assemblies  (e.g. "body_frame:femur_r")
            mass_center:  body mass center spheres      (e.g. "mass_center:pelvis")
            joint_parent: joint parent frame assemblies (e.g. "joint_parent:knee_r")
            joint_child:  joint child frame assemblies  (e.g. "joint_child:knee_r")
            contact:      contact geometry actors       (e.g. "contact:floor")
            marker:       marker actors                 (e.g. "marker:RASI")
            muscle:       muscle path actors            (e.g. "muscle:rect_fem_r")
            wrap:         wrap object actors            (e.g. "wrap:femur_r_cyl")

        Without a prefix, bodies are checked first, then muscles, wraps, contacts,
        and markers (for backward compatibility).

        Args:
            scene: Current RenderScene (or None)
            actor_name: Actor name, optionally prefixed with "category:"

        Returns:
            vtkActor/vtkAssembly or None if not found
        """
        if not scene:
            return None

        if ":" in actor_name:
            category, name = actor_name.split(":", 1)
            category_map = {
                "body_frame":   scene.body_origin_actors,
                "mass_center":  scene.body_mass_center_actors,
                "joint_parent": scene.joint_parent_actors,
                "joint_child":  scene.joint_child_actors,
                "contact":      scene.contact_actors,
                "contact_force": scene.contact_force_actors,
                "marker":       scene.marker_actors,
                "muscle":       scene.muscle_actors,
                "wrap":         scene.wrap_actors,
            }
            d = category_map.get(category)
            return d.get(name) if d else None

        for actors_dict in (
            scene.actors,
            scene.muscle_actors,
            scene.wrap_actors,
            scene.contact_actors,
            scene.contact_force_actors,
            scene.marker_actors,
        ):
            if actors_dict and actor_name in actors_dict:
                return actors_dict[actor_name]

        return None


if __name__ == "__main__":
    print("[OK] actor_property_applier imports cleanly")
