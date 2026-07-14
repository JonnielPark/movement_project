"""
movement — Digital Biomarker Framework

Biomechanical analysis framework that quantifies movement quality from monocular 3D pose data
and produces interpretable digital biomarkers.

Pipeline steps:
    ①  validation             structural integrity check
    ②  annotation             frame-level segment metadata
    ③  exercise_definition    biomechanical property object loading
    ④  preprocessing          monocular data quality correction
    ⑤  normalization          body-relative coordinate normalization
    ⑤-1 canonicalization      optional analysis-space evidence
    ⑥  segmentation           semi-automatic rep splitter + intra-rep phase splitter
    ⑦  features               side-role context + spatial / temporal / control features
                               (rep-level and phase-level when ⑥ has populated phase column)
    ⑧  biomech                biomechanical proxy modeling (CoM, moment arm, anthropometry)
    ⑨  biomarker              interpretable digital biomarkers with provenance
    ⑩  visualization          per-step visualization and reporting
    ⑪  simulation             robustness simulation (outside run_pipeline)

Step activation: enabled flags in configs/pipeline_default.yaml.
Terminology: docs/terminology.md.
"""

from __future__ import annotations

import sys as _sys

from movement.core import config as config
from movement.core import io as io
from movement.core import utils as utils
from movement.definitions import clinical as clinical
from movement.definitions import exercise_authoring as exercise_authoring
from movement.definitions import exercise_definition as exercise_definition
from movement.features import side_role_context as side_role_context
from movement.reporting import visualization as visualization
from movement import stage_context as stage_context
from movement.stages import annotation as annotation
from movement.stages import canonicalization as canonicalization
from movement.stages import floor_reference as floor_reference
from movement.stages import motion_attribution as motion_attribution
from movement.stages import normalization as normalization
from movement.stages import preprocessing as preprocessing
from movement.stages import segmentation as segmentation
from movement.stages import validation as validation

_COMPAT_MODULES = {
    "annotation": annotation,
    "canonicalization": canonicalization,
    "clinical": clinical,
    "config": config,
    "exercise_authoring": exercise_authoring,
    "exercise_definition": exercise_definition,
    "floor_reference": floor_reference,
    "io": io,
    "side_role_context": side_role_context,
    "motion_attribution": motion_attribution,
    "normalization": normalization,
    "preprocessing": preprocessing,
    "segmentation": segmentation,
    "stage_context": stage_context,
    "utils": utils,
    "validation": validation,
    "visualization": visualization,
}

for _name, _module in _COMPAT_MODULES.items():
    _sys.modules[f"{__name__}.{_name}"] = _module

from movement.io import load_participant_profile_yaml, load_pose_csv  # noqa: E402
from movement.validation import run_basic_validation  # noqa: E402
from movement.annotation import apply_annotation, load_annotation_csv  # noqa: E402
from movement.exercise_definition import (  # noqa: E402
    ExerciseContext,
    ExerciseSessionBlockSpec,
    ExerciseSessionDefinition,
    ExerciseSessionRestPolicy,
    load_all_exercise_definitions,
    load_exercise_context,
    load_exercise_definition,
    load_exercise_session_definition,
)
from movement.exercise_authoring import (  # noqa: E402
    ExerciseAuthoringSpec,
    ExerciseSessionAuthoringSpec,
    ExerciseSessionBlockAuthoringSpec,
    artifact_to_yaml,
    derive_movement_pattern_from_authoring_axes,
    exercise_session_artifact_path,
    generate_authoring_artifacts,
    generate_exercise_session_artifact,
    list_exercise_definition_ids,
    list_exercise_session_ids,
    load_authoring_registries,
    recommend_analysis_templates_for_authoring_axes,
    recommend_camera_positions_for_authoring_axes,
    recommend_counting_templates_for_authoring_axes,
    recommend_phase_templates_for_authoring_axes,
    suggest_body_regions_from_joint_actions,
    validate_exercise_session_authoring_spec,
    write_authoring_draft_artifacts,
    write_exercise_session_artifact,
)
from movement.preprocessing import preprocess_pose_dataframe  # noqa: E402
from movement.normalization import normalize_pose_by_hip_torso  # noqa: E402
from movement.floor_reference import (  # noqa: E402
    FloorReferenceConfig,
    FloorReferenceReport,
    apply_floor_relative_correction,
)
from movement.canonicalization import (  # noqa: E402
    CanonicalizationConfig,
    Corrected3DHypothesisConfig,
    XYDepthLiftConfig,
    apply_canonicalization,
)
from movement.segmentation import segment_phases, segment_reps  # noqa: E402
from movement.side_role_context import (  # noqa: E402
    SideRoleContextReport,
    SideRoleContextThresholds,
    resolve_side_role_context,
)
from movement.visualization import (  # noqa: E402
    create_pose_animation,
    create_pose_comparison_animation,
    plot_biomarker_radar,
    plot_joint_angle_timeseries,
    plot_reliability_overlay,
    plot_rep_timeline,
    plot_side_role_context_chart,
)
from movement.pipeline import load_pipeline_config, run_pipeline  # noqa
from movement.stage_context import (  # noqa: E402
    PreviousStageInputs,
    prepare_previous_stage_inputs,
    resolve_target_definitions_dir,
)
from movement.features import (  # noqa
    FeatureContext,
    FeatureRecord,
    apply_feature_context,
    resolve_feature_context,
    summarize_phase_to_rep,
)
from movement.biomech import BiomechRecord  # noqa
from movement.biomarker import (  # noqa: E402
    BiomarkerRecord,
    from_feature_record,
    from_biomech_record,
)
from movement.clinical import load_fms_mapping, traffic_light_for_score  # noqa: E402

