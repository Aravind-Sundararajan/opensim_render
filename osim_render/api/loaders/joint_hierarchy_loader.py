"""Extract joint connectivity and build multibody tree from OpenSim models.

Identifies parent-child relationships through joints and physical frames.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from osim_render.api.opensim_protocols import FrameProtocol


class JointProtocol(Protocol):
    """Protocol for OpenSim Joint objects."""

    def getName(self) -> str:
        """Get the name of this joint."""
        ...

    def getConcreteClassName(self) -> str:
        """Get the concrete class name."""
        ...

    def numCoordinates(self) -> int:
        """Get number of coordinates."""
        ...

    def getParentFrame(self) -> FrameProtocol:
        """Get parent frame (must not be None)."""
        ...

    def getChildFrame(self) -> FrameProtocol:
        """Get child frame (must not be None)."""
        ...


@dataclass(frozen=True)
class JointInfo:
    """Information about a joint connecting two bodies.

    Attributes:
        joint_name: Name of the joint
        joint_type: OpenSim concrete class name (e.g., "PinJoint")
        parent_body: Name of parent body
        child_body: Name of child body
        num_coordinates: Number of coordinates controlled by joint
    """

    joint_name: str
    joint_type: str
    parent_body: str
    child_body: str
    num_coordinates: int


@dataclass(frozen=True)
class BodyTreeNode:
    """A body node in the multibody tree hierarchy.

    Attributes:
        body_name: Name of this body
        parent_joint: Name of joint connecting to parent (None for ground)
        child_joints: Names of joints connecting to children
    """

    body_name: str
    parent_joint: str | None
    child_joints: tuple[str, ...]


class JointHierarchyExtractor:
    """Extract joint connectivity and build multibody tree.

    Parses OpenSim model structure to identify which bodies are connected
    by which joints, building the kinematic hierarchy.
    """

    def __init__(self, model: Any):
        """Initialize with loaded OpenSim model.

        Args:
            model: Loaded OpenSim Model object

        Raises:
            ValueError: If model is None
        """
        if model is None:
            raise ValueError("Model cannot be None")
        self.model = model

    def extract_joints(self) -> dict[str, JointInfo]:
        """Extract all joints from model.

        Queries the model's joint set and extracts parent-child relationships
        for each joint. Parent defaults to "ground" if getParentFrame returns None.

        Returns:
            Dictionary mapping joint name to JointInfo

        Raises:
            ValueError: If joint connectivity cannot be determined
        """
        joints = {}

        for joint in self.model.getJointList():
            joint_name = joint.getName()
            joint_type = joint.getConcreteClassName()
            num_coords = joint.numCoordinates()

            parent_body = self._get_parent_body(joint, joint_name)
            child_body = self._get_child_body(joint, joint_name)

            joints[joint_name] = JointInfo(
                joint_name=joint_name,
                joint_type=joint_type,
                parent_body=parent_body,
                child_body=child_body,
                num_coordinates=num_coords,
            )

        return joints

    def _get_parent_body(self, joint: JointProtocol, joint_name: str) -> str:
        """Get parent body name for a joint.

        The parent frame is obtained from the joint. If the frame is None,
        defaults to "ground" (root of kinematic tree). Otherwise extracts
        the frame's name which must be a body name.

        Args:
            joint: OpenSim Joint object
            joint_name: Name of joint (for error messages)

        Returns:
            Name of parent body (or "ground" if parent frame is None)

        Raises:
            ValueError: If parent frame exists but has no getName method
        """
        parent_frame = joint.getParentFrame()

        if parent_frame is None:
            return "ground"

        parent_name = parent_frame.getName()

        if parent_name is None:
            raise ValueError(f"Parent frame for joint {joint_name} has no name")

        return parent_name

    def _get_child_body(self, joint: JointProtocol, joint_name: str) -> str:
        """Get child body name for a joint.

        The child frame must exist and must have a name. If either is missing,
        raises an error (child frame is always required in OpenSim).

        Args:
            joint: OpenSim Joint object
            joint_name: Name of joint (for error messages)

        Returns:
            Name of child body

        Raises:
            ValueError: If child frame is None or has no name
        """
        child_frame = joint.getChildFrame()

        if child_frame is None:
            raise ValueError(f"Joint {joint_name} has no child frame")

        child_name = child_frame.getName()

        if child_name is None:
            raise ValueError(f"Child frame for joint {joint_name} has no name")

        return child_name

    def build_body_tree(self, joints: dict[str, JointInfo]) -> dict[str, BodyTreeNode]:
        """Build hierarchical tree of bodies connected by joints.

        Creates tree nodes for all bodies in the model, then populates
        parent-child relationships based on the joint connectivity.

        Args:
            joints: Dictionary of JointInfo objects from extract_joints()

        Returns:
            Dictionary mapping body name to BodyTreeNode

        Raises:
            ValueError: If a body referenced in joints is not in the model
        """
        tree = {}

        # Create nodes for all bodies
        for body in self.model.getBodyList():
            body_name = body.getName()
            tree[body_name] = BodyTreeNode(
                body_name=body_name,
                parent_joint=None,
                child_joints=(),
            )

        # Populate parent/child relationships from joints
        for joint_name, joint_info in joints.items():
            child_body_name = joint_info.child_body
            parent_body_name = joint_info.parent_body

            self._set_child_parent_joint(tree, child_body_name, joint_name)
            self._add_parent_child_joint(tree, parent_body_name, joint_name)

        return tree

    def _set_child_parent_joint(
        self, tree: dict[str, BodyTreeNode], child_body_name: str, joint_name: str
    ) -> None:
        """Update child body's parent joint reference.

        Args:
            tree: Body tree being built
            child_body_name: Name of child body
            joint_name: Name of joint connecting to parent

        Raises:
            ValueError: If child body not found in tree
        """
        if child_body_name not in tree:
            raise ValueError(f"Child body {child_body_name} not found in model")

        old_node = tree[child_body_name]
        tree[child_body_name] = BodyTreeNode(
            body_name=child_body_name,
            parent_joint=joint_name,
            child_joints=old_node.child_joints,
        )

    def _add_parent_child_joint(
        self, tree: dict[str, BodyTreeNode], parent_body_name: str, joint_name: str
    ) -> None:
        """Add joint to parent body's children list.

        Args:
            tree: Body tree being built
            parent_body_name: Name of parent body
            joint_name: Name of joint connecting to child

        Raises:
            ValueError: If parent body not found in tree
        """
        if parent_body_name not in tree:
            raise ValueError(f"Parent body {parent_body_name} not found in model")

        old_node = tree[parent_body_name]
        tree[parent_body_name] = BodyTreeNode(
            body_name=parent_body_name,
            parent_joint=old_node.parent_joint,
            child_joints=tuple(list(old_node.child_joints) + [joint_name]),
        )


if __name__ == "__main__":
    """Smoke test for joint hierarchy extraction."""
    import opensim

    opensim.Model.setDebugLevel(0)

    model = opensim.Model(
        "models/lowerExtremity/Gait2392_Simbody/gait2392_simbody.osim"
    )
    model.initSystem()

    extractor = JointHierarchyExtractor(model)
    joints = extractor.extract_joints()
    tree = extractor.build_body_tree(joints)

    print(f"[OK] Extracted {len(joints)} joints")
    print(f"[OK] Built tree for {len(tree)} bodies")

    print("\n[INFO] Body tree structure:")
    if "ground" in tree:
        print("  ground (root)")
        for joint_name in tree["ground"].child_joints:
            if joint_name in joints:
                child_body = joints[joint_name].child_body
                print(f"    -> {child_body} (via {joint_name})")
                if child_body in tree:
                    for child_joint in tree[child_body].child_joints:
                        if child_joint in joints:
                            grandchild = joints[child_joint].child_body
                            print(f"      -> {grandchild} (via {child_joint})")

    print("\n[OK] Joint hierarchy extraction smoke test passed!")
