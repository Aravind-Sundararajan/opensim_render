"""Visualization toolbar mixin for the main application window."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, cast

from PySide6.QtWidgets import QWidget

from osim_render.api.managers.visualization_state_manager import (
    VisualizationStateManager,
)
from osim_render.api.managers.property_control_manager import (
    PropertyControlManager,
)
from osim_render.ui.widgets.visualization_toolbutton import VisualizationToolButton

if TYPE_CHECKING:
    from osim_render.ui.protocols import MainWindowProtocol
    from osim_render.ui.vtk_widget import VTKWidget
    from osim_render.api.rendering.scene import SceneManager


class VisualizationToolbarMixin:
    """Mixin for visualization element toggle controls with individual item visibility."""

    if TYPE_CHECKING:
        vtk_widget: VTKWidget
        scene_manager: Optional[SceneManager]

    def _setup_visualization_toolbar(self: MainWindowProtocol) -> None:
        """Create toolbar with individual item visibility controls."""
        # Its own row: the element toggles alone are wider than the main and
        # camera toolbars combined, so sharing a row pushes them off screen.
        self.addToolBarBreak()

        toolbar = self.addToolBar("Visualization")
        toolbar.setObjectName("VisualizationToolbar")

        self.vis_state_manager = VisualizationStateManager()

        self.property_manager: PropertyControlManager | None = None

        # Bodies button
        self.bodies_button = VisualizationToolButton(
            "Bodies", cast(QWidget, self))
        self.bodies_button.setStatusTip(
            "Toggle body geometry visibility - click arrow for individual bodies"
        )
        self.bodies_button.setEnabled(False)
        self.bodies_button.item_toggled.connect(self._on_body_item_toggled)
        self.bodies_button.show_all_clicked.connect(
            lambda: self._on_category_show_all("bodies")
        )
        self.bodies_button.hide_all_clicked.connect(
            lambda: self._on_category_hide_all("bodies")
        )
        toolbar.addWidget(self.bodies_button)

        toolbar.addSeparator()

        # Body origin button
        self.body_origins_button = VisualizationToolButton(
            "Body Origins", cast(QWidget, self)
        )
        self.body_origins_button.setStatusTip(
            "Toggle body origin frame visibility")
        self.body_origins_button.setEnabled(False)
        self.body_origins_button.item_toggled.connect(
            self._on_body_origin_item_toggled)
        self.body_origins_button.show_all_clicked.connect(
            lambda: self._on_category_show_all("body_origins")
        )
        self.body_origins_button.hide_all_clicked.connect(
            lambda: self._on_category_hide_all("body_origins")
        )
        toolbar.addWidget(self.body_origins_button)

        # Body mass center button
        self.body_mass_centers_button = VisualizationToolButton(
            "Body Mass Centers", cast(QWidget, self)
        )
        self.body_mass_centers_button.setStatusTip(
            "Toggle body mass center visibility")
        self.body_mass_centers_button.setEnabled(False)
        self.body_mass_centers_button.item_toggled.connect(
            self._on_body_mass_center_item_toggled
        )
        self.body_mass_centers_button.show_all_clicked.connect(
            lambda: self._on_category_show_all("body_mass_centers")
        )
        self.body_mass_centers_button.hide_all_clicked.connect(
            lambda: self._on_category_hide_all("body_mass_centers")
        )
        toolbar.addWidget(self.body_mass_centers_button)

        toolbar.addSeparator()

        # Joint parent button
        self.joint_parents_button = VisualizationToolButton(
            "Joint Parents", cast(QWidget, self)
        )
        self.joint_parents_button.setStatusTip(
            "Toggle joint parent frame visibility")
        self.joint_parents_button.setEnabled(False)
        self.joint_parents_button.item_toggled.connect(
            self._on_joint_parent_item_toggled
        )
        self.joint_parents_button.show_all_clicked.connect(
            lambda: self._on_category_show_all("joint_parents")
        )
        self.joint_parents_button.hide_all_clicked.connect(
            lambda: self._on_category_hide_all("joint_parents")
        )
        toolbar.addWidget(self.joint_parents_button)

        # Joint child button
        self.joint_children_button = VisualizationToolButton(
            "Joint Children", cast(QWidget, self)
        )
        self.joint_children_button.setStatusTip(
            "Toggle joint child frame visibility")
        self.joint_children_button.setEnabled(False)
        self.joint_children_button.item_toggled.connect(
            self._on_joint_child_item_toggled
        )
        self.joint_children_button.show_all_clicked.connect(
            lambda: self._on_category_show_all("joint_children")
        )
        self.joint_children_button.hide_all_clicked.connect(
            lambda: self._on_category_hide_all("joint_children")
        )
        toolbar.addWidget(self.joint_children_button)

        toolbar.addSeparator()

        # Contacts button
        self.contacts_button = VisualizationToolButton(
            "Contacts", cast(QWidget, self))
        self.contacts_button.setStatusTip("Toggle contact geometry visibility")
        self.contacts_button.setEnabled(False)
        self.contacts_button.item_toggled.connect(
            self._on_contact_item_toggled)
        self.contacts_button.show_all_clicked.connect(
            lambda: self._on_category_show_all("contacts")
        )
        self.contacts_button.hide_all_clicked.connect(
            lambda: self._on_category_hide_all("contacts")
        )
        toolbar.addWidget(self.contacts_button)

        # Muscles button
        self.muscles_button = VisualizationToolButton(
            "Muscles", cast(QWidget, self))
        self.muscles_button.setStatusTip(
            "Toggle muscle path visibility - click arrow for individual muscles"
        )
        self.muscles_button.setEnabled(False)
        self.muscles_button.item_toggled.connect(self._on_muscle_item_toggled)
        self.muscles_button.show_all_clicked.connect(
            lambda: self._on_category_show_all("muscles")
        )
        self.muscles_button.hide_all_clicked.connect(
            lambda: self._on_category_hide_all("muscles")
        )
        toolbar.addWidget(self.muscles_button)

        # Contact Forces button
        self.contact_forces_button = VisualizationToolButton(
            "Contact Forces", cast(QWidget, self)
        )
        self.contact_forces_button.setStatusTip(
            "Toggle contact force vector visibility - "
            "click arrow for individual contact forces"
        )
        self.contact_forces_button.setEnabled(False)
        self.contact_forces_button.item_toggled.connect(
            self._on_contact_force_item_toggled
        )
        self.contact_forces_button.show_all_clicked.connect(
            lambda: self._on_category_show_all("contact_forces")
        )
        self.contact_forces_button.hide_all_clicked.connect(
            lambda: self._on_category_hide_all("contact_forces")
        )
        toolbar.addWidget(self.contact_forces_button)

        # Ground Reactions button
        self.ground_reactions_button = VisualizationToolButton(
            "Ground Reactions", cast(QWidget, self)
        )
        self.ground_reactions_button.setStatusTip(
            "Toggle recorded ground reaction force visibility - "
            "load a GRF file to enable"
        )
        self.ground_reactions_button.setEnabled(False)
        self.ground_reactions_button.item_toggled.connect(
            self._on_ground_reaction_item_toggled
        )
        self.ground_reactions_button.show_all_clicked.connect(
            lambda: self._on_category_show_all("ground_reactions")
        )
        self.ground_reactions_button.hide_all_clicked.connect(
            lambda: self._on_category_hide_all("ground_reactions")
        )
        toolbar.addWidget(self.ground_reactions_button)

        # Wrap Objects button
        self.wrap_actors_button = VisualizationToolButton(
            "Wrap Objects", cast(QWidget, self)
        )
        self.wrap_actors_button.setStatusTip(
            "Toggle wrap object visibility (cylinders, ellipsoids) - "
            "click arrow for individual wrap objects"
        )
        self.wrap_actors_button.setEnabled(False)
        self.wrap_actors_button.item_toggled.connect(
            self._on_wrap_actor_item_toggled)
        self.wrap_actors_button.show_all_clicked.connect(
            lambda: self._on_category_show_all("wrap_actors")
        )
        self.wrap_actors_button.hide_all_clicked.connect(
            lambda: self._on_category_hide_all("wrap_actors")
        )
        toolbar.addWidget(self.wrap_actors_button)

    def _populate_visualization_menus(self) -> None:
        """Populate dropdown menus with individual items from the scene."""
        if not self.scene_manager or not self.scene_manager.get_scene():
            return

        scene = self.scene_manager.get_scene()
        if not scene:
            return

        # Populate bodies menu
        body_names = list(scene.actors.keys()) if scene.actors else []
        self.bodies_button.populate_menu(body_names, default_visible=True)
        self.vis_state_manager.initialize_category(
            "bodies", body_names, default_visible=True
        )

        # Populate body origins menu
        body_origin_names = (
            list(scene.body_origin_actors.keys()
                 ) if scene.body_origin_actors else []
        )
        self.body_origins_button.populate_menu(
            body_origin_names, default_visible=False)
        self.vis_state_manager.initialize_category(
            "body_origins", body_origin_names, default_visible=False
        )

        # Populate body mass centers menu
        body_mass_center_names = (
            list(scene.body_mass_center_actors.keys())
            if scene.body_mass_center_actors
            else []
        )
        self.body_mass_centers_button.populate_menu(
            body_mass_center_names, default_visible=False
        )
        self.vis_state_manager.initialize_category(
            "body_mass_centers", body_mass_center_names, default_visible=False
        )

        # Populate joint parents menu
        joint_parent_names = (
            list(scene.joint_parent_actors.keys()
                 ) if scene.joint_parent_actors else []
        )
        self.joint_parents_button.populate_menu(
            joint_parent_names, default_visible=False
        )
        self.vis_state_manager.initialize_category(
            "joint_parents", joint_parent_names, default_visible=False
        )

        # Populate joint children menu
        joint_child_names = (
            list(scene.joint_child_actors.keys()
                 ) if scene.joint_child_actors else []
        )
        self.joint_children_button.populate_menu(
            joint_child_names, default_visible=False
        )
        self.vis_state_manager.initialize_category(
            "joint_children", joint_child_names, default_visible=False
        )

        # Populate contacts menu
        contact_names = (
            list(scene.contact_actors.keys()) if scene.contact_actors else []
        )
        self.contacts_button.populate_menu(
            contact_names, default_visible=False)
        self.vis_state_manager.initialize_category(
            "contacts", contact_names, default_visible=False
        )

        # Populate muscles menu
        muscle_names = list(scene.muscle_actors.keys()
                            ) if scene.muscle_actors else []
        self.muscles_button.populate_menu(muscle_names, default_visible=False)
        self.vis_state_manager.initialize_category(
            "muscles", muscle_names, default_visible=False
        )

        # Populate contact forces menu
        contact_force_names = (
            list(scene.contact_force_actors.keys())
            if scene.contact_force_actors
            else []
        )
        self.contact_forces_button.populate_menu(
            contact_force_names, default_visible=False
        )
        self.vis_state_manager.initialize_category(
            "contact_forces", contact_force_names, default_visible=False
        )
        self.contact_forces_button.setEnabled(bool(contact_force_names))

        # Populate wrap objects menu
        wrap_actor_names = list(scene.wrap_actors.keys()
                                ) if scene.wrap_actors else []
        self.wrap_actors_button.populate_menu(
            wrap_actor_names, default_visible=False)
        self.vis_state_manager.initialize_category(
            "wrap_actors", wrap_actor_names, default_visible=False
        )
        self.wrap_actors_button.setEnabled(True)

    def _on_body_item_toggled(self, body_name: str, visible: bool) -> None:
        """Handle individual body visibility toggle."""
        if self.property_manager:
            self.property_manager.set_visibility(
                body_name, visible, category="bodies")
            self.vtk_widget.render()

    def _on_body_origin_item_toggled(self, body_name: str, visible: bool) -> None:
        """Handle individual body origin visibility toggle."""
        if self.property_manager:
            self.property_manager.set_visibility(
                body_name, visible, category="body_origins")
            self.vtk_widget.render()

    def _on_body_mass_center_item_toggled(self, body_name: str, visible: bool) -> None:
        """Handle individual body mass center visibility toggle."""
        if self.property_manager:
            self.property_manager.set_visibility(
                body_name, visible, category="body_mass_centers")
            self.vtk_widget.render()

    def _on_joint_parent_item_toggled(self, joint_name: str, visible: bool) -> None:
        """Handle individual joint parent visibility toggle."""
        if self.property_manager:
            self.property_manager.set_visibility(
                joint_name, visible, category="joint_parents")
            self.vtk_widget.render()

    def _on_joint_child_item_toggled(self, joint_name: str, visible: bool) -> None:
        """Handle individual joint child visibility toggle."""
        if self.property_manager:
            self.property_manager.set_visibility(
                joint_name, visible, category="joint_children")
            self.vtk_widget.render()

    def _on_contact_item_toggled(self, contact_name: str, visible: bool) -> None:
        """Handle individual contact visibility toggle."""
        if self.property_manager:
            self.property_manager.set_visibility(
                contact_name, visible, category="contacts")
            self.vtk_widget.render()

    def _on_muscle_item_toggled(self, muscle_name: str, visible: bool) -> None:
        """Handle individual muscle visibility toggle."""
        if self.property_manager:
            self.property_manager.set_visibility(
                muscle_name, visible, category="muscles")
            self.vtk_widget.render()

    def _on_contact_force_item_toggled(self, force_name: str, visible: bool) -> None:
        """Handle individual contact force visibility toggle."""
        if self.property_manager:
            self.property_manager.set_visibility(
                force_name, visible, category="contact_forces")
            self.vtk_widget.render()

    def _on_ground_reaction_item_toggled(self, source_name: str, visible: bool) -> None:
        """Handle individual ground reaction visibility toggle."""
        if self.property_manager:
            self.property_manager.set_visibility(
                source_name, visible, category="ground_reactions")
            self.vtk_widget.render()

    def _populate_ground_reaction_menu(self, source_names: list[str]) -> None:
        """Fill the ground reactions menu after a GRF file is loaded.

        Ground reactions arrive with a data file rather than the model, so
        this runs separately from the other visualization menus.

        Args:
            source_names: Names of the loaded ground reaction sources
        """
        self.ground_reactions_button.populate_menu(
            source_names, default_visible=False
        )
        self.vis_state_manager.initialize_category(
            "ground_reactions", source_names, default_visible=False
        )
        self.ground_reactions_button.setEnabled(bool(source_names))

        if self.property_manager:
            self.property_manager.rebuild_actor_registry()

    def _on_wrap_actor_item_toggled(self, wrap_name: str, visible: bool) -> None:
        """Handle individual wrap object visibility toggle."""
        if self.property_manager:
            self.property_manager.set_visibility(
                wrap_name, visible, category="wrap_actors")
            self.vtk_widget.render()

    def _on_category_show_all(self, category: str) -> None:
        """Show all items in a category."""
        if self.property_manager:
            self.property_manager.set_category_visibility(category, True)
            self.vtk_widget.render()

    def _on_category_hide_all(self, category: str) -> None:
        """Hide all items in a category."""
        if self.property_manager:
            self.property_manager.set_category_visibility(category, False)
            self.vtk_widget.render()

    def _clear_visualization_menus(self) -> None:
        """Clear all visualization menus (called on model unload)."""
        self.bodies_button.populate_menu([], False)
        self.body_origins_button.populate_menu([], False)
        self.body_mass_centers_button.populate_menu([], False)
        self.joint_parents_button.populate_menu([], False)
        self.joint_children_button.populate_menu([], False)
        self.contacts_button.populate_menu([], False)
        self.muscles_button.populate_menu([], False)
        self.contact_forces_button.populate_menu([], False)
        self.wrap_actors_button.populate_menu([], False)

        # Disable all buttons
        self.bodies_button.setEnabled(False)
        self.body_origins_button.setEnabled(False)
        self.body_mass_centers_button.setEnabled(False)
        self.joint_parents_button.setEnabled(False)
        self.joint_children_button.setEnabled(False)
        self.contacts_button.setEnabled(False)
        self.muscles_button.setEnabled(False)
        self.contact_forces_button.setEnabled(False)
        self.wrap_actors_button.setEnabled(False)

        self.vis_state_manager.clear()


if __name__ == "__main__":
    print(f"[OK] {VisualizationToolbarMixin.__name__} imports cleanly")
