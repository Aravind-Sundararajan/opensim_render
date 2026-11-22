"""A transform gizmo for placing and orienting the multibody tree base.

Drag-to-pose articulates joints but deliberately holds a floating base still.
This gizmo is the counterpart: it moves the base itself, driving the root
joint's own coordinates so the model stays consistent with its mobilizer
rather than being pushed around in world space.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt
import vtkmodules.all as vtk

from osim_render.api.logging import get_logger_for
from osim_render.api.posing.model_root import ModelRoot
from osim_render.api.posing.pose_applier import PoseApplier
from osim_render.api.posing.root_transform import (
    matrix_to_root_coordinates,
    read_root_matrix,
)

logger = get_logger_for(__name__)

# 4x4 homogeneous transform
Matrix4 = npt.NDArray[np.float64]

# The representation's own length settings are normalized and clamped to small
# ranges, so world size comes from a uniform scale baked into the transform.
# The fraction keeps the gizmo readable on a forearm and on a full skeleton.
GIZMO_EXTENT_FRACTION = 0.18
FALLBACK_EXTENT = 1.0

TORUS_THICKNESS = 0.004
TORUS_LENGTH = 3.0
ARROW_LENGTH = 0.35


class RootGizmo:
    """Drive a model's root joint from a VTK orientation widget."""

    def __init__(
        self,
        scene_manager: Any,
        root: ModelRoot,
        applier: PoseApplier,
        renderer: vtk.vtkRenderer,
        interactor: vtk.vtkRenderWindowInteractor,
    ):
        """Initialize the gizmo.

        Args:
            scene_manager: SceneManager owning the model and state
            root: Root joint description, must support a gizmo
            applier: Shared pose applier for redraw and notification
            renderer: Renderer the gizmo draws into
            interactor: Interactor the widget listens to

        Raises:
            ValueError: If the root joint cannot be driven by a transform
        """
        if not root.supports_gizmo:
            raise ValueError(f"Root joint {root.joint_name} cannot be driven by a gizmo")

        self.scene_manager = scene_manager
        self.root = root
        self.applier = applier
        self.renderer = renderer

        self.representation = vtk.vtkOrientationRepresentation()
        self._size_representation()

        self.widget = vtk.vtkOrientationWidget()
        self.widget.SetInteractor(interactor)
        self.widget.SetRepresentation(self.representation)

        self.widget.AddObserver(vtk.vtkCommand.InteractionEvent, self._on_interaction)
        self.widget.AddObserver(
            vtk.vtkCommand.EndInteractionEvent, self._on_interaction
        )

        self.sync_from_model()

    def set_enabled(self, enabled: bool) -> None:
        """Show or hide the gizmo.

        Args:
            enabled: True to display and activate the gizmo
        """
        if enabled:
            self.sync_from_model()

        self.widget.SetEnabled(1 if enabled else 0)
        logger.info(f"Root gizmo {'enabled' if enabled else 'disabled'}")

    @property
    def is_enabled(self) -> bool:
        """Whether the gizmo is currently shown."""
        return bool(self.widget.GetEnabled())

    def sync_from_model(self) -> None:
        """Move the gizmo to the root's current pose.

        Call after anything else repositions the model, so the handles do not
        drift away from the base they control.
        """
        matrix = read_root_matrix(
            self.scene_manager.opensim_model, self.scene_manager.state, self.root
        )
        matrix[:3, :3] = matrix[:3, :3] * self._handle_scale()
        self.representation.GetTransform().SetMatrix(_to_vtk_matrix(matrix))

    def _on_interaction(self, obj: Any, event: str) -> None:
        """Apply the gizmo's transform to the root joint.

        Args:
            obj: Emitting VTK object
            event: VTK event name
        """
        matrix = _strip_scale(
            _from_vtk_matrix(self.representation.GetTransform().GetMatrix())
        )
        values = matrix_to_root_coordinates(
            self.scene_manager.opensim_model,
            self.scene_manager.state,
            self.root,
            matrix,
        )

        accepted = self.applier.write_coordinates(values)
        self.applier.apply(accepted)

    def _size_representation(self) -> None:
        """Give the handles a readable shape.

        Only the proportions are set here; world size comes from the uniform
        scale applied to the transform in sync_from_model.
        """
        self.representation.SetTorusThickness(TORUS_THICKNESS)
        self.representation.SetTorusLength(TORUS_LENGTH)
        self.representation.SetArrowLength(ARROW_LENGTH)
        self.representation.SetShowArrows(True)

    def _handle_scale(self) -> float:
        """Compute the world size of the gizmo handles.

        Returns:
            Uniform scale factor for the transform
        """
        return self._scene_extent() * GIZMO_EXTENT_FRACTION

    def _scene_extent(self) -> float:
        """Measure the model's overall size.

        Returns:
            The diagonal of the visible bounds, or a fallback when empty
        """
        bounds = self.renderer.ComputeVisiblePropBounds()
        spans = [bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]]
        if any(span <= 0.0 for span in spans):
            return FALLBACK_EXTENT

        return float(np.linalg.norm(spans))


