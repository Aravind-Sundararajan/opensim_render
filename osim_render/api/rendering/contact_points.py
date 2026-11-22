"""Resolve the drawable contact points of OpenSim contact forces.

Different contact force classes describe their geometry in different ways, and
a single force may cover several contact points. This module reduces them all
to one shape — where the point is, and which slice of the force's record output
belongs to it — so the visualizer never has to branch on force type.

No VTK here: this is model interrogation only, and is testable without a scene.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import opensim

from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)

# getRecordValues() emits force XYZ then torque XYZ for each contributing
# geometry, in the order the force declares them.
RECORD_CHANNELS_PER_GEOMETRY = 6

CONTACT_SPHERE_CLASS = "ContactSphere"


class ContactForceType(Enum):
    """Contact force classes this package can locate contact points for.

    OpenSim 4.5.2 ships exactly three compliant contact force classes. All
    three appear here, but only geometry that reduces to a point (a
    ContactSphere) produces an arrow — mesh and half-space geometry has no
    single application point.
    """

    HUNT_CROSSLEY = "HuntCrossleyForce"
    ELASTIC_FOUNDATION = "ElasticFoundationForce"
    SMOOTH_SPHERE_HALFSPACE = "SmoothSphereHalfSpaceForce"


# HuntCrossleyForce and ElasticFoundationForce both describe their geometry
# through a contact_parameters property holding a list of geometry names.
_PARAMETER_SET_TYPES = {
    ContactForceType.HUNT_CROSSLEY.value,
    ContactForceType.ELASTIC_FOUNDATION.value,
}


@dataclass(frozen=True)
class ContactPoint:
    """The resultant contact force a force applies to one body.

    This is deliberately per body, not per sphere. HuntCrossleyForce reports a
    single resultant per body and repeats it for each of that body's contact
    geometries, so drawing one arrow per sphere would show the same force
    several times over. Verified against Newton's third law: summing per body
    balances the reaction exactly, summing per sphere does not.

    Attributes:
        key: Unique actor key for this arrow
        force_name: Force this resultant belongs to
        body_name: Body the force is applied to, as named in the record labels
        stations: (frame, location) of each sphere contributing to the
            resultant; the arrow is drawn at their centroid
        geometry_names: Names of those spheres, for display and debugging
        record_offset: Index of this body's Fx within the force's record output
    """

    key: str
    force_name: str
    body_name: str
    stations: tuple[tuple[Any, Any], ...]
    geometry_names: tuple[str, ...]
    record_offset: int

    def force_vector(self, record_values: Any) -> tuple[float, float, float]:
        """Read this body's resultant force from the force's record output.

        Args:
            record_values: Result of force.getRecordValues(state)

        Returns:
            The resultant force on this body in ground coordinates, in newtons
        """
        return (
            record_values.get(self.record_offset),
            record_values.get(self.record_offset + 1),
            record_values.get(self.record_offset + 2),
        )

    def location_in_ground(self, state: Any, ground: Any) -> tuple[float, float, float]:
        """Centroid of the contributing spheres, in ground coordinates.

        Args:
            state: State realized at least to Position
            ground: The model's ground frame

        Returns:
            Where the resultant arrow should be drawn
        """
        totals = [0.0, 0.0, 0.0]
        for frame, location in self.stations:
            point = frame.findStationLocationInAnotherFrame(state, location, ground)
            for axis in range(3):
                totals[axis] += point.get(axis)

        count = len(self.stations)
        return (totals[0] / count, totals[1] / count, totals[2] / count)


def is_contact_force(force: Any) -> bool:
    """Check whether a force is a contact force this module understands.

    Args:
        force: OpenSim Force

    Returns:
        True if the force's class is a known contact type
    """
    return force.getConcreteClassName() in {t.value for t in ContactForceType}


def resolve_contact_points(model: Any, force: Any) -> tuple[ContactPoint, ...]:
    """Find every drawable contact point belonging to a force.

    Args:
        model: OpenSim Model owning the force
        force: OpenSim Force to inspect

    Returns:
        One ContactPoint per sphere the force acts through, empty if none
    """
    class_name = force.getConcreteClassName()

    if class_name == ContactForceType.SMOOTH_SPHERE_HALFSPACE.value:
        return _resolve_smooth_sphere(force)

    if class_name in _PARAMETER_SET_TYPES:
        return _resolve_parameter_set(model, force)

    return ()


def _resolve_smooth_sphere(force: Any) -> tuple[ContactPoint, ...]:
    """Resolve the single sphere of a SmoothSphereHalfSpaceForce.

    The sphere is reached through a socket, and its force is the first record
    group — the reaction on the sphere's body, which is what should be drawn.

    Args:
        force: SmoothSphereHalfSpaceForce

    Returns:
        A single ContactPoint, or empty if the socket cannot be resolved
    """
    geometry = _socket_geometry(force, "sphere")
    if geometry is None:
        logger.info(f"Contact force {force.getName()}: sphere socket unresolved")
        return ()

    frame = geometry.getFrame()
    if frame is None:
        return ()

    force_name = force.getName()
    return (
        ContactPoint(
            key=force_name,
            force_name=force_name,
            body_name=frame.getName(),
            stations=((frame, geometry.getLocation()),),
            geometry_names=(geometry.getName(),),
            record_offset=0,
        ),
    )


def _resolve_parameter_set(model: Any, force: Any) -> tuple[ContactPoint, ...]:
    """Resolve every sphere of a force that lists geometry by name.

    HuntCrossleyForce and ElasticFoundationForce name their geometry in a
    contact_parameters property. Record groups follow that declared order, so
    a geometry's index gives its slice of the record output — verified against
    every contact force in the bundled models.

    Args:
        model: OpenSim Model owning the force
        force: HuntCrossleyForce or ElasticFoundationForce

    Returns:
        One ContactPoint per ContactSphere in the force's geometry list
    """
    names = _parameter_set_geometry_names(force)
    bodies = _record_group_bodies(force)

    if not names:
        logger.info(f"Contact force {force.getName()}: no geometry declared")
        return ()

    if len(names) != len(bodies):
        logger.warning(
            f"Contact force {force.getName()}: {len(names)} geometries but "
            f"{len(bodies)} record groups; cannot map forces to bodies"
        )
        return ()

    geometry_set = model.getContactGeometrySet()
    available = {
        geometry_set.get(i).getName(): geometry_set.get(i)
        for i in range(geometry_set.getSize())
    }

    grouped = _group_spheres_by_body(force, available, names, bodies)
    if not grouped:
        logger.info(
            f"Contact force {force.getName()}: no sphere geometry among {names}"
        )

    force_name = force.getName()
    return tuple(
        ContactPoint(
            key=f"{force_name}.{body_name}",
            force_name=force_name,
            body_name=body_name,
            stations=tuple(group["stations"]),
            geometry_names=tuple(group["names"]),
            record_offset=group["offset"],
        )
        for body_name, group in grouped.items()
    )


def _group_spheres_by_body(
    force: Any,
    available: dict[str, Any],
    names: list[str],
    bodies: list[str],
) -> dict[str, dict[str, Any]]:
    """Collect each body's contributing spheres and its record offset.

    A body may carry several spheres in one force. They share a single
    resultant, so they collapse into one entry whose offset is that of the
    body's first record group.

    Args:
        force: The owning force
        available: Model contact geometry by name
        names: Declared geometry names, in order
        bodies: Body named by each record group, in the same order

    Returns:
        Map of body name -> {offset, stations, names}
    """
    grouped: dict[str, dict[str, Any]] = {}

    for index, geometry_name in enumerate(names):
        geometry = _sphere_or_none(force, available, geometry_name)
        if geometry is None:
            continue

        entry = grouped.setdefault(
            bodies[index],
            {
                "offset": index * RECORD_CHANNELS_PER_GEOMETRY,
                "stations": [],
                "names": [],
            },
        )
        entry["stations"].append((geometry.getFrame(), geometry.getLocation()))
        entry["names"].append(geometry_name)

    return grouped


def _sphere_or_none(
    force: Any, available: dict[str, Any], geometry_name: str
) -> Any | None:
    """Return the named geometry when it is a usable ContactSphere.

    Args:
        force: The owning force, for logging
        available: Model contact geometry by name
        geometry_name: Declared geometry name

    Returns:
        The ContactSphere, or None if absent, not a sphere, or frameless
    """
    geometry = available.get(geometry_name)
    if geometry is None:
        logger.warning(
            f"Contact force {force.getName()} names unknown geometry {geometry_name}"
        )
        return None

    if geometry.getConcreteClassName() != CONTACT_SPHERE_CLASS:
        return None

    if geometry.getFrame() is None:
        return None

    return geometry


def _record_group_bodies(force: Any) -> list[str]:
    """Read which body each record group reports a force on.

    Grouping is taken from the record labels rather than inferred from the
    geometry's frame, so it matches the record layout by construction.

    Args:
        force: Contact force to inspect

    Returns:
        One body name per record group, in order
    """
    labels = force.getRecordLabels()
    group_count = labels.getSize() // RECORD_CHANNELS_PER_GEOMETRY

    return [
        labels.get(group * RECORD_CHANNELS_PER_GEOMETRY).split(".")[1]
        for group in range(group_count)
    ]


def _parameter_set_geometry_names(force: Any) -> list[str]:
    """Read the declared geometry names from a contact_parameters property.

    The typed ContactParametersSet accessor returns an unwrapped SwigPyObject
    in these bindings, so the generic property API is used instead.

    Args:
        force: HuntCrossleyForce or ElasticFoundationForce

    Returns:
        Geometry names in declaration order, across all parameter entries
    """
    prop = force.getPropertyByName("contact_parameters")
    names: list[str] = []

    for set_index in range(prop.size()):
        parameter_set = prop.getValueAsObject(set_index)
        names.extend(_names_in_parameter_set(parameter_set))

    return names


def _names_in_parameter_set(parameter_set: Any) -> list[str]:
    """Read geometry names from one ContactParametersSet.

    Args:
        parameter_set: A ContactParametersSet object

    Returns:
        Geometry names declared by its entries, in order
    """
    entries = parameter_set.getPropertyByName("objects")
    names: list[str] = []

    for entry_index in range(entries.size()):
        geometry = entries.getValueAsObject(entry_index).getPropertyByName("geometry")
        names.extend(geometry.toString().strip("()").split())

    return names


def _socket_geometry(force: Any, socket_name: str) -> Any | None:
    """Return the ContactGeometry connected to a named socket, or None.

    Args:
        force: Force owning the socket
        socket_name: Name of the socket to read

    Returns:
        The connected ContactGeometry, or None if absent
    """
    try:
        socket = force.getSocket(socket_name)
    except RuntimeError:
        return None

    connectee = socket.getConnecteeAsObject()
    if connectee is None:
        return None

    return opensim.ContactGeometry.safeDownCast(connectee)


if __name__ == "__main__":
    """Smoke test: resolve contact points across the bundled models."""
    import glob
    import sys
    from pathlib import Path

    opensim.Model.setDebugLevel(-1)

    candidates = (
        [sys.argv[1]]
        if len(sys.argv) > 1
        else sorted(glob.glob("resources/Models/**/*.osim", recursive=True))
    )

    print("contact_points smoke test")
    print(f"Supported types: {[t.value for t in ContactForceType]}\n")

    total_forces = total_points = 0
    for path in candidates:
        model = opensim.Model(path)
        model.initSystem()

        described = []
        for force in model.getForceSet():
            if not is_contact_force(force):
                continue
            points = resolve_contact_points(model, force)
            total_forces += 1
            total_points += len(points)
            described.append((force, points))

        if not described:
            continue

        print(f"{Path(path).name}")
        for force, points in described:
            print(f"  {force.getName()} ({force.getConcreteClassName()}) -> {len(points)} resultant(s)")
            for point in points:
                print(
                    f"      {point.key:<28} body={point.body_name:<12} "
                    f"offset={point.record_offset:<3} spheres={list(point.geometry_names)}"
                )

    print(f"\n[OK] {total_points} contact points across {total_forces} contact forces")
    assert total_points > 0, "expected to resolve at least one contact point"
    print("\n[OK] Smoke test passed!")
