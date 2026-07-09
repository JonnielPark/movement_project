import pandas as pd

from movement.pose_data_state import (
    NORMALIZED_POSE_DATA,
    PREPROCESSED_POSE_DATA,
    RAW_POSE_DATA,
)
from movement.pipeline import NormalizationConfig, PreprocessingConfig
from movement.stage_context import (
    DEFAULT_STAGE_CHECK_EXERCISE_ID,
    build_stage_check_pipeline_config,
    prepare_previous_stage_inputs,
    recording_id_from_pose_csv,
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
        data[f"{landmark}_confidence"] = [1.0] * len(frames)
    return pd.DataFrame(data)


def _minimal_xy_pose_df() -> pd.DataFrame:
    return _minimal_pose_df().drop(
        columns=[
            "left_hip_z",
            "right_hip_z",
            "left_shoulder_z",
            "right_shoulder_z",
        ]
    )


def test_prepare_previous_stage_inputs_stops_at_requested_stage():
    context = prepare_previous_stage_inputs(
        prepare_until="exercise_definition",
        pose_df=_minimal_pose_df(),
        exercise_id="squat",
        landmarks=LANDMARKS,
    )

    assert context.validation_report["passed"] is True
    assert context.raw_df.attrs["pose_data_state"] == RAW_POSE_DATA
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
    assert context.preprocessing_report["output_pose_data_state"] == (
        PREPROCESSED_POSE_DATA
    )
    assert context.preprocessed_df.attrs["pose_data_state"] == PREPROCESSED_POSE_DATA
    assert "preprocessing_valid" in context.preprocessed_df.columns
    assert "preprocessing_valid" in context.normalized_df.columns
    assert "left_hip_norm_x" in context.normalized_df.columns
    assert context.normalized_df.attrs["pose_data_state"] == NORMALIZED_POSE_DATA
    assert context.normalization_report["model_depth_scale"] == 0.5
    assert context.normalization_report["output_pose_data_state"] == (
        NORMALIZED_POSE_DATA
    )


def test_prepare_previous_stage_inputs_accepts_xy_only_for_normalization():
    context = prepare_previous_stage_inputs(
        prepare_until="normalization",
        pose_df=_minimal_xy_pose_df(),
        exercise_id="squat",
        landmarks=LANDMARKS,
        normalization_config=NormalizationConfig(
            enabled=True,
            keep_reference_columns=True,
            coordinate_axes="xy",
        ),
    )

    assert context.validation_report["passed"] is True
    assert context.validation_report["coordinate_axes"]["raw"] == ["x", "y", "z"]
    assert context.validation_report["schema_harmonization"]["validation_axes"] == [
        "x",
        "y",
    ]
    assert context.validation_report["schema_harmonization"]["z_evaluable"] is False
    assert context.normalization_report["normalized_axes"] == ["x", "y", "z"]
    assert context.normalization_report["normalized_evidence_axes"] == ["x", "y"]
    assert context.normalized_df.attrs["coordinate_axes"]["norm"] == ["x", "y", "z"]
    assert "left_hip_norm_x" in context.normalized_df.columns
    assert context.normalized_df["left_hip_norm_z"].isna().all()


def test_resolve_target_definitions_dir_falls_back_to_runtime_definitions():
    definitions_dir = resolve_target_definitions_dir("squat")

    assert (definitions_dir / "squat.yaml").exists()


def test_default_stage_check_exercise_id_uses_promoted_squat():
    assert DEFAULT_STAGE_CHECK_EXERCISE_ID == "squat"


def test_recording_id_from_pose_csv_uses_pose_filename_convention():
    recording_id = recording_id_from_pose_csv(
        "data/pose/example/p01_squat_set1_output_pose.csv"
    )

    assert recording_id == "p01_squat_set1"


def test_build_stage_check_pipeline_config_copies_stage_configs():
    norm_config = NormalizationConfig(
        enabled=True,
        keep_reference_columns=True,
        model_depth_scale=0.5,
    )

    cfg = build_stage_check_pipeline_config(
        exercise_id="draft_squat",
        definitions_dir="data/definitions/exercises",
        annotation_csv="annotation.csv",
        normalization_config=norm_config,
        enable_rep_segmentation=True,
        enable_phase_segmentation=True,
        enable_features=True,
        enable_role_context=True,
        enable_biomech=True,
        enable_biomarker=True,
    )

    assert cfg.annotation.enabled is True
    assert cfg.annotation.path == "annotation.csv"
    assert cfg.exercise_definition.exercise_id == "draft_squat"
    assert cfg.rep_segmentation.enabled is True
    assert cfg.phase_segmentation.enabled is True
    assert cfg.features.enabled is True
    assert cfg.features.role_context.enabled is True
    assert cfg.biomech.enabled is True
    assert cfg.biomarker.enabled is True
    assert cfg.normalization.model_depth_scale == 0.5
    assert cfg.normalization is not norm_config
