import pandas as pd

from movement.annotation import apply_annotation, load_annotation_csv


def test_apply_annotation_preserves_filming_and_performance_metadata():
    pose_df = pd.DataFrame({"frame": range(5)})
    ann_df = pd.DataFrame(
        {
            "segment_type": ["rep"],
            "set_id": [1],
            "rep_id": [1],
            "start_frame": [1],
            "end_frame": [3],
            "use_for_analysis": [True],
            "exercise_type": ["pike_pushup"],
            "pattern": ["bilateral"],
            "session_id": ["session_001"],
            "recording_id": ["recording_001"],
            "set_index": [2],
            "camera_zone": ["Z3"],
            "camera_height_level": ["H1"],
            "reference_mat_used": [True],
            "filming_protocol_status": ["recommended"],
            "performance_protocol_status": ["partial"],
            "actual_rep_count": [7],
            "failure_point_frame": [3],
            "failure_rep_id": [1],
            "failure_reason": ["posture_breakdown"],
            "performance_note": ["hip dropped before target count"],
        }
    )

    annotated, report = apply_annotation(pose_df, ann_df)

    assert report["num_analysis_frames"] == 3
    assert annotated.loc[1, "session_id"] == "session_001"
    assert annotated.loc[1, "recording_id"] == "recording_001"
    assert annotated.loc[1, "set_index"] == 2
    assert annotated.loc[1, "camera_zone"] == "Z3"
    assert annotated.loc[1, "camera_height_level"] == "H1"
    assert bool(annotated.loc[1, "reference_mat_used"]) is True
    assert annotated.loc[1, "filming_protocol_status"] == "recommended"
    assert annotated.loc[1, "performance_protocol_status"] == "partial"
    assert annotated.loc[1, "actual_rep_count"] == 7
    assert annotated.loc[1, "failure_point_frame"] == 3
    assert annotated.loc[1, "failure_rep_id"] == 1
    assert annotated.loc[1, "failure_reason"] == "posture_breakdown"
    assert annotated.loc[1, "performance_note"] == "hip dropped before target count"

    assert pd.isna(annotated.loc[0, "actual_rep_count"])
    assert pd.isna(annotated.loc[0, "reference_mat_used"])


def test_load_annotation_csv_normalizes_optional_metadata(tmp_path):
    ann_path = tmp_path / "annotation.csv"
    ann_path.write_text(
        "\n".join(
            [
                "segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,"
                "reference_mat_used,actual_rep_count,failure_point_frame,failure_rep_id",
                "rep,1,1,0,2,true,yes,7,2,1",
            ]
        ),
        encoding="utf-8",
    )

    ann_df = load_annotation_csv(ann_path)

    assert str(ann_df["actual_rep_count"].dtype) == "Int64"
    assert str(ann_df["failure_point_frame"].dtype) == "Int64"
    assert str(ann_df["failure_rep_id"].dtype) == "Int64"
    assert str(ann_df["reference_mat_used"].dtype) == "boolean"
    assert bool(ann_df.loc[0, "reference_mat_used"]) is True
