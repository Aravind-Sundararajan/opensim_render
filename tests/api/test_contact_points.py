"""Tests for resolving contact points from OpenSim contact forces.

The bundled models all use HuntCrossleyForce, which reports one resultant per
body and repeats it for each of that body's contact geometries. Grouping that
wrongly double counts the force, so the balance test below is the important one.
"""

from pathlib import Path

import opensim
import pytest

from osim_render.api.rendering.contact_points import (
    ContactForceType,
    is_contact_force,
    resolve_contact_points,
)

# Ships with the repo and uses HuntCrossleyForce on a two-segment foot.
_TOY_LANDING = Path("resources/Models/ToyDropLanding/ToyLandingModel.osim")
_SOCCER = Path("resources/Models/SoccerKick/SoccerKickingModel.osim")

pytestmark = pytest.mark.skipif(
    not _TOY_LANDING.is_file(), reason=f"model not found at {_TOY_LANDING}"
)


@pytest.fixture(scope="module")
def toy_landing() -> tuple[opensim.Model, opensim.State]:
    """Drop-landing model with HuntCrossley contact under each foot."""
    opensim.Model.setDebugLevel(-1)
    model = opensim.Model(str(_TOY_LANDING))
    state = model.initSystem()
    return model, state


def _in_contact(model: opensim.Model, state: opensim.State, drop: float) -> None:
    """Lower the model onto the platform by `drop` metres."""
    pelvis = model.getCoordinateSet().get("pelvis_ty")
    pelvis.setValue(state, pelvis.getDefaultValue() - drop, False)
    model.realizeDynamics(state)


class TestForceTypeRecognition:
    """Only real OpenSim contact classes are claimed as supported."""

    def test_supported_types_all_exist_in_opensim(self) -> None:
        for force_type in ContactForceType:
            assert hasattr(opensim, force_type.value), (
                f"{force_type.value} is not a real OpenSim class"
            )

    def test_contact_forces_are_recognised(self, toy_landing) -> None:
        model, _state = toy_landing

        recognised = [f.getName() for f in model.getForceSet() if is_contact_force(f)]

        assert sorted(recognised) == ["foot_l", "foot_r"]

    def test_muscles_are_not_contact_forces(self, toy_landing) -> None:
        model, _state = toy_landing

        muscles = [f for f in model.getForceSet() if "Muscle" in f.getConcreteClassName()]

        assert muscles, "expected the model to have muscles"
        assert not any(is_contact_force(m) for m in muscles)


class TestHuntCrossleyGrouping:
    """Resultants are grouped per body, not per sphere."""

    def test_one_resultant_per_body(self, toy_landing) -> None:
        model, _state = toy_landing
        force = model.getForceSet().get("foot_r")

        points = resolve_contact_points(model, force)

        assert sorted(p.body_name for p in points) == ["calcn_r", "toes_r"]

    def test_multiple_spheres_collapse_into_one_resultant(self, toy_landing) -> None:
        model, _state = toy_landing
        force = model.getForceSet().get("foot_r")

        points = {p.body_name: p for p in resolve_contact_points(model, force)}

        # Two spheres sit on toes_r but share a single reported resultant.
        assert len(points["toes_r"].geometry_names) == 2
        assert len(points["calcn_r"].geometry_names) == 1

    def test_half_space_geometry_produces_no_resultant(self, toy_landing) -> None:
        model, _state = toy_landing
        force = model.getForceSet().get("foot_r")

        points = resolve_contact_points(model, force)

        # platform_surface is a ContactHalfSpace and has no application point.
        assert "platform" not in {p.body_name for p in points}

    def test_keys_are_unique_across_the_model(self, toy_landing) -> None:
        model, _state = toy_landing

        keys = [
            p.key
            for f in model.getForceSet()
            if is_contact_force(f)
            for p in resolve_contact_points(model, f)
        ]

        assert len(keys) == len(set(keys))

    def test_record_offset_selects_the_named_body(self, toy_landing) -> None:
        model, state = toy_landing
        force = model.getForceSet().get("foot_r")
        labels = force.getRecordLabels()

        for point in resolve_contact_points(model, force):
            label = labels.get(point.record_offset)
            assert label.split(".")[1] == point.body_name


