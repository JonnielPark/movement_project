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
    ⑥  segmentation           semi-automatic intra-rep kinematic phase splitter
    ⑦  motion_attribution     per-rep active-side consistency
    ⑧  features               spatial / temporal / control feature extraction
                               (rep-level and phase-level when ⑥ has populated phase column)
    ⑨  biomech                biomechanical proxy modeling (CoM, moment arm, anthropometry)
    ⑩  biomarker              interpretable digital biomarkers with provenance
    ⑪  visualization          per-step visualization and reporting
    ⑫  simulation             robustness simulation (outside run_pipeline)

Step activation: enabled flags in configs/pipeline_default.yaml.
Terminology: docs/_terminology.md.
"""
from __future__ import annotations

from movement.io import load_pose_csv  # noqa
from movement.validation import run_basic_validation  # noqa
from movement.annotation import apply_annotation, load_annotation_csv  # noqa
from movement.exercise_definition import (  # noqa
    load_exercise_definition,
    load_all_exercise_definitions,
)
from movement.preprocessing import preprocess_pose_dataframe  # noqa
from movement.normalization import normalize_pose_by_hip_torso  # noqa
from movement.segmentation import segment_phases  # noqa
from movement.motion_attribution import attribute_motion, AttributionThresholds  # noqa
from movement.visualization import (  # noqa
    create_pose_animation,
    create_pose_comparison_animation,
    plot_reliability_overlay,
    plot_joint_angle_timeseries,
    plot_rep_timeline,
    plot_attribution_chart,
    plot_biomarker_radar,
)
from movement.pipeline import load_pipeline_config, run_pipeline  # noqa
from movement.features import FeatureRecord, summarize_phase_to_rep  # noqa
from movement.biomech import BiomechRecord  # noqa
from movement.biomarker import BiomarkerRecord, from_feature_record, from_biomech_record  # noqa

__all__ = [
    # I/O
    "load_pose_csv",
    # ① validation
    "run_basic_validation",
    # ② annotation
    "apply_annotation",
    "load_annotation_csv",
    # ③ exercise definition
    "load_exercise_definition",
    "load_all_exercise_definitions",
    # ④ preprocessing
    "preprocess_pose_dataframe",
    # ⑤ normalization
    "normalize_pose_by_hip_torso",
    # ⑥ phase segmentation
    "segment_phases",
    # ⑦ motion attribution
    "attribute_motion",
    "AttributionThresholds",
    # ⑧ features (prefer direct import from submodules)
    "FeatureRecord",
    "summarize_phase_to_rep",
    # ⑨ biomech proxy (prefer direct import from submodules)
    "BiomechRecord",
    # ⑩ biomarker
    "BiomarkerRecord",
    "from_feature_record",
    "from_biomech_record",
    # ⑪ visualization
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
]
