from types import SimpleNamespace

import numpy as np
import pandas as pd

from movement.exercise_definition import (
    PhaseSegmentationSpec,
    SmoothingSpec,
    TurnaroundHoldSpec,
)
from movement.segmentation import segment_phases


def _phase_definition(**overrides):
    params = {
        "reference_landmark": "hip_center",
        "reference_axis": "vertical",
        "phase_sequence": ["Descent", "Ascent"],
        "split_logic": "local_minimum",
        "smoothing": SmoothingSpec(
            method="savitzky_golay",
            window_frames=1,
            polyorder=0,
        ),
        "turnaround_hold": TurnaroundHoldSpec(
            enabled=False,
            half_window_frames=0,
        ),
        "minimum_rep_length_frames": 3,
        "multi_inflection_policy": "global_extremum",
    }
    params.update(overrides)
    return SimpleNamespace(phase_segmentation=PhaseSegmentationSpec(**params))


def _phase_df(trace, phase_values=None):
    n = len(trace)
    if phase_values is None:
        phase_values = [pd.NA] * n
    return pd.DataFrame(
        {
            "frame": list(range(n)),
            "timestamp": np.arange(n) / 30.0,
            "hip_center_norm_z": trace,
            "segment_type": "rep",
            "rep_id": pd.array([1] * n, dtype="Int64"),
            "phase": pd.array(phase_values, dtype=object),
        }
    )


def _raw_phase_df(trace):
    n = len(trace)
    return pd.DataFrame(
        {
            "frame": list(range(n)),
            "timestamp": np.arange(n) / 30.0,
            "left_hip_y": trace,
            "right_hip_y": trace,
            "segment_type": "rep",
            "rep_id": pd.array([1] * n, dtype="Int64"),
            "phase": pd.array([pd.NA] * n, dtype=object),
        }
    )


def test_segment_phases_splits_nominal_two_phase_rep():
    df, reports = segment_phases(
        _phase_df([1.0, 0.75, 0.0, 0.75, 1.0]),
        _phase_definition(),
    )

    assert df["phase"].tolist() == [
        "Descent",
        "Descent",
        "Ascent",
        "Ascent",
        "Ascent",
    ]
    assert len(reports) == 1
    assert reports[0].rejected_reason is None
    assert reports[0].inflection_frames == [2]
    assert reports[0].phase_assignments == {
        "Ascent": (2, 4),
        "Descent": (0, 1),
    }


def test_segment_phases_can_use_recording_view_raw_hip_center_y():
    df, reports = segment_phases(
        _raw_phase_df([0.2, 0.5, 0.8, 0.5, 0.2]),
        _phase_definition(
            reference_coordinate_family="recording_view_raw",
            reference_axis="image_y",
            split_logic="local_maximum",
        ),
    )

    assert df["phase"].tolist() == [
        "Descent",
        "Descent",
        "Ascent",
        "Ascent",
        "Ascent",
    ]
    assert reports[0].rejected_reason is None
    assert reports[0].inflection_frames == [2]


def test_segment_phases_records_too_short_rep_without_labels():
    df, reports = segment_phases(
        _phase_df([1.0, 0.0, 1.0]),
        _phase_definition(minimum_rep_length_frames=4),
    )

    assert df["phase"].isna().all()
    assert len(reports) == 1
    assert reports[0].rep_id == 1
    assert reports[0].phase_assignments == {}
    assert reports[0].rejected_reason == "rep too short: 3 < 4 frames"


def test_segment_phases_uses_deterministic_global_extremum_policy():
    df, reports = segment_phases(
        _phase_df([1.0, 0.4, 1.0, 0.1, 1.0]),
        _phase_definition(multi_inflection_policy="global_extremum"),
    )

    assert df["phase"].tolist() == [
        "Descent",
        "Descent",
        "Descent",
        "Ascent",
        "Ascent",
    ]
    assert reports[0].inflection_frames == [3]
    assert reports[0].multi_inflection_collapsed is True


def test_segment_phases_preserves_annotation_override():
    manual_phase = ["Manual_A", "Manual_A", "Manual_B", "Manual_B"]

    df, reports = segment_phases(
        _phase_df([1.0, 0.0, 0.5, 1.0], phase_values=manual_phase),
        _phase_definition(),
    )

    assert df["phase"].tolist() == manual_phase
    assert len(reports) == 1
    assert (
        reports[0].rejected_reason
        == "explicit annotation override: phase column already populated"
    )
