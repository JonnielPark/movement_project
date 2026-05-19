import pandas as pd
import pytest

from movement.stages.recording_phase_split import (
    DEFAULT_RECORDING_PHASE_ORDER,
    generate_recording_plane_phase_split,
    promote_phase_split_to_annotation,
    validate_phase_split_for_promotion,
)


def _pose_df() -> pd.DataFrame:
    hip_y = [0.10, 0.20, 0.50, 0.90, 0.60, 0.20, 0.10, 0.30, 0.70, 1.00, 0.65, 0.20]
    return pd.DataFrame(
        {
            "frame": list(range(len(hip_y))),
            "left_hip_y": hip_y,
            "right_hip_y": hip_y,
        }
    )


def _annotation_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "recording_id": ["p01_squat_set1", "p01_squat_set1"],
            "set_id": [1, 1],
            "rep_id": [1, 2],
            "segment_type": ["rep", "rep"],
            "start_frame": [0, 6],
            "end_frame": [5, 11],
            "camera_zone": ["Z8", "Z8"],
        }
    )


def test_generate_recording_plane_phase_split_from_rep_annotation():
    phase_df, qc_df = generate_recording_plane_phase_split(
        _pose_df(),
        _annotation_df(),
        recording_id="p01_squat_set1",
        camera_zone="Z8",
        smooth_window_frames=1,
        hold_half_window_frames=0,
    )

    assert qc_df["bottom_frame_estimate"].tolist() == [3, 9]
    assert phase_df.groupby("rep_id")["phase"].apply(list).to_dict() == {
        1: DEFAULT_RECORDING_PHASE_ORDER,
        2: DEFAULT_RECORDING_PHASE_ORDER,
    }
    assert phase_df.loc[
        phase_df["rep_id"].eq(1), ["start_frame", "end_frame"]
    ].values.tolist() == [
        [0, 2],
        [3, 3],
        [4, 5],
    ]
    assert set(phase_df["camera_zone"]) == {"Z8"}
    assert set(phase_df["reference_signal"]) == {"hip_center_y_raw_image_space"}


def test_manual_bottom_override_is_preserved():
    phase_df, qc_df = generate_recording_plane_phase_split(
        _pose_df(),
        _annotation_df(),
        recording_id="p01_squat_set1",
        camera_zone="Z8",
        smooth_window_frames=1,
        hold_half_window_frames=1,
        manual_bottom_frame_overrides={1: 2},
    )

    rep1 = phase_df[phase_df["rep_id"].eq(1)]
    assert qc_df.loc[qc_df["rep_id"].eq(1), "bottom_frame_estimate"].item() == 2
    assert set(rep1["phase_source"]) == {"manual_bottom_override"}
    hold = rep1[rep1["phase"].eq("Turnaround_Hold")].iloc[0]
    assert int(hold["start_frame"]) <= 2 <= int(hold["end_frame"])


def test_validate_phase_split_for_promotion_requires_exact_rep_coverage():
    phase_df, _ = generate_recording_plane_phase_split(
        _pose_df(),
        _annotation_df(),
        recording_id="p01_squat_set1",
        camera_zone="Z8",
        smooth_window_frames=1,
        hold_half_window_frames=0,
    )
    broken = phase_df.copy()
    broken.loc[broken["phase"].eq("Ascent") & broken["rep_id"].eq(1), "start_frame"] = 5

    report, detail_df = validate_phase_split_for_promotion(
        broken,
        _annotation_df(),
        expected_camera_zone="Z8",
    )

    assert report["passed"] is False
    assert any("gap/overlap" in error for error in report["errors"])
    assert detail_df["rep_id"].tolist() == [1, 2]


def test_validate_phase_split_for_promotion_reports_missing_required_columns():
    report, detail_df = validate_phase_split_for_promotion(
        pd.DataFrame({"rep_id": [1], "phase": ["Descent"]}),
        _annotation_df(),
        expected_camera_zone="Z8",
    )

    assert report["passed"] is False
    assert "missing required columns" in report["errors"][0]
    assert detail_df.empty


def test_promote_phase_split_requires_visual_qc_confirmation():
    phase_df, _ = generate_recording_plane_phase_split(
        _pose_df(),
        _annotation_df(),
        recording_id="p01_squat_set1",
        camera_zone="Z8",
        smooth_window_frames=1,
        hold_half_window_frames=0,
    )

    with pytest.raises(ValueError, match="visual_qc_confirmed"):
        promote_phase_split_to_annotation(
            phase_df,
            _annotation_df(),
            visual_qc_confirmed=False,
            expected_camera_zone="Z8",
        )


def test_promote_phase_split_marks_confirmed_annotation():
    phase_df, _ = generate_recording_plane_phase_split(
        _pose_df(),
        _annotation_df(),
        recording_id="p01_squat_set1",
        camera_zone="Z8",
        smooth_window_frames=1,
        hold_half_window_frames=0,
    )

    promoted_df, report, detail_df = promote_phase_split_to_annotation(
        phase_df,
        _annotation_df(),
        visual_qc_confirmed=True,
        expected_camera_zone="Z8",
        source_phase_split_file="p01_squat_set1_phase_split.csv",
    )

    assert report["passed"] is True
    assert detail_df["bottom_in_hold"].all()
    assert set(promoted_df["split_status"]) == {"ok"}
    assert set(promoted_df["status"]) == {"visually_confirmed"}
    assert set(promoted_df["confirmation_source"]) == {"researcher_visual_qc"}
    assert set(promoted_df["source_phase_split_file"]) == {
        "p01_squat_set1_phase_split.csv"
    }
