import numpy as np
import pandas as pd

from movement.exercise_definition import load_exercise_definition
from movement.pipeline import (
    FarSideStabilizationConfig,
    InterpolationConfig,
    PreprocessingConfig,
    ReliabilityConfig,
    load_pipeline_config,
)
from movement.preprocessing import preprocess_pose_dataframe


DEFINITIONS_DIR = "data/definitions/exercises"


def _side_view_squat_df() -> pd.DataFrame:
    frames = np.arange(6)
    data: dict[str, object] = {
        "frame": frames,
        "timestamp": frames / 30.0,
        "exercise_id": ["squat"] * len(frames),
        "execution_pattern": ["bilateral_symmetric"] * len(frames),
        "camera_zone": ["Z3"] * len(frames),
    }

    base = {
        "left_shoulder": (-0.2, 1.0, -0.20),
        "right_shoulder": (0.2, 1.0, 0.20),
        "left_hip": (-0.2, 0.0, -0.20),
        "right_hip": (0.2, 0.0, 0.20),
        "left_knee": (-0.2, -0.8, -0.20),
        "right_knee": (0.2, -0.8, 0.20),
        "left_ankle": (-0.2, -1.6, -0.20),
        "right_ankle": (0.2, -1.6, 0.20),
    }
    for landmark, (x, y, z) in base.items():
        data[f"{landmark}_x"] = np.full(len(frames), x, dtype=float)
        data[f"{landmark}_y"] = np.full(len(frames), y, dtype=float)
        data[f"{landmark}_z"] = np.full(len(frames), z, dtype=float)
        data[f"{landmark}_visibility"] = np.ones(len(frames), dtype=float)

    # Camera-far right knee has a short, obvious monocular jitter event.
    data["right_knee_x"][3] = 1.6
    data["right_knee_visibility"][3] = 0.2
    return pd.DataFrame(data)


def _stable_visibility_gap_df() -> pd.DataFrame:
    df = _side_view_squat_df()
    df["right_knee_x"] = 0.2
    df["right_knee_visibility"] = 1.0
    df.loc[3, "right_knee_visibility"] = 0.2
    return df


def _setup_frames_before_exercise_df() -> pd.DataFrame:
    df = _side_view_squat_df()
    df.loc[0, "exercise_id"] = None
    df.loc[0, "execution_pattern"] = None
    return df


def test_view_metric_reliability_is_parsed_from_exercise_yaml():
    squat = load_exercise_definition("squat", DEFINITIONS_DIR)

    assert squat.view_metric_reliability["structure"] == "bilateral_symmetric"
    assert squat.view_metric_reliability["zones"]["Z3"]["bilateral_symmetry"] == "low"


def test_pipeline_config_loads_far_side_stabilization_defaults():
    config = load_pipeline_config("configs/pipeline_default.yaml")

    far_side = config.preprocessing.far_side_stabilization
    assert far_side.enabled is False
    assert far_side.camera_side_inference is True
    assert far_side.near_depth_sign == "negative"
    assert far_side.min_depth_offset_torso == 0.05
    assert far_side.jitter_threshold_torso_per_sec is None
    assert far_side.acceleration_threshold_torso_per_sec2 is None
    assert config.preprocessing.interpolation.post_velocity_check is True


def test_short_gap_interpolation_separates_observed_reliability_from_usability():
    df = _stable_visibility_gap_df()
    squat = load_exercise_definition("squat", DEFINITIONS_DIR)
    config = PreprocessingConfig(
        reliability=ReliabilityConfig(visibility_threshold=0.5),
        interpolation=InterpolationConfig(enabled=True, max_gap_frames=1),
    )

    pre_df, report = preprocess_pose_dataframe(
        df,
        landmarks=[
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_ankle",
            "right_ankle",
        ],
        exercise_definition=squat,
        config=config,
    )

    assert pre_df.loc[3, "right_knee_observed_reliable"] == np.False_
    assert pre_df.loc[3, "right_knee_usable"] == np.True_
    assert pre_df.loc[3, "right_knee_preprocessing_source"] == (
        "short_gap_interpolated"
    )
    assert report["reliability_summary"]["num_observed_unreliable_landmark_frames"] >= 1
    assert (
        report["reliability_summary"]["num_unusable_landmark_frames"]
        < report["reliability_summary"]["num_observed_unreliable_landmark_frames"]
    )
    assert report["interpolation_summary"]["num_landmark_frames_recovered"] >= 1
    right_knee_qc = next(
        row
        for row in report["landmark_quality_summary"]
        if row["landmark"] == "right_knee"
    )
    assert right_knee_qc["low_visibility_frames"] == 1
    assert right_knee_qc["observed_unreliable_frames"] >= 1
    assert right_knee_qc["unusable_frames"] == 0
    assert right_knee_qc["recovered_by_interpolation"] >= 1
    assert report["worst_landmarks_by_observed_unreliable"][0]["landmark"] == (
        "right_knee"
    )
    assert report["worst_landmarks_by_unusable"] == []
    assert report["frames_with_many_unusable_landmarks"] == []
    assert report["rule_contribution_summary"][
        "landmark_frames_recovered_by_interpolation"
    ] >= 1


