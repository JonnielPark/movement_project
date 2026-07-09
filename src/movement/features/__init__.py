"""
⑦ Feature Extraction

Computes spatial, temporal, and control domain features from normalized pose data.
Each feature is returned as a FeatureRecord with value, unit, and explicit
operational metadata for downstream biomarker derivation (⑨). Optional
source_fields may be carried as audit references for reports/debug exports.

When the `phase` column is populated by ⑥ Segmentation, features are
emitted at both rep-level (phase=None) and phase-level (phase='Descent', etc.),
enabling the hierarchical analysis structure described in dissertation §5.5.

Submodules:
    features.spatial   → range of motion, role alignment, movement path, support consistency
    features.temporal  → tempo, inter-rep variability
    features.control   → CoM stability, compensation movements

Coordinate convention : (T, J, 3) = (frame, joint_index, xyz).
Column convention     : <landmark>_norm_x/y/z (normalized coordinates).
Unit convention       : torso_length_ratio (dimensionless) or degree.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from movement.record_metadata import (
    COMMON_RECORD_METADATA_FIELDS,
    EVALUATION_DOMAINS,
    EVIDENCE_AXES,
    apply_common_record_metadata,
)

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class FeatureRecord:
    """Single feature computation result.

    Parameters
    ----------
    feature_id    : unique identifier (e.g. 'spatial.range_of_motion.xy.left_knee')
                    Phase-level records append a phase suffix:
                    'spatial.range_of_motion.xy.left_knee.descent'
    exercise_id   : exercise identifier
    rep_id        : rep number (None = sequence-level feature)
    value         : feature value
    unit          : torso_length_ratio | degree | second | dimensionless_cv
    source_fields : optional audit references for reports/debug exports.
    note          : optional interpretation note
    phase         : kinematic phase label (None = rep-level; 'Descent' etc. = phase-level)
    depth_dependency : dependency on monocular depth inference, separate from
                    camera-zone view reliability
    model_depth_reliability : pose-estimator depth confidence for this recording
    landmark_quality : feature-level landmark evidence summary
    focus_tier     : scoring-intent tier derived from the exercise definition
                    (primary, secondary, context_constraint, compensation,
                    diagnostic)
    landmark_ids   : canonical landmark ids represented by this record
    support_role   : support/proxy role of the represented landmark
    coordinate_reference : coordinate family used by the feature
    evaluation_domain : scoring/evaluation evidence domain
    evidence_axes  : coordinate axes used by the calculation
    feature_family : broad feature family used by scoring and audits
    quality_gravity : quality-trust multiplier for promoted analysis evidence
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
    focus_tier: str = "primary"
    landmark_ids: list[str] = field(default_factory=list)
    support_role: str | None = None
    coordinate_reference: str = "unknown"
    evaluation_domain: str = "unknown"
    evidence_axes: str | None = None
    feature_family: str | None = None
    quality_gravity: float = 1.0

    def __post_init__(self) -> None:
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
        if self.quality_gravity < 0.0 or self.quality_gravity > 1.0:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': quality_gravity must be "
                f"between 0 and 1; got {self.quality_gravity}."
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
        valid_focus_tiers = {
            "primary",
            "secondary",
            "context_constraint",
            "compensation",
            "diagnostic",
        }
        if self.focus_tier not in valid_focus_tiers:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': invalid focus_tier "
                f"{self.focus_tier!r}."
            )
        if self.evaluation_domain not in EVALUATION_DOMAINS:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': invalid evaluation_domain "
                f"{self.evaluation_domain!r}."
            )
        if self.evidence_axes is not None and self.evidence_axes not in EVIDENCE_AXES:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': invalid evidence_axes "
                f"{self.evidence_axes!r}."
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
    implemented_compensation_patterns: list[str] = field(default_factory=list)
    unimplemented_compensation_patterns: list[dict[str, Any]] = field(
        default_factory=list
    )
    compensation_pattern_availability: list[dict[str, Any]] = field(
        default_factory=list
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "exercise_id": self.exercise_id,
            "connected_feature_domain_entries": self.connected_feature_domain_entries,
            "unsupported_feature_domain_entries": self.unsupported_feature_domain_entries,
            "external_step_feature_domain_entries": self.external_step_feature_domain_entries,
            "implemented_compensation_patterns": self.implemented_compensation_patterns,
            "unimplemented_compensation_patterns": self.unimplemented_compensation_patterns,
            "compensation_pattern_availability": self.compensation_pattern_availability,
        }


@dataclass
class AnalysisDisruptingPatternDetectabilityReport:
    """Detectability audit for performance_protocol.analysis_disrupting_patterns."""

    exercise_id: str
    pose_detectable_score_features: list[dict[str, Any]] = field(default_factory=list)
    acquisition_control_factors: list[dict[str, Any]] = field(default_factory=list)
    interpretation_limitation_factors: list[dict[str, Any]] = field(
        default_factory=list
    )
    unknown_patterns: list[dict[str, Any]] = field(default_factory=list)
    all_patterns: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "exercise_id": self.exercise_id,
            "pose_detectable_score_features": self.pose_detectable_score_features,
            "acquisition_control_factors": self.acquisition_control_factors,
            "interpretation_limitation_factors": self.interpretation_limitation_factors,
            "unknown_patterns": self.unknown_patterns,
            "all_patterns": self.all_patterns,
        }


