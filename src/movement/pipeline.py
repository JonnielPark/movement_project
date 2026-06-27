"""
Pipeline Runner

Documented analysis stages:
    ① validation             structural integrity check
    ② annotation             frame-level segment metadata
    ③ exercise_definition    biomechanical property object loading
    ④ preprocessing          monocular data quality correction
    ⑤ normalization          body-relative coordinate normalization
    ⑥ canonicalization       optional analysis-space candidate evidence
    ⑦ segmentation           semi-automatic rep splitting + intra-rep phase splitting
    ⑨ features               side-role context + spatial / temporal / control features
    ⑩ biomech                biomechanical proxy modeling (CoM, moment arm)
    ⑪ biomarker              interpretable digital biomarkers with provenance

The current runner supports implemented stages ①–⑪; canonicalization remains
disabled unless explicitly enabled.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from movement.core.config import (
    LANDMARKS,
    make_coordinate_columns,
    make_required_columns,
    make_visibility_columns,
)
from movement.stages.normalization import normalize_pose_by_hip_torso
from movement.stages.validation import run_basic_validation
from movement.stages.canonicalization import (
    CanonicalizationConfig,
    CanonicalizationDataConfidenceConfig,
    Corrected3DHypothesisConfig,
    MovementPlaneAlignmentConfig,
    ProtocolHeightLateralWidthAlignmentConfig,
    apply_canonicalization,
)
from movement.stages.floor_reference import FloorReferenceConfig

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
    post_velocity_check: bool = True


@dataclass
class SmoothingConfig:
    enabled: bool = False
    method: str = "rolling_median"
    window_size: int = 3


@dataclass
class FarSideStabilizationConfig:
    enabled: bool = False
    camera_side_inference: bool = True
    visibility_threshold: float = 0.6
    jitter_threshold_torso_per_sec: float | None = None
    acceleration_threshold_torso_per_sec2: float | None = None
    max_gap_frames: int = 3
    smoothing_method: str = "rolling_median"
    smoothing_window_size: int = 3
    mark_long_gaps_low_confidence: bool = True
    depth_axis: str = "z"
    near_depth_sign: str = "negative"
    min_depth_offset_torso: float = 0.05


@dataclass
class PreprocessingConfig:
    enabled: bool = False
    reliability: ReliabilityConfig = field(default_factory=ReliabilityConfig)
    swap_detection: SwapDetectionConfig = field(default_factory=SwapDetectionConfig)
    interpolation: InterpolationConfig = field(default_factory=InterpolationConfig)
    smoothing: SmoothingConfig = field(default_factory=SmoothingConfig)
    far_side_stabilization: FarSideStabilizationConfig = field(
        default_factory=FarSideStabilizationConfig
    )


@dataclass
class NormalizationConfig:
    enabled: bool = True
    method: str = "hip_torso"
    keep_reference_columns: bool = True
    model_depth_scale: float = 1.0


@dataclass
class FloorRelativeCorrectionConfig:
    enabled: bool = False
    method: str = "support_contact_plane"
    coordinate_mode: str = "norm"
    vertical_axis: str = "y"
    support_landmarks: list[str] = field(default_factory=list)
    diagnostic_landmarks: list[str] = field(default_factory=list)
    visibility_threshold: float = 0.7
    stability_window_frames: int = 5
    max_anchor_residual_torso: float = 0.08
    correction_transform: str = "rigid_rotation"
    camera_pitch_deg: float = 0.0
    camera_roll_deg: float = 0.0
    correction_strength: float = 1.0
    max_correction_torso: float = 0.25


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
class RoleContextConfig:
    enabled: bool = False
    tau_active: float = 0.70
    tau_ambiguous: float = 0.55
    tau_swap: float = 0.85
    mode: str = "conservative"


# backward-compatibility alias
MotionAttributionConfig = RoleContextConfig


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
    role_context: RoleContextConfig = field(default_factory=RoleContextConfig)
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
    canonicalization: CanonicalizationConfig = field(
        default_factory=CanonicalizationConfig
    )
    floor_relative_correction: FloorRelativeCorrectionConfig = field(
        default_factory=FloorRelativeCorrectionConfig
    )
    rep_segmentation: RepSegmentationConfig = field(
        default_factory=RepSegmentationConfig
    )
    phase_segmentation: PhaseSegmentationConfig = field(
        default_factory=PhaseSegmentationConfig
    )
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    biomech: BiomechConfig = field(default_factory=BiomechConfig)
    biomarker: BiomarkerConfig = field(default_factory=BiomarkerConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @property
    def motion_attribution(self) -> RoleContextConfig:
        """Legacy alias for `features.role_context`."""
        return self.features.role_context

    @motion_attribution.setter
    def motion_attribution(self, value: RoleContextConfig) -> None:
        self.features.role_context = value


# ── Config loader ─────────────────────────────────────────────────────────────


def _protocol_height_lateral_width_alignment_config(
    raw: dict[str, Any],
) -> ProtocolHeightLateralWidthAlignmentConfig:
    kwargs: dict[str, Any] = {
        "enabled": bool(raw.get("enabled", False)),
        "method": raw.get("method", "height_anchor_lateral_width"),
        "observed_height_level": raw.get("observed_height_level"),
        "observed_height_column": raw.get(
            "observed_height_column",
            "camera_height_level",
        ),
        "recommended_height_level": raw.get("recommended_height_level"),
        "require_height_match": bool(raw.get("require_height_match", True)),
        "near_depth_sign": raw.get("near_depth_sign", "negative"),
        "correction_mode": raw.get("correction_mode", "near_side_attenuation"),
        "correction_strength": float(raw.get("correction_strength", 0.3)),
        "max_scale_change": float(raw.get("max_scale_change", 0.20)),
        "max_correction_torso": float(raw.get("max_correction_torso", 0.15)),
        "min_depth_offset_torso": float(raw.get("min_depth_offset_torso", 0.05)),
        "visibility_threshold": float(raw.get("visibility_threshold", 0.6)),
        "apply_to_landmarks": list(raw.get("apply_to_landmarks", []) or []),
        "preserve_anchor_landmarks": bool(raw.get("preserve_anchor_landmarks", True)),
    }
    if "height_anchor_map" in raw:
        kwargs["height_anchor_map"] = {
            str(key): list(value or [])
            for key, value in (raw.get("height_anchor_map") or {}).items()
        }
    return ProtocolHeightLateralWidthAlignmentConfig(**kwargs)


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
    fss = pre.get("far_side_stabilization", {})
    nor = raw.get("normalization", {})
    can = raw.get("canonicalization", nor.get("canonicalization", {})) or {}
    corrected_3d = (
        can.get(
            "corrected_3d_hypothesis",
            nor.get("corrected_3d_hypothesis", {}),
        )
        or {}
    )
    can_conf = can.get("data_confidence", {})
    can_support = can.get("support_plane_alignment", {})
    can_movement = can.get("movement_plane_alignment", {})
    can_protocol_height = can.get("protocol_height_lateral_width_alignment", {}) or {}
    # floor_relative_correction is a legacy alias for the ⑥ support-plane prior.
    frc = can.get(
        "floor_relative_correction",
        nor.get("floor_relative_correction", raw.get("floor_relative_correction", {})),
    )
    support_alias = can_support or frc
    rsg = raw.get("rep_segmentation", {})
    psg = raw.get("phase_segmentation", {})
    feat = raw.get("features", {})
    rc = feat.get("role_context", raw.get("motion_attribution", {}))
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
                post_velocity_check=bool(itp.get("post_velocity_check", True)),
            ),
            smoothing=SmoothingConfig(
                enabled=bool(sm.get("enabled", False)),
                method=sm.get("method", "rolling_median"),
                window_size=int(sm.get("window_size", 3)),
            ),
            far_side_stabilization=FarSideStabilizationConfig(
                enabled=bool(fss.get("enabled", False)),
                camera_side_inference=bool(fss.get("camera_side_inference", True)),
                visibility_threshold=float(fss.get("visibility_threshold", 0.6)),
                jitter_threshold_torso_per_sec=(
                    None
                    if fss.get("jitter_threshold_torso_per_sec") is None
                    else float(fss.get("jitter_threshold_torso_per_sec"))
                ),
                acceleration_threshold_torso_per_sec2=(
                    None
                    if fss.get("acceleration_threshold_torso_per_sec2") is None
                    else float(fss.get("acceleration_threshold_torso_per_sec2"))
                ),
                max_gap_frames=int(fss.get("max_gap_frames", 3)),
                smoothing_method=fss.get("smoothing_method", "rolling_median"),
                smoothing_window_size=int(fss.get("smoothing_window_size", 3)),
                mark_long_gaps_low_confidence=bool(
                    fss.get("mark_long_gaps_low_confidence", True)
                ),
                depth_axis=fss.get("depth_axis", "z"),
                near_depth_sign=fss.get("near_depth_sign", "negative"),
                min_depth_offset_torso=float(fss.get("min_depth_offset_torso", 0.05)),
            ),
        ),
        normalization=NormalizationConfig(
            enabled=nor.get("enabled", True),
            method=nor.get("method", "hip_torso"),
            keep_reference_columns=nor.get("keep_reference_columns", True),
            model_depth_scale=float(nor.get("model_depth_scale", 1.0)),
        ),
        canonicalization=CanonicalizationConfig(
            enabled=bool(can.get("enabled", False)),
            coordinate_mode=can.get("coordinate_mode", "norm"),
            output_prefix=can.get("output_prefix", "canon"),
            report_only=bool(can.get("report_only", True)),
            downstream_coordinate_mode=can.get("downstream_coordinate_mode", "norm"),
            data_confidence=CanonicalizationDataConfidenceConfig(
                emit=bool(can_conf.get("emit", True)),
                correction_magnitude_warn_torso=float(
                    can_conf.get("correction_magnitude_warn_torso", 0.15)
                ),
                correction_magnitude_fail_torso=float(
                    can_conf.get("correction_magnitude_fail_torso", 0.30)
                ),
                residual_warn_torso=float(can_conf.get("residual_warn_torso", 0.08)),
            ),
            support_plane_alignment=FloorReferenceConfig(
                enabled=bool(support_alias.get("enabled", False)),
                method=support_alias.get("method", "support_contact_plane"),
                coordinate_mode=can.get(
                    "coordinate_mode",
                    support_alias.get("coordinate_mode", "norm"),
                ),
                vertical_axis=support_alias.get("vertical_axis", "y"),
                support_landmarks=list(
                    support_alias.get("support_landmarks", []) or []
                ),
                diagnostic_landmarks=list(
                    support_alias.get("diagnostic_landmarks", []) or []
                ),
                visibility_threshold=float(
                    support_alias.get("visibility_threshold", 0.7)
                ),
                stability_window_frames=int(
                    support_alias.get("stability_window_frames", 5)
                ),
                max_anchor_residual_torso=float(
                    support_alias.get("max_anchor_residual_torso", 0.08)
                ),
                correction_transform=support_alias.get(
                    "correction_transform", "rigid_rotation"
                ),
                camera_pitch_deg=float(support_alias.get("camera_pitch_deg", 0.0)),
                camera_roll_deg=float(support_alias.get("camera_roll_deg", 0.0)),
                correction_strength=float(
                    support_alias.get("correction_strength", 1.0)
                ),
                max_correction_torso=float(
                    support_alias.get("max_correction_torso", 0.25)
                ),
            ),
            movement_plane_alignment=MovementPlaneAlignmentConfig(
                enabled=bool(can_movement.get("enabled", False)),
                method=can_movement.get("method", "principal_motion_plane"),
                fit_landmarks=list(can_movement.get("fit_landmarks", []) or []),
                minimum_visible_landmark_ratio=float(
                    can_movement.get("minimum_visible_landmark_ratio", 0.7)
                ),
                correction_strength=float(can_movement.get("correction_strength", 0.5)),
                max_rotation_deg=float(can_movement.get("max_rotation_deg", 20.0)),
                preserve_out_of_plane_residual=bool(
                    can_movement.get("preserve_out_of_plane_residual", True)
                ),
            ),
            protocol_height_lateral_width_alignment=(
                _protocol_height_lateral_width_alignment_config(can_protocol_height)
            ),
            corrected_3d_hypothesis=Corrected3DHypothesisConfig(
                enabled=bool(corrected_3d.get("enabled", False)),
                output_family=str(
                    corrected_3d.get("output_family", "corrected_3d_hypothesis")
                ),
                downstream_coordinate_mode=str(
                    corrected_3d.get("downstream_coordinate_mode", "norm")
                ),
                emit_sensitivity_report=bool(
                    corrected_3d.get("emit_sensitivity_report", True)
                ),
                support_pair=tuple(
                    str(item)
                    for item in (
                        corrected_3d.get(
                            "support_pair",
                            ["left_ankle", "right_ankle"],
                        )
                        or []
                    )
                ),
                report_burden_before_feature_use=bool(
                    corrected_3d.get("report_burden_before_feature_use", True)
                ),
                require_feature_domain_declaration=bool(
                    corrected_3d.get("require_feature_domain_declaration", True)
                ),
            ),
        ),
        floor_relative_correction=FloorRelativeCorrectionConfig(
            enabled=bool(frc.get("enabled", False)),
            method=frc.get("method", "support_contact_plane"),
            coordinate_mode=frc.get("coordinate_mode", "norm"),
            vertical_axis=frc.get("vertical_axis", "y"),
            support_landmarks=list(frc.get("support_landmarks", []) or []),
            diagnostic_landmarks=list(frc.get("diagnostic_landmarks", []) or []),
            visibility_threshold=float(frc.get("visibility_threshold", 0.7)),
            stability_window_frames=int(frc.get("stability_window_frames", 5)),
            max_anchor_residual_torso=float(frc.get("max_anchor_residual_torso", 0.08)),
            correction_transform=frc.get("correction_transform", "rigid_rotation"),
            camera_pitch_deg=float(frc.get("camera_pitch_deg", 0.0)),
            camera_roll_deg=float(frc.get("camera_roll_deg", 0.0)),
            correction_strength=float(frc.get("correction_strength", 1.0)),
            max_correction_torso=float(frc.get("max_correction_torso", 0.25)),
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
        features=FeaturesConfig(
            enabled=feat.get("enabled", False),
            role_context=RoleContextConfig(
                enabled=rc.get("enabled", False),
                tau_active=float(rc.get("thresholds", {}).get("active", 0.70)),
                tau_ambiguous=float(rc.get("thresholds", {}).get("ambiguous", 0.55)),
                tau_swap=float(rc.get("thresholds", {}).get("swap", 0.85)),
                mode=rc.get("mode", "conservative"),
            ),
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
        from movement.stages.annotation import apply_annotation

        df, ann_report = apply_annotation(df, ann_df)
        report["annotation"] = ann_report

    # ── ③ Exercise Definition Loading ────────────────────────────────────────
    if config.exercise_definition.enabled:
        import warnings as _warnings
        from movement.definitions.exercise_definition import load_exercise_definition

        ex_id = config.exercise_definition.exercise_id
        if ex_id is None:
            if "exercise_id" in df.columns:
                id_column = "exercise_id"
                unique_ids = df[id_column].dropna().unique().tolist()
            else:
                unique_ids = []
            if len(unique_ids) == 1:
                ex_id = unique_ids[0]
            elif len(unique_ids) > 1:
                _warnings.warn(
                    f"[Step ③] Multiple exercise_id values found: {unique_ids}. "
                    "Using the first. For multi-exercise sessions, load "
                    "definitions per segment.",
                    stacklevel=2,
                )
                ex_id = unique_ids[0]

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
            "movement_template_id": exercise_def.classification.get(
                "movement_template_id"
            ),
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
        from movement.stages.preprocessing import preprocess_pose_dataframe

        df, pre_report = preprocess_pose_dataframe(
            df=df,
            landmarks=landmarks,
            exercise_definition=exercise_def,
            config=config.preprocessing,
        )
        report["preprocessing"] = pre_report
        if "feature_availability_summary" in pre_report:
            df.attrs["feature_availability_summary"] = pre_report[
                "feature_availability_summary"
            ]

    # ── ⑤ Normalization ───────────────────────────────────────────────────────
    if config.normalization.enabled:
        df, norm_report = normalize_pose_by_hip_torso(
            df=df,
            landmarks=landmarks,
            keep_reference_columns=config.normalization.keep_reference_columns,
            model_depth_scale=config.normalization.model_depth_scale,
        )
        report["normalization"] = norm_report

    # ── ⑥ Canonicalization ──────────────────────────────────────────────────
    if config.canonicalization.enabled:
        canonicalization_config = config.canonicalization
        protocol_height_config = (
            canonicalization_config.protocol_height_lateral_width_alignment
        )
        protocol = getattr(exercise_def, "camera_protocol", None)
        recommended_height = (
            getattr(protocol, "recommended_height", None)
            if protocol is not None
            else None
        )
        if (
            protocol_height_config.enabled
            and protocol_height_config.recommended_height_level is None
            and recommended_height
        ):
            canonicalization_config = replace(
                canonicalization_config,
                protocol_height_lateral_width_alignment=replace(
                    protocol_height_config,
                    recommended_height_level=recommended_height,
                ),
            )

        df, canonicalization_report = apply_canonicalization(
            df=df,
            landmarks=landmarks,
            config=canonicalization_config,
        )
        report["canonicalization"] = canonicalization_report

        if (
            not canonicalization_config.report_only
            and canonicalization_config.downstream_coordinate_mode == "canon"
        ):
            warnings.warn(
                "[Step ⑥] downstream_coordinate_mode='canon' is recorded but "
                "downstream stages still read their documented normalized "
                "coordinate inputs in this implementation pass.",
                stacklevel=2,
            )

    # ── ⑥ Legacy Canonicalization Alias: Floor-Relative Correction ───────────
    if not config.canonicalization.enabled and config.floor_relative_correction.enabled:
        from movement.stages.floor_reference import (
            FloorReferenceConfig,
            apply_floor_relative_correction,
        )

        floor_config = FloorReferenceConfig(
            enabled=True,
            method=config.floor_relative_correction.method,
            coordinate_mode=config.floor_relative_correction.coordinate_mode,
            vertical_axis=config.floor_relative_correction.vertical_axis,
            support_landmarks=config.floor_relative_correction.support_landmarks,
            diagnostic_landmarks=(
                config.floor_relative_correction.diagnostic_landmarks
            ),
            visibility_threshold=(
                config.floor_relative_correction.visibility_threshold
            ),
            stability_window_frames=(
                config.floor_relative_correction.stability_window_frames
            ),
            max_anchor_residual_torso=(
                config.floor_relative_correction.max_anchor_residual_torso
            ),
            correction_transform=config.floor_relative_correction.correction_transform,
            camera_pitch_deg=config.floor_relative_correction.camera_pitch_deg,
            camera_roll_deg=config.floor_relative_correction.camera_roll_deg,
            correction_strength=(config.floor_relative_correction.correction_strength),
            max_correction_torso=(
                config.floor_relative_correction.max_correction_torso
            ),
        )
        df, floor_report = apply_floor_relative_correction(
            df=df,
            landmarks=landmarks,
            config=floor_config,
        )
        report["floor_relative_correction"] = floor_report.as_dict()

    corrected_policy = config.canonicalization.corrected_3d_hypothesis
    if (
        config.canonicalization.enabled
        and corrected_policy.enabled
        and corrected_policy.emit_sensitivity_report
    ):
        from movement.stages.corrected_3d_hypothesis import (
            build_corrected_3d_hypothesis_candidates,
        )

        corrected_review = build_corrected_3d_hypothesis_candidates(
            df,
            landmarks=landmarks,
            exercise_support_context={
                "exercise_id": (
                    exercise_def.exercise_id if exercise_def is not None else None
                ),
            },
            solver_config={
                "output_family": corrected_policy.output_family,
                "support_pair": list(corrected_policy.support_pair),
            },
        )
        review_dict = corrected_review.as_dict()
        report["corrected_3d_hypothesis_review"] = review_dict
        report.setdefault("canonicalization", {}).setdefault(
            "corrected_3d_hypothesis", {}
        )["review_status"] = review_dict["readiness_provenance"]["status"]

    # ── ⑦ Segmentation: Rep Boundaries ───────────────────────────────────────
    if config.rep_segmentation.enabled:
        if exercise_def is None:
            print("[Step ⑦] Rep Segmentation: exercise_def not available — skipped.")
        else:
            from movement.stages.segmentation import segment_reps

            df, rep_report = segment_reps(
                df,
                exercise_def,
                fps_default=config.rep_segmentation.fps_default,
            )
            report["rep_segmentation"] = rep_report.as_dict()
            if rep_report.status == "skipped":
                print(
                    f"[Step ⑦] Rep Segmentation: exercise "
                    f"'{exercise_def.exercise_id}' has no rep_segmentation block — skipped."
                )

    # ── ⑦ Segmentation: Intra-Rep Phases ─────────────────────────────────────
    if config.phase_segmentation.enabled:
        if exercise_def is None:
            print("[Step ⑦] Phase Segmentation: exercise_def not available — skipped.")
        elif getattr(exercise_def, "phase_segmentation", None) is None:
            print(
                f"[Step ⑦] Phase Segmentation: exercise '{exercise_def.exercise_id}' "
                "has no phase_segmentation block — skipped."
            )
        else:
            _has_reps = (
                "segment_type" in df.columns and (df["segment_type"] == "rep").any()
            )
            if not _has_reps:
                print("[Step ⑦] Phase Segmentation: no rep frames found — skipped.")
            else:
                from movement.stages.segmentation import segment_phases

                df, phase_reports = segment_phases(
                    df,
                    exercise_def,
                    fps_default=config.phase_segmentation.fps_default,
                )
                report["phase_segmentation"] = [r.as_dict() for r in phase_reports]
    else:
        pass  # ⑦ disabled — phase column stays NA (set by ② Annotation)

    # ── ⑨ Feature Extraction ─────────────────────────────────────────────────
    feat_records: list[Any] = []
    if config.features.enabled:
        from movement.features import (
            audit_analysis_disrupting_patterns,
            audit_feature_registry,
            extract_rep_features,
        )
        from movement.features.side_role_context import (
            SideRoleContextThresholds,
            resolve_side_role_context,
        )

        if exercise_def is None:
            print("[Step ⑨] Feature Extraction: exercise_def not available — skipped.")
        else:
            if config.features.role_context.enabled:
                thresholds = SideRoleContextThresholds(
                    active=config.features.role_context.tau_active,
                    ambiguous=config.features.role_context.tau_ambiguous,
                    swap=config.features.role_context.tau_swap,
                )
                df, role_context_report = resolve_side_role_context(
                    df=df,
                    exercise_definition=exercise_def,
                    thresholds=thresholds,
                    mode=config.features.role_context.mode,
                )
                report["feature_role_context"] = role_context_report.as_dict()

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
                    "view_reliability": r.view_reliability,
                    "availability": r.availability,
                    "availability_reasons": r.availability_reasons,
                    "camera_zone": r.camera_zone,
                    "role_context": r.role_context,
                    "depth_dependency": r.depth_dependency,
                    "model_depth_reliability": r.model_depth_reliability,
                    "landmark_quality": r.landmark_quality,
                }
                for r in feat_records
            ]

    # ── ⑩ Biomechanical Proxy Modeling ───────────────────────────────────────
    biomech_records: list[Any] = []
    if config.biomech.enabled:
        if exercise_def is None:
            print("[Step ⑩] Biomech Proxy: exercise_def not available — skipped.")
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

    # ── ⑪ Biomarker Derivation ────────────────────────────────────────────────
    if config.biomarker.enabled:
        if exercise_def is None:
            print(
                "[Step ⑪] Biomarker Derivation: exercise_def not available — skipped."
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
