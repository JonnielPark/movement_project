"""Common context helpers for feature, biomech, and biomarker records.

Record metadata describes the evidence path of a computed metric. Stable
anatomical facts live in ``data/reference/landmarks/common_landmark_metadata.yaml``
and are joined through ``landmark_ids`` when reports need them.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

COMMON_RECORD_METADATA_FIELDS = [
    "landmark_ids",
    "support_role",
    "coordinate_reference",
    "evaluation_domain",
    "evidence_axes",
    "feature_family",
]

EVALUATION_DOMAINS = {
    "recording_view_only",
    "corrected_3d_hypothesis",
    "dual_domain_compare",
    "timing_only",
    "unknown",
}

EVIDENCE_AXES = {
    "x",
    "y",
    "z",
    "xy",
    "xz",
    "yz",
    "xyz",
    "time",
    "scalar",
    "unknown",
}

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LANDMARK_METADATA_PATH = (
    _PROJECT_ROOT / "data" / "reference" / "landmarks" / "common_landmark_metadata.yaml"
)
_JOINT_PROFILES_PATH = (
    _PROJECT_ROOT / "data" / "reference" / "landmarks" / "joint_profiles.yaml"
)

_KNOWN_LANDMARK_IDS = (
    "left_eye_inner",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye_outer",
    "left_foot_index",
    "right_foot_index",
    "shoulder_center",
    "whole_body_com",
    "support_center",
    "left_shoulder",
    "right_shoulder",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_ankle",
    "right_ankle",
    "left_knee",
    "right_knee",
    "left_heel",
    "right_heel",
    "hip_center",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_hip",
    "right_hip",
    "nose",
)


def default_landmark_metadata_path() -> Path:
    """Return the default joint/landmark metadata registry path."""

    return _LANDMARK_METADATA_PATH


def default_joint_profiles_path() -> Path:
    """Return the default joint/profile interpretation registry path."""

    return _JOINT_PROFILES_PATH


def load_landmark_metadata(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Load stable anatomical metadata keyed by canonical landmark id."""

    metadata_path = Path(path) if path is not None else default_landmark_metadata_path()
    with metadata_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    defaults = raw.get("defaults", {}) or {}
    landmarks = raw.get("landmarks", {}) or {}
    return {
        str(landmark_id): {**defaults, **(values or {}), "landmark_id": landmark_id}
        for landmark_id, values in landmarks.items()
    }