# ── Phase-aware feature families ─────────────────────────────────────────────
# These feature families are computed per (rep_id, phase) when the phase column
# is populated.  control.compensation is rep-level only because compensation
# patterns span the full rep trajectory (crossing phase boundaries).

PHASE_AWARE_FEATURE_FAMILIES: frozenset[str] = frozenset(
    {
        "spatial.range_of_motion",
        "spatial.movement_path",
        "spatial.support_consistency",
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
            role_context={"role_alignment_context": "bilateral_symmetric"},
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
            context_reasons=["bilateral_asymmetric_requires_side_bias_feature_policy"],
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
        return record.feature_id.startswith("spatial.role_alignment.")

    if feature_context.role_mode == "active_side":
        if feature_context.role_confidence != "assessed":
            return False
        is_side_specific = (
            ".left" in record.feature_id
            or ".right" in record.feature_id
            or ".left_" in record.feature_id
            or ".right_" in record.feature_id
        )
        return (
            record.feature_id.startswith("control.compensation.") and is_side_specific
        )

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
    if feature_id.startswith("spatial.role_alignment.left_right.support_consistency_"):
        aliases.extend(
            [
                "support_consistency",
                "step_width",
                "centerline_stability",
                "foot_contact",
            ]
        )
    elif feature_id.startswith("spatial.role_alignment."):
        aliases.extend(
            [
                "role_alignment",
                "bilateral_symmetry",
                "upper_limb_symmetry",
                "side_to_side_comparison",
            ]
        )
    elif feature_id.startswith(
        ("spatial.range_of_motion.xy.", "spatial.range_of_motion.xyz.")
    ):
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
        aliases.append("range_of_motion")
    elif feature_id.startswith("spatial.movement_path."):
        aliases.extend(
            ["active_hand_trajectory", "hip_position", "depth", "step_length"]
        )
    elif feature_id.startswith("spatial.support_consistency."):
        aliases.extend(
            [
                "support_consistency",
                "step_width",
                "centerline_stability",
                "foot_contact",
            ]
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
    if feature_id.startswith("spatial.range_of_motion.xy."):
        return "none"
    if feature_id.startswith("spatial.range_of_motion.xyz."):
        return "moderate"
    if "spatial.movement_path.arc_length_xyz." in feature_id:
        return "high"
    if "spatial.movement_path.arc_length_xy." in feature_id:
        return "none"
    if "spatial.movement_path.axis_path_z." in feature_id:
        return "high"
    if feature_id.startswith("temporal."):
        return "none"
    if feature_id.startswith("control.compensation.heel_lift"):
        return "none"
    if feature_id.startswith("control.compensation.pelvis_rotation"):
        return "high"
    if feature_id.startswith("control.compensation.excessive_trunk_flexion.xyz"):
        return "moderate"
    if ".xyz" in feature_id and feature_id.startswith("control.compensation."):
        return "high"
    normalized_tokens = f".{feature_id.lower()}."
    if ".xy." in normalized_tokens and feature_id.startswith("control.compensation."):
        return "none"

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
        "range_of_motion",
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

    if feature_id.startswith("spatial.role_alignment."):
        return "high"
    if feature_id.startswith("control.stability."):
        return "moderate"
    if feature_id.startswith("control.compensation.pelvis_rotation"):
        return "high"
    if feature_id.startswith("control.compensation.knee_"):
        return "none"
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


def _downgrade_availability(current: str, new_value: str) -> str:
    rank = {"assessed": 0, "low_confidence": 1, "not_assessed": 2}
    return new_value if rank[new_value] > rank[current] else current


def _feature_id_mentions_any(feature_id: str, tokens: Iterable[str]) -> bool:
    normalized = feature_id.lower()
    for token in tokens:
        key = str(token).strip().lower()
        if key and key in normalized:
            return True
    return False


def _focus_tokens(exercise_definition: Any, group: str) -> list[str]:
    landmarks = getattr(exercise_definition, "landmarks", None)
    joint_actions = getattr(exercise_definition, "joint_actions", {}) or {}
    biomech = getattr(exercise_definition, "biomechanical_focus", None)

    tokens: list[str] = []
    if group == "primary":
        tokens.extend(getattr(landmarks, "primary_joints", []) or [])
        tokens.extend(getattr(exercise_definition, "primary_body_regions", []) or [])
        tokens.extend(getattr(biomech, "main_load_regions", []) or [])
    elif group == "secondary":
        tokens.extend(getattr(landmarks, "secondary_joints", []) or [])

    for action in joint_actions.get(group, []) or []:
        tokens.extend(str(action).split("_"))
        tokens.append(str(action))

    return _unique_preserve_order([str(token) for token in tokens if str(token)])


def _feature_focus_tier(record: FeatureRecord, exercise_definition: Any) -> str:
    """Infer scoring-intent tier from explicit record identifiers and metadata."""

    feature_id = record.feature_id
    reasons = set(record.availability_reasons)

    if (
        "axis_path_" in feature_id
        or "axis_diagnostic" in feature_id
        or any("diagnostic_report_only" in reason for reason in reasons)
    ):
        return "diagnostic"

    if feature_id.startswith("control.compensation."):
        return "compensation"

    if feature_id.startswith("spatial.support_consistency.") or feature_id.startswith(
        "spatial.role_alignment.left_right.support_consistency_"
    ):
        return "context_constraint"

    if _feature_id_mentions_any(
        feature_id, _focus_tokens(exercise_definition, "primary")
    ):
        return "primary"

    if _feature_id_mentions_any(
        feature_id, _focus_tokens(exercise_definition, "secondary")
    ):
        return "secondary"

    # Preserve legacy behavior for generic feature records whose intent has not
    # yet been classified by the exercise definition.
    return "primary"


_SELF_REFERENCE_CONTROL_FEATURE_PREFIXES: tuple[str, ...] = (
    "control.stability.hip_center_x_std",
    "control.stability.hip_center_z_std",
    "control.compensation.lateral_pelvic_shift",
)


def _is_self_reference_control_feature(feature_id: str) -> bool:
    return feature_id.startswith(_SELF_REFERENCE_CONTROL_FEATURE_PREFIXES)


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
        record.focus_tier = _feature_focus_tier(record, exercise_definition)
        if _is_self_reference_control_feature(record.feature_id):
            record.availability = "not_assessed"
            record.focus_tier = "diagnostic"
            record.availability_reasons = _unique_preserve_order(
                list(record.availability_reasons)
                + ["coordinate_reference_self_measurement"]
            )
        apply_common_record_metadata(record, exercise_definition=exercise_definition)

    return records


_FEATURE_DOMAIN_EXTRACTOR_REGISTRY: dict[str, dict[str, str]] = {
    "spatial": {
        "range_of_motion": "compute_range_of_motion",
        "role_alignment": "compute_role_alignment",
        "movement_path": "compute_movement_path",
        "support_consistency": "compute_support_consistency",
        "phase_profile": "summarize_phase_to_rep",
    },
    "temporal": {
        "tempo": "compute_tempo",
        "rep_duration": "compute_tempo",
        "variability": "compute_variability",
        "phase_profile": "summarize_phase_to_rep",
    },
    "control": {
        "stability": "compute_stability",
        "com_stability": "compute_stability",
        "compensation": "compute_compensation",
    },
}
_FEATURE_DOMAIN_EXTERNAL_STEPS: dict[str, str] = {
    "biomechanical_proxy": "08_biomechanical_proxy",
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

_POSE_DETECTABLE_SCORE_FEATURE = "pose_detectable_score_feature"
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
        "confidence_dependency": "medium",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_patterns": [],
        "linked_feature_domain_entries": [],
        "basis": (
            "Arm motion has observable confidence, but whether it assists the movement cannot be "
            "proven from pose trajectories alone."
        ),
    },
    "heel_lift": {
        "classification": _POSE_DETECTABLE_SCORE_FEATURE,
        "required_landmarks": ["left_heel", "right_heel", "left_ankle", "right_ankle"],
        "view_sensitivity": "medium",
        "confidence_dependency": "high",
        "annotation_fallback": None,
        "linked_compensation_patterns": ["heel_lift"],
        "linked_feature_domain_entries": ["control.compensation"],
        "basis": "Heel vertical displacement can be estimated when heel landmark confidence is sufficient.",
    },
    "unstable_foot_contact": {
        "classification": _ACQUISITION_CONTROL_FACTOR,
        "required_landmarks": ["left_ankle", "right_ankle", "left_heel", "right_heel"],
        "view_sensitivity": "medium",
        "confidence_dependency": "high",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_patterns": [],
        "linked_feature_domain_entries": ["spatial.support_width"],
        "basis": (
            "Foot landmark motion can suggest support changes, but true floor contact "
            "and landmark jitter are hard to separate."
        ),
    },
    "excessive_knee_deviation": {
        "classification": _POSE_DETECTABLE_SCORE_FEATURE,
        "required_landmarks": [
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_ankle",
            "right_ankle",
        ],
        "view_sensitivity": "high",
        "confidence_dependency": "medium",
        "annotation_fallback": None,
        "linked_compensation_patterns": ["knee_valgus", "knee_varus"],
        "linked_feature_domain_entries": ["control.compensation", "spatial.alignment"],
        "basis": "Knee deviation can map to frontal-plane valgus or varus proxies.",
    },
    "inconsistent_depth": {
        "classification": _POSE_DETECTABLE_SCORE_FEATURE,
        "required_landmarks": ["hip_center", "left_hip", "right_hip"],
        "view_sensitivity": "medium",
        "confidence_dependency": "medium",
        "annotation_fallback": "rep_segmentation.report",
        "linked_compensation_patterns": [
            "asymmetric_depth",
            "insufficient_head_descent",
        ],
        "linked_feature_domain_entries": [
            "spatial.depth_proxy",
            "spatial.range_of_motion",
        ],
        "basis": "Depth variation is pose-detectable when rep boundaries and reference landmarks are stable.",
    },
    "excessive_trunk_flexion": {
        "classification": _POSE_DETECTABLE_SCORE_FEATURE,
        "required_landmarks": [
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
        ],
        "view_sensitivity": "medium",
        "confidence_dependency": "medium",
        "annotation_fallback": None,
        "linked_compensation_patterns": ["excessive_trunk_flexion"],
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
        "confidence_dependency": "high",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_patterns": ["unstable_step_width"],
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
        "confidence_dependency": "medium",
        "annotation_fallback": "recording_metadata.camera_zone or annotation.note",
        "linked_compensation_patterns": [],
        "linked_feature_domain_entries": [],
        "basis": "A camera-facing direction change weakens side comparison and is best reported as a limitation.",
    },
    "hip_drop_to_pushup": {
        "classification": _POSE_DETECTABLE_SCORE_FEATURE,
        "required_landmarks": [
            "left_hip",
            "right_hip",
            "left_shoulder",
            "right_shoulder",
        ],
        "view_sensitivity": "medium",
        "confidence_dependency": "medium",
        "annotation_fallback": "failure_reason",
        "linked_compensation_patterns": ["hip_drop"],
        "linked_feature_domain_entries": [
            "control.trunk_stability",
            "spatial.depth_proxy",
        ],
        "basis": "Hip-height collapse changes the pike geometry and is observable from hip/shoulder landmarks.",
    },
    "head_forward_shift": {
        "classification": _POSE_DETECTABLE_SCORE_FEATURE,
        "required_landmarks": [
            "nose",
            "left_wrist",
            "right_wrist",
            "left_shoulder",
            "right_shoulder",
        ],
        "view_sensitivity": "medium",
        "confidence_dependency": "high",
        "annotation_fallback": "head_proxy note when nose is unstable",
        "linked_compensation_patterns": ["head_forward_shift"],
        "linked_feature_domain_entries": [
            "spatial.depth_proxy",
            "spatial.movement_path",
        ],
        "basis": "Head trajectory relative to hand/shoulder landmarks can indicate forward drift.",
    },
    "elbow_flare": {
        "classification": _POSE_DETECTABLE_SCORE_FEATURE,
        "required_landmarks": [
            "left_shoulder",
            "right_shoulder",
            "left_elbow",
            "right_elbow",
            "left_wrist",
            "right_wrist",
        ],
        "view_sensitivity": "high",
        "confidence_dependency": "high",
        "annotation_fallback": None,
        "linked_compensation_patterns": ["elbow_flare"],
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
        "confidence_dependency": "high",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_patterns": [],
        "linked_feature_domain_entries": ["spatial.support_width"],
        "basis": "Support-point changes alter the task reference and should remain a protocol warning.",
    },
    "excessive_pelvic_rotation": {
        "classification": _POSE_DETECTABLE_SCORE_FEATURE,
        "required_landmarks": ["left_hip", "right_hip"],
        "view_sensitivity": "medium",
        "confidence_dependency": "medium",
        "annotation_fallback": None,
        "linked_compensation_patterns": ["pelvis_rotation", "trunk_rotation"],
        "linked_feature_domain_entries": [
            "control.compensation",
            "control.rotation_control",
        ],
        "basis": "Left-right hip depth asymmetry is a pose-based transverse-plane rotation proxy.",
    },
    "hip_height_drift": {
        "classification": _POSE_DETECTABLE_SCORE_FEATURE,
        "required_landmarks": ["left_hip", "right_hip"],
        "view_sensitivity": "medium",
        "confidence_dependency": "medium",
        "annotation_fallback": "set-level trend note",
        "linked_compensation_patterns": ["hip_drop", "hip_pike"],
        "linked_feature_domain_entries": [
            "control.trunk_stability",
            "control.stability",
        ],
        "basis": "Set-level hip-center vertical drift is interpretable when hip landmarks remain stable.",
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
        "confidence_dependency": "high",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_patterns": [],
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
        "confidence_dependency": "medium",
        "annotation_fallback": "annotation.starting_side and performance_protocol.side_sequence",
        "linked_compensation_patterns": ["left_right_timing_variability"],
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
        "confidence_dependency": "high",
        "annotation_fallback": "annotation.note or video_review",
        "linked_compensation_patterns": [],
        "linked_feature_domain_entries": ["spatial.reach_distance"],
        "basis": "Wrist proximity can suggest a missed tap, but true shoulder contact is not proven by pose alone.",
    },
}


def _compensation_pattern_availability(
    pattern: str,
    *,
    has_rule: bool,
    declared_unimplemented: bool,
    deferred_feature_design: bool,
    control_compensation_enabled: bool,
) -> dict[str, Any]:
    """Return one availability-matrix row for a YAML compensation pattern."""
    if has_rule:
        status = "implemented_rule"
        next_action = "available_for_feature_extraction"
    elif declared_unimplemented:
        status = "declared_unimplemented"
        next_action = "implement_rule_or_keep_as_explicit_unimplemented_pattern"
    elif deferred_feature_design:
        status = "deferred_feature_design"
        next_action = "define_feature_rule_confidence_policy_and_test_fixture"
    else:
        status = "no_rule_registered"
        next_action = "register_rule_or_mark_as_deferred_feature_design"

    source_fields = [f"compensation_patterns.{pattern}"]
    if control_compensation_enabled:
        source_fields.append("feature_domains.control.compensation")

    return {
        "pattern": pattern,
        "availability_status": status,
        "emits_feature": has_rule,
        "report_reason": status,
        "source_fields": source_fields,
        "next_action": next_action,
    }


def audit_feature_registry(exercise_definition: Any) -> FeatureRegistryCoverageReport:
    """Report YAML feature-domain and compensation patterns without failing extraction."""
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

    for pattern in list(
        getattr(exercise_definition, "compensation_patterns", []) or []
    ):
        if pattern in COMPENSATION_RULES:
            report.implemented_compensation_patterns.append(pattern)
        else:
            reason = (
                "declared_unimplemented"
                if pattern in _UNIMPLEMENTED
                else "no_rule_registered"
            )
            report.unimplemented_compensation_patterns.append(
                {
                    "pattern": pattern,
                    "reason": reason,
                }
            )
        report.compensation_pattern_availability.append(
            _compensation_pattern_availability(
                pattern,
                has_rule=pattern in COMPENSATION_RULES,
                declared_unimplemented=pattern in _UNIMPLEMENTED,
                deferred_feature_design=(
                    pattern in _DEFERRED_COMPENSATION_FEATURE_DESIGN
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
    declared_patterns = set(
        getattr(exercise_definition, "compensation_patterns", []) or []
    )

    for pattern in patterns:
        spec = _ANALYSIS_DISRUPTING_PATTERN_REGISTRY.get(pattern)
        if spec is None:
            item = {
                "pattern": pattern,
                "classification": _UNKNOWN_PATTERN,
                "required_landmarks": [],
                "view_sensitivity": "unknown",
                "confidence_dependency": "unknown",
                "annotation_fallback": None,
                "linked_compensation_patterns": [],
                "declared_linked_compensation_patterns": [],
                "linked_feature_domain_entries": [],
                "source_fields": [
                    f"performance_protocol.analysis_disrupting_patterns.{pattern}"
                ],
                "basis": "No detectability classification registered.",
            }
        else:
            linked_patterns = list(spec.get("linked_compensation_patterns", []))
            item = {
                "pattern": pattern,
                "classification": spec["classification"],
                "required_landmarks": list(spec.get("required_landmarks", [])),
                "view_sensitivity": spec.get("view_sensitivity", "unknown"),
                "confidence_dependency": spec.get("confidence_dependency", "unknown"),
                "annotation_fallback": spec.get("annotation_fallback"),
                "linked_compensation_patterns": linked_patterns,
                "declared_linked_compensation_patterns": [
                    pattern
                    for pattern in linked_patterns
                    if pattern in declared_patterns
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
        if classification == _POSE_DETECTABLE_SCORE_FEATURE:
            report.pose_detectable_score_features.append(item)
        elif classification == _ACQUISITION_CONTROL_FACTOR:
            report.acquisition_control_factors.append(item)
        elif classification == _INTERPRETATION_LIMITATION_FACTOR:
            report.interpretation_limitation_factors.append(item)
        else:
            report.unknown_patterns.append(item)

    return report


def _phase_source_fields(exercise_definition: Any) -> list[str]:
    """Return optional audit references for phase segmentation."""
    ps = getattr(exercise_definition, "phase_segmentation", None)
    if ps is None:
        return []
    return [
        "phase_segmentation.reference_landmark",
        "phase_segmentation.reference_axis",
        "phase_segmentation.split_logic",
    ]


def _has_depth_axis(df: Any) -> bool:
    """Return True when normalized or raw z coordinates are available."""
    columns = [str(column) for column in getattr(df, "columns", [])]
    norm_z_columns = [column for column in columns if column.endswith("_norm_z")]
    if any(column.endswith("_norm_x") for column in columns):
        if not norm_z_columns:
            return False
        values = df[norm_z_columns].astype(float).to_numpy()
        return bool(np.isfinite(values).any())
    raw_z_columns = [
        column
        for column in columns
        if column.endswith("_z")
        and "_norm_" not in column
        and "_canon_" not in column
        and "_corrected_3d_hypothesis_" not in column
    ]
    if not raw_z_columns:
        return False
    values = df[raw_z_columns].astype(float).to_numpy()
    return bool(np.isfinite(values).any())


def _emit_rep_level(
    df_rep: "pd.DataFrame",
    exercise_definition: Any,
    rep_id: int,
) -> "list[FeatureRecord]":
    """Compute all rep-level features (phase=None)."""
    from movement.features.control import compute_compensation, compute_stability
    from movement.features.spatial import (
        compute_range_of_motion,
        compute_movement_path,
        compute_support_consistency,
        compute_role_alignment,
    )

    records: list[FeatureRecord] = []
    records += compute_range_of_motion(df_rep, exercise_definition, rep_id=rep_id)
    records += compute_role_alignment(df_rep, exercise_definition, rep_id=rep_id)
    records += compute_movement_path(df_rep, exercise_definition, rep_id=rep_id)
    records += compute_support_consistency(df_rep, exercise_definition, rep_id=rep_id)
    if _has_depth_axis(df_rep):
        records += compute_stability(df_rep, exercise_definition, rep_id=rep_id)
        # Compensation is always rep-level (patterns span phase boundaries)
        records += compute_compensation(df_rep, exercise_definition, rep_id=rep_id)
    return records


def _with_phase(
    rec: FeatureRecord,
    *,
    phase_suffix: str,
    phase_label: str,
    phase_source_fields: list[str],
) -> FeatureRecord:
    """Return a phase-level copy while preserving feature metadata."""

    return FeatureRecord(
        feature_id=rec.feature_id + phase_suffix,
        exercise_id=rec.exercise_id,
        rep_id=rec.rep_id,
        value=rec.value,
        unit=rec.unit,
        source_fields=_unique_preserve_order(rec.source_fields + phase_source_fields),
        note=rec.note,
        phase=phase_label,
        view_reliability=rec.view_reliability,
        availability=rec.availability,
        availability_reasons=list(rec.availability_reasons),
        camera_zone=rec.camera_zone,
        role_context=dict(rec.role_context) if rec.role_context else None,
        depth_dependency=rec.depth_dependency,
        model_depth_reliability=rec.model_depth_reliability,
        landmark_quality=rec.landmark_quality,
        focus_tier=rec.focus_tier,
        landmark_ids=list(rec.landmark_ids),
        support_role=rec.support_role,
        coordinate_reference=rec.coordinate_reference,
        evaluation_domain=rec.evaluation_domain,
        evidence_axes=rec.evidence_axes,
        feature_family=rec.feature_family,
    )


def _phase_label_to_suffix(phase_label: str) -> str:
    """Convert a human-readable exercise phase label to a feature-id suffix."""

    suffix = re.sub(r"[^0-9A-Za-z]+", "_", str(phase_label).strip())
    suffix = suffix.strip("_").lower()
    return suffix or "unknown_phase"


def _emit_phase_level(
    df_phase: "pd.DataFrame",
    exercise_definition: Any,
    rep_id: int,
    phase_label: str,
) -> "list[FeatureRecord]":
    """
    Compute phase-level features for one (rep_id, phase) segment.

    Only PHASE_AWARE_FEATURE_FAMILIES are computed at phase level; others stay
    rep-level only.  Each feature_id gets a lower-snake-case phase suffix so that
    rep-level and phase-level IDs remain distinct in the baseline namespace.
    """
    from movement.features.spatial import (
        compute_range_of_motion,
        compute_movement_path,
        compute_support_consistency,
    )
    from movement.features.control import compute_stability
    from movement.features.temporal import compute_tempo

    if len(df_phase) == 0:
        return []

    phase_suffix = "." + _phase_label_to_suffix(phase_label)
    ps_fields = _phase_source_fields(exercise_definition)

    records: list[FeatureRecord] = []

    for rec in compute_range_of_motion(df_phase, exercise_definition, rep_id=rep_id):
        records.append(
            _with_phase(
                rec,
                phase_suffix=phase_suffix,
                phase_label=phase_label,
                phase_source_fields=ps_fields,
            )
        )

    for rec in compute_movement_path(
        df_phase,
        exercise_definition,
        rep_id=rep_id,
        include_support_consistency_axis_diagnostics=False,
    ):
        records.append(
            _with_phase(
                rec,
                phase_suffix=phase_suffix,
                phase_label=phase_label,
                phase_source_fields=ps_fields,
            )
        )

    for rec in compute_support_consistency(
        df_phase, exercise_definition, rep_id=rep_id
    ):
        records.append(
            _with_phase(
                rec,
                phase_suffix=phase_suffix,
                phase_label=phase_label,
                phase_source_fields=ps_fields,
            )
        )

    if _has_depth_axis(df_phase):
        for rec in compute_stability(df_phase, exercise_definition, rep_id=rep_id):
            records.append(
                _with_phase(
                    rec,
                    phase_suffix=phase_suffix,
                    phase_label=phase_label,
                    phase_source_fields=ps_fields,
                )
            )

    for rec in compute_tempo(df_phase, exercise_definition, rep_id=rep_id):
        records.append(
            _with_phase(
                rec,
                phase_suffix=phase_suffix,
                phase_label=phase_label,
                phase_source_fields=ps_fields,
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

    When the `phase` column is populated by ⑥ Segmentation, features
    in PHASE_AWARE_FEATURE_FAMILIES are also emitted for each (rep_id, phase)
    segment.  The rep-level records (phase=None) are always emitted regardless.

    Per-rep features (one record per rep_id, phase=None):
        spatial  : range of motion, role alignment, movement path, support consistency
        control  : CoM stability, compensation arc length

    Phase-level features (one record per rep_id × phase, when phase column is set):
        spatial  : range of motion and movement path (per Descent/Ascent/etc.)
        control  : CoM stability (per phase)

    Sequence-level features (rep_id = None):
        temporal : tempo per rep, inter-rep variability (requires ≥ 2 reps)
        spatial  : role alignment and movement path over the full sequence (when no reps found)

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
            compute_range_of_motion,
            compute_movement_path,
            compute_support_consistency,
            compute_role_alignment,
        )
        from movement.features.control import compute_compensation, compute_stability

        records += compute_range_of_motion(df, exercise_definition)
        records += compute_role_alignment(df, exercise_definition)
        records += compute_movement_path(df, exercise_definition)
        records += compute_support_consistency(df, exercise_definition)
        if _has_depth_axis(df):
            records += compute_stability(df, exercise_definition)
            records += compute_compensation(df, exercise_definition)

    feature_context = resolve_feature_context(df, exercise_definition)
    records = apply_feature_context(records, feature_context)
    return annotate_feature_availability(records, df, exercise_definition)


def _is_hold_phase_label(phase_label: str) -> bool:
    suffix = _phase_label_to_suffix(phase_label)
    return suffix == "hold" or suffix.endswith("_hold")


def _ordered_phase_labels(
    group: list[FeatureRecord],
    exercise_definition: Any | None,
) -> list[str]:
    observed = list(
        dict.fromkeys(str(r.phase) for r in group if r.phase is not None).keys()
    )
    ps = getattr(exercise_definition, "phase_segmentation", None)
    sequence = list(getattr(ps, "phase_sequence", None) or [])
    if sequence:
        ordered = [str(label) for label in sequence if str(label) in observed]
        extras = [label for label in observed if label not in ordered]
        return ordered + extras
    return observed


def _phase_duration_ratio_pair(
    group: list[FeatureRecord],
    exercise_definition: Any | None,
) -> tuple[str, str] | None:
    phases = [
        label
        for label in _ordered_phase_labels(group, exercise_definition)
        if not _is_hold_phase_label(label)
    ]
    if len(phases) < 2:
        return None
    return phases[0], phases[-1]


def summarize_phase_to_rep(
    records: "list[FeatureRecord]",
    exercise_definition: Any | None = None,
) -> "list[FeatureRecord]":
    """
    Derive rep-level summary features from phase-level FeatureRecords.

    Dissertation §5.5: hierarchical summary structure.

    Currently computes:
        - Descent/Ascent ROM ratio, for exercise definitions whose phase model
          explicitly uses those labels.
        - Temporal duration ratio between the first and last non-hold labels in
          exercise_definition.phase_segmentation.phase_sequence.

    This is intentionally template-specific. Generic phase-profile aggregates
    must be designed from the exercise-defined phase sequence before they are
    used for scoring.

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

        # Template-specific Descent vs Ascent mean ROM ratio.
        descent_rom = [
            r.value
            for r in group
            if r.phase == "Descent" and "spatial.range_of_motion" in r.feature_id
        ]
        ascent_rom = [
            r.value
            for r in group
            if r.phase == "Ascent" and "spatial.range_of_motion" in r.feature_id
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
            record = FeatureRecord(
                feature_id="spatial.phase_profile.range_of_motion_ratio.descent_ascent",
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
            apply_common_record_metadata(record)
            summary.append(record)

        phase_pair = _phase_duration_ratio_pair(group, exercise_definition)
        if phase_pair is not None:
            phase_a, phase_b = phase_pair
            suffix_a = _phase_label_to_suffix(phase_a)
            suffix_b = _phase_label_to_suffix(phase_b)
            duration_by_phase = {
                str(r.phase): float(r.value)
                for r in group
                if r.phase is not None
                and r.feature_id.startswith("temporal.tempo.rep_duration.")
            }
            value_a = duration_by_phase.get(phase_a)
            value_b = duration_by_phase.get(phase_b)
            if value_a is not None and value_b is not None and value_b > 0:
                ratio = value_a / value_b
                pair_records = [r for r in group if r.phase in {phase_a, phase_b}]
                ps_fields = [r.source_fields for r in pair_records]
                merged_fields = list(dict.fromkeys(f for sf in ps_fields for f in sf))
                for field_name in [
                    "feature_domains.temporal.phase_profile",
                    "phase_segmentation.phase_sequence",
                    f"temporal.tempo.rep_duration.{suffix_a}",
                    f"temporal.tempo.rep_duration.{suffix_b}",
                ]:
                    if field_name not in merged_fields:
                        merged_fields.append(field_name)
                record = FeatureRecord(
                    feature_id=(
                        "temporal.phase_profile.duration_ratio."
                        f"{suffix_a}_{suffix_b}"
                    ),
                    exercise_id=ex_id,
                    rep_id=rep_id,
                    value=round(ratio, 4),
                    unit="dimensionless",
                    source_fields=merged_fields,
                    note=(
                        f"Ratio of {phase_a} duration to {phase_b} duration "
                        "for this rep. Values > 1 indicate a longer first phase."
                    ),
                    phase=None,
                    depth_dependency="none",
                )
                apply_common_record_metadata(record)
                summary.append(record)

    return summary


def features_to_dataframe(
    records: "list[FeatureRecord]",
    *,
    include_audit_references: bool = True,
) -> "pd.DataFrame":
    """
    Convert a list of FeatureRecord objects to a tidy DataFrame.

    Columns include value/unit metadata plus view reliability and availability.
    source_fields are optional audit references and are included by default for
    in-memory review compatibility.
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
                "note",
                "view_reliability",
                "availability",
                "availability_reasons",
                "camera_zone",
                "role_context",
                "depth_dependency",
                "model_depth_reliability",
                "landmark_quality",
                "focus_tier",
                *COMMON_RECORD_METADATA_FIELDS,
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
            "note": r.note,
            "view_reliability": r.view_reliability,
            "availability": r.availability,
            "availability_reasons": "|".join(r.availability_reasons),
            "camera_zone": r.camera_zone,
            "role_context": r.role_context,
            "depth_dependency": r.depth_dependency,
            "model_depth_reliability": r.model_depth_reliability,
            "landmark_quality": r.landmark_quality,
            "focus_tier": r.focus_tier,
            "landmark_ids": r.landmark_ids,
            "support_role": r.support_role,
            "coordinate_reference": r.coordinate_reference,
            "evaluation_domain": r.evaluation_domain,
            "evidence_axes": r.evidence_axes,
            "feature_family": r.feature_family,
        }
        for r in records
    ]
    if include_audit_references:
        for row, record in zip(rows, records, strict=True):
            row["source_fields"] = "|".join(record.source_fields)
    return pd.DataFrame(rows)


FEATURE_REQUIRED_COLUMNS = [
    "feature_id",
    "exercise_id",
    "rep_id",
    "phase",
    "value",
    "unit",
    "availability",
    "availability_reasons",
    "view_reliability",
    "depth_dependency",
    "model_depth_reliability",
    "landmark_quality",
    "focus_tier",
    "landmark_ids",
    "support_role",
    "coordinate_reference",
    "evaluation_domain",
    "evidence_axes",
    "feature_family",
    "camera_zone",
    "role_context",
]


def _serialize_feature_output_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    try:
        import pandas as pd

        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return value


def _feature_output_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "as_dict"):
        return value.as_dict()
    raise TypeError(f"Cannot serialize {type(value)!r} as a feature output dict.")


def _relative_feature_output_path(path: Path, project_root: Path | None) -> str:
    if project_root is None:
        return str(path)
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _assert_feature_output_round_trip(
    *,
    csv_path: Path,
    expected_rows: int,
    required_columns: list[str],
) -> "pd.DataFrame":
    import pandas as pd

    reloaded = pd.read_csv(csv_path)
    if len(reloaded) != expected_rows:
        raise AssertionError(
            f"Saved row count mismatch for {csv_path}: "
            f"expected {expected_rows}, got {len(reloaded)}."
        )
    for column in required_columns:
        if column not in reloaded.columns:
            raise AssertionError(f"Saved feature CSV missing column: {column}")
    return reloaded


def _feature_audit_reference_rows(feature_df: "pd.DataFrame") -> int | None:
    if "source_fields" not in feature_df.columns:
        return None
    return int(feature_df["source_fields"].fillna("").astype(str).str.len().gt(0).sum())


def save_feature_outputs(
    *,
    feature_df: "pd.DataFrame",
    recording_id: str,
    exercise_id: str,
    output_dir: str | Path,
    feature_context: Any,
    feature_role_context_report: Any,
    project_root: str | Path | None = None,
    required_columns: list[str] | None = None,
    include_audit_references: bool = False,
) -> "pd.DataFrame":
    """Save ⑦ Feature Extraction table/context/QC and verify CSV round-trip."""

    import pandas as pd

    required = required_columns or FEATURE_REQUIRED_COLUMNS
    output_path = Path(output_dir)
    root = Path(project_root) if project_root is not None else None
    output_path.mkdir(parents=True, exist_ok=True)
    csv_path = output_path / f"{recording_id}_features.csv"
    context_path = output_path / f"{recording_id}_feature_context.json"
    qc_path = output_path / f"{recording_id}_feature_qc.json"

    csv_df = feature_df.copy()
    if not include_audit_references and "source_fields" in csv_df.columns:
        csv_df = csv_df.drop(columns=["source_fields"])
    for column in required:
        if column not in csv_df.columns:
            csv_df[column] = ""
    csv_df = csv_df[required + [c for c in csv_df.columns if c not in required]]
    for column in (
        "source_fields",
        "availability_reasons",
        "landmark_ids",
        "role_context",
    ):
        if column in csv_df.columns:
            csv_df[column] = csv_df[column].map(_serialize_feature_output_value)
    csv_df.to_csv(csv_path, index=False, encoding="utf-8")

    context_payload = {
        "recording_id": recording_id,
        "exercise_id": exercise_id,
        "feature_context": _feature_output_dict(feature_context),
        "feature_role_context_report": _feature_output_dict(
            feature_role_context_report
        ),
    }
    context_path.write_text(
        json.dumps(context_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    qc_payload = {
        "recording_id": recording_id,
        "exercise_id": exercise_id,
        "feature_rows": int(len(feature_df)),
        "feature_columns": list(feature_df.columns),
        "availability_counts": feature_df["availability"]
        .value_counts(dropna=False)
        .to_dict(),
        "phase_counts": feature_df["phase"]
        .fillna("rep_level")
        .value_counts()
        .to_dict(),
        "feature_family_counts": (
            feature_df.assign(
                feature_family=feature_df["feature_id"]
                .str.split(".")
                .str[:2]
                .str.join(".")
            )
            .groupby("feature_family", dropna=False)
            .size()
            .to_dict()
        ),
    }
    audit_rows = _feature_audit_reference_rows(feature_df)
    if audit_rows is not None:
        qc_payload["audit_reference_rows"] = audit_rows
    qc_path.write_text(
        json.dumps(qc_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    reloaded = _assert_feature_output_round_trip(
        csv_path=csv_path,
        expected_rows=len(feature_df),
        required_columns=required,
    )
    return pd.DataFrame(
        [
            {
                "artifact": "features_csv",
                "path": _relative_feature_output_path(csv_path, root),
                "rows": len(reloaded),
            },
            {
                "artifact": "feature_context_json",
                "path": _relative_feature_output_path(context_path, root),
                "rows": 1,
            },
            {
                "artifact": "feature_qc_json",
                "path": _relative_feature_output_path(qc_path, root),
                "rows": 1,
            },
        ]
    )


__all__ = [
    "AnalysisDisruptingPatternDetectabilityReport",
    "FEATURE_REQUIRED_COLUMNS",
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
    "save_feature_outputs",
    "summarize_phase_to_rep",
    "features_to_dataframe",
]
