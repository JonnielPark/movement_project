import pandas as pd

from movement.annotation import apply_annotation, load_annotation_csv
from movement.pipeline import PipelineConfig, run_pipeline


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
            "exercise_id": ["pike_pushup"],
            "execution_pattern": ["bilateral"],
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
            "rep_side_sequence": ["left,right,left"],
            "side_block_size": [pd.NA],
            "rep_unit": ["tap"],
            "protocol_cycle_id": [1],
        }
    )

    annotated, report = apply_annotation(pose_df, ann_df)

    assert report["num_analysis_frames"] == 3
    performance = report["performance_provenance"]
    assert performance["available"] is True
    assert performance["policy"] == "warning_provenance_only"
    assert performance["forced_exclusion"] is False
    assert performance["score_penalty_applied"] is False
    assert performance["summary"] == {
        "num_records": 1,
        "statuses": ["partial"],
        "actual_rep_counts": [7],
        "failure_reasons": ["posture_breakdown"],
        "has_partial_completion": True,
        "has_failure_point": True,
    }
    assert performance["records"][0]["source_fields"] == [
        "annotation.performance_protocol_status",
        "annotation.actual_rep_count",
        "annotation.failure_point_frame",
        "annotation.failure_rep_id",
        "annotation.failure_reason",
        "annotation.performance_note",
    ]
    assert "actual_rep_count=7" in performance["interpretation_confidence_notes"][0]
    assert "failure_reason=posture_breakdown" in (
        performance["interpretation_confidence_notes"][0]
    )
    assert annotated.loc[1, "session_id"] == "session_001"
    assert annotated.loc[1, "exercise_id"] == "pike_pushup"
    assert annotated.loc[1, "execution_pattern"] == "bilateral"
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
    assert annotated.loc[1, "rep_side_sequence"] == "left,right,left"
    assert pd.isna(annotated.loc[1, "side_block_size"])
    assert annotated.loc[1, "rep_unit"] == "tap"
    assert annotated.loc[1, "protocol_cycle_id"] == 1

    assert pd.isna(annotated.loc[0, "actual_rep_count"])
    assert pd.isna(annotated.loc[0, "reference_mat_used"])
    assert pd.isna(annotated.loc[0, "protocol_cycle_id"])


def test_apply_annotation_no_annotation_reports_no_performance_provenance():
    pose_df = pd.DataFrame({"frame": range(3)})

    _, report = apply_annotation(pose_df, None)

    performance = report["performance_provenance"]
    assert performance["available"] is False
    assert performance["forced_exclusion"] is False
    assert performance["score_penalty_applied"] is False
    assert performance["summary"]["num_records"] == 0


def test_apply_annotation_preserves_exercise_id_and_execution_pattern():
    pose_df = pd.DataFrame({"frame": range(4)})
    ann_df = pd.DataFrame(
        {
            "segment_type": ["rep"],
            "set_id": [1],
            "rep_id": [1],
            "start_frame": [1],
            "end_frame": [2],
            "use_for_analysis": [True],
            "exercise_id": ["draft_squat"],
            "execution_pattern": ["bilateral_symmetric"],
        }
    )

    annotated, _ = apply_annotation(pose_df, ann_df)

    assert annotated.loc[1, "exercise_id"] == "draft_squat"
    assert annotated.loc[1, "execution_pattern"] == "bilateral_symmetric"
    assert "exercise_type" not in annotated.columns
    assert "annotation_pattern" not in annotated.columns
    assert "pattern" not in annotated.columns


def test_pipeline_annotation_report_consumes_performance_provenance():
    pose_df = pd.DataFrame({"frame": range(5)})
    ann_df = pd.DataFrame(
        {
            "segment_type": ["rep"],
            "set_id": [1],
            "rep_id": [1],
            "start_frame": [1],
            "end_frame": [3],
            "use_for_analysis": [True],
            "performance_protocol_status": ["stopped_at_failure_point"],
            "actual_rep_count": [6],
            "failure_point_frame": [3],
            "failure_reason": ["participant_stop"],
        }
    )
    config = PipelineConfig()
    config.validation.enabled = False
    config.annotation.enabled = True
    config.exercise_definition.enabled = False
    config.preprocessing.enabled = False
    config.normalization.enabled = False
    config.rep_segmentation.enabled = False
    config.phase_segmentation.enabled = False
    config.motion_attribution.enabled = False
    config.features.enabled = False
    config.biomech.enabled = False
    config.biomarker.enabled = False

    _, report = run_pipeline(pose_df, config, ann_df=ann_df)

    performance = report["annotation"]["performance_provenance"]
    assert performance["available"] is True
    assert performance["summary"]["actual_rep_counts"] == [6]
    assert performance["summary"]["failure_reasons"] == ["participant_stop"]
    assert performance["score_penalty_applied"] is False


def test_pipeline_exercise_definition_uses_exercise_id():
    pose_df = pd.DataFrame({"frame": range(4)})
    ann_df = pd.DataFrame(
        {
            "segment_type": ["rep"],
            "set_id": [1],
            "rep_id": [1],
            "start_frame": [1],
            "end_frame": [2],
            "use_for_analysis": [True],
            "exercise_id": ["squat"],
            "execution_pattern": ["bilateral"],
        }
    )
    config = PipelineConfig()
    config.validation.enabled = False
    config.annotation.enabled = True
    config.exercise_definition.enabled = True
    config.exercise_definition.exercise_id = None
    config.preprocessing.enabled = False
    config.normalization.enabled = False
    config.rep_segmentation.enabled = False
    config.phase_segmentation.enabled = False
    config.motion_attribution.enabled = False
    config.features.enabled = False
    config.biomech.enabled = False
    config.biomarker.enabled = False

    _, report = run_pipeline(pose_df, config, ann_df=ann_df)

    exercise_report = report["exercise_definition"]
    assert exercise_report["exercise_id"] == "squat"
    assert (
        exercise_report["movement_template_id"] == "bilateral_lower_body_closed_chain"
    )


def test_load_annotation_csv_normalizes_optional_metadata(tmp_path):
    ann_path = tmp_path / "annotation.csv"
    ann_path.write_text(
        "\n".join(
            [
                "segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,"
                "reference_mat_used,actual_rep_count,failure_point_frame,failure_rep_id,"
                "side_block_size,protocol_cycle_id",
                "rep,1,1,0,2,true,yes,7,2,1,5,3",
            ]
        ),
        encoding="utf-8",
    )

    ann_df = load_annotation_csv(ann_path)

    assert str(ann_df["actual_rep_count"].dtype) == "Int64"
    assert str(ann_df["failure_point_frame"].dtype) == "Int64"
    assert str(ann_df["failure_rep_id"].dtype) == "Int64"
    assert str(ann_df["side_block_size"].dtype) == "Int64"
    assert str(ann_df["protocol_cycle_id"].dtype) == "Int64"
    assert str(ann_df["reference_mat_used"].dtype) == "boolean"
    assert bool(ann_df.loc[0, "reference_mat_used"]) is True
