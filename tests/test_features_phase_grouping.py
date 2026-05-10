from types import SimpleNamespace

import pandas as pd

from movement.exercise_definition import (
    LandmarkSpec,
    PhaseSegmentationSpec,
    SmoothingSpec,
    TurnaroundHoldSpec,
)
from movement.features import extract_rep_features


def _exercise_definition():
    return SimpleNamespace(
        exercise_id="phase_fixture",
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
