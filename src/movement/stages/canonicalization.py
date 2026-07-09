"""Analysis-space canonicalization for monocular pose coordinates.

Optional substage ⑤-1 consumes ⑤ norm coordinates. It does not reconstruct
physical 3D or fit the pose to a good-movement template. It preserves raw/norm
coordinates and emits separate analysis-space coordinates plus confidence
reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np
import pandas as pd

from movement.pose_data_state import (
    CANONICALIZED_POSE_DATA,
    NORM_COORDINATE_FAMILY,
    RAW_COORDINATE_FAMILY,
    get_coordinate_axes,
    get_coordinate_families,
    get_family_axes,
    get_pose_data_state,
    set_pose_data_state,
)
from movement.stages.floor_reference import (
    FloorReferenceConfig,
    apply_floor_relative_correction,
)

_DEFAULT_MOVEMENT_PLANE_LANDMARKS = [
    "left_hip",
    "left_knee",
    "left_ankle",
    "right_hip",
    "right_knee",
    "right_ankle",
]

_DEFAULT_HEIGHT_ANCHOR_MAP = {
    "H1": ["left_ankle", "right_ankle"],
    "H2": ["left_hip", "right_hip"],
    "H3": ["left_shoulder", "right_shoulder"],
}


@dataclass
class CanonicalizationDataConfidenceConfig:
    emit: bool = True
    correction_magnitude_warn_torso: float = 0.15
    correction_magnitude_fail_torso: float = 0.30
    residual_warn_torso: float = 0.08


@dataclass
class MovementPlaneAlignmentConfig:
    enabled: bool = False
    method: str = "principal_motion_plane"
    fit_landmarks: list[str] = field(
        default_factory=lambda: list(_DEFAULT_MOVEMENT_PLANE_LANDMARKS)
    )
    minimum_confident_landmark_ratio: float = 0.7
    correction_strength: float = 0.5
    max_rotation_deg: float = 20.0
    preserve_out_of_plane_residual: bool = True


@dataclass
class ProtocolHeightLateralWidthAlignmentConfig:
    enabled: bool = False
    method: str = "height_anchor_lateral_width"
    observed_height_level: str | None = None
    observed_height_column: str = "camera_height_level"
    recommended_height_level: str | None = None
    require_height_match: bool = True
    height_anchor_map: dict[str, list[str]] = field(
        default_factory=lambda: {
            key: list(value) for key, value in _DEFAULT_HEIGHT_ANCHOR_MAP.items()
        }
    )
    near_depth_sign: str = "negative"
    correction_mode: str = "near_side_attenuation"
    correction_strength: float = 0.3
    max_scale_change: float = 0.20
    max_correction_torso: float = 0.15
    min_depth_offset_torso: float = 0.05
    confidence_threshold: float = 0.6
    apply_to_landmarks: list[str] = field(default_factory=list)
    preserve_anchor_landmarks: bool = True


@dataclass
class Corrected3DHypothesisConfig:
    enabled: bool = False
    output_family: str = "corrected_3d_hypothesis"
    downstream_coordinate_mode: str = "norm"
    emit_sensitivity_report: bool = True
    support_pair: tuple[str, ...] = ("left_ankle", "right_ankle")
    report_burden_before_feature_use: bool = True
    require_feature_domain_declaration: bool = True


@dataclass
class XYDepthLiftConfig:
    enabled: bool = False
    method: str = "recording_view_depth_hypothesis"
    segment_pairs: list[tuple[str, str]] = field(
        default_factory=lambda: [
            ("left_hip", "left_knee"),
            ("left_knee", "left_ankle"),
            ("right_hip", "right_knee"),
            ("right_knee", "right_ankle"),
            ("left_shoulder", "left_hip"),
            ("right_shoulder", "right_hip"),
        ]
    )
    default_segment_length_torso: float = 1.0
    max_depth_torso: float = 0.75
    confidence_threshold: float = 0.5
    depth_sign: str = "positive"


@dataclass
class CanonicalizationConfig:
    enabled: bool = False
    coordinate_mode: str = "norm"
    output_prefix: str = "canon"
    report_only: bool = True
    downstream_coordinate_mode: str = "norm"
    data_confidence: CanonicalizationDataConfidenceConfig = field(
        default_factory=CanonicalizationDataConfidenceConfig
    )
    support_plane_alignment: FloorReferenceConfig = field(
        default_factory=FloorReferenceConfig
    )
    movement_plane_alignment: MovementPlaneAlignmentConfig = field(
        default_factory=MovementPlaneAlignmentConfig
    )
    protocol_height_lateral_width_alignment: (
        ProtocolHeightLateralWidthAlignmentConfig
    ) = field(default_factory=ProtocolHeightLateralWidthAlignmentConfig)
    xy_depth_lift: XYDepthLiftConfig = field(default_factory=XYDepthLiftConfig)
    corrected_3d_hypothesis: Corrected3DHypothesisConfig = field(
        default_factory=Corrected3DHypothesisConfig
    )


def _source_columns(
    landmark: str,
    coordinate_mode: str,
    axes: tuple[str, ...] = ("x", "y", "z"),
) -> dict[str, str]:
    if coordinate_mode == "raw":
        prefix = landmark
    elif coordinate_mode == "norm":
        prefix = f"{landmark}_norm"
    else:
        raise ValueError(
            "canonicalization currently supports coordinate_mode 'raw' or 'norm', "
            f"got {coordinate_mode!r}."
        )
    return {axis: f"{prefix}_{axis}" for axis in axes}


def _canon_columns(landmark: str, output_prefix: str) -> dict[str, str]:
    return {axis: f"{landmark}_{output_prefix}_{axis}" for axis in ("x", "y", "z")}


def _horizontal_axes(vertical_axis: str) -> tuple[str, str]:
    if vertical_axis not in {"x", "y", "z"}:
        raise ValueError(
            f"Unsupported vertical_axis={vertical_axis!r}. Use one of x, y, z."
        )
    axes = [axis for axis in ("x", "y", "z") if axis != vertical_axis]
    return axes[0], axes[1]


def _axis_index() -> dict[str, int]:
    return {"x": 0, "y": 1, "z": 2}


def _copy_base_coordinates(
    df: pd.DataFrame,
    landmarks: list[str],
    coordinate_mode: str,
    output_prefix: str,
    axes: tuple[str, ...] = ("x", "y", "z"),
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    missing: list[str] = []
    for landmark in landmarks:
        src = _source_columns(landmark, coordinate_mode, axes)
        dst = _canon_columns(landmark, output_prefix)
        for axis in axes:
            if src[axis] not in df.columns:
                missing.append(src[axis])
            else:
                output[dst[axis]] = df[src[axis]]
    if missing:
        raise ValueError(
            "canonicalization requires complete source coordinate columns. "
            f"Missing: {missing[:10]}"
        )
    return output


def _source_family(coordinate_mode: str) -> str:
    if coordinate_mode == "raw":
        return RAW_COORDINATE_FAMILY
    if coordinate_mode == "norm":
        return NORM_COORDINATE_FAMILY
    raise ValueError(
        "canonicalization currently supports coordinate_mode 'raw' or 'norm', "
        f"got {coordinate_mode!r}."
    )


def _resolve_source_axes(
    df: pd.DataFrame,
    *,
    landmarks: list[str],
    coordinate_mode: str,
) -> tuple[str, ...]:
    family = _source_family(coordinate_mode)
    axes = get_family_axes(df, family, default=())
    if not axes:
        axes = [
            axis
            for axis in ("x", "y", "z")
            if all(
                _source_columns(landmark, coordinate_mode, (axis,))[axis] in df.columns
                for landmark in landmarks
            )
        ]
    ordered_axes = tuple(axis for axis in ("x", "y", "z") if axis in axes)
    if "z" in ordered_axes:
        z_columns = [
            _source_columns(landmark, coordinate_mode, ("z",))["z"]
            for landmark in landmarks
        ]
        existing_z = [column for column in z_columns if column in df.columns]
        finite_z = False
        if existing_z:
            values = df[existing_z].astype(float).to_numpy()
            finite_z = bool(np.isfinite(values).any())
        if not finite_z:
            ordered_axes = tuple(axis for axis in ordered_axes if axis != "z")
    if not {"x", "y"}.issubset(ordered_axes):
        raise ValueError(
            "canonicalization requires at least x/y source coordinates. "
            f"Resolved axes for {family!r}: {list(ordered_axes)}"
        )
    return ordered_axes


def _canonical_axes_from_columns(
    canonical_columns: dict[str, Any],
    *,
    landmarks: list[str],
    output_prefix: str,
) -> list[str]:
    axes: list[str] = []
    for axis in ("x", "y", "z"):
        if all(
            _canon_columns(landmark, output_prefix)[axis] in canonical_columns
            for landmark in landmarks
        ):
            axes.append(axis)
    return axes


def _confidence_level(
    *,
    max_correction: float,
    residual_after_fit: float | None,
    notes: list[str],
    config: CanonicalizationDataConfidenceConfig,
) -> dict[str, Any]:
    reasons: list[str] = []
    level = "high"

    if max_correction >= config.correction_magnitude_fail_torso:
        level = "low"
        reasons.append("correction_magnitude_exceeds_fail_threshold")
    elif max_correction >= config.correction_magnitude_warn_torso:
        level = "moderate"
        reasons.append("correction_magnitude_exceeds_warn_threshold")

    if residual_after_fit is not None and np.isfinite(residual_after_fit):
        if residual_after_fit >= config.residual_warn_torso:
            if level == "high":
                level = "moderate"
            reasons.append("residual_after_fit_exceeds_warn_threshold")

    if notes and level == "high":
        level = "moderate"
        reasons.append("prior_confidence_notes_present")

    return {"level": level, "reasons": reasons}


def _canonicalization_burden_level(
    *,
    max_correction: float,
    config: CanonicalizationDataConfidenceConfig,
) -> str:
    if not np.isfinite(max_correction) or max_correction <= 0.0:
        return "none"
    if max_correction >= config.correction_magnitude_fail_torso:
        return "high"
    if max_correction >= config.correction_magnitude_warn_torso:
        return "moderate"
    return "low"


def _quality_gravity_from_confidence(confidence_level: str) -> float:
    """Map evidence confidence to a downstream quality-trust summary."""
    return {
        "high": 1.0,
        "moderate": 0.5,
        "low": 0.1,
        "very_low": 0.05,
        "not_available": 0.0,
        "not_emitted": 0.0,
    }.get(str(confidence_level), 0.0)


def _canonicalization_evidence_summary(
    *,
    status: str,
    max_correction: float,
    data_confidence: dict[str, Any],
    config: CanonicalizationDataConfidenceConfig,
) -> dict[str, Any]:
    evidence_available = status in {"applied", "partial"}
    evidence_confidence = (
        str(data_confidence.get("level", "not_available"))
        if evidence_available
        else "not_available"
    )
    quality_gravity = (
        _quality_gravity_from_confidence(evidence_confidence)
        if evidence_available
        else 0.0
    )
    return {
        "evidence_available": evidence_available,
        "evidence_confidence": evidence_confidence,
        "quality_gravity": quality_gravity,
        "burden_level": (
            _canonicalization_burden_level(
                max_correction=max_correction,
                config=config,
            )
            if evidence_available
            else "none"
        ),
    }


def _series_from_column_data(values: Any, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).astype(float)


def _collect_movement_vectors(
    df: pd.DataFrame,
    canonical_columns: dict[str, Any],
    *,
    output_prefix: str,
    fit_landmarks: list[str],
    vertical_axis: str,
    minimum_confident_landmark_ratio: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, float], dict[str, list[str]], list[str]]:
    h1_axis, h2_axis = _horizontal_axes(vertical_axis)
    axis_idx = _axis_index()
    vectors: list[np.ndarray] = []
    weights: list[np.ndarray] = []
    coverage_by_landmark: dict[str, float] = {}
    excluded: dict[str, list[str]] = {}
    notes: list[str] = []

    for landmark in fit_landmarks:
        cols = _canon_columns(landmark, output_prefix)
        missing = [col for col in cols.values() if col not in canonical_columns]
        if missing:
            excluded.setdefault(landmark, []).append(
                f"missing canonical columns: {missing[:3]}"
            )
            continue

        coords = np.column_stack(
            [
                _series_from_column_data(
                    canonical_columns[cols[axis]], df.index
                ).to_numpy(dtype=float)
                for axis in ("x", "y", "z")
            ]
        )
        valid = np.isfinite(coords).all(axis=1)
        confidence_col = f"{landmark}_confidence"
        if confidence_col in df.columns:
            confidence = df[confidence_col].astype(float).to_numpy()
            finite_confidence = np.isfinite(confidence)
            valid &= finite_confidence
            frame_weights = np.clip(confidence, 0.0, 1.0)
        else:
            notes.append(
                f"{landmark}: confidence column missing; movement-plane coverage "
                "uses finite coordinates only"
            )
            frame_weights = np.ones(len(df), dtype=float)

        coverage = float(valid.mean()) if len(valid) else 0.0
        coverage_by_landmark[landmark] = coverage
        if coverage < minimum_confident_landmark_ratio:
            excluded.setdefault(landmark, []).append(
                "confident_landmark_ratio_below_minimum"
            )
            continue

        pair_valid = valid[:-1] & valid[1:]
        if not bool(pair_valid.any()):
            excluded.setdefault(landmark, []).append("no_valid_motion_pairs")
            continue

        deltas = coords[1:] - coords[:-1]
        horizontal = deltas[:, [axis_idx[h1_axis], axis_idx[h2_axis]]]
        motion_norm = np.linalg.norm(horizontal, axis=1)
        pair_valid &= motion_norm > 1e-9
        if not bool(pair_valid.any()):
            excluded.setdefault(landmark, []).append("no_horizontal_motion")
            continue

        pair_weights = (frame_weights[:-1] + frame_weights[1:]) / 2.0
        pair_valid &= np.isfinite(pair_weights) & (pair_weights > 0.0)
        if not bool(pair_valid.any()):
            excluded.setdefault(landmark, []).append("no_positive_confidence_weight")
            continue

        vectors.append(horizontal[pair_valid])
        weights.append(pair_weights[pair_valid])

    if not vectors:
        return (
            np.empty((0, 2), dtype=float),
            np.empty((0,), dtype=float),
            coverage_by_landmark,
            excluded,
            notes,
        )

    return (
        np.vstack(vectors).astype(float),
        np.concatenate(weights).astype(float),
        coverage_by_landmark,
        excluded,
        notes,
    )


def _estimate_primary_motion_axis(
    horizontal_vectors: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray | None, str | None]:
    finite = np.isfinite(horizontal_vectors).all(axis=1) & np.isfinite(weights)
    finite &= weights > 0.0
    if not bool(finite.any()):
        return None, "no_finite_weighted_motion_vectors"

    vectors = horizontal_vectors[finite]
    vector_weights = weights[finite]
    second_moment = (vectors.T * vector_weights) @ vectors / vector_weights.sum()
    if not np.isfinite(second_moment).all():
        return None, "non_finite_motion_covariance"

    eigenvalues, eigenvectors = np.linalg.eigh(second_moment)
    dominant_idx = int(np.argmax(eigenvalues))
    if float(eigenvalues[dominant_idx]) <= 1e-12:
        return None, "insufficient_horizontal_motion_variance"

    axis = eigenvectors[:, dominant_idx].astype(float)
    axis_norm = float(np.linalg.norm(axis))
    if axis_norm <= 1e-12:
        return None, "zero_primary_motion_axis"

    axis = axis / axis_norm
    if axis[1] < 0.0:
        axis = -axis
    return axis, None


def _summarize_values(values: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return {"median": 0.0, "p90": 0.0, "max": 0.0}
    return {
        "median": float(np.nanmedian(finite)),
        "p90": float(np.nanpercentile(finite, 90)),
        "max": float(np.nanmax(finite)),
    }


def _out_of_plane_motion_summary(
    horizontal_vectors: np.ndarray,
    rotation_rad: float,
) -> dict[str, float]:
    if len(horizontal_vectors) == 0:
        return {"median": 0.0, "p90": 0.0, "max": 0.0}

    cos_a = float(np.cos(rotation_rad))
    sin_a = float(np.sin(rotation_rad))
    h1 = horizontal_vectors[:, 0]
    h2 = horizontal_vectors[:, 1]
    rotated_h1 = cos_a * h1 - sin_a * h2
    rotated_h2 = sin_a * h1 + cos_a * h2
    horizontal_norm = np.sqrt(rotated_h1**2 + rotated_h2**2)
    ratio = np.divide(
        np.abs(rotated_h1),
        horizontal_norm,
        out=np.zeros_like(rotated_h1, dtype=float),
        where=horizontal_norm > 1e-12,
    )
    return _summarize_values(ratio)


def _movement_rotation_pivot(
    canonical_columns: dict[str, Any],
    *,
    output_prefix: str,
    index: pd.Index,
) -> np.ndarray:
    left_cols = _canon_columns("left_hip", output_prefix)
    right_cols = _canon_columns("right_hip", output_prefix)
    if all(
        col in canonical_columns for col in [*left_cols.values(), *right_cols.values()]
    ):
        left = np.column_stack(
            [
                _series_from_column_data(
                    canonical_columns[left_cols[axis]], index
                ).to_numpy(dtype=float)
                for axis in ("x", "y", "z")
            ]
        )
        right = np.column_stack(
            [
                _series_from_column_data(
                    canonical_columns[right_cols[axis]], index
                ).to_numpy(dtype=float)
                for axis in ("x", "y", "z")
            ]
        )
        return (left + right) / 2.0

    return np.zeros((len(index), 3), dtype=float)


def _rotate_canonical_columns(
    canonical_columns: dict[str, Any],
    *,
    landmarks: list[str],
    output_prefix: str,
    vertical_axis: str,
    rotation_rad: float,
    index: pd.Index,
) -> tuple[dict[str, Any], np.ndarray, float, float]:
    h1_axis, h2_axis = _horizontal_axes(vertical_axis)
    axis_idx = _axis_index()
    h1_idx = axis_idx[h1_axis]
    h2_idx = axis_idx[h2_axis]
    cos_a = float(np.cos(rotation_rad))
    sin_a = float(np.sin(rotation_rad))
    pivot = _movement_rotation_pivot(
        canonical_columns,
        output_prefix=output_prefix,
        index=index,
    )
    updated = dict(canonical_columns)
    frame_abs_correction = np.zeros(len(index), dtype=float)
    abs_corrections: list[np.ndarray] = []

    for landmark in landmarks:
        cols = _canon_columns(landmark, output_prefix)
        if any(col not in canonical_columns for col in cols.values()):
            continue

        coords = np.column_stack(
            [
                _series_from_column_data(canonical_columns[cols[axis]], index).to_numpy(
                    dtype=float
                )
                for axis in ("x", "y", "z")
            ]
        )
        corrected = coords.copy()
        rel_h1 = coords[:, h1_idx] - pivot[:, h1_idx]
        rel_h2 = coords[:, h2_idx] - pivot[:, h2_idx]
        corrected[:, h1_idx] = pivot[:, h1_idx] + cos_a * rel_h1 - sin_a * rel_h2
        corrected[:, h2_idx] = pivot[:, h2_idx] + sin_a * rel_h1 + cos_a * rel_h2

        delta = np.linalg.norm(corrected - coords, axis=1)
        abs_corrections.append(delta)
        frame_abs_correction = np.maximum(
            frame_abs_correction,
            np.nan_to_num(delta, nan=0.0, posinf=0.0, neginf=0.0),
        )
        for axis in ("x", "y", "z"):
            updated[cols[axis]] = corrected[:, axis_idx[axis]]

    if not abs_corrections:
        return updated, frame_abs_correction, 0.0, 0.0

    all_corrections = np.concatenate(abs_corrections)
    finite = all_corrections[np.isfinite(all_corrections)]
    if len(finite) == 0:
        return updated, frame_abs_correction, 0.0, 0.0

    return (
        updated,
        frame_abs_correction,
        float(np.max(finite)),
        float(np.median(finite)),
    )


def _apply_movement_plane_alignment(
    df: pd.DataFrame,
    canonical_columns: dict[str, Any],
    *,
    landmarks: list[str],
    output_prefix: str,
    config: MovementPlaneAlignmentConfig,
    vertical_axis: str = "y",
) -> tuple[dict[str, Any], dict[str, Any], np.ndarray, float, float]:
    if config.method != "principal_motion_plane":
        raise ValueError(
            "Unsupported movement_plane_alignment method: "
            f"{config.method!r}. Use 'principal_motion_plane'."
        )
    if config.max_rotation_deg < 0.0:
        raise ValueError("max_rotation_deg must be non-negative.")

    fit_landmarks = [
        landmark for landmark in (config.fit_landmarks or []) if landmark in landmarks
    ]
    report: dict[str, Any] = {
        "enabled": True,
        "status": "skipped",
        "method": config.method,
        "vertical_axis": vertical_axis,
        "fit_landmarks": fit_landmarks,
        "minimum_confident_landmark_ratio": float(
            config.minimum_confident_landmark_ratio
        ),
        "correction_strength": float(config.correction_strength),
        "effective_correction_strength": float(config.correction_strength),
        "max_rotation_deg": float(config.max_rotation_deg),
        "preserve_out_of_plane_residual": bool(config.preserve_out_of_plane_residual),
        "num_motion_vectors": 0,
        "primary_motion_axis": {},
        "requested_rotation_deg": 0.0,
        "applied_rotation_deg": 0.0,
        "max_abs_correction": 0.0,
        "median_abs_correction": 0.0,
        "out_of_plane_residual_ratio_before": {
            "median": 0.0,
            "p90": 0.0,
            "max": 0.0,
        },
        "out_of_plane_residual_ratio_after": {
            "median": 0.0,
            "p90": 0.0,
            "max": 0.0,
        },
        "landmark_coverage": {},
        "excluded_landmark_reasons": {},
        "confidence_notes": [],
    }

    if not fit_landmarks:
        report["confidence_notes"].append(
            "No configured fit landmarks are present in the requested landmark set."
        )
        return canonical_columns, report, np.zeros(len(df), dtype=float), 0.0, 0.0

    horizontal_vectors, weights, coverage, excluded, notes = _collect_movement_vectors(
        df,
        canonical_columns,
        output_prefix=output_prefix,
        fit_landmarks=fit_landmarks,
        vertical_axis=vertical_axis,
        minimum_confident_landmark_ratio=float(config.minimum_confident_landmark_ratio),
    )
    report["num_motion_vectors"] = int(len(horizontal_vectors))
    report["landmark_coverage"] = coverage
    report["excluded_landmark_reasons"] = excluded
    report["confidence_notes"].extend(notes)

    if not config.preserve_out_of_plane_residual:
        report["confidence_notes"].append(
            "preserve_out_of_plane_residual=False is recorded, but the prototype "
            "still preserves residual motion and only applies a rigid rotation."
        )

    if len(horizontal_vectors) < 2:
        report["confidence_notes"].append(
            "Too few valid motion vectors for movement-plane fitting."
        )
        return canonical_columns, report, np.zeros(len(df), dtype=float), 0.0, 0.0

    primary_axis, skip_reason = _estimate_primary_motion_axis(
        horizontal_vectors,
        weights,
    )
    if primary_axis is None:
        report["confidence_notes"].append(str(skip_reason))
        return canonical_columns, report, np.zeros(len(df), dtype=float), 0.0, 0.0

    h1_axis, h2_axis = _horizontal_axes(vertical_axis)
    requested_rotation_deg = float(
        np.rad2deg(np.arctan2(primary_axis[0], primary_axis[1]))
    )
    strength = float(config.correction_strength)
    effective_strength = float(np.clip(strength, 0.0, 1.0))
    if not np.isclose(effective_strength, strength):
        report["confidence_notes"].append(
            "movement_plane_alignment correction_strength was clipped to [0, 1]."
        )

    applied_rotation_deg = requested_rotation_deg * effective_strength
    clipped_rotation_deg = float(
        np.clip(
            applied_rotation_deg,
            -float(config.max_rotation_deg),
            float(config.max_rotation_deg),
        )
    )
    status = "applied"
    if not np.isclose(clipped_rotation_deg, applied_rotation_deg):
        status = "warning"
        report["confidence_notes"].append(
            "Requested movement-plane rotation exceeded max_rotation_deg and was clipped."
        )

    report["status"] = status
    report["primary_motion_axis"] = {
        h1_axis: float(primary_axis[0]),
        h2_axis: float(primary_axis[1]),
    }
    report["requested_rotation_deg"] = requested_rotation_deg
    report["applied_rotation_deg"] = clipped_rotation_deg
    report["effective_correction_strength"] = effective_strength
    report["out_of_plane_residual_ratio_before"] = _out_of_plane_motion_summary(
        horizontal_vectors,
        0.0,
    )
    report["out_of_plane_residual_ratio_after"] = _out_of_plane_motion_summary(
        horizontal_vectors,
        np.deg2rad(clipped_rotation_deg),
    )

    updated, frame_abs, max_abs, median_abs = _rotate_canonical_columns(
        canonical_columns,
        landmarks=landmarks,
        output_prefix=output_prefix,
        vertical_axis=vertical_axis,
        rotation_rad=float(np.deg2rad(clipped_rotation_deg)),
        index=df.index,
    )
    report["max_abs_correction"] = max_abs
    report["median_abs_correction"] = median_abs
    return updated, report, frame_abs, max_abs, median_abs


def _normalize_height_level(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if not text or text == "UNKNOWN" or text == "NAN":
        return None
    return text


def _resolve_observed_height_level(
    df: pd.DataFrame,
    config: ProtocolHeightLateralWidthAlignmentConfig,
) -> tuple[str | None, list[str]]:
    notes: list[str] = []
    configured = _normalize_height_level(config.observed_height_level)
    if configured is not None:
        return configured, notes

    if config.observed_height_column not in df.columns:
        notes.append(
            f"Observed camera height column '{config.observed_height_column}' missing."
        )
        return None, notes

    values = [
        _normalize_height_level(value)
        for value in df[config.observed_height_column].dropna().unique().tolist()
    ]
    values = [value for value in values if value is not None]
    if not values:
        notes.append("Observed camera height metadata is empty or unknown.")
        return None, notes
    if len(set(values)) > 1:
        notes.append(f"Multiple observed camera height levels found: {values}.")
        return None, notes
    return values[0], notes


def _protocol_anchor_center(
    df: pd.DataFrame,
    canonical_columns: dict[str, Any],
    *,
    output_prefix: str,
    anchor_landmarks: list[str],
    confidence_threshold: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, list[str]], list[str]]:
    coords_by_anchor: list[np.ndarray] = []
    valid_by_anchor: list[np.ndarray] = []
    excluded: dict[str, list[str]] = {}
    notes: list[str] = []

    for landmark in anchor_landmarks:
        cols = _canon_columns(landmark, output_prefix)
        missing = [col for col in cols.values() if col not in canonical_columns]
        if missing:
            excluded.setdefault(landmark, []).append(
                f"missing canonical columns: {missing[:3]}"
            )
            continue

        coords = np.column_stack(
            [
                _series_from_column_data(
                    canonical_columns[cols[axis]], df.index
                ).to_numpy(dtype=float)
                for axis in ("x", "y", "z")
            ]
        )
        valid = np.isfinite(coords).all(axis=1)
        confidence_col = f"{landmark}_confidence"
        if confidence_col in df.columns:
            confidence = df[confidence_col].astype(float).to_numpy()
            valid &= np.isfinite(confidence) & (confidence >= confidence_threshold)
        else:
            notes.append(
                f"{landmark}: confidence column missing; anchor confidence "
                "filter skipped"
            )

        if not bool(valid.any()):
            excluded.setdefault(landmark, []).append("no_valid_anchor_frames")
            continue

        coords_by_anchor.append(coords)
        valid_by_anchor.append(valid)

    if not coords_by_anchor:
        return np.empty((0, 3), dtype=float), np.array([], dtype=bool), excluded, notes

    stacked = np.stack(coords_by_anchor, axis=1)
    valid_stack = np.stack(valid_by_anchor, axis=1)
    stacked = np.where(valid_stack[:, :, None], stacked, 0.0)
    valid_counts = valid_stack.sum(axis=1)
    anchor = np.divide(
        stacked.sum(axis=1),
        valid_counts[:, None],
        out=np.full((len(df), 3), np.nan, dtype=float),
        where=valid_counts[:, None] > 0,
    )
    anchor_valid = np.isfinite(anchor).all(axis=1)
    return anchor, anchor_valid, excluded, notes


def _apply_protocol_height_lateral_width_alignment(
    df: pd.DataFrame,
    canonical_columns: dict[str, Any],
    *,
    landmarks: list[str],
    output_prefix: str,
    config: ProtocolHeightLateralWidthAlignmentConfig,
) -> tuple[dict[str, Any], dict[str, Any], np.ndarray, float, float]:
    if config.method != "height_anchor_lateral_width":
        raise ValueError(
            "Unsupported protocol_height_lateral_width_alignment method: "
            f"{config.method!r}. Use 'height_anchor_lateral_width'."
        )
    if config.near_depth_sign not in {"negative", "positive"}:
        raise ValueError("near_depth_sign must be 'negative' or 'positive'.")
    if config.correction_mode != "near_side_attenuation":
        raise ValueError(
            "Unsupported correction_mode: "
            f"{config.correction_mode!r}. Use 'near_side_attenuation'."
        )

    observed_height, height_notes = _resolve_observed_height_level(df, config)
    recommended_height = _normalize_height_level(config.recommended_height_level)
    height_match = (
        observed_height is not None
        and recommended_height is not None
        and observed_height == recommended_height
    )
    report: dict[str, Any] = {
        "enabled": True,
        "status": "skipped",
        "method": config.method,
        "observed_height_level": observed_height,
        "observed_height_column": config.observed_height_column,
        "recommended_height_level": recommended_height,
        "require_height_match": bool(config.require_height_match),
        "height_match": height_match,
        "anchor_height_level": observed_height if height_match else None,
        "anchor_landmarks": [],
        "near_depth_sign": config.near_depth_sign,
        "correction_mode": config.correction_mode,
        "correction_strength": float(config.correction_strength),
        "max_scale_change": float(config.max_scale_change),
        "max_correction_torso": float(config.max_correction_torso),
        "min_depth_offset_torso": float(config.min_depth_offset_torso),
        "confidence_threshold": float(config.confidence_threshold),
        "num_corrected_values": 0,
        "num_far_side_report_only_values": 0,
        "max_scale_delta": 0.0,
        "max_abs_correction": 0.0,
        "median_abs_correction": 0.0,
        "anchor_frame_coverage": 0.0,
        "excluded_landmark_reasons": {},
        "confidence_notes": height_notes,
    }

    if observed_height is None:
        report["confidence_notes"].append("Observed camera height is unavailable.")
        return canonical_columns, report, np.zeros(len(df), dtype=float), 0.0, 0.0
    if recommended_height is None:
        report["confidence_notes"].append("Recommended camera height is unavailable.")
        return canonical_columns, report, np.zeros(len(df), dtype=float), 0.0, 0.0
    if config.require_height_match and not height_match:
        report["confidence_notes"].append(
            "Observed camera height does not match the exercise protocol."
        )
        return canonical_columns, report, np.zeros(len(df), dtype=float), 0.0, 0.0

    anchor_height = observed_height if height_match else recommended_height
    anchor_landmarks = [
        landmark
        for landmark in config.height_anchor_map.get(anchor_height, [])
        if landmark in landmarks
    ]
    report["anchor_height_level"] = anchor_height
    report["anchor_landmarks"] = anchor_landmarks
    if not anchor_landmarks:
        report["confidence_notes"].append(
            f"No anchor landmarks available for height level {anchor_height}."
        )
        return canonical_columns, report, np.zeros(len(df), dtype=float), 0.0, 0.0

    anchor, anchor_valid, excluded, notes = _protocol_anchor_center(
        df,
        canonical_columns,
        output_prefix=output_prefix,
        anchor_landmarks=anchor_landmarks,
        confidence_threshold=float(config.confidence_threshold),
    )
    report["excluded_landmark_reasons"].update(excluded)
    report["confidence_notes"].extend(notes)
    if len(anchor_valid) == 0 or not bool(anchor_valid.any()):
        report["confidence_notes"].append("No valid anchor frames for height prior.")
        return canonical_columns, report, np.zeros(len(df), dtype=float), 0.0, 0.0

    report["anchor_frame_coverage"] = float(anchor_valid.mean())
    axis_idx = _axis_index()
    target_landmarks = config.apply_to_landmarks or landmarks
    anchor_set = set(anchor_landmarks)
    updated = dict(canonical_columns)
    frame_abs_correction = np.zeros(len(df), dtype=float)
    frame_scale_delta = np.zeros(len(df), dtype=float)
    abs_corrections: list[np.ndarray] = []
    corrected_values = 0
    far_side_report_only_values = 0

    for landmark in target_landmarks:
        if landmark not in landmarks:
            continue
        if config.preserve_anchor_landmarks and landmark in anchor_set:
            continue

        cols = _canon_columns(landmark, output_prefix)
        missing = [col for col in cols.values() if col not in canonical_columns]
        if missing:
            report["excluded_landmark_reasons"].setdefault(landmark, []).append(
                f"missing canonical columns: {missing[:3]}"
            )
            continue

        coords = np.column_stack(
            [
                _series_from_column_data(
                    canonical_columns[cols[axis]], df.index
                ).to_numpy(dtype=float)
                for axis in ("x", "y", "z")
            ]
        )
        valid = anchor_valid & np.isfinite(coords).all(axis=1)
        confidence_col = f"{landmark}_confidence"
        if confidence_col in df.columns:
            confidence = df[confidence_col].astype(float).to_numpy()
            valid &= np.isfinite(confidence) & (
                confidence >= config.confidence_threshold
            )

        depth_offset = coords[:, axis_idx["z"]] - anchor[:, axis_idx["z"]]
        if config.near_depth_sign == "negative":
            near_mask = depth_offset <= -float(config.min_depth_offset_torso)
            far_mask = depth_offset >= float(config.min_depth_offset_torso)
        else:
            near_mask = depth_offset >= float(config.min_depth_offset_torso)
            far_mask = depth_offset <= -float(config.min_depth_offset_torso)

        apply_mask = valid & near_mask
        far_side_report_only_values += int((valid & far_mask).sum())
        if not bool(apply_mask.any()):
            continue

        scale_delta = np.zeros(len(df), dtype=float)
        scale_delta[apply_mask] = np.clip(
            np.abs(depth_offset[apply_mask]) * float(config.correction_strength),
            0.0,
            float(config.max_scale_change),
        )
        x_rel = coords[:, axis_idx["x"]] - anchor[:, axis_idx["x"]]
        correction = x_rel * scale_delta
        correction_clipped = np.clip(
            correction,
            -float(config.max_correction_torso),
            float(config.max_correction_torso),
        )

        corrected_x = coords[:, axis_idx["x"]] - correction_clipped
        output_x = coords[:, axis_idx["x"]].copy()
        output_x[apply_mask] = corrected_x[apply_mask]
        updated[cols["x"]] = output_x

        abs_correction = np.abs(correction_clipped)
        abs_correction[~apply_mask] = 0.0
        abs_corrections.append(abs_correction[apply_mask])
        corrected_values += int(apply_mask.sum())
        frame_abs_correction = np.maximum(frame_abs_correction, abs_correction)
        frame_scale_delta = np.maximum(frame_scale_delta, scale_delta)

    if corrected_values == 0:
        report["confidence_notes"].append(
            "No near-side frames met the correction criteria."
        )
        report["num_far_side_report_only_values"] = far_side_report_only_values
        return updated, report, frame_abs_correction, 0.0, 0.0

    all_abs = np.concatenate(abs_corrections)
    finite_abs = all_abs[np.isfinite(all_abs)]
    max_abs = float(np.max(finite_abs)) if len(finite_abs) else 0.0
    median_abs = float(np.median(finite_abs)) if len(finite_abs) else 0.0
    status = "applied"
    if max_abs >= float(config.max_correction_torso):
        status = "warning"
        report["confidence_notes"].append(
            "Protocol-height lateral correction reached max_correction_torso."
        )

    report["status"] = status
    report["num_corrected_values"] = corrected_values
    report["num_far_side_report_only_values"] = far_side_report_only_values
    report["max_scale_delta"] = float(np.max(frame_scale_delta))
    report["max_abs_correction"] = max_abs
    report["median_abs_correction"] = median_abs
    updated["canonicalization_lateral_width_scale_delta_frame"] = frame_scale_delta
    return updated, report, frame_abs_correction, max_abs, median_abs


def _confidence_pair_valid(
    df: pd.DataFrame,
    proximal: str,
    distal: str,
    threshold: float,
) -> np.ndarray:
    valid = np.ones(len(df), dtype=bool)
    for landmark in (proximal, distal):
        confidence_col = f"{landmark}_confidence"
        if confidence_col not in df.columns:
            continue
        confidence = df[confidence_col].astype(float).to_numpy()
        valid &= np.isfinite(confidence) & (confidence >= threshold)
    return valid


def _apply_xy_depth_lift(
    df: pd.DataFrame,
    canonical_columns: dict[str, Any],
    *,
    landmarks: list[str],
    output_prefix: str,
    config: XYDepthLiftConfig,
) -> tuple[dict[str, Any], dict[str, Any], np.ndarray, float, float]:
    if config.method != "recording_view_depth_hypothesis":
        raise ValueError(
            "Unsupported xy_depth_lift method: "
            f"{config.method!r}. Use 'recording_view_depth_hypothesis'."
        )
    if config.depth_sign not in {"positive", "negative"}:
        raise ValueError("xy_depth_lift.depth_sign must be 'positive' or 'negative'.")

    report: dict[str, Any] = {
        "enabled": True,
        "status": "skipped",
        "method": config.method,
        "source_axes": ["x", "y"],
        "target_axes": ["x", "y", "z"],
        "segment_pairs": [list(pair) for pair in config.segment_pairs],
        "default_segment_length_torso": float(config.default_segment_length_torso),
        "max_depth_torso": float(config.max_depth_torso),
        "confidence_threshold": float(config.confidence_threshold),
        "depth_sign": config.depth_sign,
        "num_accepted_values": 0,
        "num_rejected_values": 0,
        "rejection_reasons": {},
        "max_abs_correction": 0.0,
        "median_abs_correction": 0.0,
        "confidence_notes": [
            "xy_depth_lift emits low-confidence canonical depth hypothesis evidence."
        ],
    }

    if config.default_segment_length_torso <= 0:
        report["confidence_notes"].append("default_segment_length_torso must be > 0.")
        return canonical_columns, report, np.zeros(len(df), dtype=float), 0.0, 0.0
    if config.max_depth_torso <= 0:
        report["confidence_notes"].append("max_depth_torso must be > 0.")
        return canonical_columns, report, np.zeros(len(df), dtype=float), 0.0, 0.0

    updated = dict(canonical_columns)
    index = df.index
    n_frames = len(df)
    sign = 1.0 if config.depth_sign == "positive" else -1.0
    frame_abs_correction = np.zeros(n_frames, dtype=float)
    frame_burden = np.zeros(n_frames, dtype=float)
    frame_residual = np.full(n_frames, np.nan, dtype=float)
    frame_available = np.zeros(n_frames, dtype=bool)
    frame_reason = np.full(n_frames, "", dtype=object)
    accepted_corrections: list[np.ndarray] = []
    rejection_counts: dict[str, int] = {}

    for landmark in landmarks:
        cols = _canon_columns(landmark, output_prefix)
        if cols["z"] not in updated:
            updated[cols["z"]] = np.full(n_frames, np.nan, dtype=float)

    def record_rejection(mask: np.ndarray, reason: str) -> None:
        count = int(np.sum(mask))
        if count <= 0:
            return
        rejection_counts[reason] = rejection_counts.get(reason, 0) + count
        empty = frame_reason == ""
        frame_reason[mask & empty] = reason

    for proximal, distal in config.segment_pairs:
        if proximal not in landmarks or distal not in landmarks:
            continue
        prox_cols = _canon_columns(proximal, output_prefix)
        dist_cols = _canon_columns(distal, output_prefix)
        required = [
            prox_cols["x"],
            prox_cols["y"],
            prox_cols["z"],
            dist_cols["x"],
            dist_cols["y"],
            dist_cols["z"],
        ]
        if any(column not in updated for column in required):
            continue

        prox_xy = np.column_stack(
            [
                _series_from_column_data(updated[prox_cols[axis]], index).to_numpy(
                    dtype=float
                )
                for axis in ("x", "y")
            ]
        )
        dist_xy = np.column_stack(
            [
                _series_from_column_data(updated[dist_cols[axis]], index).to_numpy(
                    dtype=float
                )
                for axis in ("x", "y")
            ]
        )
        d_xy = np.linalg.norm(dist_xy - prox_xy, axis=1)
        target = float(config.default_segment_length_torso)
        finite = np.isfinite(d_xy)
        confident = _confidence_pair_valid(
            df,
            proximal,
            distal,
            float(config.confidence_threshold),
        )
        inside_projection = finite & (d_xy <= target)
        dz_abs = np.sqrt(np.clip(target**2 - d_xy**2, 0.0, None))
        within_cap = np.isfinite(dz_abs) & (dz_abs <= float(config.max_depth_torso))
        accepted = confident & inside_projection & within_cap

        record_rejection(~finite, "nonfinite_xy_projection")
        record_rejection(finite & ~confident, "confidence_below_threshold")
        record_rejection(
            finite & confident & ~inside_projection, "projected_length_exceeds_prior"
        )
        record_rejection(
            finite & confident & inside_projection & ~within_cap,
            "depth_hypothesis_exceeds_cap",
        )

        if not bool(accepted.any()):
            continue

        prox_z = _series_from_column_data(updated[prox_cols["z"]], index).to_numpy(
            dtype=float
        )
        prox_z = np.where(np.isfinite(prox_z), prox_z, 0.0)
        dist_z = _series_from_column_data(updated[dist_cols["z"]], index).to_numpy(
            dtype=float
        )
        dist_z = np.where(np.isfinite(dist_z), dist_z, prox_z + sign * dz_abs)
        dist_z[accepted] = prox_z[accepted] + sign * dz_abs[accepted]
        updated[prox_cols["z"]] = prox_z
        updated[dist_cols["z"]] = dist_z

        segment_3d = np.sqrt(d_xy**2 + (dist_z - prox_z) ** 2)
        residual = np.abs(segment_3d - target)
        frame_residual[accepted] = np.nanmax(
            np.column_stack(
                [
                    np.nan_to_num(frame_residual, nan=0.0),
                    np.nan_to_num(residual, nan=0.0),
                ]
            ),
            axis=1,
        )[accepted]
        correction_abs = np.abs(dz_abs)
        burden = correction_abs / float(config.max_depth_torso)
        frame_abs_correction = np.maximum(
            frame_abs_correction,
            np.nan_to_num(correction_abs, nan=0.0),
        )
        frame_burden = np.maximum(frame_burden, np.nan_to_num(burden, nan=0.0))
        frame_available |= accepted
        accepted_corrections.append(correction_abs[accepted])

    if accepted_corrections:
        accepted_values = np.concatenate(accepted_corrections)
        finite_values = accepted_values[np.isfinite(accepted_values)]
        report["status"] = "applied"
        report["num_accepted_values"] = int(len(finite_values))
        report["max_abs_correction"] = (
            float(np.max(finite_values)) if len(finite_values) else 0.0
        )
        report["median_abs_correction"] = (
            float(np.median(finite_values)) if len(finite_values) else 0.0
        )
    else:
        report["confidence_notes"].append("No segment passed xy-depth-lift gates.")

    report["num_rejected_values"] = int(sum(rejection_counts.values()))
    report["rejection_reasons"] = rejection_counts

    updated["canonical_depth_hypothesis_available"] = frame_available
    updated["canonical_depth_hypothesis_confidence"] = np.where(
        frame_available,
        "low",
        "not_available",
    )
    updated["canonical_depth_hypothesis_quality_gravity"] = np.where(
        frame_available,
        _quality_gravity_from_confidence("low"),
        0.0,
    )
    updated["canonical_depth_hypothesis_rejection_reason"] = frame_reason

    accepted_burden = frame_burden[frame_available & np.isfinite(frame_burden)]
    accepted_residual = frame_residual[frame_available & np.isfinite(frame_residual)]
    report["quality_diagnostics"] = {
        "max_correction_burden": (
            float(np.max(accepted_burden)) if accepted_burden.size else None
        ),
        "median_correction_burden": (
            float(np.median(accepted_burden)) if accepted_burden.size else None
        ),
        "max_residual_torso": (
            float(np.max(accepted_residual)) if accepted_residual.size else None
        ),
        "median_residual_torso": (
            float(np.median(accepted_residual)) if accepted_residual.size else None
        ),
    }

    return (
        updated,
        report,
        frame_abs_correction,
        float(report["max_abs_correction"]),
        float(report["median_abs_correction"]),
    )


def _empty_report(config: CanonicalizationConfig, status: str) -> dict[str, Any]:
    data_confidence = {"level": "high", "reasons": []}
    evidence_summary = _canonicalization_evidence_summary(
        status=status,
        max_correction=0.0,
        data_confidence=data_confidence,
        config=config.data_confidence,
    )
    return {
        "enabled": config.enabled,
        **evidence_summary,
        "status": status,
        "coordinate_mode": config.coordinate_mode,
        "output_prefix": config.output_prefix,
        "report_only": config.report_only,
        "downstream_coordinate_mode": config.downstream_coordinate_mode,
        "active_priors": [],
        "applied_priors": [],
        "skipped_priors": {},
        "max_correction_torso": 0.0,
        "median_correction_torso": 0.0,
        "residual_after_fit_torso": None,
        "data_confidence": data_confidence,
        "prior_reports": {
            "xy_depth_lift": None,
            "support_plane_alignment": None,
            "movement_plane_alignment": None,
            "protocol_height_lateral_width_alignment": None,
        },
    }


def _attach_pose_state_report_fields(
    report: dict[str, Any],
    *,
    input_state: str,
    output_state: str,
    input_families: list[str],
    output_families: list[str],
    added_family: str | None,
    input_axes: dict[str, list[str]] | None = None,
    output_axes: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    fields = {
        "input_pose_data_state": input_state,
        "output_pose_data_state": output_state,
        "input_coordinate_families": input_families,
        "output_coordinate_families": output_families,
        "added_coordinate_family": added_family,
    }
    if input_axes is not None:
        fields["input_coordinate_axes"] = input_axes
    if output_axes is not None:
        fields["output_coordinate_axes"] = output_axes
    report.update(fields)
    return report


def apply_canonicalization(
    df: pd.DataFrame,
    landmarks: list[str],
    config: CanonicalizationConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply optional analysis-space canonicalization.

    Disabled configs return a dataframe copy and a disabled report. Enabled
    configs always start by copying the selected source coordinate family to
    `<landmark>_canon_x/y/z`; priors then update that canon family when applied.
    """

    if config is None:
        config = CanonicalizationConfig()

    result = df.copy()
    input_pose_data_state = get_pose_data_state(df)
    input_coordinate_families = get_coordinate_families(df)
    input_coordinate_axes = get_coordinate_axes(df)
    if not config.enabled:
        set_pose_data_state(
            result,
            input_pose_data_state,
            input_coordinate_families,
            input_coordinate_axes,
        )
        report = _attach_pose_state_report_fields(
            _empty_report(config, "disabled"),
            input_state=input_pose_data_state,
            output_state=input_pose_data_state,
            input_families=input_coordinate_families,
            output_families=input_coordinate_families,
            added_family=None,
            input_axes=input_coordinate_axes,
            output_axes=input_coordinate_axes,
        )
        return result, report

    source_axes = _resolve_source_axes(
        result,
        landmarks=landmarks,
        coordinate_mode=config.coordinate_mode,
    )
    canonical_columns = _copy_base_coordinates(
        result,
        landmarks=landmarks,
        coordinate_mode=config.coordinate_mode,
        output_prefix=config.output_prefix,
        axes=source_axes,
    )

    active_priors: list[str] = []
    applied_priors: list[str] = []
    skipped_priors: dict[str, str] = {}
    prior_reports: dict[str, Any] = {
        "xy_depth_lift": None,
        "support_plane_alignment": None,
        "movement_plane_alignment": None,
        "protocol_height_lateral_width_alignment": None,
    }
    max_correction = 0.0
    median_correction = 0.0
    residual_after_fit: float | None = None
    confidence_notes: list[str] = []

    if config.xy_depth_lift.enabled:
        active_priors.append("xy_depth_lift")
        if "z" in source_axes:
            prior_reports["xy_depth_lift"] = {
                "enabled": True,
                "status": "skipped",
                "reason": "source_z_present",
                "source_axes": list(source_axes),
                "target_axes": list(source_axes),
                "confidence_notes": [
                    "xy_depth_lift is used only when the selected source family has x/y but no z."
                ],
            }
            skipped_priors["xy_depth_lift"] = "skipped"
            confidence_notes.append(
                "xy_depth_lift skipped because source z is present."
            )
        else:
            (
                canonical_columns,
                xy_lift_report,
                xy_lift_frame_abs,
                xy_lift_max_correction,
                xy_lift_median_correction,
            ) = _apply_xy_depth_lift(
                result,
                canonical_columns,
                landmarks=landmarks,
                output_prefix=config.output_prefix,
                config=config.xy_depth_lift,
            )
            prior_reports["xy_depth_lift"] = xy_lift_report

            if xy_lift_report["status"] in {"applied", "warning"}:
                applied_priors.append("xy_depth_lift")
                max_correction = max(max_correction, xy_lift_max_correction)
                median_correction = max(
                    median_correction,
                    xy_lift_median_correction,
                )
                canonical_columns["canonicalization_correction_abs_frame"] = (
                    xy_lift_frame_abs
                )
                confidence_notes.extend(xy_lift_report["confidence_notes"])
            else:
                skipped_priors["xy_depth_lift"] = xy_lift_report["status"]
                confidence_notes.extend(xy_lift_report["confidence_notes"])

    support_config = config.support_plane_alignment
    if support_config.enabled:
        active_priors.append("support_plane_alignment")
        if "z" not in source_axes:
            prior_reports["support_plane_alignment"] = {
                "enabled": True,
                "status": "skipped",
                "reason": "missing_source_z",
                "coordinate_mode": config.coordinate_mode,
                "confidence_notes": [
                    "support_plane_alignment requires an x/y/z source family."
                ],
            }
            skipped_priors["support_plane_alignment"] = "skipped"
            confidence_notes.append(
                "support_plane_alignment skipped because source z is absent."
            )
        else:
            support_config = replace(
                support_config, coordinate_mode=config.coordinate_mode
            )
            floor_df, floor_report = apply_floor_relative_correction(
                result,
                landmarks=landmarks,
                config=support_config,
            )
            floor_report_dict = floor_report.as_dict()
            prior_reports["support_plane_alignment"] = floor_report_dict

            if floor_report.status in {"applied", "warning"}:
                applied_priors.append("support_plane_alignment")
                for landmark in landmarks:
                    dst = _canon_columns(landmark, config.output_prefix)
                    for axis in ("x", "y", "z"):
                        floor_col = f"{landmark}_floor_{axis}"
                        if floor_col in floor_df.columns:
                            canonical_columns[dst[axis]] = floor_df[floor_col]

                for landmark in floor_report.diagnostic_landmarks:
                    floor_height_col = f"{landmark}_floor_height"
                    if floor_height_col in floor_df.columns:
                        canonical_columns[
                            f"{landmark}_{config.output_prefix}_support_plane_height"
                        ] = floor_df[floor_height_col]

                if "floor_correction_abs_frame" in floor_df.columns:
                    canonical_columns["canonicalization_correction_abs_frame"] = (
                        floor_df["floor_correction_abs_frame"]
                    )
                if "floor_correction_transform" in floor_df.columns:
                    canonical_columns["canonicalization_support_plane_transform"] = (
                        floor_df["floor_correction_transform"]
                    )

                max_correction = max(max_correction, floor_report.max_abs_correction)
                median_correction = max(
                    median_correction,
                    floor_report.median_abs_correction,
                )
                residual_after_fit = floor_report.anchor_residual_summary.get("max")
                confidence_notes.extend(floor_report.confidence_notes)
            else:
                skipped_priors["support_plane_alignment"] = floor_report.status
                confidence_notes.extend(floor_report.confidence_notes)

    if config.movement_plane_alignment.enabled:
        active_priors.append("movement_plane_alignment")
        (
            canonical_columns,
            movement_report,
            movement_frame_abs,
            movement_max_correction,
            movement_median_correction,
        ) = _apply_movement_plane_alignment(
            result,
            canonical_columns,
            landmarks=landmarks,
            output_prefix=config.output_prefix,
            config=config.movement_plane_alignment,
            vertical_axis=config.support_plane_alignment.vertical_axis,
        )
        prior_reports["movement_plane_alignment"] = movement_report

        if movement_report["status"] in {"applied", "warning"}:
            applied_priors.append("movement_plane_alignment")
            max_correction = max(max_correction, movement_max_correction)
            median_correction = max(
                median_correction,
                movement_median_correction,
            )
            if "canonicalization_correction_abs_frame" in canonical_columns:
                previous_frame_abs = _series_from_column_data(
                    canonical_columns["canonicalization_correction_abs_frame"],
                    result.index,
                ).to_numpy(dtype=float)
                movement_frame_abs = np.maximum(
                    np.nan_to_num(
                        previous_frame_abs,
                        nan=0.0,
                        posinf=0.0,
                        neginf=0.0,
                    ),
                    np.nan_to_num(
                        movement_frame_abs,
                        nan=0.0,
                        posinf=0.0,
                        neginf=0.0,
                    ),
                )
            canonical_columns["canonicalization_correction_abs_frame"] = (
                movement_frame_abs
            )
            confidence_notes.extend(movement_report["confidence_notes"])
        else:
            skipped_priors["movement_plane_alignment"] = movement_report["status"]
            confidence_notes.extend(movement_report["confidence_notes"])

    protocol_config = config.protocol_height_lateral_width_alignment
    if protocol_config.enabled:
        active_priors.append("protocol_height_lateral_width_alignment")
        (
            canonical_columns,
            protocol_report,
            protocol_frame_abs,
            protocol_max_correction,
            protocol_median_correction,
        ) = _apply_protocol_height_lateral_width_alignment(
            result,
            canonical_columns,
            landmarks=landmarks,
            output_prefix=config.output_prefix,
            config=protocol_config,
        )
        prior_reports["protocol_height_lateral_width_alignment"] = protocol_report

        if protocol_report["status"] in {"applied", "warning"}:
            applied_priors.append("protocol_height_lateral_width_alignment")
            max_correction = max(max_correction, protocol_max_correction)
            median_correction = max(
                median_correction,
                protocol_median_correction,
            )
            if "canonicalization_correction_abs_frame" in canonical_columns:
                previous_frame_abs = _series_from_column_data(
                    canonical_columns["canonicalization_correction_abs_frame"],
                    result.index,
                ).to_numpy(dtype=float)
                protocol_frame_abs = np.maximum(
                    np.nan_to_num(
                        previous_frame_abs,
                        nan=0.0,
                        posinf=0.0,
                        neginf=0.0,
                    ),
                    np.nan_to_num(
                        protocol_frame_abs,
                        nan=0.0,
                        posinf=0.0,
                        neginf=0.0,
                    ),
                )
            canonical_columns["canonicalization_correction_abs_frame"] = (
                protocol_frame_abs
            )
            confidence_notes.extend(protocol_report["confidence_notes"])
        else:
            skipped_priors["protocol_height_lateral_width_alignment"] = protocol_report[
                "status"
            ]
            confidence_notes.extend(protocol_report["confidence_notes"])

    if not active_priors:
        status = "skipped"
    elif applied_priors and skipped_priors:
        status = "partial"
    elif applied_priors:
        status = "applied"
    else:
        status = "rejected"

    data_confidence = (
        _confidence_level(
            max_correction=max_correction,
            residual_after_fit=residual_after_fit,
            notes=confidence_notes,
            config=config.data_confidence,
        )
        if config.data_confidence.emit
        else {"level": "not_emitted", "reasons": []}
    )
    evidence_summary = _canonicalization_evidence_summary(
        status=status,
        max_correction=max_correction,
        data_confidence=data_confidence,
        config=config.data_confidence,
    )

    report = {
        "enabled": True,
        **evidence_summary,
        "status": status,
        "coordinate_mode": config.coordinate_mode,
        "source_coordinate_family": _source_family(config.coordinate_mode),
        "source_coordinate_axes": list(source_axes),
        "output_prefix": config.output_prefix,
        "report_only": config.report_only,
        "downstream_coordinate_mode": config.downstream_coordinate_mode,
        "active_priors": active_priors,
        "applied_priors": applied_priors,
        "skipped_priors": skipped_priors,
        "max_correction_torso": float(max_correction),
        "median_correction_torso": float(median_correction),
        "residual_after_fit_torso": (
            None if residual_after_fit is None else float(residual_after_fit)
        ),
        "data_confidence": data_confidence,
        "prior_reports": prior_reports,
    }

    canonical_columns["canonicalization_valid"] = status in {"applied", "partial"}
    canonical_columns["canonicalization_evidence_available"] = evidence_summary[
        "evidence_available"
    ]
    canonical_columns["canonicalization_evidence_confidence"] = evidence_summary[
        "evidence_confidence"
    ]
    canonical_columns["canonicalization_quality_gravity"] = evidence_summary[
        "quality_gravity"
    ]
    canonical_columns["canonicalization_status"] = status
    canonical_columns["canonicalization_confidence"] = data_confidence["level"]
    canonical_columns["canonicalization_note"] = "; ".join(confidence_notes)

    result = pd.concat(
        [result, pd.DataFrame(canonical_columns, index=result.index)],
        axis=1,
    )
    output_coordinate_families = list(input_coordinate_families)
    if config.output_prefix not in output_coordinate_families:
        output_coordinate_families.append(config.output_prefix)
    output_coordinate_axes = dict(input_coordinate_axes)
    output_coordinate_axes[config.output_prefix] = _canonical_axes_from_columns(
        canonical_columns,
        landmarks=landmarks,
        output_prefix=config.output_prefix,
    )
    set_pose_data_state(
        result,
        CANONICALIZED_POSE_DATA,
        output_coordinate_families,
        output_coordinate_axes,
    )
    _attach_pose_state_report_fields(
        report,
        input_state=input_pose_data_state,
        output_state=CANONICALIZED_POSE_DATA,
        input_families=input_coordinate_families,
        output_families=output_coordinate_families,
        added_family=config.output_prefix,
        input_axes=input_coordinate_axes,
        output_axes=output_coordinate_axes,
    )
    return result, report