def _strip_scale(matrix: Matrix4) -> Matrix4:
    """Remove the handle scale, leaving a pure rotation and translation.

    The gizmo carries a uniform scale so its handles are visible at model
    size. Euler decomposition needs an orthonormal rotation, and the scale
    is applied in the local frame so the translation column is untouched.

    Args:
        matrix: 4x4 transform including uniform scale

    Returns:
        The same pose with unit-length rotation columns
    """
    result = matrix.copy()
    lengths = np.linalg.norm(result[:3, :3], axis=0)
    result[:3, :3] = result[:3, :3] / lengths
    return result


def _to_vtk_matrix(matrix: Matrix4) -> vtk.vtkMatrix4x4:
    """Convert a 4x4 numpy matrix into a VTK matrix.

    Args:
        matrix: 4x4 homogeneous transform

    Returns:
        Equivalent vtkMatrix4x4
    """
    result = vtk.vtkMatrix4x4()
    for row in range(4):
        for column in range(4):
            result.SetElement(row, column, float(matrix[row, column]))
    return result


def _from_vtk_matrix(matrix: vtk.vtkMatrix4x4) -> Matrix4:
    """Convert a VTK matrix into a 4x4 numpy matrix.

    Args:
        matrix: vtkMatrix4x4 to read

    Returns:
        Equivalent numpy array
    """
    return np.array(
        [[matrix.GetElement(row, column) for column in range(4)] for row in range(4)]
    )


if __name__ == "__main__":
    """Smoke test for RootGizmo."""
    import sys

    import opensim

    from osim_render.api.managers.event_bus import EventBus
    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.posing.model_root import find_model_root
    from osim_render.api.rendering.scene import SceneManager

    model_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "resources/Models/Rajagopal/Rajagopal2016.osim"
    )
    print(f"RootGizmo smoke test on {model_path}")

    opensim.Model.setDebugLevel(-1)
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    model_manager.load_model(model_path)

    scene_manager = SceneManager(model_manager, model_path)

    render_window = vtk.vtkRenderWindow()
    render_window.SetOffScreenRendering(1)
    render_window.SetSize(400, 400)
    renderer = vtk.vtkRenderer()
    render_window.AddRenderer(renderer)
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)

    scene_manager.create_scene(renderer=renderer)
    renderer.ResetCamera()
    render_window.Render()

    model = model_manager.get_opensim_model()
    assert model is not None, "model manager has no model"

    root = find_model_root(model)
    assert root is not None and root.supports_gizmo, "need a floating base"
    print(f"[OK] Root {root.joint_name} supports a gizmo")

    applier = PoseApplier(scene_manager, event_bus)
    gizmo = RootGizmo(scene_manager, root, applier, renderer, interactor)
    print(f"[OK] Gizmo built, handle length {gizmo.representation.GetArrowLength():.3f}")

    gizmo.set_enabled(True)
    assert gizmo.is_enabled

    print("\nTranslating the gizmo should move the root...")
    state = scene_manager.state
    before = {n: model.getCoordinateSet().get(n).getValue(state) for n in root.coordinate_names}

    transform = gizmo.representation.GetTransform()
    moved = _from_vtk_matrix(transform.GetMatrix())
    moved[:3, 3] += np.array([0.20, 0.05, -0.10])
    transform.SetMatrix(_to_vtk_matrix(moved))
    gizmo._on_interaction(None, "InteractionEvent")

    after = {n: model.getCoordinateSet().get(n).getValue(state) for n in root.coordinate_names}
    delta = {k: round(after[k] - before[k], 4) for k in before if abs(after[k] - before[k]) > 1e-6}
    print(f"[OK] Root coordinates changed: {delta}")
    assert delta, "gizmo did not move the root"

    landed = read_root_matrix(model, state, root)
    error = float(np.linalg.norm(landed[:3, 3] - moved[:3, 3]))
    print(f"[OK] Root reached the requested position, error {error:.2e}")
    assert error < 1e-6

    print("\nRotating the gizmo should rotate the root...")
    gizmo.sync_from_model()
    spun = _strip_scale(_from_vtk_matrix(gizmo.representation.GetTransform().GetMatrix()))
    turn = vtk.vtkTransform()
    turn.RotateY(25.0)
    turn_matrix = _from_vtk_matrix(turn.GetMatrix())
    spun[:3, :3] = turn_matrix[:3, :3] @ spun[:3, :3]
    scaled = spun.copy()
    scaled[:3, :3] = scaled[:3, :3] * gizmo._handle_scale()
    gizmo.representation.GetTransform().SetMatrix(_to_vtk_matrix(scaled))
    gizmo._on_interaction(None, "InteractionEvent")

    turned = read_root_matrix(model, state, root)
    rotation_error = float(np.abs(turned[:3, :3] - spun[:3, :3]).max())
    print(f"[OK] Root orientation matched the gizmo, error {rotation_error:.2e}")
    assert rotation_error < 1e-9

    print("\nSyncing pulls the gizmo back to the model...")
    model.getCoordinateSet().get(root.translation_coordinates[0]).setValue(state, 0.75, False)
    model.realizePosition(state)
    gizmo.sync_from_model()
    synced = _strip_scale(_from_vtk_matrix(gizmo.representation.GetTransform().GetMatrix()))
    expected = read_root_matrix(model, state, root)
    print(f"[OK] Gizmo tracks model, error {np.abs(synced - expected).max():.2e}")
    assert np.allclose(synced, expected)

    gizmo.set_enabled(False)
    assert not gizmo.is_enabled
    print("[OK] Gizmo hides cleanly")

    print("\n[OK] Smoke test passed!")
