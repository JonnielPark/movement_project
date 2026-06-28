"""
⑧ Feature Extraction

Computes spatial, temporal, and control domain features from normalized pose data.
Each feature is returned as a FeatureRecord with (value, unit, source_fields)
so that downstream biomarker derivation (⑩) can trace provenance.

When the `phase` column is populated by ⑦ Segmentation, features are
emitted at both rep-level (phase=None) and phase-level (phase='Descent', etc.),
enabling the hierarchical analysis structure described in dissertation §5.5.

Submodules:
    features.spatial   → ROM, left/right symmetry, trajectory shape
    features.temporal  → tempo, inter-rep variability
    features.control   → CoM stability, compensation movements

Coordinate convention : (T, J, 3) = (frame, joint_index, xyz).
Column convention     : <landmark>_norm_x/y/z (normalized coordinates).
Unit convention       : torso_length_ratio (dimensionless) or degree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class FeatureRecord:
    """Single feature computation result.

    Parameters
    ----------
    feature_id    : unique identifier (e.g. 'spatial.rom.left_knee')
                    Phase-level records append a phase suffix:
                    'spatial.rom.left_knee.descent'
    exercise_id   : exercise identifier
    rep_id        : rep number (None = sequence-level feature)
    value         : feature value
    unit          : torso_length_ratio | degree | second | dimensionless_cv
    source_fields : exercise definition fields that drove this feature (provenance).
                    Phase-level records must include 'phase_segmentation.*' entries.
    note          : optional interpretation note
    phase         : kinematic phase label (None = rep-level; 'Descent' etc. = phase-level)
    depth_dependency : dependency on monocular depth inference, separate from
                    camera-zone view reliability
    model_depth_reliability : pose-estimator depth confidence for this recording
    landmark_quality : feature-level landmark evidence summary
    """

    feature_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str] = field(default_factory=list)
    note: str | None = None
    phase: str | None = None
    view_reliability: str = "unknown"
    availability: str = "assessed"
    availability_reasons: list[str] = field(default_factory=list)
    camera_zone: str | None = None
    role_context: dict[str, str] | None = None
    depth_dependency: str = "unknown"
    model_depth_reliability: str = "unknown"
    landmark_quality: str = "unknown"

    def __post_init__(self) -> None:
        if not self.source_fields:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': source_fields is empty. "
                "Provenance fields from the exercise definition must be specified."
            )
        valid_reliability = {"high", "moderate", "low", "not_assessed", "unknown"}
        if self.view_reliability not in valid_reliability:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': invalid view_reliability "
                f"{self.view_reliability!r}."
            )
        valid_availability = {"assessed", "low_confidence", "not_assessed"}
        if self.availability not in valid_availability:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': invalid availability "
                f"{self.availability!r}."
            )
        valid_depth_dependency = {"none", "low", "moderate", "high", "unknown"}
        if self.depth_dependency not in valid_depth_dependency:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': invalid depth_dependency "
                f"{self.depth_dependency!r}."
            )
        valid_model_depth_reliability = {"high", "moderate", "low", "unknown"}
        if self.model_depth_reliability not in valid_model_depth_reliability:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': invalid model_depth_reliability "
                f"{self.model_depth_reliability!r}."
            )
        valid_landmark_quality = {"sufficient", "mixed", "low", "unknown"}
        if self.landmark_quality not in valid_landmark_quality:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': invalid landmark_quality "
                f"{self.landmark_quality!r}."
            )


@dataclass
class FeatureContext:
    """Role/context resolution summary prepared before feature interpretation.

    The context does not modify pose coordinates, rep/phase labels, or feature
    values. It describes how side-aware feature families should interpret the
    current exercise and recording provenance.
    """

    laterality: str | None
    role_mode: str
    role_context: dict[str, str] = field(default_factory=dict)
    role_confidence: str = "not_assessed"
    context_reasons: list[str] = field(default_factory=list)
    source_fields: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "laterality": self.laterality,
            "role_mode": self.role_mode,
            "role_context": self.role_context,
            "role_confidence": self.role_confidence,
            "context_reasons": self.context_reasons,
            "source_fields": self.source_fields,
        }

    @property
    def attribution_confidence(self) -> str:
        """Legacy alias for role_confidence."""
        return self.role_confidence


@dataclass
class FeatureRegistryCoverageReport:
    """Coverage audit for YAML-declared feature and compensation entries."""

    exercise_id: str
    connected_feature_domain_entries: dict[str, list[str]] = field(default_factory=dict)
    unsupported_feature_domain_entries: list[dict[str, Any]] = field(
        default_factory=list
    )
    external_step_feature_domain_entries: list[dict[str, Any]] = field(
        default_factory=list
    )
    implemented_compensation_candidates: list[str] = field(default_factory=list)
    unimplemented_compensation_candidates: list[dict[str, Any]] = field(
        default_factory=list
    )
    compensation_candidate_availability: list[dict[str, Any]] = field(
        default_factory=list
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "exercise_id": self.exercise_id,
            "connected_feature_domain_entries": self.connected_feature_domain_entries,
            "unsupported_feature_domain_entries": self.unsupported_feature_domain_entries,
            "external_step_feature_domain_entries": self.external_step_feature_domain_entries,
            "implemented_compensation_candidates": self.implemented_compensation_candidates,
            "unimplemented_compensation_candidates": self.unimplemented_compensation_candidates,
            "compensation_candidate_availability": self.compensation_candidate_availability,
        }


@dataclass
class AnalysisDisruptingPatternDetectabilityReport:
    """Detectability audit for performance_protocol.analysis_disrupting_patterns."""

    exercise_id: str
    pose_detectable_scoring_candidates: list[dict[str, Any]] = field(
        default_factory=list
    )
    acquisition_control_factors: list[dict[str, Any]] = field(default_factory=list)
    interpretation_limitation_factors: list[dict[str, Any]] = field(
        default_factory=list
    )
    unknown_patterns: list[dict[str, Any]] = field(default_factory=list)
    all_patterns: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "exercise_id": self.exercise_id,
            "pose_detectable_scoring_candidates": self.pose_detectable_scoring_candidates,
            "acquisition_control_factors": self.acquisition_control_factors,
            "interpretation_limitation_factors": self.interpretation_limitation_factors,
            "unknown_patterns": self.unknown_patterns,
            "all_patterns": self.all_patterns,
        }


# ── Phase-aware feature families ─────────────────────────────────────────────
# These feature families are computed per (rep_id, phase) when the phase column
# is populated.  control.compensation is rep-level only because compensation
# candidates span the full rep trajectory (crossing phase boundaries).

PHASE_AWARE_FEATURE_FAMILIES: frozenset[str] = frozenset(
    {
        "spatial.rom",
        "spatial.shape",
        "temporal.tempo",
        "control.stability",
    }
)

_VIEW_RELIABILITY_VALUES = {"high", "moderate", "low", "not_assessed"}
_MODEL_DEPTH_RELIABILITY_VALUES = {"high", "moderate", "low", "unknown"}
_DEPTH_DEPENDENCY_VALUES = {"none", "low", "moderate", "high", "unknown"}
_LANDMARK_QUALITY_LOW_REASONS = {
    "far_side_jitter_high",
    "far_side_jitter_present",
    "bilateral_landmark_coverage_low",
    "swap_risk_high",
}


def _report_value(report: Any, key: str, default: Any = None) -> Any:
    if report is None:
        return default
    if isinstance(report, dict):
        return report.get(key, default)
    return getattr(report, key, default)


def _side_role_columns_available(df: Any) -> bool:
    columns = set(getattr(df, "columns", []))
    return {
        "detected_active_limb",
        "expected_active_limb",
        "side_role_consistent",
        "side_role_confidence",
    }.issubset(columns)


def resolve_feature_context(
    df: Any,
    exercise_definition: Any,
    role_context_report: Any | None = None,
) -> FeatureContext:
    """Resolve side/role context for feature interpretation.

    This helper is a Feature Extraction side-role preparation surface. It
    deliberately avoids coordinate changes, rep/phase relabeling, and scoring.
    """

    classification = getattr(exercise_definition, "classification", {}) or {}
    laterality = classification.get("laterality")
    source_fields = ["classification.laterality"]

    if laterality == "bilateral_symmetric":
        return FeatureContext(
            laterality=laterality,
            role_mode="bilateral_symmetry",
            role_context={"symmetry_context": "bilateral_symmetric"},
            role_confidence="not_assessed",
            context_reasons=[
                "bilateral_symmetric_uses_symmetry_or_side_bias_context",
                "active_side_role_context_not_applicable",
            ],
            source_fields=source_fields,
        )

    if laterality in {"alternating", "unilateral_left", "unilateral_right"}:
        source_fields.extend(
            [
                "performance_protocol.side_sequence",
                "feature_role_context",
            ]
        )
        skipped = bool(_report_value(role_context_report, "skipped", False))
        has_columns = _side_role_columns_available(df)
        reasons: list[str] = []

        if skipped:
            confidence = "low_confidence"
            reasons.append("feature_role_context_skipped")
        elif role_context_report is not None or has_columns:
            confidence = "assessed"
            reasons.append("feature_role_context_available")
        else:
            confidence = "low_confidence"
            reasons.append("feature_role_context_missing")

        mode = _report_value(role_context_report, "mode")
        if mode:
            reasons.append(f"feature_role_context_mode_{mode}")

        return FeatureContext(
            laterality=laterality,
            role_mode="active_side",
            role_context={"side_role": "active_side"},
            role_confidence=confidence,
            context_reasons=reasons,
            source_fields=source_fields,
        )

    if laterality == "unilateral_unspecified":
        return FeatureContext(
            laterality=laterality,
            role_mode="unavailable",
            role_context={},
            role_confidence="low_confidence",
            context_reasons=["unilateral_side_requires_context_or_manual_review"],
            source_fields=source_fields + ["performance_protocol.side_sequence"],
        )

    if laterality == "bilateral_asymmetric":
        return FeatureContext(
            laterality=laterality,
            role_mode="unavailable",
            role_context={},
            role_confidence="not_assessed",
            context_reasons=[
                "bilateral_asymmetric_requires_side_bias_feature_policy"
            ],
            source_fields=source_fields,
        )

    return FeatureContext(
        laterality=laterality,
        role_mode="unavailable",
        role_context={},
        role_confidence="not_assessed",
        context_reasons=[f"unsupported_laterality_{laterality}"],
        source_fields=source_fields,
    )


def _record_needs_feature_context(
    record: FeatureRecord,
    feature_context: FeatureContext,
) -> bool:
    if feature_context.role_mode == "bilateral_symmetry":
        return record.feature_id.startswith("spatial.symmetry.")

    if feature_context.role_mode == "active_side":
        if feature_context.role_confidence != "assessed":
            return False
        is_side_specific = (
            ".left" in record.feature_id
            or ".right" in record.feature_id
            or ".left_" in record.feature_id
            or ".right_" in record.feature_id
        )
        return record.feature_id.startswith("control.compensation.") and is_side_specific

    return False


def apply_feature_context(
    records: list[FeatureRecord],
    feature_context: FeatureContext,
) -> list[FeatureRecord]:
    """Attach role context to feature records without changing feature values."""

    if not feature_context.role_context:
        return records

    context_source_fields = list(feature_context.source_fields) + [
        "feature_context.role_mode",
        "feature_context.role_context",
    ]
    if feature_context.role_confidence != "not_assessed":
        context_source_fields.append("feature_context.role_confidence")

    for record in records:
        if not _record_needs_feature_context(record, feature_context):
            continue
        existing_context = record.role_context or {}
        record.role_context = {**feature_context.role_context, **existing_context}
        record.source_fields = _unique_preserve_order(
            list(record.source_fields) + context_source_fields
        )

    return records


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _recording_camera_zone(df: Any) -> str:
    if "camera_zone" not in getattr(df, "columns", []):
        return "unknown"
    values = [
        str(value)
        for value in df["camera_zone"].dropna().tolist()
        if str(value).strip() and str(value).strip().lower() != "unknown"
    ]
    if not values:
        return "unknown"
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return max(counts, key=lambda key: (counts[key], -values.index(key)))


def _feature_metric_aliases(feature_id: str, exercise_definition: Any) -> list[str]:
    primary_plane = str(
        getattr(exercise_definition, "classification", {}).get("primary_plane", "")
    ).lower()

    aliases: list[str] = []
    if feature_id.startswith("spatial.symmetry."):
        aliases.extend(
            [
                "bilateral_symmetry",
                "upper_limb_symmetry",
                "side_to_side_comparison",
            ]
        )
    elif feature_id.startswith("spatial.rom."):
        if primary_plane == "sagittal":
            aliases.extend(
                [
                    "sagittal_rom",
                    "forward_limb_sagittal_rom",
                    "anterior_knee_travel",
                    "rear_limb_extension",
                    "depth",
                    "hip_height",
                ]
            )
        aliases.append("rom")
    elif feature_id.startswith("spatial.shape."):
        aliases.extend(
            ["active_hand_trajectory", "hip_position", "depth", "step_length"]
        )
    elif feature_id.startswith("temporal.tempo."):
        aliases.extend(["tempo", "smoothness"])
    elif feature_id.startswith("temporal.variability."):
        aliases.extend(["tempo", "smoothness"])
    elif feature_id.startswith("control.stability."):
        aliases.extend(
            [
                "centerline_stability",
                "hip_center_stability",
                "hip_position",
                "lateral_shift",
                "hip_height",
            ]
        )
    elif feature_id.startswith("control.compensation.knee_valgus"):
        aliases.extend(["frontal_alignment", "frontal_knee_tracking"])
    elif feature_id.startswith("control.compensation.knee_varus"):
        aliases.extend(["frontal_alignment", "frontal_knee_tracking"])
    elif feature_id.startswith("control.compensation.lateral_pelvic_shift"):
        aliases.extend(["frontal_alignment", "lateral_shift", "pelvis_drop_or_shift"])
    elif feature_id.startswith("control.compensation.heel_lift"):
        aliases.extend(["heel_lift", "sagittal_rom"])
    elif feature_id.startswith("control.compensation.pelvis_rotation"):
        aliases.extend(["transverse_rotation", "pelvis_rotation"])
    elif feature_id.startswith("control.compensation.excessive_trunk_flexion"):
        aliases.extend(["trunk_flexion", "trunk_sagittal_alignment", "sagittal_rom"])

    return _unique_preserve_order(aliases)


def _view_reliability_for_record(
    record: FeatureRecord,
    exercise_definition: Any,
    camera_zone: str,
) -> tuple[str, str | None]:
    view_map = getattr(exercise_definition, "view_metric_reliability", {}) or {}
    zone_map = view_map.get("zones") or {}
    values = zone_map.get(camera_zone) or {}
    for metric_key in _feature_metric_aliases(record.feature_id, exercise_definition):
        reliability = values.get(metric_key)
        if reliability in _VIEW_RELIABILITY_VALUES:
            return str(reliability), metric_key
    return "unknown", None


def _model_depth_reliability(df: Any, exercise_definition: Any) -> str:
    attrs = getattr(df, "attrs", {}) or {}
    attr_reliability = attrs.get("model_depth_reliability")
    if attr_reliability in _MODEL_DEPTH_RELIABILITY_VALUES:
        return str(attr_reliability)

    pose_estimator = attrs.get("pose_estimator_reliability")
    if isinstance(pose_estimator, dict):
        value = pose_estimator.get("model_depth_reliability")
        if value in _MODEL_DEPTH_RELIABILITY_VALUES:
            return str(value)

    view_map = getattr(exercise_definition, "view_metric_reliability", {}) or {}
    yaml_reliability = view_map.get("model_depth_reliability")
    if yaml_reliability in _MODEL_DEPTH_RELIABILITY_VALUES:
        return str(yaml_reliability)

    landmarks = getattr(exercise_definition, "landmarks", None)
    landmark_model = str(getattr(landmarks, "model", "")).lower()
    if "mediapipe" in landmark_model:
        return "low"
    return "unknown"


def _depth_dependency_for_record(
    record: FeatureRecord,
    metric_key: str | None,
) -> str:
    if record.depth_dependency in _DEPTH_DEPENDENCY_VALUES - {"unknown"}:
        return record.depth_dependency

    feature_id = record.feature_id
    high_keys = {
        "bilateral_symmetry",
        "side_to_side_comparison",
        "transverse_rotation",
        "pelvis_rotation",
    }
    moderate_keys = {
        "sagittal_rom",
        "forward_limb_sagittal_rom",
        "rear_limb_extension",
        "anterior_knee_travel",
        "depth",
        "hip_height",
        "trunk_flexion",
        "heel_lift",
        "centerline_stability",
        "hip_center_stability",
        "hip_position",
        "lateral_shift",
        "step_length",
        "active_hand_trajectory",
        "rom",
    }
    low_keys = {
        "frontal_alignment",
        "frontal_knee_tracking",
        "pelvis_drop_or_shift",
        "tempo",
        "smoothness",
        "step_width",
        "side_order",
    }

    if metric_key in high_keys:
        return "high"
    if metric_key in moderate_keys:
        return "moderate"
    if metric_key in low_keys:
        return "low" if metric_key not in {"tempo", "smoothness"} else "none"

    if feature_id.startswith("spatial.symmetry."):
        return "high"
    if feature_id.startswith("temporal."):
        return "none"
    if feature_id.startswith("spatial.rom.") or feature_id.startswith(
        "control.stability."
    ):
        return "moderate"
    if feature_id.startswith("control.compensation.pelvis_rotation"):
        return "high"
    if feature_id.startswith("control.compensation.knee_"):
        return "low"
    return "unknown"


def _landmark_quality_from_reasons(
    summary: dict[str, Any],
    reasons: list[str],
) -> str:
    if any(reason in _LANDMARK_QUALITY_LOW_REASONS for reason in reasons):
        return "low"
    quality = summary.get("landmark_quality")
    if quality in {"sufficient", "mixed", "low", "unknown"}:
        return str(quality)
    if summary:
        return "sufficient"
    return "unknown"


def _matches_feature_family(feature_id: str, family_pattern: str) -> bool:
    return (
        family_pattern.endswith(".*")
        and feature_id.startswith(family_pattern[:-1])
        or feature_id == family_pattern
    )


def _downgrade_availability(current: str, candidate: str) -> str:
    rank = {"assessed": 0, "low_confidence": 1, "not_assessed": 2}
    return candidate if rank[candidate] > rank[current] else current


def annotate_feature_availability(
    records: list[FeatureRecord],
    df: Any,
    exercise_definition: Any,
) -> list[FeatureRecord]:
    """Attach camera-zone reliability and scoring availability metadata.

    The numeric feature values are left unchanged. This stage only records whether
    a computed metric is eligible for composite scoring from the current view.
    """

    camera_zone = _recording_camera_zone(df)
    summary = getattr(df, "attrs", {}).get("feature_availability_summary", {}) or {}
    low_families = summary.get("low_confidence_feature_families", []) or []
    not_families = summary.get("not_assessed_feature_families", []) or []
    summary_reasons = summary.get("reasons", {}) or {}
    model_depth_reliability = _model_depth_reliability(df, exercise_definition)

    for record in records:
        record.camera_zone = camera_zone
        reasons = list(record.availability_reasons)

        reliability, metric_key = _view_reliability_for_record(
            record, exercise_definition, camera_zone
        )
        record.view_reliability = reliability
        record.depth_dependency = _depth_dependency_for_record(record, metric_key)
        record.model_depth_reliability = model_depth_reliability
        if metric_key is not None:
            source = f"view_metric_reliability.zones.{camera_zone}.{metric_key}"
            if source not in record.source_fields:
                record.source_fields.append(source)

        if reliability == "low":
            record.availability = _downgrade_availability(
                record.availability, "low_confidence"
            )
            reasons.append("view_metric_low")
        elif reliability == "not_assessed":
            record.availability = "not_assessed"
            reasons.append("view_metric_not_assessed")
        elif reliability == "unknown" and camera_zone == "unknown":
            reasons.append("camera_zone_unknown")

        if (
            record.depth_dependency == "high"
            and record.model_depth_reliability == "low"
            and record.availability == "assessed"
        ):
            record.availability = "low_confidence"
            reasons.append("model_depth_reliability_low")
            source = "pose_estimator.model_depth_reliability"
            if source not in record.source_fields:
                record.source_fields.append(source)

        for family in low_families:
            if _matches_feature_family(record.feature_id, str(family)):
                record.availability = _downgrade_availability(
                    record.availability, "low_confidence"
                )
                reasons.extend(summary_reasons.get(family, []))
        for family in not_families:
            if _matches_feature_family(record.feature_id, str(family)):
                record.availability = "not_assessed"
                reasons.extend(summary_reasons.get(family, []))

        record.availability_reasons = _unique_preserve_order(
            [reason for reason in reasons if reason]
        )
        record.landmark_quality = _landmark_quality_from_reasons(
            summary, record.availability_reasons
        )

    return records


_FEATURE_DOMAIN_EXTRACTOR_REGISTRY: dict[str, dict[str, str]] = {
    "spatial": {
        "rom": "compute_rom",
        "symmetry": "compute_symmetry",
        "shape": "compute_shape",
    },
    "temporal": {
        "tempo": "compute_tempo",
        "rep_duration": "compute_tempo",
        "variability": "compute_variability",
    },
    "control": {
        "stability": "compute_stability",
        "com_stability": "compute_stability",
        "compensation": "compute_compensation",
    },
}
_FEATURE_DOMAIN_EXTERNAL_STEPS: dict[str, str] = {
    "biomechanical_proxy": "09_biomechanical_proxy",
}

_DEFERRED_COMPENSATION_FEATURE_DESIGN: frozenset[str] = frozenset(
    {
        "asymmetric_knee_flexion",
        "asymmetric_hip_flexion",
        "insufficient_rear_hip_extension",
        "lateral_trunk_lean",
        "pelvis_drop",
        "unstable_step_width",
        "elbow_flare",
        "elbow_asymmetry",
        "shoulder_asymmetry",
        "shoulder_collapse",
        "shoulder_elevation_compensation",
        "scapular_instability_proxy",
        "insufficient_head_descent",
        "head_forward_shift",
        "hip_drop",
        "hip_pike",
        "trunk_rotation",
        "excessive_com_lateral_shift",
        "excessive_com_variability",
        "left_right_timing_variability",
        "phase_timing_asymmetry",
        "movement_discontinuity",
    }
)

_POSE_DETECTABLE_SCORING_CANDIDATE = "pose_detectable_scoring_candidate"
_ACQUISITION_CONTROL_FACTOR = "acquisition_control_factor"
_INTERPRETATION_LIMITATION_FACTOR = "interpretation_limitation_factor"
_UNKNOWN_PATTERN = "unknown"

_ANALYSIS_DISRUPTING_PATTERN_REGISTRY: dict[str, dict[str, Any]] = {
    "arm_swing": {
        "classification": _ACQUISITION_CONTROL_FACTOR,
        "required_landmarks": [
            "left_shoulder",
            "right_shoulder",
            "left_wrist",
            "right_wrist",
        ],
        "view_sensitivity": "medium",
        "visibility_dependency": "medium",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_candidates": [],
        "linked_feature_domain_entries": [],
        "basis": (
            "Arm motion is visible, but whether it assists the movement cannot be "
            "proven from pose trajectories alone."
        ),
    },
    "heel_lift": {
        "classification": _POSE_DETECTABLE_SCORING_CANDIDATE,
        "required_landmarks": ["left_heel", "right_heel", "left_ankle", "right_ankle"],
        "view_sensitivity": "medium",
        "visibility_dependency": "high",
        "annotation_fallback": None,
        "linked_compensation_candidates": ["heel_lift"],
        "linked_feature_domain_entries": ["control.compensation"],
        "basis": "Heel vertical displacement can be estimated from heel landmarks when visible.",
    },
    "unstable_foot_contact": {
        "classification": _ACQUISITION_CONTROL_FACTOR,
        "required_landmarks": ["left_ankle", "right_ankle", "left_heel", "right_heel"],
        "view_sensitivity": "medium",
        "visibility_dependency": "high",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_candidates": [],
        "linked_feature_domain_entries": ["spatial.support_width"],
        "basis": (
            "Foot landmark motion can suggest support changes, but true floor contact "
            "and landmark jitter are hard to separate."
        ),
    },
    "excessive_knee_deviation": {
        "classification": _POSE_DETECTABLE_SCORING_CANDIDATE,
        "required_landmarks": [
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_ankle",
            "right_ankle",
        ],
        "view_sensitivity": "high",
        "visibility_dependency": "medium",
        "annotation_fallback": None,
        "linked_compensation_candidates": ["knee_valgus", "knee_varus"],
        "linked_feature_domain_entries": ["control.compensation", "spatial.alignment"],
        "basis": "Knee deviation can map to frontal-plane valgus or varus proxies.",
    },
    "inconsistent_depth": {
        "classification": _POSE_DETECTABLE_SCORING_CANDIDATE,
        "required_landmarks": ["hip_center", "left_hip", "right_hip"],
        "view_sensitivity": "medium",
        "visibility_dependency": "medium",
        "annotation_fallback": "rep_segmentation.report",
        "linked_compensation_candidates": [
            "asymmetric_depth",
            "insufficient_head_descent",
        ],
        "linked_feature_domain_entries": ["spatial.depth_proxy", "spatial.rom"],
        "basis": "Depth variation is pose-detectable when rep boundaries and reference landmarks are stable.",
    },
    "excessive_trunk_flexion": {
        "classification": _POSE_DETECTABLE_SCORING_CANDIDATE,
        "required_landmarks": [
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
        ],
        "view_sensitivity": "medium",
        "visibility_dependency": "medium",
        "annotation_fallback": None,
        "linked_compensation_candidates": ["excessive_trunk_flexion"],
        "linked_feature_domain_entries": [
            "control.compensation",
            "spatial.posture_angle",
        ],
        "basis": "Trunk lean from the shoulder-center to hip-center vector is already feature-compatible.",
    },
    "inconsistent_step_length": {
        "classification": _ACQUISITION_CONTROL_FACTOR,
        "required_landmarks": ["left_ankle", "right_ankle", "left_foot", "right_foot"],
        "view_sensitivity": "medium",
        "visibility_dependency": "high",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_candidates": ["unstable_step_width"],
        "linked_feature_domain_entries": ["spatial.support_width"],
        "basis": "Step changes affect comparability and active-side interpretation before they are score factors.",
    },
    "camera_side_change": {
        "classification": _INTERPRETATION_LIMITATION_FACTOR,
        "required_landmarks": [
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
        ],
        "view_sensitivity": "high",
        "visibility_dependency": "medium",
        "annotation_fallback": "recording_metadata.camera_zone or annotation.note",
        "linked_compensation_candidates": [],
        "linked_feature_domain_entries": [],
        "basis": "A camera-facing direction change weakens side comparison and is best reported as a limitation.",
    },
    "hip_drop_to_pushup": {
        "classification": _POSE_DETECTABLE_SCORING_CANDIDATE,
        "required_landmarks": [
            "left_hip",
            "right_hip",
            "left_shoulder",
            "right_shoulder",
        ],
        "view_sensitivity": "medium",
        "visibility_dependency": "medium",
        "annotation_fallback": "failure_reason",
        "linked_compensation_candidates": ["hip_drop"],
        "linked_feature_domain_entries": [
            "control.trunk_stability",
            "spatial.depth_proxy",
        ],
        "basis": "Hip-height collapse changes the pike geometry and is observable from hip/shoulder landmarks.",
    },
    "head_forward_shift": {
        "classification": _POSE_DETECTABLE_SCORING_CANDIDATE,
        "required_landmarks": [
            "nose",
            "left_wrist",
            "right_wrist",
            "left_shoulder",
            "right_shoulder",
        ],
        "view_sensitivity": "medium",
        "visibility_dependency": "high",
        "annotation_fallback": "head_proxy note when nose is unstable",
        "linked_compensation_candidates": ["head_forward_shift"],
        "linked_feature_domain_entries": ["spatial.depth_proxy", "spatial.shape"],
        "basis": "Head trajectory relative to hand/shoulder landmarks can indicate forward drift.",
    },
    "elbow_flare": {
        "classification": _POSE_DETECTABLE_SCORING_CANDIDATE,
        "required_landmarks": [
            "left_shoulder",
            "right_shoulder",
            "left_elbow",
            "right_elbow",
            "left_wrist",
            "right_wrist",
        ],
        "view_sensitivity": "high",
        "visibility_dependency": "high",
        "annotation_fallback": None,
        "linked_compensation_candidates": ["elbow_flare"],
        "linked_feature_domain_entries": ["control.compensation", "spatial.alignment"],
        "basis": "Elbow line deviation is pose-readable but view and self-occlusion sensitive.",
    },
    "hand_foot_repositioning": {
        "classification": _ACQUISITION_CONTROL_FACTOR,
        "required_landmarks": [
            "left_wrist",
            "right_wrist",
            "left_ankle",
            "right_ankle",
        ],
        "view_sensitivity": "medium",
        "visibility_dependency": "high",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_candidates": [],
        "linked_feature_domain_entries": ["spatial.support_width"],
        "basis": "Support-point changes alter the task reference and should remain a protocol warning.",
    },
    "excessive_pelvic_rotation": {
        "classification": _POSE_DETECTABLE_SCORING_CANDIDATE,
        "required_landmarks": ["left_hip", "right_hip"],
        "view_sensitivity": "medium",
        "visibility_dependency": "medium",
        "annotation_fallback": None,
        "linked_compensation_candidates": ["pelvis_rotation", "trunk_rotation"],
        "linked_feature_domain_entries": [
            "control.compensation",
            "control.rotation_control",
        ],
        "basis": "Left-right hip depth asymmetry is a pose-based transverse-plane rotation proxy.",
    },
    "hip_height_drift": {
        "classification": _POSE_DETECTABLE_SCORING_CANDIDATE,
        "required_landmarks": ["left_hip", "right_hip"],
        "view_sensitivity": "medium",
        "visibility_dependency": "medium",
        "annotation_fallback": "set-level trend note",
        "linked_compensation_candidates": ["hip_drop", "hip_pike"],
        "linked_feature_domain_entries": [
            "control.trunk_stability",
            "control.stability",
        ],
        "basis": "Set-level hip-center vertical drift is visible when hip landmarks remain stable.",
    },
    "base_of_support_shift": {
        "classification": _ACQUISITION_CONTROL_FACTOR,
        "required_landmarks": [
            "left_wrist",
            "right_wrist",
            "left_ankle",
            "right_ankle",
        ],
        "view_sensitivity": "medium",
        "visibility_dependency": "high",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_candidates": [],
        "linked_feature_domain_entries": ["spatial.support_width"],
        "basis": "Support-width changes can be tracked but true contact changes remain acquisition-control issues.",
    },
    "side_order_error": {
        "classification": _ACQUISITION_CONTROL_FACTOR,
        "required_landmarks": [
            "left_wrist",
            "right_wrist",
            "left_shoulder",
            "right_shoulder",
        ],
        "view_sensitivity": "low",
        "visibility_dependency": "medium",
        "annotation_fallback": "annotation.starting_side and performance_protocol.side_sequence",
        "linked_compensation_candidates": ["left_right_timing_variability"],
        "linked_feature_domain_entries": ["temporal.left_right_timing_variability"],
        "basis": "Side-order errors are protocol-adherence warnings tied to side-role context.",
    },
    "missed_shoulder_tap": {
        "classification": _INTERPRETATION_LIMITATION_FACTOR,
        "required_landmarks": [
            "left_wrist",
            "right_wrist",
            "left_shoulder",
            "right_shoulder",
        ],
        "view_sensitivity": "high",
        "visibility_dependency": "high",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_candidates": [],
        "linked_feature_domain_entries": ["spatial.reach_distance"],
        "basis": "Wrist proximity can suggest a missed tap, but true shoulder contact is not proven by pose alone.",
    },
}


def _compensation_candidate_availability(
    candidate: str,
    *,
    has_rule: bool,
    declared_unimplemented: bool,
    deferred_feature_design: bool,
    control_compensation_enabled: bool,
) -> dict[str, Any]:
    """Return one availability-matrix row for a YAML compensation candidate."""
    if has_rule:
        status = "implemented_rule"
        next_action = "available_for_feature_extraction"
    elif declared_unimplemented:
        status = "declared_unimplemented"
        next_action = "implement_rule_or_keep_as_explicit_unimplemented_candidate"
    elif deferred_feature_design:
        status = "deferred_feature_design"
        next_action = "define_feature_rule_visibility_policy_and_test_fixture"
    else:
        status = "no_rule_registered"
        next_action = "register_rule_or_mark_as_deferred_feature_design"

    source_fields = [f"compensation_candidates.{candidate}"]
    if control_compensation_enabled:
        source_fields.append("feature_domains.control.compensation")

    return {
        "candidate": candidate,
        "availability_status": status,
        "emits_feature": has_rule,
        "report_reason": status,
        "source_fields": source_fields,
        "next_action": next_action,
    }


def audit_feature_registry(exercise_definition: Any) -> FeatureRegistryCoverageReport:
    """Report YAML feature-domain and compensation candidates without failing extraction."""
    from movement.features.compensation import COMPENSATION_RULES, _UNIMPLEMENTED

    feature_domains = getattr(exercise_definition, "feature_domains", None)
    report = FeatureRegistryCoverageReport(
        exercise_id=getattr(exercise_definition, "exercise_id", "unknown")
    )

    for domain in ("spatial", "temporal", "control"):
        entries = list(getattr(feature_domains, domain, []) or [])
        registry = _FEATURE_DOMAIN_EXTRACTOR_REGISTRY.get(domain, {})
        report.connected_feature_domain_entries.setdefault(domain, [])
        for entry in entries:
            if entry in registry:
                report.connected_feature_domain_entries[domain].append(entry)
            else:
                report.unsupported_feature_domain_entries.append(
                    {
                        "domain": domain,
                        "entry": entry,
                        "reason": "no_extractor_registered",
                    }
                )

    for domain, target_step in _FEATURE_DOMAIN_EXTERNAL_STEPS.items():
        entries = list(getattr(feature_domains, domain, []) or [])
        for entry in entries:
            report.external_step_feature_domain_entries.append(
                {
                    "domain": domain,
                    "entry": entry,
                    "target_step": target_step,
                }
            )

    control_entries = set(getattr(feature_domains, "control", []) or [])
    control_compensation_enabled = "compensation" in control_entries

    for candidate in list(
        getattr(exercise_definition, "compensation_candidates", []) or []
    ):
        if candidate in COMPENSATION_RULES:
            report.implemented_compensation_candidates.append(candidate)
        else:
            reason = (
                "declared_unimplemented"
                if candidate in _UNIMPLEMENTED
                else "no_rule_registered"
            )
            report.unimplemented_compensation_candidates.append(
                {
                    "candidate": candidate,
                    "reason": reason,
                }
            )
        report.compensation_candidate_availability.append(
            _compensation_candidate_availability(
                candidate,
                has_rule=candidate in COMPENSATION_RULES,
                declared_unimplemented=candidate in _UNIMPLEMENTED,
                deferred_feature_design=(
                    candidate in _DEFERRED_COMPENSATION_FEATURE_DESIGN
                ),
                control_compensation_enabled=control_compensation_enabled,
            )
        )

    return report


def audit_analysis_disrupting_patterns(
    exercise_definition: Any,
) -> AnalysisDisruptingPatternDetectabilityReport:
    """Classify analysis-disrupting patterns by joint-point detectability."""
    protocol = getattr(exercise_definition, "performance_protocol", None)
    patterns = list(getattr(protocol, "analysis_disrupting_patterns", []) or [])
    exercise_id = getattr(exercise_definition, "exercise_id", "unknown")

    report = AnalysisDisruptingPatternDetectabilityReport(exercise_id=exercise_id)
    declared_candidates = set(
        getattr(exercise_definition, "compensation_candidates", []) or []
    )

    for pattern in patterns:
        spec = _ANALYSIS_DISRUPTING_PATTERN_REGISTRY.get(pattern)
        if spec is None:
            item = {
                "pattern": pattern,
                "classification": _UNKNOWN_PATTERN,
                "required_landmarks": [],
                "view_sensitivity": "unknown",
                "visibility_dependency": "unknown",
                "annotation_fallback": None,
                "linked_compensation_candidates": [],
                "declared_linked_compensation_candidates": [],
                "linked_feature_domain_entries": [],
                "source_fields": [
                    f"performance_protocol.analysis_disrupting_patterns.{pattern}"
                ],
                "basis": "No detectability classification registered.",
            }
        else:
            linked_candidates = list(spec.get("linked_compensation_candidates", []))
            item = {
                "pattern": pattern,
                "classification": spec["classification"],
                "required_landmarks": list(spec.get("required_landmarks", [])),
                "view_sensitivity": spec.get("view_sensitivity", "unknown"),
                "visibility_dependency": spec.get("visibility_dependency", "unknown"),
                "annotation_fallback": spec.get("annotation_fallback"),
                "linked_compensation_candidates": linked_candidates,
                "declared_linked_compensation_candidates": [
                    candidate
                    for candidate in linked_candidates
                    if candidate in declared_candidates
                ],
                "linked_feature_domain_entries": list(
                    spec.get("linked_feature_domain_entries", [])
                ),
                "source_fields": [
                    f"performance_protocol.analysis_disrupting_patterns.{pattern}",
                    "landmarks",
                    "view_requirements",
                    "camera_protocol",
                ],
                "basis": spec.get("basis", ""),
            }

        report.all_patterns.append(item)
        classification = item["classification"]
        if classification == _POSE_DETECTABLE_SCORING_CANDIDATE:
            report.pose_detectable_scoring_candidates.append(item)
        elif classification == _ACQUISITION_CONTROL_FACTOR:
            report.acquisition_control_factors.append(item)
        elif classification == _INTERPRETATION_LIMITATION_FACTOR:
            report.interpretation_limitation_factors.append(item)
        else:
            report.unknown_patterns.append(item)

    return report


def _phase_source_fields(exercise_definition: Any) -> list[str]:
    """Return source_fields provenance entries for phase segmentation."""
    ps = getattr(exercise_definition, "phase_segmentation", None)
    if ps is None:
        return []
    return [
        "phase_segmentation.reference_landmark",
        "phase_segmentation.reference_axis",
        "phase_segmentation.split_logic",
    ]


def _emit_rep_level(
    df_rep: "pd.DataFrame",
    exercise_definition: Any,
    rep_id: int,
) -> "list[FeatureRecord]":
    """Compute all rep-level features (phase=None)."""
    from movement.features.control import compute_compensation, compute_stability
    from movement.features.spatial import compute_rom, compute_shape, compute_symmetry

    records: list[FeatureRecord] = []
    records += compute_rom(df_rep, exercise_definition, rep_id=rep_id)
    records += compute_symmetry(df_rep, exercise_definition, rep_id=rep_id)
    records += compute_shape(df_rep, exercise_definition, rep_id=rep_id)
    records += compute_stability(df_rep, exercise_definition, rep_id=rep_id)
    # Compensation is always rep-level (candidates span phase boundaries)
    records += compute_compensation(df_rep, exercise_definition, rep_id=rep_id)
    return records


def _emit_phase_level(
    df_phase: "pd.DataFrame",
    exercise_definition: Any,
    rep_id: int,
    phase_label: str,
) -> "list[FeatureRecord]":
    """
    Compute phase-level features for one (rep_id, phase) segment.

    Only PHASE_AWARE_FEATURE_FAMILIES are computed at phase level; others stay
    rep-level only.  Each feature_id gets a lowercased phase suffix so that
    rep-level and phase-level IDs remain distinct in the baseline namespace.
    """
    from movement.features.spatial import compute_rom, compute_shape
    from movement.features.control import compute_stability
    from movement.features.temporal import compute_tempo

    if len(df_phase) == 0:
        return []

    phase_suffix = "." + phase_label.lower()
    ps_fields = _phase_source_fields(exercise_definition)

    records: list[FeatureRecord] = []

    for rec in compute_rom(df_phase, exercise_definition, rep_id=rep_id):
        records.append(
            FeatureRecord(
                feature_id=rec.feature_id + phase_suffix,
                exercise_id=rec.exercise_id,
                rep_id=rep_id,
                value=rec.value,
                unit=rec.unit,
                source_fields=rec.source_fields + ps_fields,
                note=rec.note,
                phase=phase_label,
            )
        )

    for rec in compute_shape(df_phase, exercise_definition, rep_id=rep_id):
        records.append(
            FeatureRecord(
                feature_id=rec.feature_id + phase_suffix,
                exercise_id=rec.exercise_id,
                rep_id=rep_id,
                value=rec.value,
                unit=rec.unit,
                source_fields=rec.source_fields + ps_fields,
                note=rec.note,
                phase=phase_label,
            )
        )

    for rec in compute_stability(df_phase, exercise_definition, rep_id=rep_id):
        records.append(
            FeatureRecord(
                feature_id=rec.feature_id + phase_suffix,
                exercise_id=rec.exercise_id,
                rep_id=rep_id,
                value=rec.value,
                unit=rec.unit,
                source_fields=rec.source_fields + ps_fields,
                note=rec.note,
                phase=phase_label,
            )
        )

    for rec in compute_tempo(df_phase, exercise_definition, rep_id=rep_id):
        records.append(
            FeatureRecord(
                feature_id=rec.feature_id + phase_suffix,
                exercise_id=rec.exercise_id,
                rep_id=rep_id,
                value=rec.value,
                unit=rec.unit,
                source_fields=rec.source_fields + ps_fields,
                note=rec.note,
                phase=phase_label,
            )
        )

    return records


def extract_rep_features(
    df: "pd.DataFrame",
    exercise_definition: Any,
) -> "list[FeatureRecord]":
    """
    Extract spatial, temporal, and control features per rep (and optionally per phase).

    Rep boundaries are read from annotation columns (segment_type, rep_id).
    When annotation columns are absent, all features are computed sequence-level.

    When the `phase` column is populated by ⑦ Segmentation, features
    in PHASE_AWARE_FEATURE_FAMILIES are also emitted for each (rep_id, phase)
    segment.  The rep-level records (phase=None) are always emitted regardless.

    Per-rep features (one record per rep_id, phase=None):
        spatial  : ROM, symmetry, trajectory shape
        control  : CoM stability, compensation arc length

    Phase-level features (one record per rep_id × phase, when phase column is set):
        spatial  : ROM, trajectory shape (per Descent/Ascent/etc.)
        control  : CoM stability (per phase)

    Sequence-level features (rep_id = None):
        temporal : tempo per rep, inter-rep variability (requires ≥ 2 reps)
        spatial  : symmetry, shape over the full sequence (when no reps found)

    Parameters
    ----------
    df : pd.DataFrame
        Normalized pose dataframe. Must contain <landmark>_norm_x/y/z columns.
    exercise_definition : ExerciseDefinition

    Returns
    -------
    list[FeatureRecord]
    """
    from movement.features.temporal import compute_tempo, compute_variability

    records: list[FeatureRecord] = []

    has_annotation = "segment_type" in df.columns and "rep_id" in df.columns
    has_phase = (
        has_annotation
        and "phase" in df.columns
        and df.loc[df["segment_type"] == "rep", "phase"].notna().any()
    )

    rep_ids: list = []
    if has_annotation:
        rep_mask = df["segment_type"] == "rep"
        rep_ids = sorted(df.loc[rep_mask, "rep_id"].dropna().unique())

    if rep_ids:
        for rep_id in rep_ids:
            mask = (df["segment_type"] == "rep") & (df["rep_id"] == rep_id)
            df_rep = df.loc[mask]
            rid = int(rep_id)

            # Always emit rep-level features
            records += _emit_rep_level(df_rep, exercise_definition, rid)

            # Emit phase-level features when the phase column is populated for this rep
            if has_phase:
                rep_phases = df_rep["phase"].dropna().unique()
                for phase_label in sorted(rep_phases):
                    df_phase = df_rep.loc[df_rep["phase"] == phase_label]
                    records += _emit_phase_level(
                        df_phase, exercise_definition, rid, str(phase_label)
                    )

        # Temporal features span multiple reps — computed on the full df
        records += compute_tempo(df, exercise_definition)
        records += compute_variability(df, exercise_definition)
    else:
        # No rep annotation: sequence-level fallback
        from movement.features.spatial import (
            compute_rom,
            compute_shape,
            compute_symmetry,
        )
        from movement.features.control import compute_compensation, compute_stability

        records += compute_rom(df, exercise_definition)
        records += compute_symmetry(df, exercise_definition)
        records += compute_shape(df, exercise_definition)
        records += compute_stability(df, exercise_definition)
        records += compute_compensation(df, exercise_definition)

    feature_context = resolve_feature_context(df, exercise_definition)
    records = apply_feature_context(records, feature_context)
    return annotate_feature_availability(records, df, exercise_definition)


def summarize_phase_to_rep(records: "list[FeatureRecord]") -> "list[FeatureRecord]":
    """
    Derive rep-level summary features from phase-level FeatureRecords.

    Dissertation §5.5: hierarchical summary structure.

    Currently computes:
        - Descent/Ascent duration ratio  (requires temporal.tempo phase-level records)
        - Phase ROM asymmetry            (Descent vs Ascent mean ROM difference)

    Parameters
    ----------
    records : list[FeatureRecord]
        Mixed list of rep-level and phase-level records.

    Returns
    -------
    list[FeatureRecord]
        New summary records only (not a copy of the input).
    """
    phase_recs = [r for r in records if r.phase is not None]
    if not phase_recs:
        return []

    summary: list[FeatureRecord] = []

    # Group by (exercise_id, rep_id) for per-rep summaries
    from itertools import groupby

    def _key(r: FeatureRecord) -> tuple:
        return (r.exercise_id, r.rep_id)

    phase_recs_sorted = sorted(phase_recs, key=_key)

    for (ex_id, rep_id), group_iter in groupby(phase_recs_sorted, key=_key):
        group = list(group_iter)

        # Descent vs Ascent mean ROM ratio
        descent_rom = [
            r.value
            for r in group
            if r.phase == "Descent" and "spatial.rom" in r.feature_id
        ]
        ascent_rom = [
            r.value
            for r in group
            if r.phase == "Ascent" and "spatial.rom" in r.feature_id
        ]

        if descent_rom and ascent_rom:
            mean_d = sum(descent_rom) / len(descent_rom)
            mean_a = sum(ascent_rom) / len(ascent_rom)
            ratio = mean_d / mean_a if mean_a > 0 else 1.0
            ps_fields = [
                r.source_fields for r in group if r.phase in ("Descent", "Ascent")
            ]
            merged_fields = list(dict.fromkeys(f for sf in ps_fields for f in sf))
            if not merged_fields:
                merged_fields = ["phase_segmentation.phase_sequence"]
            summary.append(
                FeatureRecord(
                    feature_id="spatial.phase_rom_ratio.descent_ascent",
                    exercise_id=ex_id,
                    rep_id=rep_id,
                    value=round(ratio, 4),
                    unit="dimensionless",
                    source_fields=merged_fields,
                    note=(
                        "Ratio of mean Descent ROM to mean Ascent ROM per rep. "
                        "Values > 1 indicate larger descent range of motion."
                    ),
                    phase=None,
                )
            )

    return summary


def features_to_dataframe(records: "list[FeatureRecord]") -> "pd.DataFrame":
    """
    Convert a list of FeatureRecord objects to a tidy DataFrame.

    Columns include value/unit provenance plus view reliability and availability.
    source_fields and availability_reasons are serialized as pipe-joined strings
    for tabular compatibility.
    Returns an empty DataFrame (with schema columns) when records is empty.
    """
    import pandas as pd

    if not records:
        return pd.DataFrame(
            columns=[
                "feature_id",
                "exercise_id",
                "rep_id",
                "phase",
                "value",
                "unit",
                "source_fields",
                "note",
                "view_reliability",
                "availability",
                "availability_reasons",
                "camera_zone",
                "role_context",
                "depth_dependency",
                "model_depth_reliability",
                "landmark_quality",
            ]
        )

    rows = [
        {
            "feature_id": r.feature_id,
            "exercise_id": r.exercise_id,
            "rep_id": r.rep_id,
            "phase": r.phase,
            "value": r.value,
            "unit": r.unit,
            "source_fields": "|".join(r.source_fields),
            "note": r.note,
            "view_reliability": r.view_reliability,
            "availability": r.availability,
            "availability_reasons": "|".join(r.availability_reasons),
            "camera_zone": r.camera_zone,
            "role_context": r.role_context,
            "depth_dependency": r.depth_dependency,
            "model_depth_reliability": r.model_depth_reliability,
            "landmark_quality": r.landmark_quality,
        }
        for r in records
    ]
    return pd.DataFrame(rows)


__all__ = [
    "AnalysisDisruptingPatternDetectabilityReport",
    "FeatureContext",
    "FeatureRecord",
    "FeatureRegistryCoverageReport",
    "PHASE_AWARE_FEATURE_FAMILIES",
    "annotate_feature_availability",
    "apply_feature_context",
    "audit_analysis_disrupting_patterns",
    "audit_feature_registry",
    "extract_rep_features",
    "resolve_feature_context",
    "summarize_phase_to_rep",
    "features_to_dataframe",
]
