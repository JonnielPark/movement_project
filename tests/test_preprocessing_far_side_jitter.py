import numpy as np
import pandas as pd

from movement.exercise_definition import load_exercise_definition
from movement.pipeline import (
    FarSideStabilizationConfig,
    InterpolationConfig,
    PreprocessingConfig,
    load_pipeline_config,
)
from movement.preprocessing import preprocess_pose_dataframe


DEFINITIONS_DIR = "data/definitions/exercises"


def _side_view_squat_df() -> pd.DataFrame:
    frames = np.arange(6)
    data: dict[str, object] = {
        "frame": frames,
        "timestamp": frames / 30.0,
        "exercise_type": ["squat"] * len(frames),
        "pattern": ["bilateral_symmetric"] * len(frames),
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


def test_far_side_jitter_metadata_and_symmetry_availability_gate():
    df = _side_view_squat_df()
    squat = load_exercise_definition("squat", DEFINITIONS_DIR)
    config = PreprocessingConfig(
        interpolation=InterpolationConfig(enabled=False),
        far_side_stabilization=FarSideStabilizationConfig(
            enabled=True,
            jitter_threshold_torso_per_sec=1.0,
            acceleration_threshold_torso_per_sec2=30.0,
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
    assert far_summary["num_high_jitter_far_side_landmark_frames"] > 0
    assert "right_knee_camera_side" in pre_df.columns
    assert pre_df.loc[3, "right_knee_camera_side"] == "far_side"
    assert pre_df.loc[3, "preprocessing_confidence"] == "low_confidence"
    assert availability["symmetry_gate_ready"] is False
    assert "spatial.symmetry.*" in availability["low_confidence_feature_families"]
