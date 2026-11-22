"""Hidden per-body markers that give OpenSim's IK solver something to drag.

OpenSim's InverseKinematicsSolver can only pull on markers that belong to the
model, so interactive posing needs a marker on whichever body the user grabs.
Markers are installed once at load time (adding one later would require a
system rebuild mid-drag); grabbing a point then just moves the relevant
marker's local offset.
"""

from __future__ import annotations

from typing import Any

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)

DRAG_MARKER_PREFIX = "__drag_"
DRAG_MARKER_SUFFIX = "__"


def drag_marker_name(body_name: str) -> str:
    """Build the reserved marker name for a body.

    Args:
        body_name: Name of the OpenSim body

    Returns:
        Reserved marker name, e.g. "__drag_tibia_r__"
    """
    return f"{DRAG_MARKER_PREFIX}{body_name}{DRAG_MARKER_SUFFIX}"


def is_drag_marker(marker_name: str) -> bool:
    """Check whether a marker is an internal drag handle.

    Args:
        marker_name: Name of a marker in the model

    Returns:
        True if the marker is reserved for drag-to-pose
    """
    return marker_name.startswith(DRAG_MARKER_PREFIX)


class DragMarkerRig:
    """Install and retarget the hidden markers used for drag-to-pose."""

    def __init__(self, model: Any):
        """Initialize the rig for a model.

        Args:
            model: OpenSim Model that already has drag markers installed
        """
        self.model = model

    @classmethod
    def install(cls, model: Any) -> "DragMarkerRig":
        """Add one drag marker per body to the model.

        Must be called BEFORE initSystem(), because adding a marker changes
        the multibody system's topology.

        Args:
            model: Freshly constructed OpenSim Model

        Returns:
            DragMarkerRig bound to the model
        """
        import opensim

        for body in model.getBodySet():
            marker = opensim.Marker(
                drag_marker_name(body.getName()), body, opensim.Vec3(0, 0, 0)
            )
            model.addMarker(marker)

        logger.info(f"Installed {model.getBodySet().getSize()} drag markers")
        return cls(model)

    def has_marker_for(self, body_name: str) -> bool:
        """Check whether a drag marker exists for a body.

        Args:
            body_name: Name of the body

        Returns:
            True if the body can be dragged
        """
        index: int = self.model.getMarkerSet().getIndex(drag_marker_name(body_name))
        return index >= 0

    def set_grab_point(self, body_name: str, local_point: tuple[float, float, float]) -> str:
        """Move a body's drag marker to the grabbed point.

        The marker's cached ground location is only recomputed when the
        Position stage is invalidated, so callers must invalidate before
        realizing (see PoseSolver, which does this as part of solving).

        Args:
            body_name: Body the user grabbed
            local_point: Grab point in the body's local frame

        Returns:
            Name of the marker now sitting at the grab point

        Raises:
            ValueError: If the body has no drag marker installed
        """
        import opensim

        marker_name = drag_marker_name(body_name)
        if not self.has_marker_for(body_name):
            raise ValueError(f"No drag marker installed for body: {body_name}")

        marker = self.model.getMarkerSet().get(marker_name)
        marker.set_location(opensim.Vec3(*local_point))
        return marker_name


if __name__ == "__main__":
    """Smoke test for DragMarkerRig."""
    import sys

    import opensim

    model_path = (
        sys.argv[1] if len(sys.argv) > 1 else "resources/Models/Arm26/arm26.osim"
    )
    print(f"DragMarkerRig smoke test on {model_path}")

    opensim.Model.setDebugLevel(-1)
    model = opensim.Model(model_path)
    model.initSystem()

    rig = DragMarkerRig.install(model)
    state = model.initSystem()
    model.realizePosition(state)

    body_names = [b.getName() for b in model.getBodySet()]
    print(f"[OK] Bodies: {body_names}")

    for name in body_names:
        assert rig.has_marker_for(name), f"missing drag marker for {name}"
    print("[OK] Every body has a drag marker")

    assert is_drag_marker(drag_marker_name(body_names[0]))
    assert not is_drag_marker("r_toe_marker")
    print("[OK] Drag marker naming round-trips")

    target_body = body_names[-1]
    marker_name = rig.set_grab_point(target_body, (0.0, -0.15, 0.0))
    print(f"[OK] Grab point set on {target_body} -> {marker_name}")

    print("\n[OK] Smoke test passed!")
