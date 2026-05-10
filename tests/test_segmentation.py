from types import SimpleNamespace

import numpy as np
import pandas as pd

from movement.exercise_definition import RepSegmentationSpec, SmoothingSpec
from movement.pipeline import PipelineConfig, run_pipeline
from movement.segmentation import segment_reps


def _rep_definition(**overrides):
    params = {
        "reference_landmark": "hip_center",
        "reference_axis": "vertical",
        "boundary_logic": "local_maximum",
        "smoothing": SmoothingSpec(
            method="savitzky_golay", window_frames=3, polyorder=1
        ),
        "minimum_rep_length_frames": 3,
        "minimum_boundary_distance_frames": 3,
        "minimum_reps": 1,
        "include_endpoints": True,
    }
    params.update(overrides)
    spec = RepSegmentationSpec(**params)
    return SimpleNamespace(rep_segmentation=spec)


def _pose_df(trace):
    return pd.DataFrame(
        {
            "frame": list(range(len(trace))),
            "timestamp": np.arange(len(trace)) / 30.0,
            "hip_center_norm_z": trace,
            "use_for_analysis": True,
            "segment_type": "full_sequence",
            "rep_id": pd.array([pd.NA] * len(trace), dtype="Int64"),
        }
    )


def test_segment_reps_assigns_rep_ids_from_boundary_peaks():
    trace = np.array([1.0, 0.75, 0.0, 0.75, 1.0, 0.75, 0.0, 0.75, 1.0])
    df, report = segment_reps(_pose_df(trace), _rep_definition())

    assert report.status == "success"
    assert report.boundary_frames == [0, 4, 8]
    assert report.rep_assignments == {1: (0, 3), 2: (4, 8)}
    assert df["rep_id"].tolist() == [1, 1, 1, 1, 2, 2, 2, 2, 2]
    assert set(df["rep_segmentation_source"]) == {"semi_auto"}


def test_segment_reps_preserves_existing_manual_rep_labels():
    df = _pose_df(np.ones(6))
    df["segment_type"] = "rep"
    df["rep_id"] = pd.array([1, 1, 1, 2, 2, 2], dtype="Int64")

    out, report = segment_reps(df, _rep_definition())

    assert out["rep_id"].tolist() == [1, 1, 1, 2, 2, 2]
    assert report.status == "manual_override"
    assert report.source == "annotation"
    assert report.rep_assignments == {1: (0, 2), 2: (3, 5)}


def test_segment_reps_records_failure_when_required_rep_count_not_met():
    df, report = segment_reps(_pose_df(np.ones(9)), _rep_definition(minimum_reps=2))

    assert report.status == "failed"
    assert report.failure_points[0]["failure_level"] == "rep_boundary"
    assert report.failure_points[0]["reason"] == "insufficient_reps"
    assert df["rep_id"].isna().all()
    assert set(df["rep_segmentation_status"]) == {"failed"}


def test_pipeline_reports_skipped_rep_segmentation_when_definition_has_no_block():
    config = PipelineConfig()
    config.validation.enabled = False
    config.annotation.enabled = False
    config.exercise_definition.enabled = True
    config.exercise_definition.exercise_id = "generic"
    config.preprocessing.enabled = False
    config.normalization.enabled = False
    config.rep_segmentation.enabled = True
    config.phase_segmentation.enabled = False

    _, report = run_pipeline(_pose_df(np.ones(5)), config)

    assert report["rep_segmentation"]["status"] == "skipped"
    assert report["rep_segmentation"]["source"] == "fallback"
    assert (
        report["rep_segmentation"]["rejected_reason"]
        == "exercise definition has no rep_segmentation block"
    )
