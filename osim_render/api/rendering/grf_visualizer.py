"""Visualization of ground reaction forces as VTK arrow actors.

Unlike contact forces, ground reactions come from recorded data rather than the
model's own dynamics, so they are sampled at the playback time rather than read
from the state. The arrow is drawn at the measured centre of pressure.
"""

from __future__ import annotations

from typing import Any, Optional

import opensim
import vtkmodules.all as vtk

from osim_render.api.loaders.grf_loader import (
    GROUND_FRAME,
    GroundReactionData,
    GroundReactionSample,
    GroundReactionSource,
)
from osim_render.api.logging import get_logger_for
from osim_render.api.rendering.force_arrow import (
    ArrowStyle,
    create_arrow_actor,
    place_arrow,
)

logger = get_logger_for(__name__)

# Green, to read apart from the red contact force arrows.
GRF_STYLE = ArrowStyle(color=(0.1, 0.85, 0.3), opacity=1.0)

# Below this the plate is unloaded and an arrow would be visual noise.
MIN_VISIBLE_FORCE = 1.0


class GroundReactionVisualizer:
    """Draw recorded ground reaction forces at their centre of pressure."""

    def __init__(
        self,
        model: Any,
        state: Any,
        style: ArrowStyle = GRF_STYLE,
        min_visible_force: float = MIN_VISIBLE_FORCE,
    ):
        """Initialize the visualizer.

        Args:
            model: OpenSim model, used only to resolve non-ground frames
            state: OpenSim state, used only to resolve non-ground frames
            style: Arrow appearance and scaling
            min_visible_force: Hide arrows carrying less than this, in newtons
        """
        self.model = model
        self.state = state
        self.style = style
        self.min_visible_force = min_visible_force
        self.data: Optional[GroundReactionData] = None

    def set_data(self, data: Optional[GroundReactionData]) -> None:
        """Attach or clear the ground reaction traces.

        Args:
            data: Loaded traces, or None to clear
        """
        self.data = data

    def create_actors(self) -> dict[str, vtk.vtkActor]:
        """Create one arrow actor per ground reaction source.

        Returns:
            Map of source name -> vtkActor, empty when no data is attached
        """
        if self.data is None:
            return {}

        actors = {
            source.name: create_arrow_actor(self.style) for source in self.data.sources
        }
        logger.info(f"Created {len(actors)} ground reaction arrows")
        return actors

    def update(
        self,
        actors: dict[str, vtk.vtkActor],
        time: float,
        visible_sources: set[str] | None = None,
    ) -> None:
        """Place each arrow for the given playback time.

        An arrow is drawn only when the user wants it, the time falls inside
        the recording, and the plate is actually loaded.

        Args:
            actors: Map of source name -> vtkActor
            time: Playback time in seconds
            visible_sources: Names the user has chosen to show. None means no
                caller is managing visibility.
        """
        if self.data is None:
            self._hide_all(actors)
            return

        for source in self.data.sources:
            actor = actors.get(source.name)
            if actor is None:
                continue

            self._update_one(actor, source, time, visible_sources)

    def _update_one(
        self,
        actor: vtk.vtkActor,
        source: GroundReactionSource,
        time: float,
        visible_sources: set[str] | None,
    ) -> None:
        """Place a single source's arrow, or hide it.

        Args:
            actor: Arrow actor for this source
            source: Source being drawn
            time: Playback time in seconds
            visible_sources: Names the user wants shown, or None if unmanaged
        """
        if visible_sources is not None and source.name not in visible_sources:
            actor.SetVisibility(False)
            return

        assert self.data is not None
        sample = self.data.sample(source, time)

        if sample is None or sample.magnitude < self.min_visible_force:
            actor.SetVisibility(False)
            return

        position, force = self._in_ground(source, sample)
        place_arrow(actor, position, force, self.style)
        actor.SetVisibility(True)

    def _in_ground(
        self, source: GroundReactionSource, sample: GroundReactionSample
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Express a sample's point and force in ground coordinates.

        Recorded ground reactions are almost always already in ground, so this
        is a passthrough in practice.

        Args:
            source: Source describing the frames the data is expressed in
            sample: The reading to convert

        Returns:
            Tuple of (point, force) in ground coordinates
        """
        if source.is_in_ground:
            return (sample.point, sample.force)

        return (
            self._station_in_ground(source.point_expressed_in, sample.point),
            self._vector_in_ground(source.force_expressed_in, sample.force),
        )

    def _station_in_ground(
        self, frame_name: str, point: tuple[float, float, float]
    ) -> tuple[float, float, float]:
        """Convert a point in a named frame into ground coordinates.

        Args:
            frame_name: Frame the point is expressed in
            point: The point

        Returns:
            The point in ground coordinates
        """
        frame = self._frame(frame_name)
        if frame is None:
            return point

        located = frame.findStationLocationInGround(self.state, opensim.Vec3(*point))
        return (located.get(0), located.get(1), located.get(2))

    def _vector_in_ground(
        self, frame_name: str, vector: tuple[float, float, float]
    ) -> tuple[float, float, float]:
        """Rotate a vector from a named frame into ground coordinates.

        Args:
            frame_name: Frame the vector is expressed in
            vector: The vector

        Returns:
            The vector in ground coordinates
        """
        frame = self._frame(frame_name)
        if frame is None:
            return vector

        rotated = frame.expressVectorInGround(self.state, opensim.Vec3(*vector))
        return (rotated.get(0), rotated.get(1), rotated.get(2))

    def _frame(self, frame_name: str) -> Any | None:
        """Look up a body frame by name.

        Args:
            frame_name: Name of the frame

        Returns:
            The body, or None for ground or an unknown name
        """
        if frame_name == GROUND_FRAME:
            return None

        body_set = self.model.getBodySet()
        if body_set.getIndex(frame_name) < 0:
            logger.warning(f"Ground reaction frame not found in model: {frame_name}")
            return None

        return body_set.get(frame_name)

    def _hide_all(self, actors: dict[str, vtk.vtkActor]) -> None:
        """Hide every arrow.

        Args:
            actors: Map of source name -> vtkActor
        """
        for actor in actors.values():
            actor.SetVisibility(False)


if __name__ == "__main__":
    """Smoke test for GroundReactionVisualizer."""
    import sys

    from osim_render.api.loaders.grf_loader import load_ground_reactions

    opensim.Model.setDebugLevel(-1)

    model_path = "resources/Models/Gait2354_Simbody/gait2354_simbody.osim"
    grf_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "resources/Models/Gait2354_Simbody/subject01_walk1_grf.xml"
    )
    print(f"GroundReactionVisualizer smoke test on {grf_path}")

    model = opensim.Model(model_path)
    state = model.initSystem()
    model.realizePosition(state)

    data = load_ground_reactions(grf_path)
    visualizer = GroundReactionVisualizer(model, state)
    visualizer.set_data(data)

    actors = visualizer.create_actors()
    print(f"[OK] Created arrows: {sorted(actors)}")
    assert len(actors) == len(data.sources)

    print("\nStepping through the trial...")
    for time in (0.0, 0.25, 0.6, 0.9, 1.2):
        visualizer.update(actors, time)
        shown = sorted(name for name, a in actors.items() if a.GetVisibility())
        print(f"   t={time:.2f} -> visible {shown}")

    print("\nChecking an arrow sits at the measured centre of pressure...")
    visualizer.update(actors, 1.2)
    right = data.sources[0]
    sample = data.sample(right, 1.2)
    assert sample is not None
    base = actors[right.name].GetUserTransform().TransformPoint(0.0, 0.0, 0.0)
    print(f"   COP  {tuple(round(v, 4) for v in sample.point)}")
    print(f"   base {tuple(round(v, 4) for v in base)}")
    assert all(abs(base[i] - sample.point[i]) < 1e-9 for i in range(3))

    print("\nChecking out-of-range time hides the arrows...")
    visualizer.update(actors, data.end_time + 5.0)
    assert not any(a.GetVisibility() for a in actors.values())
    print("   [OK] all hidden past the end of the recording")

    print("\nChecking the visibility filter is respected...")
    visualizer.update(actors, 1.2, visible_sources=set())
    assert not any(a.GetVisibility() for a in actors.values())
    visualizer.update(actors, 1.2, visible_sources={right.name})
    assert actors[right.name].GetVisibility()
    print("   [OK] only the requested source is drawn")

    print("\n[OK] Smoke test passed!")