del _name, _module, _COMPAT_MODULES, _sys

__all__ = [
    # I/O
    "load_pose_csv",
    "load_participant_profile_yaml",
    # ① validation
    "run_basic_validation",
    # ② annotation
    "apply_annotation",
    "load_annotation_csv",
    # ③ exercise definition
    "load_exercise_definition",
    "load_exercise_context",
    "load_all_exercise_definitions",
    "load_exercise_session_definition",
    "ExerciseContext",
    "ExerciseSessionBlockSpec",
    "ExerciseSessionDefinition",
    "ExerciseSessionRestPolicy",
    "ExerciseAuthoringSpec",
    "ExerciseSessionAuthoringSpec",
    "ExerciseSessionBlockAuthoringSpec",
    "artifact_to_yaml",
    "derive_movement_pattern_from_authoring_axes",
    "exercise_session_artifact_path",
    "generate_authoring_artifacts",
    "generate_exercise_session_artifact",
    "list_exercise_definition_ids",
    "list_exercise_session_ids",
    "load_authoring_registries",
    "recommend_analysis_templates_for_authoring_axes",
    "recommend_camera_positions_for_authoring_axes",
    "recommend_counting_templates_for_authoring_axes",
    "recommend_phase_templates_for_authoring_axes",
    "suggest_body_regions_from_joint_actions",
    "validate_exercise_session_authoring_spec",
    "write_authoring_draft_artifacts",
    "write_exercise_session_artifact",
    # ④ preprocessing
    "preprocess_pose_dataframe",
    # ⑤ normalization
    "normalize_pose_by_hip_torso",
    # ⑤-1 canonicalization and floor-relative support prior
    "CanonicalizationConfig",
    "Corrected3DHypothesisConfig",
    "XYDepthLiftConfig",
    "apply_canonicalization",
    "FloorReferenceConfig",
    "FloorReferenceReport",
    "apply_floor_relative_correction",
    # ⑥ segmentation
    "segment_reps",
    "segment_phases",
    # ⑦ feature side-role context
    "resolve_side_role_context",
    "SideRoleContextThresholds",
    "SideRoleContextReport",
    # ⑦ features (prefer direct import from submodules)
    "FeatureContext",
    "FeatureRecord",
    "apply_feature_context",
    "resolve_feature_context",
    "summarize_phase_to_rep",
    # ⑧ biomech proxy (prefer direct import from submodules)
    "BiomechRecord",
    # ⑨ biomarker
    "BiomarkerRecord",
    "from_feature_record",
    "from_biomech_record",
    "load_fms_mapping",
    "traffic_light_for_score",
    # ⑩ visualization
    "create_pose_animation",
    "create_pose_comparison_animation",
    "plot_reliability_overlay",
    "plot_joint_angle_timeseries",
    "plot_rep_timeline",
    "plot_side_role_context_chart",
    "plot_biomarker_radar",
    # pipeline runner
    "load_pipeline_config",
    "run_pipeline",
    "PreviousStageInputs",
    "prepare_previous_stage_inputs",
    "resolve_target_definitions_dir",
]
