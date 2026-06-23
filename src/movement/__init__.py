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
    ⑥  canonicalization       optional analysis-space candidate evidence
    ⑦  segmentation           semi-automatic rep splitter + intra-rep phase splitter
    ⑧  motion_attribution     per-rep active-side consistency
    ⑨  features               spatial / temporal / control feature extraction
                               (rep-level and phase-level when ⑦ has populated phase column)
    ⑩  biomech                biomechanical proxy modeling (CoM, moment arm, anthropometry)
    ⑪  biomarker              interpretable digital biomarkers with provenance
    ⑫  visualization          per-step visualization and reporting
    ⑬  simulation             robustness simulation (outside run_pipeline)

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
    load_all_exercise_definitions,
    load_exercise_context,
    load_exercise_definition,
)
from movement.exercise_authoring import (  # noqa: E402
    ExerciseAuthoringSpec,
    artifact_to_yaml,
    derive_movement_pattern_from_authoring_axes,
    generate_authoring_artifacts,
    load_authoring_registries,
    recommend_analysis_templates_for_authoring_axes,
    recommend_camera_positions_for_authoring_axes,
    recommend_counting_templates_for_authoring_axes,
    recommend_phase_templates_for_authoring_axes,
    suggest_body_regions_from_joint_actions,
    write_authoring_draft_artifacts,
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
    apply_canonicalization,
)
from movement.segmentation import segment_phases, segment_reps  # noqa: E402
from movement.motion_attribution import (  # noqa: E402
    AttributionThresholds,
    attribute_motion,
)
from movement.visualization import (  # noqa: E402
    create_pose_animation,
    create_pose_comparison_animation,
    plot_attribution_chart,
    plot_biomarker_radar,
    plot_joint_angle_timeseries,
    plot_reliability_overlay,
    plot_rep_timeline,
)
from movement.pipeline import load_pipeline_config, run_pipeline  # noqa
from movement.stage_context import (  # noqa: E402
    PreviousStageInputs,
    prepare_previous_stage_inputs,
    resolve_target_definitions_dir,
)
from movement.features import FeatureRecord, summarize_phase_to_rep  # noqa
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
    "ExerciseContext",
    "ExerciseAuthoringSpec",
    "artifact_to_yaml",
    "derive_movement_pattern_from_authoring_axes",
    "generate_authoring_artifacts",
    "load_authoring_registries",
    "recommend_analysis_templates_for_authoring_axes",
    "recommend_camera_positions_for_authoring_axes",
    "recommend_counting_templates_for_authoring_axes",
    "recommend_phase_templates_for_authoring_axes",
    "suggest_body_regions_from_joint_actions",
    "write_authoring_draft_artifacts",
    # ④ preprocessing
    "preprocess_pose_dataframe",
    # ⑤ normalization
    "normalize_pose_by_hip_torso",
    # ⑥ canonicalization and floor-relative support prior
    "CanonicalizationConfig",
    "Corrected3DHypothesisConfig",
    "apply_canonicalization",
    "FloorReferenceConfig",
    "FloorReferenceReport",
    "apply_floor_relative_correction",
    # ⑦ segmentation
    "segment_reps",
    "segment_phases",
    # ⑧ motion attribution
    "attribute_motion",
    "AttributionThresholds",
    # ⑨ features (prefer direct import from submodules)
    "FeatureRecord",
    "summarize_phase_to_rep",
    # ⑩ biomech proxy (prefer direct import from submodules)
    "BiomechRecord",
    # ⑪ biomarker
    "BiomarkerRecord",
    "from_feature_record",
    "from_biomech_record",
    "load_fms_mapping",
    "traffic_light_for_score",
    # ⑫ visualization
    "create_pose_animation",
    "create_pose_comparison_animation",
    "plot_reliability_overlay",
    "plot_joint_angle_timeseries",
    "plot_rep_timeline",
    "plot_attribution_chart",
    "plot_biomarker_radar",
    # pipeline runner
    "load_pipeline_config",
    "run_pipeline",
    "PreviousStageInputs",
    "prepare_previous_stage_inputs",
    "resolve_target_definitions_dir",
]
