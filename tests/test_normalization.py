import pandas as pd

from movement.stages.normalization import normalize_pose_by_hip_torso


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
    assert out.loc[0, "left_knee_norm_x"] == 0.0
    assert out.loc[0, "left_knee_norm_y"] == 0.25
    assert out.loc[0, "left_knee_norm_z"] == 1.0


def test_corrected_3d_hypothesis_policy_defaults_to_candidate_evidence_only():
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
        corrected_3d_hypothesis={
            "enabled": True,
            "output_family": "rv_skeleton_fit_bounded_xy_endpoint_blend_support_memory",
        },
    )

    policy = report["corrected_3d_hypothesis"]
    assert policy["enabled"] is True
    assert policy["output_family"] == (
        "rv_skeleton_fit_bounded_xy_endpoint_blend_support_memory"
    )
    assert policy["used_for_features_or_scores"] is False
    assert policy["depth_evidence_policy"] == "candidate_evidence_only"
    assert "feature_depth_gravity" not in policy
    assert "score_gravity" not in policy
    assert "score_contribution_enabled" not in policy
