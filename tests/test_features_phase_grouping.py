from types import SimpleNamespace

import pandas as pd

from movement.exercise_definition import (
    LandmarkSpec,
    PhaseSegmentationSpec,
    SmoothingSpec,
    TurnaroundHoldSpec,
)
from movement.features import extract_rep_features, summarize_phase_to_rep
from movement.pipeline import PipelineConfig, run_pipeline


def _exercise_definition():
    return SimpleNamespace(
        exercise_id="phase_fixture",
        display_name="Phase Fixture",
        version="0.0.0-test",
        is_generic_fallback=False,
        classification={
            "laterality": "bilateral_symmetric",
            "movement_template_id": "phase_fixture",
            "primary_plane": "sagittal",
        },
        angle_definitions={
            "left_knee": {
                "proximal": "left_hip",
                "vertex": "left_knee",
                "distal": "left_ankle",
            },
        },
        landmarks=LandmarkSpec(
            model="mediapipe_pose",
            primary_joints=["left_knee"],
        ),
        compensation_candidates=[],
        camera_protocol=None,
        phase_segmentation=PhaseSegmentationSpec(
            reference_landmark="hip_center",
            reference_axis="vertical",
            phase_sequence=["Descent", "Ascent"],
            split_logic="local_minimum",
            smoothing=SmoothingSpec(
                method="savitzky_golay",
                window_frames=1,
                polyorder=0,
            ),
            turnaround_hold=TurnaroundHoldSpec(
                enabled=False,
                half_window_frames=0,
            ),
        ),
    )


def _featured_df():
    return pd.DataFrame(
        {
            "frame": [0, 1, 2, 3],
            "timestamp": [0.0, 0.1, 0.2, 0.3],
            "segment_type": ["rep", "rep", "rep", "rep"],
            "rep_id": pd.array([1, 1, 1, 1], dtype="Int64"),
            "phase": ["Descent", "Descent", "Ascent", "Ascent"],
            "left_hip_norm_x": [0.0, 0.0, 0.0, 0.0],
            "left_hip_norm_y": [1.0, 1.0, 1.0, 1.0],
            "left_hip_norm_z": [1.0, 1.0, 1.0, 1.0],
            "right_hip_norm_x": [0.2, 0.2, 0.2, 0.2],
            "right_hip_norm_y": [1.0, 1.0, 1.0, 1.0],
            "right_hip_norm_z": [1.0, 1.0, 1.0, 1.0],
            "left_knee_norm_x": [0.0, 0.0, 0.0, 0.0],
            "left_knee_norm_y": [0.0, 0.0, 0.0, 0.0],
            "left_knee_norm_z": [0.0, 0.0, 0.0, 0.0],
            "left_ankle_norm_x": [1.0, 1.0, 1.0, 1.0],
            "left_ankle_norm_y": [0.0, 0.0, 0.0, 0.0],
            "left_ankle_norm_z": [0.0, 0.0, 0.0, 0.0],
        }
    )


def test_phase_level_feature_records_include_phase_provenance():
    records = extract_rep_features(_featured_df(), _exercise_definition())

    phase_records = [record for record in records if record.phase is not None]
    assert phase_records
    assert {record.phase for record in phase_records} == {"Descent", "Ascent"}
    assert any(
        record.feature_id.startswith("temporal.tempo.") for record in phase_records
    )

    for record in phase_records:
        assert record.feature_id.endswith(f".{record.phase.lower()}")
        assert "phase_segmentation.reference_landmark" in record.source_fields
        assert "phase_segmentation.reference_axis" in record.source_fields
        assert "phase_segmentation.split_logic" in record.source_fields

    assert any(record.phase is None for record in records)


def test_phase_level_feature_ids_use_lower_snake_case_suffix():
    df = _featured_df().copy()
    df["phase"] = ["Turnaround Hold", "Turnaround Hold", "Step-Out", "Step-Out"]

    records = extract_rep_features(df, _exercise_definition())
    phase_ids = {record.feature_id for record in records if record.phase is not None}

    assert any(feature_id.endswith(".turnaround_hold") for feature_id in phase_ids)
    assert any(feature_id.endswith(".step_out") for feature_id in phase_ids)


