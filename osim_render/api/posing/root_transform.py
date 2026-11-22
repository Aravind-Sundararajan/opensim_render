"""Convert between a world transform and the root joint's coordinates.

A gizmo hands back a pose in world space, but the model can only be moved by
writing joint coordinates. This module decomposes the world transform into the
root joint's own rotation sequence and translation axes, so the gizmo drives
the multibody tree through its mobilizer rather than around it.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt
from scipy.spatial.transform import Rotation

from osim_render.api.logging import get_logger_for
from osim_render.api.posing.model_root import ModelRoot

logger = get_logger_for(__name__)

# 4x4 homogeneous transform
Matrix4 = npt.NDArray[np.float64]


def transform_to_matrix(transform: Any) -> Matrix4:
    """Convert an OpenSim Transform into a 4x4 matrix.

    Args:
        transform: SimTK Transform

    Returns:
        4x4 homogeneous transform
    """
    rotation = transform.R()
    position = transform.p()

    matrix = np.eye(4)
    for row in range(3):
        for column in range(3):
            matrix[row, column] = rotation.get(row, column)
        matrix[row, 3] = position.get(row)
    return matrix


def read_root_matrix(model: Any, state: Any, root: ModelRoot) -> Matrix4:
    """Read the current world transform of the root joint's child frame.

    Args:
        model: OpenSim Model
        state: State to read
        root: Root joint description

    Returns:
        4x4 world transform of the root child frame
    """
    joint = model.getJointSet().get(root.joint_name)
    return transform_to_matrix(joint.getChildFrame().getTransformInGround(state))


def matrix_to_root_coordinates(
    model: Any, state: Any, root: ModelRoot, world_matrix: Matrix4
) -> dict[str, float]:
    """Decompose a desired world transform into root joint coordinates.

    Args:
        model: OpenSim Model
        state: State providing the parent frame's current pose
        root: Root joint description
        world_matrix: Desired 4x4 world transform of the root child frame

    Returns:
        Mapping of root coordinate name to value

    Raises:
        ValueError: If the root joint cannot be decomposed
    """
    if not root.supports_gizmo:
        raise ValueError(f"Root joint {root.joint_name} cannot be decomposed")

    joint = model.getJointSet().get(root.joint_name)
    parent = transform_to_matrix(joint.getParentFrame().getTransformInGround(state))
    joint_matrix = np.linalg.inv(parent) @ world_matrix

    values = _decompose_rotation(root, joint_matrix)
    values.update(_decompose_translation(root, joint_matrix))
    return values


def _decompose_rotation(root: ModelRoot, joint_matrix: Matrix4) -> dict[str, float]:
    """Split the joint rotation into the root's Euler sequence.

    Args:
        root: Root joint description
        joint_matrix: 4x4 transform of child frame relative to parent frame

    Returns:
        Mapping of rotational coordinate name to angle in radians
    """
    angles = Rotation.from_matrix(joint_matrix[:3, :3]).as_euler(
        root.rotation_sequence
    )
    return dict(zip(root.rotation_coordinates, (float(a) for a in angles), strict=False))


def _decompose_translation(
    root: ModelRoot, joint_matrix: Matrix4
) -> dict[str, float]:
    """Project the joint translation onto the root's translation axes.

    Args:
        root: Root joint description
        joint_matrix: 4x4 transform of child frame relative to parent frame

    Returns:
        Mapping of translational coordinate name to offset
    """
    translation = joint_matrix[:3, 3]
    return {
        name: float(np.dot(translation, np.asarray(axis)))
        for name, axis in zip(root.translation_coordinates, root.translation_axes, strict=False)
    }


if __name__ == "__main__":
    """Smoke test: round-trip coordinates through a world transform."""
    import sys

    import opensim

    from osim_render.api.posing.model_root import find_model_root

    model_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "resources/Models/Rajagopal/Rajagopal2016.osim"
    )
    print(f"root_transform smoke test on {model_path}")

    opensim.Model.setDebugLevel(-1)
    model = opensim.Model(model_path)
    state = model.initSystem()

    root = find_model_root(model)
    assert root is not None and root.supports_gizmo, "need a floating base to test"
    print(f"[OK] Root {root.joint_name} sequence={root.rotation_sequence}")

    rng = np.random.default_rng(20260718)
    worst = 0.0

    for _trial in range(25):
        expected = {}
        for name in root.rotation_coordinates:
            expected[name] = float(rng.uniform(-0.6, 0.6))
        for name in root.translation_coordinates:
            expected[name] = float(rng.uniform(-0.8, 0.8))

        for name, value in expected.items():
            model.getCoordinateSet().get(name).setValue(state, value, False)
        model.realizePosition(state)

        world = read_root_matrix(model, state, root)
        recovered = matrix_to_root_coordinates(model, state, root, world)

        for name, value in expected.items():
            worst = max(worst, abs(recovered[name] - value))

    print(f"[OK] 25 random poses round-tripped, worst error {worst:.2e}")
    assert worst < 1e-9, f"decomposition does not invert cleanly: {worst}"

    print("\nChecking the transform actually drives the model...")
    for name in root.coordinate_names:
        model.getCoordinateSet().get(name).setValue(state, 0.0, False)
    model.realizePosition(state)
    origin = read_root_matrix(model, state, root)

    shifted = origin.copy()
    shifted[:3, 3] += np.array([0.25, 0.10, -0.15])
    values = matrix_to_root_coordinates(model, state, root, shifted)
    for name, value in values.items():
        model.getCoordinateSet().get(name).setValue(state, value, False)
    model.realizePosition(state)

    landed = read_root_matrix(model, state, root)
    error = float(np.linalg.norm(landed[:3, 3] - shifted[:3, 3]))
    print(f"[OK] Requested translation reached, error {error:.2e}")
    assert error < 1e-9

    print("\n[OK] Smoke test passed!")
