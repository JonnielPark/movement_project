import pandas as pd

from movement.pose_data_state import NORMALIZED_POSE_DATA
from movement.stages.normalization import (
    check_normalization_result,
    normalize_pose_by_hip_torso,
)


def test_model_depth_scale_attenuates_norm_z_only():
    df = pd.DataFrame(
        {
            "frame": [0],
            "timestamp": [0.0],
            "left_hip_x": [0.0],
            "left_hip_y": [0.0],
            "left_hip_z": [0.0],
            "right_hip_x": [2.0],
            "right_hip_y": [0.0],
            "right_hip_z": [0.0],
            "left_shoulder_x": [0.0],
            "left_shoulder_y": [1.0],
            "left_shoulder_z": [0.0],
            "right_shoulder_x": [2.0],
            "right_shoulder_y": [1.0],
            "right_shoulder_z": [0.0],
            "left_knee_x": [1.0],
            "left_knee_y": [0.25],
            "left_knee_z": [2.0],
        }
    )

    out, report = normalize_pose_by_hip_torso(
        df,
        landmarks=[
            "left_hip",
            "right_hip",
            "left_shoulder",
            "right_shoulder",
            "left_knee",
        ],
        model_depth_scale=0.5,
    )

    assert report["model_depth_scale"] == 0.5
    assert report["output_pose_data_state"] == NORMALIZED_POSE_DATA
    assert out.attrs["pose_data_state"] == NORMALIZED_POSE_DATA
    assert out.attrs["coordinate_families"] == ["raw", "norm"]
    assert out.loc[0, "left_knee_norm_x"] == 0.0
    assert out.loc[0, "left_knee_norm_y"] == 0.25
    assert out.loc[0, "left_knee_norm_z"] == 1.0


def test_normalization_report_does_not_define_corrected_3d_policy():
    df = pd.DataFrame(
        {
            "left_hip_x": [0.0],
            "left_hip_y": [0.0],
            "left_hip_z": [0.0],
            "right_hip_x": [2.0],
            "right_hip_y": [0.0],
            "right_hip_z": [0.0],
            "left_shoulder_x": [0.0],
            "left_shoulder_y": [1.0],
            "left_shoulder_z": [0.0],
            "right_shoulder_x": [2.0],
            "right_shoulder_y": [1.0],
            "right_shoulder_z": [0.0],
        }
    )

    _, report = normalize_pose_by_hip_torso(
        df,
        landmarks=["left_hip", "right_hip", "left_shoulder", "right_shoulder"],
    )

    assert "corrected_3d_hypothesis" not in report
    assert "canonicalization_report" not in report
    assert "score_gravity" not in report


def test_xy_only_normalization_emits_recording_plane_norm_with_nan_z_placeholder():
    df = pd.DataFrame(
        {
            "frame": [0],
            "timestamp": [0.0],
            "left_hip_x": [0.0],
            "left_hip_y": [0.0],
            "right_hip_x": [2.0],
            "right_hip_y": [0.0],
            "left_shoulder_x": [0.0],
            "left_shoulder_y": [1.0],
            "right_shoulder_x": [2.0],
            "right_shoulder_y": [1.0],
            "left_knee_x": [0.4],
            "left_knee_y": [0.3],
        }
    )

    out, report = normalize_pose_by_hip_torso(
        df,
        landmarks=[
            "left_hip",
            "right_hip",
            "left_shoulder",
            "right_shoulder",
            "left_knee",
        ],
        coordinate_axes="auto",
    )
    check = check_normalization_result(out)

    assert check["passed"] is True
    assert check["normalized_axes"] == ["x", "y", "z"]
    assert check["normalized_evidence_axes"] == ["x", "y"]
    assert report["normalized_axes"] == ["x", "y", "z"]
    assert report["normalized_evidence_axes"] == ["x", "y"]
    assert report["z_axis_policy"] == "nan_placeholder"
    assert report["z_source"] == "absent"
    assert report["z_evaluable"] is False
    assert report["output_coordinate_axes"]["raw"] == ["x", "y", "z"]
    assert report["output_coordinate_axes"]["norm"] == ["x", "y", "z"]
    assert out.attrs["coordinate_axes"]["raw"] == ["x", "y", "z"]
    assert out.attrs["coordinate_axes"]["norm"] == ["x", "y", "z"]
    assert "left_knee_norm_x" in out.columns
    assert "left_knee_norm_y" in out.columns
    assert out["left_knee_norm_z"].isna().all()