def test_pipeline_feature_report_includes_phase_summary_records(monkeypatch):
    import movement.definitions.exercise_definition as definition_loader

    monkeypatch.setattr(
        definition_loader,
        "load_exercise_definition",
        lambda *args, **kwargs: _exercise_definition(),
    )

    config = PipelineConfig()
    config.validation.enabled = False
    config.annotation.enabled = False
    config.exercise_definition.enabled = True
    config.exercise_definition.exercise_id = "phase_fixture"
    config.preprocessing.enabled = False
    config.normalization.enabled = False
    config.rep_segmentation.enabled = False
    config.phase_segmentation.enabled = False
    config.features.enabled = True
    config.features.role_context.enabled = False
    config.biomech.enabled = False
    config.biomarker.enabled = False

    _, report = run_pipeline(_featured_df(), config)

    feature_ids = [record["feature_id"] for record in report["features"]]
    assert "spatial.phase_profile.range_of_motion_ratio.descent_ascent" in feature_ids
    assert "temporal.phase_profile.duration_ratio.descent_ascent" in feature_ids
    summary = next(
        record
        for record in report["features"]
        if record["feature_id"]
        == "spatial.phase_profile.range_of_motion_ratio.descent_ascent"
    )
    assert summary["exercise_id"] == "phase_fixture"
    assert summary["rep_id"] == 1
    assert summary["phase"] is None
    assert summary["unit"] == "dimensionless"
    assert summary["source_fields"]

    temporal_summary = next(
        record
        for record in report["features"]
        if record["feature_id"]
        == "temporal.phase_profile.duration_ratio.descent_ascent"
    )
    assert temporal_summary["exercise_id"] == "phase_fixture"
    assert temporal_summary["rep_id"] == 1
    assert temporal_summary["phase"] is None
    assert temporal_summary["unit"] == "dimensionless"
    assert temporal_summary["source_fields"]


def test_temporal_phase_profile_uses_exercise_phase_sequence_labels():
    exercise = _exercise_definition()
    records = extract_rep_features(_featured_df(), exercise)
    summary_records = summarize_phase_to_rep(records, exercise)

    temporal_summary = next(
        record
        for record in summary_records
        if record.feature_id == "temporal.phase_profile.duration_ratio.descent_ascent"
    )

    assert temporal_summary.value == 1.0
    assert temporal_summary.evaluation_domain == "timing_only"
    assert temporal_summary.evidence_axes == "time"
    assert temporal_summary.feature_family == "phase_profile"
    assert "phase_segmentation.phase_sequence" in temporal_summary.source_fields
    assert "feature_domains.temporal.phase_profile" in temporal_summary.source_fields


def test_temporal_rep_duration_uses_rep_invariant_feature_id():
    records = extract_rep_features(_featured_df(), _exercise_definition())

    rep_temporal = [
        record
        for record in records
        if record.phase is None and record.feature_id.startswith("temporal.tempo.")
    ]

    assert rep_temporal
    assert {record.feature_id for record in rep_temporal} == {
        "temporal.tempo.rep_duration"
    }
    assert {record.rep_id for record in rep_temporal} == {1}
    assert all(
        "feature_domains.temporal.tempo" in record.source_fields
        for record in rep_temporal
    )
    assert all("segmentation.rep_id" in record.source_fields for record in rep_temporal)
    assert all("timestamp" in record.source_fields for record in rep_temporal)


def test_phase_level_axis_diagnostics_remain_report_only():
    records = extract_rep_features(_featured_df(), _exercise_definition())

    axis_records = [
        record
        for record in records
        if record.phase is not None
        and record.feature_id.startswith("spatial.movement_path.axis_path_z.left_knee.")
    ]

    assert axis_records
    assert {record.availability for record in axis_records} == {"not_assessed"}
    assert {record.depth_dependency for record in axis_records} == {"high"}
    assert all(
        "movement_path_axis_diagnostic_report_only" in record.availability_reasons
        for record in axis_records
    )
