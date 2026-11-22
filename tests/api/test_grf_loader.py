"""Tests for loading ground reaction force data.

GRF ships in several column-naming conventions and reaches OpenSim either
through an ExternalLoads XML or as a bare data file. Both routes are covered
here against the real trial data in resources/.
"""

from pathlib import Path

import pytest

from osim_render.api.loaders.grf_loader import (
    GroundReactionData,
    detect_sources,
    load_data_file,
    load_external_loads,
    load_ground_reactions,
)

_GAIT2354 = Path("resources/Models/Gait2354_Simbody")
_XML = _GAIT2354 / "subject01_walk1_grf.xml"
_MOT = _GAIT2354 / "subject01_walk1_grf.mot"

pytestmark = pytest.mark.skipif(
    not _XML.is_file(), reason=f"trial data not found at {_XML}"
)


@pytest.fixture(scope="module")
def loaded() -> GroundReactionData:
    """GRF loaded through its ExternalLoads XML."""
    return load_ground_reactions(_XML)


class TestExternalLoadsXml:
    """An ExternalLoads XML names its data file and columns."""

    def test_resolves_datafile_relative_to_the_xml(self, loaded) -> None:
        assert loaded.path.name == "subject01_walk1_grf.mot"
        assert loaded.path.is_file()

    def test_reads_both_plates(self, loaded) -> None:
        assert [source.name for source in loaded.sources] == ["right", "left"]

    def test_carries_body_attribution(self, loaded) -> None:
        bodies = {source.name: source.applied_to_body for source in loaded.sources}

        assert bodies == {"right": "calcn_r", "left": "calcn_l"}

    def test_data_is_expressed_in_ground(self, loaded) -> None:
        assert all(source.is_in_ground for source in loaded.sources)

    def test_finds_torque_columns_when_present(self, loaded) -> None:
        assert all(source.torque_columns is not None for source in loaded.sources)

    def test_missing_file_is_reported(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_external_loads(_GAIT2354 / "does_not_exist.xml")


class TestColumnDetection:
    """Bare data files are read by recognising the column convention."""

    @pytest.mark.parametrize(
        ("labels", "expected"),
        [
            # Plate-numbered, as used by the gait2354 family
            (
                ("ground_force_vx", "ground_force_vy", "ground_force_vz",
                 "ground_force_px", "ground_force_py", "ground_force_pz"),
                ["ground_force"],
            ),
            # Side-suffixed, as used by the Moco examples
            (
                ("ground_force_r_vx", "ground_force_r_vy", "ground_force_r_vz",
                 "ground_force_r_px", "ground_force_r_py", "ground_force_r_pz",
                 "ground_force_l_vx", "ground_force_l_vy", "ground_force_l_vz",
                 "ground_force_l_px", "ground_force_l_py", "ground_force_l_pz"),
                ["ground_force_r", "ground_force_l"],
            ),
            # Side-prefixed, as used by the running examples
            (
                ("R_ground_force_vx", "R_ground_force_vy", "R_ground_force_vz",
                 "R_ground_force_px", "R_ground_force_py", "R_ground_force_pz"),
                ["R_ground_force"],
            ),
        ],
    )
    def test_recognises_each_convention(self, labels, expected) -> None:
        sources = detect_sources(labels)

        assert [source.name for source in sources] == expected

    def test_force_without_matching_point_is_skipped(self) -> None:
        labels = ("ground_force_vx", "ground_force_vy", "ground_force_vz")

        assert detect_sources(labels) == ()

    def test_unrelated_columns_are_ignored(self) -> None:
        labels = ("pelvis_tx", "knee_angle_r", "time")

        assert detect_sources(labels) == ()

    def test_bare_file_matches_the_xml(self, loaded) -> None:
        bare = load_data_file(_MOT)

        assert len(bare.sources) == len(loaded.sources)

    def test_file_without_grf_columns_is_reported(self, tmp_path) -> None:
        motion = tmp_path / "not_grf.mot"
        motion.write_text(
            "not_grf\nversion=1\nnRows=2\nnColumns=2\ninDegrees=no\nendheader\n"
            "time\tknee_angle_r\n0\t0.1\n0.01\t0.2\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="No ground reaction columns"):
            load_data_file(motion)


class TestSampling:
    """Readings are interpolated and bounded by the recording."""

    def test_sample_at_a_recorded_time(self, loaded) -> None:
        right = loaded.sources[0]

        sample = loaded.sample(right, loaded.times[0])

        assert sample is not None
        assert sample.magnitude > 0.0

    def test_interpolates_between_rows(self, loaded) -> None:
        right = loaded.sources[0]
        first, second = loaded.times[10], loaded.times[11]

        low = loaded.sample(right, first)
        mid = loaded.sample(right, (first + second) / 2.0)
        high = loaded.sample(right, second)

        assert low is not None and mid is not None and high is not None
        bounds = sorted((low.force[1], high.force[1]))
        assert bounds[0] <= mid.force[1] <= bounds[1]

    def test_interpolation_is_strictly_between_when_values_differ(self, loaded) -> None:
        right = loaded.sources[0]
        first, second = loaded.times[10], loaded.times[11]
        low = loaded.sample(right, first)
        high = loaded.sample(right, second)
        assert low is not None and high is not None
        assert low.force[1] != high.force[1], "need differing rows for this test"

        mid = loaded.sample(right, (first + second) / 2.0)

        assert mid is not None
        assert mid.force[1] not in (low.force[1], high.force[1])

    def test_before_the_recording_returns_nothing(self, loaded) -> None:
        assert loaded.sample(loaded.sources[0], loaded.start_time - 0.1) is None

    def test_after_the_recording_returns_nothing(self, loaded) -> None:
        assert loaded.sample(loaded.sources[0], loaded.end_time + 0.1) is None

    def test_covers_reports_the_recorded_range(self, loaded) -> None:
        assert loaded.covers(loaded.start_time)
        assert loaded.covers(loaded.end_time)
        assert not loaded.covers(loaded.end_time + 1e-6)


class TestPhysicalPlausibility:
    """The loaded traces look like real walking data."""

    def test_peak_force_is_about_bodyweight(self, loaded) -> None:
        peaks = [
            max(
                loaded.sample(source, time).magnitude  # type: ignore[union-attr]
                for time in loaded.times
            )
            for source in loaded.sources
        ]

        # subject01 is roughly 72 kg, so a walking peak lands near 1 bodyweight.
        for peak in peaks:
            assert 500.0 < peak < 1500.0

    def test_each_plate_has_stance_and_swing(self, loaded) -> None:
        for source in loaded.sources:
            magnitudes = [
                loaded.sample(source, time).magnitude  # type: ignore[union-attr]
                for time in loaded.times
            ]
            loaded_rows = sum(1 for value in magnitudes if value > 1.0)

            assert 0 < loaded_rows < len(magnitudes), "expected stance and swing"

    def test_vertical_force_is_upward_during_stance(self, loaded) -> None:
        right = loaded.sources[0]

        vertical = [
            loaded.sample(right, time).force[1]  # type: ignore[union-attr]
            for time in loaded.times
        ]
        loaded_values = [value for value in vertical if abs(value) > 1.0]

        assert loaded_values and all(value > 0.0 for value in loaded_values)
