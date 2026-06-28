from types import SimpleNamespace

import pandas as pd

from movement.exercise_definition import (
    LandmarkSpec,
    PhaseSegmentationSpec,
    SmoothingSpec,
    TurnaroundHoldSpec,
)
from movement.features import extract_rep_features
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
    assert "spatial.phase_rom_ratio.descent_ascent" in feature_ids
    summary = next(
        record
        for record in report["features"]
        if record["feature_id"] == "spatial.phase_rom_ratio.descent_ascent"
    )
    assert summary["exercise_id"] == "phase_fixture"
    assert summary["rep_id"] == 1
    assert summary["phase"] is None
    assert summary["unit"] == "dimensionless"
    assert summary["source_fields"]
