"""
tests/test_biomech_load_shift.py

Unit tests for biomech.load_shift.compute_load_shift().
Verifies slope sign, minimum-rep guard, and metric_id format.

Synthetic input: BiomechRecord objects constructed directly
(no pose dataframe required).
"""

from __future__ import annotations

from movement.biomech import BiomechRecord
from movement.biomech.load_shift import compute_load_shift
from movement.biomarker import from_biomech_record

_SF = ["biomechanical_focus.main_load_regions"]


def test_biomech_record_defaults_to_low_confidence_depth_proxy_metadata():
    record = BiomechRecord(
        metric_id="biomech.com.range_x",
        exercise_id="squat",
        rep_id=1,
        value=0.1,
        unit="torso_length_ratio",
        source_fields=["biomechanical_focus.expected_com_motion"],
    )

    assert record.availability == "low_confidence"
    assert "monocular_biomech_proxy_low_confidence" in record.availability_reasons
    assert record.depth_dependency == "high"
    assert record.model_depth_reliability == "low"


def test_biomech_record_availability_is_preserved_in_biomarker_conversion():
    record = BiomechRecord(
        metric_id="biomech.moment_arm.knee.left.median",
        exercise_id="squat",
        rep_id=1,
        value=0.2,
        unit="torso_length_ratio",
        source_fields=["biomechanical_focus.main_load_regions"],
    )

    biomarker = from_biomech_record(record, definition_version="test")

    assert biomarker.availability == "low_confidence"
    assert biomarker.availability_reasons == record.availability_reasons
    assert biomarker.depth_dependency == "high"
    assert biomarker.model_depth_reliability == "low"


def _make_records(
    joint: str,
    side: str,
    values: list[float],
    exercise_id: str = "squat",
) -> list[BiomechRecord]:
    """Build per-rep moment-arm BiomechRecords for one (joint, side)."""
    return [
        BiomechRecord(
            metric_id=f"biomech.moment_arm.{joint}.{side}.median",
            exercise_id=exercise_id,
            rep_id=i,
            value=v,
            unit="torso_length_ratio",
            source_fields=_SF,
        )
        for i, v in enumerate(values)
    ]


# ── slope sign ────────────────────────────────────────────────────────────────


class TestSlopeSign:
    def test_pure_decreasing_gives_negative_slope(self):
        recs = _make_records("knee", "left", [0.50, 0.40, 0.30, 0.20, 0.10])
        results = compute_load_shift(recs)
        assert len(results) == 1
        assert results[0].value < 0

    def test_pure_increasing_gives_positive_slope(self):
        recs = _make_records("hip", "right", [0.10, 0.20, 0.30, 0.40, 0.50])
        results = compute_load_shift(recs)
        assert len(results) == 1
        assert results[0].value > 0

    def test_flat_trend_gives_near_zero_slope(self):
        recs = _make_records("knee", "right", [0.30, 0.30, 0.30, 0.30])
        results = compute_load_shift(recs)
        assert len(results) == 1
        assert abs(results[0].value) < 1e-6

    def test_slope_magnitude_matches_expected(self):
        # values decrease by exactly 0.1 per rep → slope = -0.1
        recs = _make_records("knee", "left", [0.50, 0.40, 0.30])
        results = compute_load_shift(recs)
        assert len(results) == 1
        assert abs(results[0].value - (-0.1)) < 1e-5


# ── minimum rep guard ─────────────────────────────────────────────────────────


class TestMinRepGuard:
    def test_two_reps_produces_no_output(self):
        recs = _make_records("knee", "left", [0.50, 0.30])
        results = compute_load_shift(recs)
        assert results == []

    def test_one_rep_produces_no_output(self):
        recs = _make_records("knee", "left", [0.40])
        results = compute_load_shift(recs)
        assert results == []

    def test_exactly_three_reps_produces_output(self):
        recs = _make_records("knee", "left", [0.50, 0.40, 0.30])
        results = compute_load_shift(recs)
        assert len(results) == 1

    def test_all_nan_values_produce_no_output(self):
        recs = _make_records("knee", "left", [float("nan"), float("nan"), float("nan")])
        results = compute_load_shift(recs)
        assert results == []

    def test_nan_values_are_excluded_before_slope_fit(self):
        recs = _make_records("knee", "left", [0.50, float("nan"), 0.30, 0.20])
        results = compute_load_shift(recs)
        assert len(results) == 1
        assert results[0].value < 0
        assert results[0].n_frames_used == 3