class TestForcesBalance:
    """The resolved resultants must obey Newton's third law.

    Grouping per sphere instead of per body would double count any body
    carrying more than one sphere, and this test would fail.
    """

    @pytest.mark.parametrize("drop", [0.528, 0.56, 0.62, 0.70])
    def test_resultants_balance_the_reaction(self, toy_landing, drop) -> None:
        model, state = toy_landing
        _in_contact(model, state, drop)
        force = model.getForceSet().get("foot_r")

        points = resolve_contact_points(model, force)
        values = force.getRecordValues(state)

        # Record group 0 is the platform's reaction to every sphere.
        reaction = [values.get(i) for i in range(3)]
        applied = [sum(p.force_vector(values)[i] for p in points) for i in range(3)]

        for axis in range(3):
            assert reaction[axis] + applied[axis] == pytest.approx(0.0, abs=1e-6)

    def test_contact_produces_upward_force(self, toy_landing) -> None:
        model, state = toy_landing
        _in_contact(model, state, 0.56)
        force = model.getForceSet().get("foot_r")
        values = force.getRecordValues(state)

        total_vertical = sum(
            p.force_vector(values)[1] for p in resolve_contact_points(model, force)
        )

        assert total_vertical > 0.0, "ground should push the foot up"

    def test_no_contact_means_no_force(self, toy_landing) -> None:
        model, state = toy_landing
        _in_contact(model, state, 0.0)
        force = model.getForceSet().get("foot_r")
        values = force.getRecordValues(state)

        for point in resolve_contact_points(model, force):
            assert point.force_vector(values) == pytest.approx((0.0, 0.0, 0.0))


class TestResultantLocation:
    """A resultant is drawn at the centroid of its contributing spheres."""

    def test_single_sphere_sits_at_that_sphere(self, toy_landing) -> None:
        model, state = toy_landing
        _in_contact(model, state, 0.0)
        force = model.getForceSet().get("foot_r")
        point = next(
            p for p in resolve_contact_points(model, force) if p.body_name == "calcn_r"
        )

        located = point.location_in_ground(state, model.getGround())
        heel = model.getContactGeometrySet().get("heel_r")
        expected = heel.getFrame().findStationLocationInGround(state, heel.getLocation())

        assert located == pytest.approx(
            (expected.get(0), expected.get(1), expected.get(2))
        )

    def test_two_spheres_sit_between_them(self, toy_landing) -> None:
        model, state = toy_landing
        _in_contact(model, state, 0.0)
        force = model.getForceSet().get("foot_r")
        point = next(
            p for p in resolve_contact_points(model, force) if p.body_name == "toes_r"
        )

        located = point.location_in_ground(state, model.getGround())
        corners = []
        for name in point.geometry_names:
            geometry = model.getContactGeometrySet().get(name)
            world = geometry.getFrame().findStationLocationInGround(
                state, geometry.getLocation()
            )
            corners.append([world.get(i) for i in range(3)])

        for axis in range(3):
            low = min(c[axis] for c in corners)
            high = max(c[axis] for c in corners)
            assert low - 1e-9 <= located[axis] <= high + 1e-9


@pytest.mark.skipif(not _SOCCER.is_file(), reason=f"model not found at {_SOCCER}")
class TestManySpheresOnOneBody:
    """A body with many spheres still yields a single resultant."""

    def test_goalie_collapses_to_one_resultant(self) -> None:
        opensim.Model.setDebugLevel(-1)
        model = opensim.Model(str(_SOCCER))
        model.initSystem()
        force = model.getForceSet().get("goalie_ball")

        points = {p.body_name: p for p in resolve_contact_points(model, force)}

        assert sorted(points) == ["ball", "goalie"]
        assert len(points["goalie"].geometry_names) == 10