def test_post_interpolation_velocity_check_rejects_implausible_recovered_frame():
    frames = np.arange(5)
    df = pd.DataFrame(
        {
            "frame": frames,
            "timestamp": frames / 30.0,
            "right_knee_x": [0.0, 0.0, 0.0, 100.0, 100.0],
            "right_knee_y": [0.0] * len(frames),
            "right_knee_z": [0.0] * len(frames),
            "right_knee_visibility": [1.0, 1.0, 1.0, 0.2, 1.0],
        }
    )
    squat = load_exercise_definition("squat", DEFINITIONS_DIR)
    config = PreprocessingConfig(
        reliability=ReliabilityConfig(
            visibility_threshold=0.5,
            velocity_threshold_torso_per_sec=5.0,
        ),
        interpolation=InterpolationConfig(
            enabled=True,
            max_gap_frames=1,
            post_velocity_check=True,
        ),
    )

    pre_df, report = preprocess_pose_dataframe(
        df,
        landmarks=["right_knee"],
        exercise_definition=squat,
        config=config,
    )

    assert pre_df.loc[3, "right_knee_observed_reliable"] == np.False_
    assert pre_df.loc[3, "right_knee_usable"] == np.False_
    assert pre_df.loc[3, "right_knee_preprocessing_source"] == (
        "post_interpolation_velocity_failed"
    )
    assert report["interpolation_summary"]["post_velocity_check_enabled"] is True
    assert (
        report["interpolation_summary"][
            "num_post_velocity_rejected_landmark_frames"
        ]
        == 1
    )
    right_knee_qc = next(
        row
        for row in report["landmark_quality_summary"]
        if row["landmark"] == "right_knee"
    )
    assert right_knee_qc["post_interpolation_velocity_failed"] == 1
    assert report["worst_landmarks_by_unusable"][0]["landmark"] == "right_knee"


def test_preprocessing_report_uses_non_null_exercise_representatives():
    df = _setup_frames_before_exercise_df()
    squat = load_exercise_definition("squat", DEFINITIONS_DIR)
    config = PreprocessingConfig(interpolation=InterpolationConfig(enabled=False))

    _, report = preprocess_pose_dataframe(
        df,
        landmarks=[
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_ankle",
            "right_ankle",
        ],
        exercise_definition=squat,
        config=config,
    )

    assert report["exercise_id"] == "squat"
    assert report["movement_template_id"] == "bilateral_lower_body_closed_chain"
    assert report["execution_pattern"] == "bilateral_symmetric"


def test_far_side_jitter_metadata_and_symmetry_availability_gate():
    df = _side_view_squat_df()
    squat = load_exercise_definition("squat", DEFINITIONS_DIR)
    config = PreprocessingConfig(
        interpolation=InterpolationConfig(enabled=False),
        far_side_stabilization=FarSideStabilizationConfig(
            enabled=True,
            max_gap_frames=1,
        ),
    )

    pre_df, report = preprocess_pose_dataframe(
        df,
        landmarks=[
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_ankle",
            "right_ankle",
        ],
        exercise_definition=squat,
        config=config,
    )

    far_summary = report["far_side_stabilization_summary"]
    availability = report["feature_availability_summary"]

    assert far_summary["enabled"] is True
    assert far_summary["camera_side_inference"]["observed_zones"] == ["Z3"]
    assert far_summary["num_far_side_landmark_frames"] > 0
    assert (
        far_summary["num_observed_low_confidence_far_side_landmark_frames"] > 0
    )
    assert far_summary["num_observed_high_jitter_far_side_landmark_frames"] > 0
    assert (
        far_summary[
            "num_post_preprocessing_low_confidence_far_side_landmark_frames"
        ]
        > 0
    )
    assert (
        far_summary[
            "num_post_preprocessing_high_jitter_far_side_landmark_frames"
        ]
        > 0
    )
    assert far_summary["jitter_detection_policy"] == (
        "conservative_motion_spike_with_low_confidence_context"
    )
    assert "right_knee_camera_side" in pre_df.columns
    assert pre_df.loc[3, "right_knee_camera_side"] == "far_side"
    assert pre_df.loc[3, "preprocessing_confidence"] == "low_confidence"
    assert availability["symmetry_gate_ready"] is False
    assert "spatial.symmetry.*" in availability["low_confidence_feature_families"]


def test_far_side_jitter_gate_ignores_small_high_visibility_wobble():
    df = _side_view_squat_df()
    df["right_knee_x"] = 0.2
    df["right_knee_visibility"] = 1.0
    df.loc[3, "right_knee_x"] = 0.25
    squat = load_exercise_definition("squat", DEFINITIONS_DIR)
    config = PreprocessingConfig(
        interpolation=InterpolationConfig(enabled=False),
        far_side_stabilization=FarSideStabilizationConfig(enabled=True),
    )

    pre_df, report = preprocess_pose_dataframe(
        df,
        landmarks=[
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_ankle",
            "right_ankle",
        ],
        exercise_definition=squat,
        config=config,
    )

    far_summary = report["far_side_stabilization_summary"]

    assert far_summary["num_far_side_landmark_frames"] > 0
    assert far_summary["num_observed_high_jitter_far_side_landmark_frames"] == 0
    assert (
        far_summary["num_observed_low_confidence_far_side_landmark_frames"] == 0
    )
    assert (
        far_summary[
            "num_post_preprocessing_high_jitter_far_side_landmark_frames"
        ]
        == 0
    )
    assert (
        far_summary[
            "num_post_preprocessing_low_confidence_far_side_landmark_frames"
        ]
        == 0
    )
    assert pre_df.loc[3, "right_knee_confidence_note"] == ""