def load_joint_profiles(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Load joint/profile-specific interpretation metadata."""

    profiles_path = Path(path) if path is not None else default_joint_profiles_path()
    with profiles_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    profiles = raw.get("profiles", {}) or {}
    return {
        str(profile_id): {**(values or {}), "profile_id": profile_id}
        for profile_id, values in profiles.items()
    }


def resolve_landmark_metadata(
    landmark_ids: Iterable[str],
    *,
    metadata: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return registry rows for landmark ids, preserving input order."""

    registry = metadata if metadata is not None else load_landmark_metadata()
    resolved: list[dict[str, Any]] = []
    for landmark_id in landmark_ids:
        key = str(landmark_id)
        resolved.append(registry.get(key, {"landmark_id": key}))
    return resolved


def classify_feature_family(record_id: str) -> str:
    """Return the broad feature family used by scoring and audits."""

    if record_id.startswith(
        ("spatial.range_of_motion.xy.", "spatial.range_of_motion.xyz.")
    ):
        return "range_of_motion"
    if record_id.startswith("spatial.role_alignment."):
        return "role_alignment"
    if record_id.startswith("spatial.support_consistency."):
        return "support_consistency"
    if record_id.startswith("spatial.movement_path."):
        return "movement_path"
    if ".phase_profile." in record_id:
        return "phase_profile"
    if record_id.startswith("temporal.tempo."):
        return "tempo"
    if record_id.startswith("temporal.variability."):
        return "variability"
    if record_id.startswith("control.stability."):
        return "stability"
    if record_id.startswith("control.compensation."):
        return "compensation"
    if record_id.startswith("biomech."):
        parts = record_id.split(".")
        return parts[1] if len(parts) > 1 else "proxy"
    return "other"


def _source_fields_contain(source_fields: Iterable[str], value: str) -> bool:
    needle = value.lower()
    return any(needle in str(field).lower() for field in source_fields)


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _known_landmarks_in_record_id(record_id: str) -> list[str]:
    normalized = record_id.lower()
    matches: list[tuple[int, int, str]] = []
    occupied: list[range] = []

    for landmark_id in sorted(_KNOWN_LANDMARK_IDS, key=len, reverse=True):
        start = 0
        while True:
            idx = normalized.find(landmark_id, start)
            if idx < 0:
                break
            span = range(idx, idx + len(landmark_id))
            if not any(_ranges_overlap(span, used) for used in occupied):
                matches.append((idx, idx + len(landmark_id), landmark_id))
                occupied.append(span)
            start = idx + 1

    return _unique_preserve_order(item[2] for item in sorted(matches))


def _ranges_overlap(left: range, right: range) -> bool:
    return left.start < right.stop and right.start < left.stop


def _infer_landmark_ids(record_id: str) -> list[str]:
    normalized = record_id.lower()
    inferred = _known_landmarks_in_record_id(normalized)

    if inferred:
        return inferred
    if "heel_lift" in normalized:
        if re.search(r"(^|[.])left($|[.])", normalized):
            return ["left_heel"]
        if re.search(r"(^|[.])right($|[.])", normalized):
            return ["right_heel"]
        return ["left_heel", "right_heel"]
    if "knee_valgus" in normalized or "knee_varus" in normalized:
        if re.search(r"(^|[.])left($|[.])", normalized):
            return ["left_hip", "left_knee", "left_ankle"]
        if re.search(r"(^|[.])right($|[.])", normalized):
            return ["right_hip", "right_knee", "right_ankle"]
        return [
            "left_hip",
            "left_knee",
            "left_ankle",
            "right_hip",
            "right_knee",
            "right_ankle",
        ]
    if "pelvis_rotation" in normalized:
        return ["left_hip", "right_hip"]
    joint_side_match = re.search(
        r"(?:moment_arm|load_shift)\."
        r"(?P<joint>hip|knee|ankle|shoulder|elbow|wrist)\."
        r"(?P<side>left|right)(?:\.|$)",
        normalized,
    )
    if joint_side_match:
        return [f"{joint_side_match.group('side')}_{joint_side_match.group('joint')}"]
    if normalized.startswith("biomech.com.") or ".com." in normalized:
        return ["whole_body_com"]
    if "width_variation" in normalized:
        return ["left_ankle", "right_ankle"]
    if normalized.startswith(
        "spatial.role_alignment.left_right.range_of_motion_xy.knee"
    ):
        return ["left_knee", "right_knee"]
    if normalized.startswith(
        "spatial.role_alignment.left_right.range_of_motion_xy.hip"
    ):
        return ["left_hip", "right_hip"]
    if normalized.startswith(
        "spatial.role_alignment.left_right.range_of_motion_xy.ankle"
    ):
        return ["left_ankle", "right_ankle"]
    if "center_drift" in normalized or "support_center" in normalized:
        return ["support_center"]
    if "hip_center" in normalized or "pelvic" in normalized:
        return ["hip_center"]
    if "trunk" in normalized:
        return ["shoulder_center", "hip_center"]
    return []


def _infer_evidence_axes(record_id: str, unit: str | None) -> str:
    normalized = record_id.lower()
    normalized_tokens = f".{normalized}."
    if normalized.startswith("temporal."):
        return "time"
    if "arc_length_xyz" in normalized or "axis_path_xyz" in normalized:
        return "xyz"
    if (
        "arc_length_xy" in normalized
        or "axis_path_xy" in normalized
        or "point_drift_xy" in normalized
        or "center_drift_xy" in normalized
        or "width_variation_xy" in normalized
        or "support_consistency_xy" in normalized
    ):
        return "xy"
    if "axis_path_x" in normalized or ".range_x" in normalized:
        return "x"
    if "axis_path_y" in normalized or ".range_y" in normalized:
        return "y"
    if "axis_path_z" in normalized or ".range_z" in normalized:
        return "z"
    if "heel_lift" in normalized:
        return "y"
    if "pelvis_rotation" in normalized:
        return "z"
    if ".xyz." in normalized_tokens:
        return "xyz"
    if ".xy." in normalized_tokens:
        return "xy"
    if "hip_center_x" in normalized or "lateral_pelvic_shift" in normalized:
        return "x"
    if "hip_center_z" in normalized:
        return "z"
    if "knee_valgus" in normalized or "knee_varus" in normalized:
        return "xy"
    if "moment_arm" in normalized:
        return "xz"
    if "path_length" in normalized:
        return "xyz"
    if normalized.startswith("spatial.range_of_motion.xy."):
        return "xy"
    if normalized.startswith("spatial.range_of_motion.xyz."):
        return "xyz"
    if unit == "degree":
        return "xyz"
    if normalized.startswith("spatial.support_consistency."):
        return "xy"
    if normalized.startswith("spatial.role_alignment.left_right.support_consistency_"):
        return "xy"
    if unit in {"dimensionless", "dimensionless_cv"}:
        return "scalar"
    return "unknown"


def _infer_support_role(
    record_id: str,
    landmark_ids: Iterable[str],
    source_fields: Iterable[str],
) -> str:
    normalized = record_id.lower()
    landmarks = set(landmark_ids)
    if normalized.startswith("control.compensation.heel_lift."):
        return "support_consistency"
    if normalized.startswith("spatial.support_consistency."):
        return "support_consistency"
    if normalized.startswith("spatial.role_alignment.left_right.support_consistency_"):
        return "support_consistency"
    if _source_fields_contain(source_fields, "support."):
        return "support_consistency" if landmarks else "unknown"
    if "whole_body_com" in landmarks:
        return "whole_body_proxy"
    if "hip_center" in landmarks:
        return "pelvis_reference"
    if "shoulder_center" in landmarks:
        return "trunk_reference"
    if normalized.startswith("biomech.moment_arm."):
        return "joint_proxy"
    if landmarks:
        return "moving_landmark"
    return "unknown"


def _infer_coordinate_reference(
    record_id: str,
    evidence_axes: str,
    source_fields: Iterable[str],
) -> str:
    normalized = record_id.lower()
    if normalized.startswith("temporal."):
        return "timestamp"
    if "corrected_3d_hypothesis" in normalized or _source_fields_contain(
        source_fields, "corrected_3d_hypothesis"
    ):
        return "corrected_3d_hypothesis"
    if normalized.startswith("biomech."):
        return "derived_proxy"
    if evidence_axes in {"x", "y", "xy"}:
        return "norm_recording_view_xy"
    if evidence_axes in {"z", "xz", "yz", "xyz"}:
        return "norm_model_depth"
    if evidence_axes == "scalar":
        return "norm"
    return "unknown"


def _infer_evaluation_domain(
    record_id: str,
    evidence_axes: str,
    source_fields: Iterable[str],
    depth_dependency: str | None,
) -> str:
    normalized = record_id.lower()
    if normalized.startswith("temporal.") or evidence_axes == "time":
        return "timing_only"
    if "corrected_3d_hypothesis" in normalized or _source_fields_contain(
        source_fields, "corrected_3d_hypothesis"
    ):
        return "corrected_3d_hypothesis"
    if evidence_axes in {"x", "y", "xy"}:
        return "recording_view_only"
    if depth_dependency in {"none", "low"} and evidence_axes != "unknown":
        return "recording_view_only"
    if evidence_axes in {"z", "xz", "yz", "xyz"} or depth_dependency in {
        "moderate",
        "high",
    }:
        return "dual_domain_compare"
    return "unknown"


def infer_common_record_metadata(
    record_id: str,
    *,
    source_fields: Iterable[str] = (),
    unit: str | None = None,
    depth_dependency: str | None = None,
    exercise_definition: Any = None,
) -> dict[str, Any]:
    """Infer common evidence/context metadata for a record id.

    The returned fields are descriptive provenance. Stable anatomical labels are
    intentionally omitted from record rows and should be joined through
    ``landmark_ids`` when needed.
    """

    del exercise_definition  # reserved for future feature-specific inference

    landmark_ids = _infer_landmark_ids(record_id)
    evidence_axes = _infer_evidence_axes(record_id, unit)
    return {
        "landmark_ids": landmark_ids,
        "support_role": _infer_support_role(record_id, landmark_ids, source_fields),
        "coordinate_reference": _infer_coordinate_reference(
            record_id, evidence_axes, source_fields
        ),
        "evaluation_domain": _infer_evaluation_domain(
            record_id, evidence_axes, source_fields, depth_dependency
        ),
        "evidence_axes": evidence_axes,
        "feature_family": classify_feature_family(record_id),
    }


def _metadata_missing(value: Any) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    if value == "unknown":
        return True
    if value == []:
        return True
    return False


def apply_common_record_metadata(
    record: Any,
    *,
    exercise_definition: Any = None,
    record_id: str | None = None,
) -> Any:
    """Populate missing common context metadata fields on a record-like object."""

    rid = (
        record_id
        or getattr(record, "feature_id", None)
        or getattr(record, "metric_id", None)
        or getattr(record, "biomarker_id", "")
    )
    metadata = infer_common_record_metadata(
        str(rid),
        source_fields=getattr(record, "source_fields", []) or [],
        unit=getattr(record, "unit", None),
        depth_dependency=getattr(record, "depth_dependency", None),
        exercise_definition=exercise_definition,
    )
    for field, value in metadata.items():
        current = getattr(record, field, None)
        if _metadata_missing(current):
            setattr(record, field, value)
    return record
