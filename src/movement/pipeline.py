"""
Pipeline Runner

Runs the analysis steps in order:
    ① validation             structural integrity check
    ② annotation             frame-level segment metadata
    ③ exercise_definition    biomechanical property object loading
    ④ preprocessing          monocular data quality correction
    ⑤ normalization          body-relative coordinate normalization
    ⑥ segmentation          semi-automatic rep splitting + intra-rep phase splitting
    ⑦ motion_attribution     per-rep active-side consistency
    ⑧ features               spatial / temporal / control feature extraction
    ⑨ biomech                biomechanical proxy modeling (CoM, moment arm)
    ⑩ biomarker              interpretable digital biomarkers with provenance

Each step is toggled via the enabled flag in configs/pipeline_default.yaml.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from movement.config import (
    LANDMARKS,
    make_coordinate_columns,
    make_required_columns,
    make_visibility_columns,
)
from movement.normalization import normalize_pose_by_hip_torso
from movement.validation import run_basic_validation

# Project root: src/movement/pipeline.py → up 3 levels
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_path(p: str | Path) -> Path:
    """Return absolute paths unchanged; resolve relative paths from project root."""
    p = Path(p)
    return p if p.is_absolute() else _PROJECT_ROOT / p


def _unique_non_null_strings(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    return [
        str(value)
        for value in df[column].dropna().unique().tolist()
        if str(value).strip()
    ]


def _evaluate_camera_protocol(
    df: pd.DataFrame,
    exercise_definition: Any,
) -> dict[str, Any]:
    """Compare observed filming metadata with the exercise camera protocol."""
    protocol = getattr(exercise_definition, "camera_protocol", None)
    if protocol is None:
        return {
            "available": False,
            "warnings": [],
            "forced_exclusion": False,
            "coordinate_correction": "none",
        }

    observed_zones = _unique_non_null_strings(df, "camera_zone")
    observed_heights = _unique_non_null_strings(df, "camera_height_level")
    recommended_zones = list(protocol.recommended_zones)
    recommended_height = protocol.recommended_height

    zone_values = [zone for zone in observed_zones if zone != "unknown"]
    height_values = [height for height in observed_heights if height != "unknown"]
    zone_mismatches = [
        zone for zone in zone_values if zone not in set(recommended_zones)
    ]
    height_mismatches = [
        height for height in height_values if height != recommended_height
    ]

    warning_messages: list[str] = []
    if zone_mismatches:
        warning_messages.append(
            "camera_zone outside recommended_zones: "
            f"observed={zone_mismatches}, recommended={recommended_zones}"
        )
    if height_mismatches:
        warning_messages.append(
            "camera_height_level outside recommended_height: "
            f"observed={height_mismatches}, recommended={recommended_height}"
        )

    for message in warning_messages:
        warnings.warn(f"[Step ③] {message}", stacklevel=2)

    return {
        "available": True,
        "recommended_zones": recommended_zones,
        "observed_zones": observed_zones,
        "zone_match": None if not zone_values else len(zone_mismatches) == 0,
        "recommended_height": recommended_height,
        "observed_height_levels": observed_heights,
        "height_match": None if not height_values else len(height_mismatches) == 0,
        "out_of_zone_policy": protocol.out_of_zone_policy,
        "coordinate_correction": protocol.coordinate_correction,
        "forced_exclusion": False,
        "warnings": warning_messages,
    }


# ── Per-step config dataclasses ───────────────────────────────────────────────


@dataclass
class ValidationConfig:
    enabled: bool = True
    missing_value_threshold: float = 0.05
    visibility_threshold: float = 0.5


@dataclass
class KalmanConfig:
    enabled: bool = False
    process_noise: float = 0.01
    measurement_noise: float = 0.1


@dataclass
class ReliabilityConfig:
    visibility_threshold: float = 0.5
    segment_length_tolerance: float = 0.25
    joint_angle_check: bool = True
    velocity_threshold_torso_per_sec: float = 5.0


@dataclass
class SwapDetectionConfig:
    enabled: bool = True
    temporal_consistency: bool = True
    orientation_prior: bool = True
    orientation_disagree_ratio: float = 0.4


@dataclass
class InterpolationConfig:
    enabled: bool = True
    method: str = "linear"
    max_gap_frames: int = 3


@dataclass
class SmoothingConfig:
    enabled: bool = False
    method: str = "rolling_median"
    window_size: int = 3


@dataclass
class PreprocessingConfig:
    enabled: bool = False
    reliability: ReliabilityConfig = field(default_factory=ReliabilityConfig)
    swap_detection: SwapDetectionConfig = field(default_factory=SwapDetectionConfig)
    interpolation: InterpolationConfig = field(default_factory=InterpolationConfig)
    smoothing: SmoothingConfig = field(default_factory=SmoothingConfig)
    kalman_filter: KalmanConfig = field(default_factory=KalmanConfig)


@dataclass
class NormalizationConfig:
    enabled: bool = True
    method: str = "hip_torso"
    keep_reference_columns: bool = True


@dataclass
class AnnotationConfig:
    enabled: bool = False
    path: str | None = None


@dataclass
class ExerciseDefinitionConfig:
    enabled: bool = True
    definitions_dir: str = "data/definitions/exercises"
    exercise_id: str | None = None


@dataclass
class MotionAttributionConfig:
    enabled: bool = False
    tau_active: float = 0.70
    tau_ambiguous: float = 0.55
    tau_swap: float = 0.85
    mode: str = "conservative"


@dataclass
class SpatialConfig:
    rom: bool = False
    symmetry: bool = False
    shape: bool = False


@dataclass
class TemporalConfig:
    tempo: bool = False
    variability: bool = False


@dataclass
class ControlConfig:
    stability: bool = False
    compensation: bool = False


@dataclass
class FeaturesConfig:
    enabled: bool = False
    spatial: SpatialConfig = field(default_factory=SpatialConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)
    control: ControlConfig = field(default_factory=ControlConfig)


@dataclass
class BiomechConfig:
    enabled: bool = False
    anthropometric_model: str = "winter_1990"
    include_com_estimation: bool = True
    include_moment_arm: bool = True
    output_unit: str = "torso_length_ratio"


@dataclass
class RepSegmentationConfig:
    enabled: bool = False
    fps_default: float = 30.0


@dataclass
class PhaseSegmentationConfig:
    enabled: bool = False
    fps_default: float = 30.0
    multi_inflection_policy: str = "global_extremum"
    minimum_rep_length_frames: int = 8


@dataclass
class BiomarkerConfig:
    enabled: bool = False
    emit_provenance: bool = True
    unit: str = "torso_length_ratio"
    domain_weights: dict[str, float] | None = None
    score_bounds: dict[str, float] | None = None


# backward-compatibility alias
ScoringConfig = BiomarkerConfig


@dataclass
class InputConfig:
    path: str = "data/pose/sample/mediapipe_squat_synthetic.csv"


@dataclass
class OutputConfig:
    save_processed: bool = False
    processed_path: str = "data/processed/normalized.csv"
    save_report: bool = False
    report_path: str = "data/processed/report.json"


@dataclass
class PipelineConfig:
    input: InputConfig = field(default_factory=InputConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    annotation: AnnotationConfig = field(default_factory=AnnotationConfig)
    exercise_definition: ExerciseDefinitionConfig = field(
        default_factory=ExerciseDefinitionConfig
    )
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    normalization: NormalizationConfig = field(default_factory=NormalizationConfig)
    rep_segmentation: RepSegmentationConfig = field(
        default_factory=RepSegmentationConfig
    )
    phase_segmentation: PhaseSegmentationConfig = field(
        default_factory=PhaseSegmentationConfig
    )
    motion_attribution: MotionAttributionConfig = field(
        default_factory=MotionAttributionConfig
    )
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    biomech: BiomechConfig = field(default_factory=BiomechConfig)
    biomarker: BiomarkerConfig = field(default_factory=BiomarkerConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


# ── Config loader ─────────────────────────────────────────────────────────────


def load_pipeline_config(path: Path | str) -> PipelineConfig:
    """Load a PipelineConfig from a YAML file."""
    with open(path, encoding="utf-8") as f:
        raw: dict = yaml.safe_load(f) or {}

    inp = raw.get("input", {})
    val = raw.get("validation", {})
    ann = raw.get("annotation", {})
    exd = raw.get("exercise_definition", {})
    pre = raw.get("preprocessing", {})
    rel = pre.get("reliability", {})
    sw = pre.get("swap_detection", {})
    itp = pre.get("interpolation", {})
    sm = pre.get("smoothing", {})
    kal = pre.get("kalman_filter", {})
    nor = raw.get("normalization", {})
    rsg = raw.get("rep_segmentation", {})
    psg = raw.get("phase_segmentation", {})
    ma = raw.get("motion_attribution", {})
    feat = raw.get("features", {})
    sp = feat.get("spatial", {})
    te = feat.get("temporal", {})
    co = feat.get("control", {})
    bio = raw.get("biomech", {})
    # backward-compat: fall back to 'scoring' key if 'biomarker' is absent
    bm = raw.get("biomarker", raw.get("scoring", {}))
    out = raw.get("output", {})

    return PipelineConfig(
        input=InputConfig(
            path=inp.get("path", "data/pose/sample/mediapipe_squat_synthetic.csv"),
        ),
        validation=ValidationConfig(
            enabled=val.get("enabled", True),
            missing_value_threshold=val.get("missing_value_threshold", 0.05),
            visibility_threshold=val.get("visibility_threshold", 0.5),
        ),
        annotation=AnnotationConfig(
            enabled=ann.get("enabled", False),
            path=ann.get("path", None),
        ),
        exercise_definition=ExerciseDefinitionConfig(
            enabled=exd.get("enabled", True),
            definitions_dir=exd.get("definitions_dir", "data/definitions/exercises"),
            exercise_id=exd.get("exercise_id", None),
        ),
        preprocessing=PreprocessingConfig(
            enabled=pre.get("enabled", False),
            reliability=ReliabilityConfig(
                visibility_threshold=float(rel.get("visibility_threshold", 0.5)),
                segment_length_tolerance=float(
                    rel.get("segment_length_tolerance", 0.25)
                ),
                joint_angle_check=bool(rel.get("joint_angle_check", True)),
                velocity_threshold_torso_per_sec=float(
                    rel.get("velocity_threshold_torso_per_sec", 5.0)
                ),
            ),
            swap_detection=SwapDetectionConfig(
                enabled=bool(sw.get("enabled", True)),
                temporal_consistency=bool(sw.get("temporal_consistency", True)),
                orientation_prior=bool(sw.get("orientation_prior", True)),
                orientation_disagree_ratio=float(
                    sw.get("orientation_disagree_ratio", 0.4)
                ),
            ),
            interpolation=InterpolationConfig(
                enabled=bool(itp.get("enabled", True)),
                method=itp.get("method", "linear"),
                max_gap_frames=int(itp.get("max_gap_frames", 3)),
            ),
            smoothing=SmoothingConfig(
                enabled=bool(sm.get("enabled", False)),
                method=sm.get("method", "rolling_median"),
                window_size=int(sm.get("window_size", 3)),
            ),
            kalman_filter=KalmanConfig(
                enabled=bool(kal.get("enabled", False)),
                process_noise=float(kal.get("process_noise", 0.01)),
                measurement_noise=float(kal.get("measurement_noise", 0.1)),
            ),
        ),
        normalization=NormalizationConfig(
            enabled=nor.get("enabled", True),
            method=nor.get("method", "hip_torso"),
            keep_reference_columns=nor.get("keep_reference_columns", True),
        ),
        rep_segmentation=RepSegmentationConfig(
            enabled=rsg.get("enabled", False),
            fps_default=float(rsg.get("fps_default", 30.0)),
        ),
        phase_segmentation=PhaseSegmentationConfig(
            enabled=psg.get("enabled", False),
            fps_default=float(psg.get("fps_default", 30.0)),
            multi_inflection_policy=psg.get(
                "multi_inflection_policy", "global_extremum"
            ),
            minimum_rep_length_frames=int(psg.get("minimum_rep_length_frames", 8)),
        ),
        motion_attribution=MotionAttributionConfig(
            enabled=ma.get("enabled", False),
            tau_active=float(ma.get("thresholds", {}).get("active", 0.70)),
            tau_ambiguous=float(ma.get("thresholds", {}).get("ambiguous", 0.55)),
            tau_swap=float(ma.get("thresholds", {}).get("swap", 0.85)),
            mode=ma.get("mode", "conservative"),
        ),
        features=FeaturesConfig(
            enabled=feat.get("enabled", False),
            spatial=SpatialConfig(
                rom=sp.get("rom", False),
                symmetry=sp.get("symmetry", False),
                shape=sp.get("shape", False),
            ),
            temporal=TemporalConfig(
                tempo=te.get("tempo", False),
                variability=te.get("variability", False),
            ),
            control=ControlConfig(
                stability=co.get("stability", False),
                compensation=co.get("compensation", False),
            ),
        ),
        biomech=BiomechConfig(
            enabled=bio.get("enabled", False),
            anthropometric_model=bio.get("anthropometric_model", "winter_1990"),
            include_com_estimation=bool(bio.get("include_com_estimation", True)),
            include_moment_arm=bool(bio.get("include_moment_arm", True)),
            output_unit=bio.get("output_unit", "torso_length_ratio"),
        ),
        biomarker=BiomarkerConfig(
            enabled=bm.get("enabled", False),
            emit_provenance=bool(bm.get("emit_provenance", True)),
            unit=bm.get("unit", "torso_length_ratio"),
            domain_weights=bm.get("domain_weights"),
            score_bounds=bm.get("score_bounds"),
        ),
        output=OutputConfig(
            save_processed=out.get("save_processed", False),
            processed_path=out.get("processed_path", "data/processed/normalized.csv"),
            save_report=out.get("save_report", False),
            report_path=out.get("report_path", "data/processed/report.json"),
        ),
    )


# ── Pipeline runner ────────────────────────────────────────────────────────────


def run_pipeline(
    df: pd.DataFrame,
    config: PipelineConfig,
    landmarks: list[str] | None = None,
    ann_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Run analysis steps in order. Only steps with enabled=True are executed.

    Parameters
    ----------
    df : pd.DataFrame
        Input pose dataframe. Shape: (T, J*4+2) — frame, timestamp, landmark xyz + visibility.
    config : PipelineConfig
        Loaded via load_pipeline_config().
    landmarks : list[str], optional
        Landmark name list. None uses movement.config.LANDMARKS.
    ann_df : pd.DataFrame | None, optional
        Pre-loaded annotation table (output of annotation.load_annotation_csv).
        None falls back to whole-sequence annotation in step ②.

    Returns
    -------
    df : pd.DataFrame
        Processed dataframe with columns added by each step.
    report : dict
        Per-step result dict keyed by step name.
    """
    if landmarks is None:
        landmarks = LANDMARKS

    report: dict[str, Any] = {}
    exercise_def = None

    # ── ① Validation ─────────────────────────────────────────────────────────
    if config.validation.enabled:
        validation_report = run_basic_validation(
            df=df,
            required_columns=make_required_columns(landmarks),
            coordinate_columns=make_coordinate_columns(landmarks),
            visibility_columns=make_visibility_columns(landmarks),
        )
        report["validation"] = validation_report
        if not validation_report["passed"]:
            print("[Step ①] Validation: one or more checks failed.")

    # ── ② Annotation ─────────────────────────────────────────────────────────
    if config.annotation.enabled:
        from movement.annotation import apply_annotation

        df, ann_report = apply_annotation(df, ann_df)
        report["annotation"] = ann_report

    # ── ③ Exercise Definition Loading ────────────────────────────────────────
    if config.exercise_definition.enabled:
        import warnings as _warnings
        from movement.exercise_definition import load_exercise_definition

        ex_id = config.exercise_definition.exercise_id
        if ex_id is None and "exercise_type" in df.columns:
            unique_types = df["exercise_type"].dropna().unique().tolist()
            if len(unique_types) == 1:
                ex_id = unique_types[0]
            elif len(unique_types) > 1:
                _warnings.warn(
                    f"[Step ③] Multiple exercise_type values found: {unique_types}. "
                    "Using the first. For multi-exercise sessions, load definitions per segment.",
                    stacklevel=2,
                )
                ex_id = unique_types[0]

        exercise_def = load_exercise_definition(
            exercise_id=ex_id,
            definitions_dir=_resolve_path(config.exercise_definition.definitions_dir),
        )
        report["exercise_definition"] = {
            "exercise_id": exercise_def.exercise_id,
            "display_name": exercise_def.display_name,
            "version": exercise_def.version,
            "is_generic_fallback": exercise_def.is_generic_fallback,
            "laterality": exercise_def.classification.get("laterality"),
            "primary_plane": exercise_def.classification.get("primary_plane"),
            "compensation_candidates": exercise_def.compensation_candidates,
            "camera_protocol": (
                exercise_def.camera_protocol.as_dict()
                if exercise_def.camera_protocol is not None
                else None
            ),
            "filming_condition": _evaluate_camera_protocol(df, exercise_def),
        }

    # ── ④ Preprocessing ───────────────────────────────────────────────────────
    if config.preprocessing.enabled:
        from movement.preprocessing import preprocess_pose_dataframe

        df, pre_report = preprocess_pose_dataframe(
            df=df,
            landmarks=landmarks,
            exercise_definition=exercise_def,
            config=config.preprocessing,
        )
        report["preprocessing"] = pre_report

    # ── ⑤ Normalization ───────────────────────────────────────────────────────
    if config.normalization.enabled:
        df, norm_report = normalize_pose_by_hip_torso(
            df=df,
            landmarks=landmarks,
            keep_reference_columns=config.normalization.keep_reference_columns,
        )
        report["normalization"] = norm_report

    # ── ⑥ Rep Segmentation ───────────────────────────────────────────────────
    if config.rep_segmentation.enabled:
        if exercise_def is None:
            print("[Step ⑥] Rep Segmentation: exercise_def not available — skipped.")
        else:
            from movement.segmentation import segment_reps

            df, rep_report = segment_reps(
                df,
                exercise_def,
                fps_default=config.rep_segmentation.fps_default,
            )
            report["rep_segmentation"] = rep_report.as_dict()
            if rep_report.status == "skipped":
                print(
                    f"[Step ⑥] Rep Segmentation: exercise "
                    f"'{exercise_def.exercise_id}' has no rep_segmentation block — skipped."
                )

    # ── ⑥ Phase Segmentation ─────────────────────────────────────────────────
    if config.phase_segmentation.enabled:
        if exercise_def is None:
            print("[Step ⑥] Phase Segmentation: exercise_def not available — skipped.")
        elif getattr(exercise_def, "phase_segmentation", None) is None:
            print(
                f"[Step ⑥] Phase Segmentation: exercise '{exercise_def.exercise_id}' "
                "has no phase_segmentation block — skipped."
            )
        else:
            _has_reps = (
                "segment_type" in df.columns and (df["segment_type"] == "rep").any()
            )
            if not _has_reps:
                print("[Step ⑥] Phase Segmentation: no rep frames found — skipped.")
            else:
                from movement.segmentation import segment_phases

                df, phase_reports = segment_phases(
                    df,
                    exercise_def,
                    fps_default=config.phase_segmentation.fps_default,
                )
                report["phase_segmentation"] = [r.as_dict() for r in phase_reports]
    else:
        pass  # ⑥ disabled — phase column stays NA (set by ② Annotation)

    # ── ⑦ Motion Attribution ─────────────────────────────────────────────────
    if config.motion_attribution.enabled:
        from movement.motion_attribution import AttributionThresholds, attribute_motion

        thresholds = AttributionThresholds(
            active=config.motion_attribution.tau_active,
            ambiguous=config.motion_attribution.tau_ambiguous,
            swap=config.motion_attribution.tau_swap,
        )
        if exercise_def is None:
            print("[Step ⑦] Motion Attribution: exercise_def not available — skipped.")
        else:
            df, attr_report = attribute_motion(
                df=df,
                exercise_definition=exercise_def,
                thresholds=thresholds,
                mode=config.motion_attribution.mode,
            )
            report["motion_attribution"] = attr_report.as_dict()

    # ── ⑧ Feature Extraction ─────────────────────────────────────────────────
    feat_records: list[Any] = []
    if config.features.enabled:
        from movement.features import (
            audit_analysis_disrupting_patterns,
            audit_feature_registry,
            extract_rep_features,
        )

        if exercise_def is None:
            print("[Step ⑧] Feature Extraction: exercise_def not available — skipped.")
        else:
            coverage_report = audit_feature_registry(exercise_def)
            report["feature_registry_coverage"] = coverage_report.as_dict()
            detectability_report = audit_analysis_disrupting_patterns(exercise_def)
            report["analysis_disrupting_pattern_detectability"] = (
                detectability_report.as_dict()
            )
            feat_records = extract_rep_features(df, exercise_def)
            report["features"] = [
                {
                    "feature_id": r.feature_id,
                    "rep_id": r.rep_id,
                    "value": r.value,
                    "unit": r.unit,
                    "source_fields": r.source_fields,
                }
                for r in feat_records
            ]

    # ── ⑨ Biomechanical Proxy Modeling ───────────────────────────────────────
    biomech_records: list[Any] = []
    if config.biomech.enabled:
        if exercise_def is None:
            print("[Step ⑨] Biomech Proxy: exercise_def not available — skipped.")
        else:
            from movement.biomech import extract_rep_biomech

            biomech_records = extract_rep_biomech(
                df, exercise_def, use_visibility_weight=True
            )
            report["biomech"] = [
                {
                    "metric_id": r.metric_id,
                    "rep_id": r.rep_id,
                    "value": r.value,
                    "unit": r.unit,
                    "source_fields": r.source_fields,
                    "note": r.note,
                    "visibility_weight_applied": r.visibility_weight_applied,
                    "n_frames_used": r.n_frames_used,
                    "n_frames_excluded_low_visibility": r.n_frames_excluded_low_visibility,
                }
                for r in biomech_records
            ]

    # ── ⑩ Biomarker Derivation ────────────────────────────────────────────────
    if config.biomarker.enabled:
        if exercise_def is None:
            print(
                "[Step ⑩] Biomarker Derivation: exercise_def not available — skipped."
            )
        else:
            from movement.biomarker.scoring import derive_biomarkers

            def_version = exercise_def.version
            biomarker_records, score_records = derive_biomarkers(
                feat_records=feat_records,
                biomech_records=biomech_records,
                exercise_definition=exercise_def,
                definition_version=def_version,
                domain_weights=config.biomarker.domain_weights,
                score_bounds=config.biomarker.score_bounds,
            )
            report["biomarker"] = [b.as_dict() for b in biomarker_records]
            if score_records:
                report["biomarker_scores"] = [s.as_dict() for s in score_records]

    return df, report