# ── metric_id and unit ────────────────────────────────────────────────────────


class TestMetadataFormat:
    def test_metric_id_format(self):
        recs = _make_records("knee", "left", [0.50, 0.40, 0.30])
        results = compute_load_shift(recs)
        assert results[0].metric_id == "biomech.load_shift.knee.left.slope"

    def test_unit_is_torso_length_ratio_per_rep(self):
        recs = _make_records("hip", "left", [0.20, 0.25, 0.30])
        results = compute_load_shift(recs)
        assert results[0].unit == "torso_length_ratio_per_rep"

    def test_rep_id_is_none_set_level(self):
        recs = _make_records("knee", "right", [0.40, 0.35, 0.30])
        results = compute_load_shift(recs)
        assert results[0].rep_id is None

    def test_source_fields_include_provenance(self):
        recs = _make_records("knee", "left", [0.50, 0.40, 0.30])
        results = compute_load_shift(recs)
        sf = results[0].source_fields
        assert any("load_shift" in f for f in sf)
        assert any("main_load_regions" in f for f in sf)

    def test_n_frames_used_equals_n_reps(self):
        recs = _make_records("knee", "left", [0.50, 0.40, 0.30, 0.20])
        results = compute_load_shift(recs)
        assert results[0].n_frames_used == 4

    def test_note_is_not_empty(self):
        recs = _make_records("knee", "left", [0.50, 0.40, 0.30])
        results = compute_load_shift(recs)
        assert results[0].note and len(results[0].note) > 0


# ── multiple joints ────────────────────────────────────────────────────────────


class TestMultipleJoints:
    def test_knee_and_hip_both_returned(self):
        knee_recs = _make_records("knee", "left", [0.50, 0.40, 0.30])
        hip_recs = _make_records("hip", "left", [0.20, 0.25, 0.30])
        results = compute_load_shift(knee_recs + hip_recs)
        metric_ids = {r.metric_id for r in results}
        assert "biomech.load_shift.knee.left.slope" in metric_ids
        assert "biomech.load_shift.hip.left.slope" in metric_ids

    def test_left_and_right_sides_independent(self):
        left = _make_records("knee", "left", [0.50, 0.40, 0.30])
        right = _make_records("knee", "right", [0.20, 0.25, 0.30])
        results = compute_load_shift(left + right)
        assert len(results) == 2
        slopes = {r.metric_id: r.value for r in results}
        assert slopes["biomech.load_shift.knee.left.slope"] < 0
        assert slopes["biomech.load_shift.knee.right.slope"] > 0

    def test_non_moment_arm_records_are_ignored(self):
        # BiomechRecord with a different metric_id (e.g. CoM metric) must be ignored
        other = BiomechRecord(
            metric_id="biomech.com.range_x",
            exercise_id="squat",
            rep_id=0,
            value=0.05,
            unit="torso_length_ratio",
            source_fields=_SF,
        )
        knee = _make_records("knee", "left", [0.50, 0.40, 0.30])
        results = compute_load_shift([other] + knee)
        assert len(results) == 1
        assert results[0].metric_id == "biomech.load_shift.knee.left.slope"

    def test_records_with_no_rep_id_are_ignored(self):
        # Sequence-level records (rep_id=None) must not contribute to slope
        seq_rec = BiomechRecord(
            metric_id="biomech.moment_arm.knee.left.median",
            exercise_id="squat",
            rep_id=None,
            value=0.99,
            unit="torso_length_ratio",
            source_fields=_SF,
        )
        rep_recs = _make_records("knee", "left", [0.50, 0.40, 0.30])
        results = compute_load_shift([seq_rec] + rep_recs)
        # slope must reflect only the 3 rep records, not the None-rep outlier
        assert len(results) == 1
        assert abs(results[0].value - (-0.1)) < 1e-5
