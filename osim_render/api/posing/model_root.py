"""Locate the root of a model's multibody tree and decode its joint.

The root is the joint attaching the tree to ground. For gait models that is a
six-degree-of-freedom pelvis that lets the whole model float; for a model like
arm26 it is an ordinary one-axis shoulder. Telling those apart matters: pinning
a floating base makes drag-to-pose articulate joints instead of sliding the
model around, but pinning a shoulder would simply freeze the arm.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)

# Coordinate.getMotionType() values
MOTION_TYPE_ROTATIONAL = 1
MOTION_TYPE_TRANSLATIONAL = 2

# A joint axis must line up with a basis direction for Euler decomposition.
_AXIS_LABELS = {(1.0, 0.0, 0.0): "X", (0.0, 1.0, 0.0): "Y", (0.0, 0.0, 1.0): "Z"}
_AXIS_TOLERANCE = 1e-6


@dataclass(frozen=True)
class ModelRoot:
    """The joint connecting the multibody tree to ground."""

    joint_name: str
    body_name: str
    coordinate_names: tuple[str, ...]
    rotation_coordinates: tuple[str, ...]
    translation_coordinates: tuple[str, ...]
    rotation_sequence: str
    translation_axes: tuple[tuple[float, float, float], ...]

    @property
    def is_floating_base(self) -> bool:
        """Whether the root lets the whole model translate freely."""
        return bool(self.translation_coordinates)

    @property
    def supports_gizmo(self) -> bool:
        """Whether this root can be driven by a transform gizmo.

        Requires a full six degrees of freedom on basis-aligned axes, which
        is what a decomposable transform needs.
        """
        return (
            len(self.rotation_coordinates) == 3
            and len(self.translation_coordinates) == 3
            and len(self.rotation_sequence) == 3
        )


def find_model_root(model: Any) -> Optional[ModelRoot]:
    """Find the joint attaching the model to ground.

    Args:
        model: OpenSim Model

    Returns:
        ModelRoot for the ground-attached joint, or None if there is none
    """
    ground_name = model.getGround().getName()

    for joint in model.getJointSet():
        if joint.getParentFrame().findBaseFrame().getName() != ground_name:
            continue
        return _describe_root(model, joint)

    logger.warning("Model has no ground-attached joint; root is undefined")
    return None


def _describe_root(model: Any, joint: Any) -> ModelRoot:
    """Build a ModelRoot from a ground-attached joint.

    Args:
        model: OpenSim Model owning the joint
        joint: The ground-attached joint

    Returns:
        ModelRoot describing the joint's coordinates and axes
    """
    coordinate_names = tuple(
        joint.get_coordinates(i).getName() for i in range(joint.numCoordinates())
    )
    rotations = tuple(
        name
        for name in coordinate_names
        if _motion_type(model, name) == MOTION_TYPE_ROTATIONAL
    )
    translations = tuple(
        name
        for name in coordinate_names
        if _motion_type(model, name) == MOTION_TYPE_TRANSLATIONAL
    )
    sequence, translation_axes = _decode_axes(joint, rotations, translations)

    return ModelRoot(
        joint_name=joint.getName(),
        body_name=joint.getChildFrame().findBaseFrame().getName(),
        coordinate_names=coordinate_names,
        rotation_coordinates=rotations,
        translation_coordinates=translations,
        rotation_sequence=sequence,
        translation_axes=translation_axes,
    )


def _motion_type(model: Any, coordinate_name: str) -> int:
    """Read a coordinate's motion type.

    Args:
        model: OpenSim Model
        coordinate_name: Name of the coordinate

    Returns:
        The OpenSim motion type enumeration value
    """
    motion_type: int = model.getCoordinateSet().get(coordinate_name).getMotionType()
    return motion_type


def _decode_axes(
    joint: Any, rotations: tuple[str, ...], translations: tuple[str, ...]
) -> tuple[str, tuple[tuple[float, float, float], ...]]:
    """Read rotation order and translation directions from a CustomJoint.

    Args:
        joint: The ground-attached joint
        rotations: Rotational coordinate names, in joint order
        translations: Translational coordinate names, in joint order

    Returns:
        Tuple of (scipy Euler sequence, translation axis directions). The
        sequence is empty when the axes are not basis-aligned.
    """
    import opensim

    custom = opensim.CustomJoint.safeDownCast(joint)
    if custom is None:
        return _default_axes(rotations, translations)

    transform = custom.getSpatialTransform()
    labels = []
    for index in range(len(rotations)):
        label = _axis_label(transform.getTransformAxis(index).getAxis())
        if label is None:
            logger.info(f"Root joint {joint.getName()} has non-basis rotation axes")
            return ("", _default_translation_axes(translations))
        labels.append(label)

    axes = []
    for offset in range(len(translations)):
        axis = transform.getTransformAxis(3 + offset).getAxis()
        axes.append((axis.get(0), axis.get(1), axis.get(2)))

    return ("".join(labels), tuple(axes))


def _axis_label(axis: Any) -> Optional[str]:
    """Map a joint axis direction to an Euler sequence letter.

    Args:
        axis: SimTK Vec3 axis direction

    Returns:
        "X", "Y" or "Z", or None if the axis is not basis-aligned
    """
    direction = (axis.get(0), axis.get(1), axis.get(2))
    for basis, label in _AXIS_LABELS.items():
        if np.allclose(direction, basis, atol=_AXIS_TOLERANCE):
            return label
    return None


def _default_axes(
    rotations: tuple[str, ...], translations: tuple[str, ...]
) -> tuple[str, tuple[tuple[float, float, float], ...]]:
    """Assume the standard XYZ layout used by FreeJoint.

    Args:
        rotations: Rotational coordinate names
        translations: Translational coordinate names

    Returns:
        Tuple of (Euler sequence, translation axis directions)
    """
    sequence = "XYZ"[: len(rotations)] if len(rotations) == 3 else ""
    return (sequence, _default_translation_axes(translations))


def _default_translation_axes(
    translations: tuple[str, ...],
) -> tuple[tuple[float, float, float], ...]:
    """Assume translation along the basis directions in order.

    Args:
        translations: Translational coordinate names

    Returns:
        One basis direction per translational coordinate
    """
    basis = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    return tuple(basis[index] for index in range(len(translations)))


if __name__ == "__main__":
    """Smoke test for model root detection."""
    import sys
    from pathlib import Path

    import opensim

    candidates = (
        [sys.argv[1]]
        if len(sys.argv) > 1
        else [
            str(Path(opensim.__file__).parent / "tests" / "arm26.osim"),
            "resources/Models/Rajagopal/Rajagopal2016.osim",
            "resources/Models/Gait2354_Simbody/gait2354_simbody.osim",
        ]
    )

    print("ModelRoot smoke test")
    opensim.Model.setDebugLevel(-1)

    for path in candidates:
        if not Path(path).exists():
            print(f"\n  {path} missing, skipping")
            continue

        model = opensim.Model(path)
        model.initSystem()
        root = find_model_root(model)
        assert root is not None, f"no root found for {path}"

        print(f"\n  {Path(path).name}")
        print(f"    joint={root.joint_name} body={root.body_name}")
        print(f"    rotations={root.rotation_coordinates} sequence={root.rotation_sequence!r}")
        print(f"    translations={root.translation_coordinates}")
        print(f"    floating_base={root.is_floating_base} gizmo={root.supports_gizmo}")

    print("\n[OK] Smoke test passed!")
