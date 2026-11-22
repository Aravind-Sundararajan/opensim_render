"""Tests for camera follow-body tracking.

The offset must be measured from a fixed base pose. Adding the total
displacement to wherever the camera currently sits compounds every frame and
the camera flies away from the very body it is meant to track.
"""

import math
from pathlib import Path

import opensim
import pytest

from osim_render.api.loaders.motion_loader import MotionFrame
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager

_MODEL = Path("resources/Models/Gait2354_Simbody/gait2354_simbody.osim")
_TRACKED = "pelvis"
_TRAVEL_COORDINATE = "pelvis_tx"

pytestmark = pytest.mark.skipif(
    not _MODEL.is_file(), reason=f"model not found at {_MODEL}"
)


@pytest.fixture
def scene() -> SceneManager:
    """A framed gait scene."""
    opensim.Model.setDebugLevel(-1)
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    model_manager.load_model(_MODEL)

    offscreen = OffscreenRenderer(resolution=(200, 200))
    scene_manager = SceneManager(model_manager, _MODEL)
    scene_manager.create_scene(renderer=offscreen.renderer)
    offscreen.renderer.ResetCamera()
    offscreen.render_window.Render()
    return scene_manager


def _neutral(scene_manager: SceneManager) -> dict[str, float]:
    """A pose with every coordinate at zero."""
    return {
        coordinate.getName(): 0.0
        for coordinate in scene_manager.opensim_model.getCoordinateSet()
    }


def _camera_position(scene_manager: SceneManager) -> tuple[float, float, float]:
    """Current camera position."""
    return tuple(scene_manager.scene.renderer.GetActiveCamera().GetPosition())


def _body_position(scene_manager: SceneManager) -> tuple[float, float, float]:
    """Current world position of the tracked body."""
    body = scene_manager.opensim_model.getBodySet().get(_TRACKED)
    point = body.getPositionInGround(scene_manager.state)
    return (point.get(0), point.get(1), point.get(2))


def _distance(a, b) -> float:
    """Euclidean distance between two points."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=False)))


def _walk(scene_manager: SceneManager, distances: list[float]) -> None:
    """Drive frames that translate the tracked body along x."""
    for index, travel in enumerate(distances):
        values = _neutral(scene_manager)
        values[_TRAVEL_COORDINATE] = travel
        scene_manager.update_frame(
            MotionFrame(time=index * 0.1, coordinate_values=values)
        )


class TestFollowTracksTheBody:
    """The camera holds a constant offset to the body it follows."""

    def test_camera_moves_with_the_body(self, scene) -> None:
        scene.set_camera_follow_body(_TRACKED)
        _walk(scene, [0.0])
        start_camera, start_body = _camera_position(scene), _body_position(scene)

        _walk(scene, [0.5])

        camera_travel = _distance(_camera_position(scene), start_camera)
        body_travel = _distance(_body_position(scene), start_body)
        assert camera_travel == pytest.approx(body_travel, abs=1e-9)

    def test_offset_does_not_compound_over_frames(self, scene) -> None:
        """Re-applying the total displacement each frame used to run away."""
        scene.set_camera_follow_body(_TRACKED)
        _walk(scene, [0.0])
        baseline = _distance(_camera_position(scene), _body_position(scene))

        # Many frames at a standstill must not move the camera at all.
        _walk(scene, [0.4] * 25)

        assert _distance(_camera_position(scene), _body_position(scene)) == pytest.approx(
            baseline, abs=1e-9
        )

    def test_framing_is_held_across_a_whole_walk(self, scene) -> None:
        scene.set_camera_follow_body(_TRACKED)
        _walk(scene, [0.0])
        baseline = _distance(_camera_position(scene), _body_position(scene))

        offsets = []
        for travel in [index * 0.05 for index in range(20)]:
            _walk(scene, [travel])
            offsets.append(_distance(_camera_position(scene), _body_position(scene)))

        assert max(offsets) - min(offsets) == pytest.approx(0.0, abs=1e-9)
        assert offsets[0] == pytest.approx(baseline, abs=1e-9)

    def test_returning_to_the_start_returns_the_camera(self, scene) -> None:
        scene.set_camera_follow_body(_TRACKED)
        _walk(scene, [0.0])
        start_camera = _camera_position(scene)

        _walk(scene, [0.6, 0.3, 0.0])

        assert _camera_position(scene) == pytest.approx(start_camera, abs=1e-9)


class TestFollowLifecycle:
    """Following can be started, queried and stopped."""

    def test_not_following_by_default(self, scene) -> None:
        assert scene.get_followed_body() is None

    def test_setting_a_body_reports_it(self, scene) -> None:
        scene.set_camera_follow_body(_TRACKED)

        assert scene.get_followed_body() == _TRACKED

    def test_clearing_stops_following(self, scene) -> None:
        scene.set_camera_follow_body(_TRACKED)
        _walk(scene, [0.0, 0.2])

        scene.clear_camera_follow()

        assert scene.get_followed_body() is None

    def test_camera_stays_put_after_clearing(self, scene) -> None:
        scene.set_camera_follow_body(_TRACKED)
        _walk(scene, [0.0, 0.2])
        parked = _camera_position(scene)

        scene.clear_camera_follow()
        _walk(scene, [0.9])

        assert _camera_position(scene) == pytest.approx(parked, abs=1e-9)

    def test_switching_body_rebaselines(self, scene) -> None:
        scene.set_camera_follow_body(_TRACKED)
        _walk(scene, [0.0, 0.4])

        scene.set_camera_follow_body("torso")
        before = _camera_position(scene)
        _walk(scene, [0.4])

        # Re-baselining means no jump on the frame the new body is adopted.
        assert _camera_position(scene) == pytest.approx(before, abs=1e-9)

    def test_unknown_body_is_survivable(self, scene) -> None:
        scene.set_camera_follow_body("no_such_body")
        parked = _camera_position(scene)

        _walk(scene, [0.0, 0.5])

        assert _camera_position(scene) == pytest.approx(parked, abs=1e-9)
