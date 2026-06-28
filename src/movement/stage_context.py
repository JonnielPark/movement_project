"""Helpers for preparing previous-stage inputs in stage-check notebooks.

The helpers in this module do not implement new movement logic. They call the
documented pipeline-stage functions so notebooks can stay focused on the stage
being inspected.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from movement.core.config import (
    LANDMARKS,
    make_coordinate_columns,
    make_required_columns,
    make_visibility_columns,
)
from movement.core.io import load_pose_csv
from movement.definitions.exercise_definition import load_exercise_definition
from movement.pipeline import (
    AnnotationConfig,
    BiomechConfig,
    ExerciseDefinitionConfig,
    FeaturesConfig,
    NormalizationConfig,
    PhaseSegmentationConfig,
    PipelineConfig,
    PreprocessingConfig,
    RepSegmentationConfig,
    RoleContextConfig,
    ValidationConfig,
)
from movement.stages.annotation import apply_annotation, load_annotation_csv
from movement.stages.canonicalization import CanonicalizationConfig
from movement.stages.normalization import normalize_pose_by_hip_torso
from movement.stages.preprocessing import preprocess_pose_dataframe
from movement.stages.validation import run_basic_validation

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_STAGE_CHECK_POSE_CSV = Path(
    "data/pose/mediapipe/no_consent/20260517/p01_squat_set1_output_pose.csv"
)
DEFAULT_STAGE_CHECK_ANNOTATION_CSV = Path(
    "data/pose/mediapipe/no_consent/20260517/p01_squat_set1_annotation.csv"
)
DEFAULT_STAGE_CHECK_EXERCISE_ID = "draft_squat"

_STAGE_ORDER: dict[str, int] = {
    "validation": 1,
    "annotation": 2,
    "exercise_definition": 3,
    "preprocessing": 4,
    "normalization": 5,
}

_STAGE_ALIASES: dict[str, str] = {
    "01": "validation",
    "1": "validation",
    "02": "annotation",
    "2": "annotation",
    "03": "exercise_definition",
    "3": "exercise_definition",
    "definition": "exercise_definition",
    "exercise": "exercise_definition",
    "04": "preprocessing",
    "4": "preprocessing",
    "05": "normalization",
    "5": "normalization",
}


@dataclass
class PreviousStageInputs:
    """Prepared stage data used by follow-along notebooks."""

    project_root: Path
    prepare_until: str
    pose_csv: Path | None
    annotation_csv: Path | None
    exercise_id: str | None
    definitions_dir: Path | None
    raw_df: pd.DataFrame
    validation_report: dict[str, Any] | None = None
    annotation_df: pd.DataFrame | None = None
    annotated_df: pd.DataFrame | None = None
    annotation_report: dict[str, Any] | None = None
    exercise_definition: Any | None = None
    preprocessed_df: pd.DataFrame | None = None
    preprocessing_report: dict[str, Any] | None = None
    normalized_df: pd.DataFrame | None = None
    normalization_report: dict[str, Any] | None = None


def _resolve_path(path: str | Path | None, project_root: Path) -> Path | None:
    if path is None:
        return None
    resolved = Path(path)
    return resolved if resolved.is_absolute() else project_root / resolved


def find_project_root(start: str | Path | None = None) -> Path:
    """Find the repository root that contains pyproject.toml."""

    root = Path(start).resolve() if start is not None else Path.cwd().resolve()
    while not (root / "pyproject.toml").exists():
        if root.parent == root:
            raise RuntimeError("Could not find project root containing pyproject.toml")
        root = root.parent
    return root


def recording_id_from_pose_csv(pose_csv: str | Path) -> str:
    """Return the conventional recording id from a pose CSV path."""

    return Path(pose_csv).stem.removesuffix("_output_pose")


def _normalize_stage_name(stage: str) -> str:
    key = str(stage).strip().lower()
    key = _STAGE_ALIASES.get(key, key)
    if key not in _STAGE_ORDER:
        valid = ", ".join(_STAGE_ORDER)
        raise ValueError(f"Unknown prepare_until={stage!r}. Expected one of: {valid}.")
    return key


def _first_non_null_string(df: pd.DataFrame, column: str) -> str | None:
    if column not in df.columns:
        return None
    values = [str(value) for value in df[column].dropna().unique().tolist()]
    return next((value for value in values if value.strip()), None)


def candidate_definition_dirs(
    exercise_id: str | None,
    *,
    project_root: str | Path | None = None,
    definitions_dir: str | Path | None = None,
    authoring_draft_root: str | Path | None = None,
    authoring_example_root: str | Path | None = None,
) -> list[Path]:
    """Return definition directories in runtime, local draft, example order."""

    root = _resolve_path(project_root, _PROJECT_ROOT) or _PROJECT_ROOT
    runtime_dir = _resolve_path(definitions_dir, root) or (
        root / "data" / "definitions" / "exercises"
    )
    draft_root = _resolve_path(authoring_draft_root, root) or (
        root / "data" / "processed" / "authoring_drafts"
    )
    example_root = _resolve_path(authoring_example_root, root) or (
        root / "data" / "examples" / "exercise_authoring"
    )

    dirs = [runtime_dir]
    if exercise_id:
        dirs.append(draft_root / exercise_id / "data" / "definitions" / "exercises")
        dirs.append(example_root / exercise_id / "data" / "definitions" / "exercises")
    return dirs


def resolve_target_definitions_dir(
    exercise_id: str | None,
    *,
    project_root: str | Path | None = None,
    definitions_dir: str | Path | None = None,
    authoring_draft_root: str | Path | None = None,
    authoring_example_root: str | Path | None = None,
) -> Path:
    """Resolve the definition directory for an exercise-id under notebook defaults."""

    candidates = candidate_definition_dirs(
        exercise_id,
        project_root=project_root,
        definitions_dir=definitions_dir,
        authoring_draft_root=authoring_draft_root,
        authoring_example_root=authoring_example_root,
    )
    if exercise_id:
        for candidate in candidates:
            if (candidate / f"{exercise_id}.yaml").exists():
                return candidate
    return candidates[0]


def build_stage_check_pipeline_config(
    *,
    exercise_id: str | None,
    definitions_dir: str | Path,
    annotation_csv: str | Path | None = None,
    preprocessing_config: PreprocessingConfig | None = None,
    normalization_config: NormalizationConfig | None = None,
    canonicalization_config: CanonicalizationConfig | None = None,
    enable_validation: bool = True,
    enable_annotation: bool = True,
    enable_preprocessing: bool = True,
    enable_normalization: bool = True,
    enable_canonicalization: bool = False,
    enable_rep_segmentation: bool = False,
    enable_phase_segmentation: bool = False,
    enable_features: bool = False,
    enable_role_context: bool = False,
    enable_biomech: bool = False,
    fps_default: float = 30.0,
) -> PipelineConfig:
    """Build a standard stage-check PipelineConfig for notebooks.

    The helper centralizes repeated notebook wiring. It does not add new
    movement logic; it only selects which documented pipeline stages are enabled.
    """

    cfg = PipelineConfig()
    cfg.validation = ValidationConfig(enabled=enable_validation)
    cfg.annotation = AnnotationConfig(
        enabled=enable_annotation,
        path=str(annotation_csv) if annotation_csv is not None else None,
    )
    cfg.exercise_definition = ExerciseDefinitionConfig(
        enabled=True,
        definitions_dir=str(definitions_dir),
        exercise_id=exercise_id,
    )
    cfg.preprocessing = (
        deepcopy(preprocessing_config)
        if preprocessing_config
        else PreprocessingConfig(enabled=enable_preprocessing)
    )
    cfg.preprocessing.enabled = enable_preprocessing
    cfg.normalization = (
        deepcopy(normalization_config)
        if normalization_config
        else NormalizationConfig(
            enabled=enable_normalization,
            keep_reference_columns=True,
        )
    )
    cfg.normalization.enabled = enable_normalization
    cfg.canonicalization = (
        deepcopy(canonicalization_config)
        if canonicalization_config
        else CanonicalizationConfig(
            enabled=enable_canonicalization,
            report_only=True,
            downstream_coordinate_mode="norm",
        )
    )
    cfg.canonicalization.enabled = enable_canonicalization
    cfg.rep_segmentation = RepSegmentationConfig(
        enabled=enable_rep_segmentation,
        fps_default=fps_default,
    )
    cfg.phase_segmentation = PhaseSegmentationConfig(
        enabled=enable_phase_segmentation,
        fps_default=fps_default,
    )
    cfg.features = FeaturesConfig(enabled=enable_features)
    cfg.features.role_context = RoleContextConfig(enabled=enable_role_context)
    cfg.biomech = BiomechConfig(enabled=enable_biomech)
    return cfg


def prepare_previous_stage_inputs(
    *,
    prepare_until: str,
    pose_csv: str | Path | None = None,
    pose_df: pd.DataFrame | None = None,
    annotation_csv: str | Path | None = None,
    exercise_id: str | None = None,
    project_root: str | Path | None = None,
    definitions_dir: str | Path | None = None,
    authoring_draft_root: str | Path | None = None,
    authoring_example_root: str | Path | None = None,
    landmarks: list[str] | None = None,
    preprocessing_config: PreprocessingConfig | None = None,
    normalization_config: NormalizationConfig | None = None,
) -> PreviousStageInputs:
    """Prepare previous-stage dataframes and reports through a requested stage.

    This function is intended for stage-check notebooks. It keeps repeated
    validation/annotation/definition/preprocessing/normalization setup in Python
    code while preserving each stage's report for notebook inspection.
    """

    stage = _normalize_stage_name(prepare_until)
    target_order = _STAGE_ORDER[stage]
    root = _resolve_path(project_root, _PROJECT_ROOT) or _PROJECT_ROOT
    resolved_pose_csv = _resolve_path(pose_csv, root)
    resolved_annotation_csv = _resolve_path(annotation_csv, root)
    active_landmarks = list(landmarks or LANDMARKS)

    if pose_df is None:
        if resolved_pose_csv is None:
            raise ValueError("Either pose_csv or pose_df must be provided.")
        raw_df = load_pose_csv(resolved_pose_csv)
    else:
        raw_df = pose_df.copy()

    context = PreviousStageInputs(
        project_root=root,
        prepare_until=stage,
        pose_csv=resolved_pose_csv,
        annotation_csv=resolved_annotation_csv,
        exercise_id=exercise_id,
        definitions_dir=None,
        raw_df=raw_df,
    )

    if target_order >= _STAGE_ORDER["validation"]:
        context.validation_report = run_basic_validation(
            df=context.raw_df,
            required_columns=make_required_columns(active_landmarks),
            coordinate_columns=make_coordinate_columns(active_landmarks),
            visibility_columns=make_visibility_columns(active_landmarks),
        )

    if target_order >= _STAGE_ORDER["annotation"]:
        if resolved_annotation_csv is None:
            annotation_df = None
        else:
            annotation_df = load_annotation_csv(resolved_annotation_csv)
        annotated_df, annotation_report = apply_annotation(
            context.raw_df, annotation_df
        )
        context.annotation_df = annotation_df
        context.annotated_df = annotated_df
        context.annotation_report = annotation_report

    if target_order >= _STAGE_ORDER["exercise_definition"]:
        definition_input_df = context.annotated_df
        resolved_exercise_id = exercise_id
        if resolved_exercise_id is None and definition_input_df is not None:
            resolved_exercise_id = _first_non_null_string(
                definition_input_df, "exercise_id"
            )
        resolved_definitions_dir = resolve_target_definitions_dir(
            resolved_exercise_id,
            project_root=root,
            definitions_dir=definitions_dir,
            authoring_draft_root=authoring_draft_root,
            authoring_example_root=authoring_example_root,
        )
        context.exercise_id = resolved_exercise_id
        context.definitions_dir = resolved_definitions_dir
        context.exercise_definition = load_exercise_definition(
            exercise_id=resolved_exercise_id,
            definitions_dir=resolved_definitions_dir,
        )

    if target_order >= _STAGE_ORDER["preprocessing"]:
        input_df = context.annotated_df if context.annotated_df is not None else raw_df
        config = preprocessing_config or PreprocessingConfig(enabled=True)
        preprocessed_df, preprocessing_report = preprocess_pose_dataframe(
            df=input_df,
            landmarks=active_landmarks,
            exercise_definition=context.exercise_definition,
            config=config,
        )
        context.preprocessed_df = preprocessed_df
        context.preprocessing_report = preprocessing_report

    if target_order >= _STAGE_ORDER["normalization"]:
        input_df = (
            context.preprocessed_df
            if context.preprocessed_df is not None
            else context.annotated_df
        )
        if input_df is None:
            input_df = raw_df
        config = normalization_config or NormalizationConfig(
            enabled=True,
            keep_reference_columns=True,
        )
        normalized_df, normalization_report = normalize_pose_by_hip_torso(
            df=input_df,
            landmarks=active_landmarks,
            keep_reference_columns=config.keep_reference_columns,
            model_depth_scale=config.model_depth_scale,
        )
        context.normalized_df = normalized_df
        context.normalization_report = normalization_report

    return context
