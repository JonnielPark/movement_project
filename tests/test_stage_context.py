import pandas as pd

from movement.pipeline import NormalizationConfig, PreprocessingConfig
from movement.stage_context import (
    prepare_previous_stage_inputs,
    resolve_target_definitions_dir,
)


LANDMARKS = ["left_hip", "right_hip", "left_shoulder", "right_shoulder"]


def _minimal_pose_df() -> pd.DataFrame:
    frames = [0, 1, 2, 3]
    data: dict[str, object] = {
        "frame": frames,
        "timestamp": [frame / 30.0 for frame in frames],
    }
    coords = {
        "left_hip": (0.0, 0.0, 0.0),
        "right_hip": (2.0, 0.0, 0.0),
        "left_shoulder": (0.0, 1.0, 0.0),
        "right_shoulder": (2.0, 1.0, 0.0),
    }
    for landmark, (x, y, z) in coords.items():
        data[f"{landmark}_x"] = [x] * len(frames)
        data[f"{landmark}_y"] = [y] * len(frames)
        data[f"{landmark}_z"] = [z] * len(frames)
        data[f"{landmark}_visibility"] = [1.0] * len(frames)
    return pd.DataFrame(data)


def test_prepare_previous_stage_inputs_stops_at_requested_stage():
    context = prepare_previous_stage_inputs(
        prepare_until="exercise_definition",
        pose_df=_minimal_pose_df(),
        exercise_id="squat",
        landmarks=LANDMARKS,
    )

    assert context.validation_report["passed"] is True
    assert context.annotation_report["annotation_provided"] is False
    assert context.annotated_df["segment_type"].eq("full_sequence").all()
    assert context.exercise_definition.exercise_id == "squat"
    assert context.preprocessed_df is None
    assert context.normalized_df is None


def test_prepare_previous_stage_inputs_preserves_preprocessing_for_normalization():
    context = prepare_previous_stage_inputs(
        prepare_until="normalization",
        pose_df=_minimal_pose_df(),
        exercise_id="squat",
        landmarks=LANDMARKS,
        preprocessing_config=PreprocessingConfig(enabled=True),
        normalization_config=NormalizationConfig(
            enabled=True,
            keep_reference_columns=True,
            model_depth_scale=0.5,
        ),
    )

    assert context.preprocessing_report["exercise_id"] == "squat"
    assert "preprocessing_valid" in context.preprocessed_df.columns
    assert "preprocessing_valid" in context.normalized_df.columns
    assert "left_hip_norm_x" in context.normalized_df.columns
    assert context.normalization_report["model_depth_scale"] == 0.5


def test_resolve_target_definitions_dir_falls_back_to_runtime_definitions():
    definitions_dir = resolve_target_definitions_dir("squat")

    assert (definitions_dir / "squat.yaml").exists()
