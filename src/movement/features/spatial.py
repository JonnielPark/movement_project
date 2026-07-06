"""
⑧ Spatial Features

Computes range of motion, role alignment, movement path, and support consistency features.

Unit convention:
  angle-based features : degree
  distance-based features : torso_length_ratio

Input: normalized pose dataframe (norm columns) and ExerciseDefinition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from movement.core.config import LANDMARKS
from movement.features import FeatureRecord

if TYPE_CHECKING:
    from movement.definitions.exercise_definition import ExerciseDefinition


def _norm_xyz(df: pd.DataFrame, lm: str) -> np.ndarray:
    """(T, 3) normalized coordinates; falls back to raw if norm columns absent."""
    ncols = [f"{lm}_norm_x", f"{lm}_norm_y", f"{lm}_norm_z"]
    if all(c in df.columns for c in ncols):
        return df[ncols].values.astype(float)
    return df[[f"{lm}_x", f"{lm}_y", f"{lm}_z"]].values.astype(float)


def _norm_xy(df: pd.DataFrame, lm: str) -> np.ndarray:
    """(T, 2) normalized camera-plane coordinates; falls back to raw x/y."""
    ncols = [f"{lm}_norm_x", f"{lm}_norm_y"]
    if all(c in df.columns for c in ncols):
        return df[ncols].values.astype(float)
    return df[[f"{lm}_x", f"{lm}_y"]].values.astype(float)


_SUPPORT_REGION_ANCHORS: dict[str, tuple[str, ...]] = {
    "left_foot": ("left_ankle",),
    "right_foot": ("right_ankle",),
    "left_hand": ("left_wrist",),
    "right_hand": ("right_wrist",),
}


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _support_landmarks(
    exercise_definition: "ExerciseDefinition",
    primary_joints: list[str],
) -> list[str]:
    """Infer support landmarks from exercise support context."""
    support = getattr(exercise_definition, "support_context", {}) or {}
    classification = getattr(exercise_definition, "classification", {}) or {}
    kinetic_chain = str(classification.get("kinetic_chain", "")).lower()
    if not support and "closed_chain" not in kinetic_chain:
        return []

    support_regions = []
    support_regions.extend(support.get("contact_points") or [])
    support_regions.extend(support.get("weight_bearing_regions") or [])
    base_of_support = str(support.get("base_of_support", "")).lower()
    if base_of_support in {"bilateral_feet", "split_stance"}:
        support_regions.extend(["left_foot", "right_foot"])
    elif base_of_support == "hands_and_feet":
        support_regions.extend(["left_hand", "right_hand", "left_foot", "right_foot"])

    anchors: list[str] = []
    for region in support_regions:
        anchors.extend(_SUPPORT_REGION_ANCHORS.get(str(region), ()))

    primary = set(primary_joints)
    return [anchor for anchor in _unique_preserve_order(anchors) if anchor in primary]


def _support_source_fields(support: dict[str, Any]) -> list[str]:
    fields = ["support"]
    if support.get("base_of_support") is not None:
        fields.append("support.base_of_support")
    if support.get("contact_points"):
        fields.append("support.contact_points")
    if support.get("weight_bearing_regions"):
        fields.append("support.weight_bearing_regions")
    return fields


def _support_consistency_axis_records(
    coords: np.ndarray,
    jname: str,
    *,
    exercise_id: str,
    rep_id: int | None,
    source_fields: list[str],
) -> list[FeatureRecord]:
    diffs = np.diff(coords, axis=0)
    if len(diffs) == 0:
        return []

    axis_values = {
        "x": float(np.nansum(np.abs(diffs[:, 0]))),
        "y": float(np.nansum(np.abs(diffs[:, 1]))),
        "z": float(np.nansum(np.abs(diffs[:, 2]))),
        "xy": float(np.nansum(np.linalg.norm(diffs[:, :2], axis=1))),
    }
    records: list[FeatureRecord] = []
    for axis, value in axis_values.items():
        records.append(
            FeatureRecord(
                feature_id=f"spatial.support_consistency.axis_path_{axis}.{jname}",
                exercise_id=exercise_id,
                rep_id=rep_id,
                value=round(value, 4),
                unit="torso_length_ratio",
                source_fields=source_fields
                + ["feature_domains.spatial", "support_consistency.axis_diagnostic"],
                note=(
                    "Report-only closed-chain support-landmark path diagnostic. "
                    "Use it to separate recording-view axis motion from depth "
                    "or mixed-axis jitter before interpreting support movement."
                ),
                availability="not_assessed",
                availability_reasons=[
                    "support_consistency_axis_diagnostic_report_only"
                ],
                depth_dependency="high" if axis == "z" else "none",
            )
        )
    return records


def _max_xy_drift_from_median(coords: np.ndarray) -> float:
    if len(coords) == 0:
        return 0.0
    xy = coords[:, :2]
    if np.isnan(xy).all():
        return 0.0
    center = np.nanmedian(xy, axis=0)
    drift = np.linalg.norm(xy - center, axis=1)
    return float(np.nanmax(drift)) if len(drift) else 0.0


def _support_width_normalized_imbalance(
    left_value: float,
    right_value: float,
    support_width: float,
) -> float:
    if not np.isfinite(support_width) or support_width <= 1e-9:
        return 0.0
    return abs(left_value - right_value) / support_width


def _bilateral_support_pair(anchors: list[str]) -> tuple[str, str] | None:
    for pair in (("left_ankle", "right_ankle"), ("left_wrist", "right_wrist")):
        if pair[0] in anchors and pair[1] in anchors:
            return pair
    return None


def compute_support_consistency(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """Compute recording-view support-consistency proxies.

    These features represent base-of-support consistency for fixed closed-chain
    support. They use normalized x/y coordinates only and do not treat monocular
    depth as movement-quality evidence.
    """
    primary_joints: list[str] = exercise_definition.landmarks.primary_joints or []
    if not primary_joints:
        return []

    support = getattr(exercise_definition, "support_context", {}) or {}
    support_fields = _support_source_fields(support)
    support_landmarks = _support_landmarks(exercise_definition, primary_joints)
    if not support_landmarks:
        return []

    ex_id = exercise_definition.exercise_id
    records: list[FeatureRecord] = []
    coords_by_anchor: dict[str, np.ndarray] = {}
    xy_drift_by_anchor: dict[str, float] = {}

    for anchor in support_landmarks:
        try:
            coords = _norm_xyz(df, anchor)
        except KeyError:
            continue
        coords_by_anchor[anchor] = coords
        xy_drift = _max_xy_drift_from_median(coords)
        xy_drift_by_anchor[anchor] = xy_drift
        records.append(
            FeatureRecord(
                feature_id=f"spatial.support_consistency.point_drift_xy.{anchor}",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(xy_drift, 4),
                unit="torso_length_ratio",
                source_fields=support_fields
                + ["feature_domains.spatial", "support_consistency.recording_view_xy"],
                note=(
                    "Recording-view support-consistency proxy. Interprets "
                    "support-point x/y drift relative to the median contact "
                    "position, not as ankle/wrist joint ROM."
                ),
                depth_dependency="none",
            )
        )

    pair = _bilateral_support_pair(list(coords_by_anchor))
    if pair is None:
        return records

    left, right = pair
    left_xy = coords_by_anchor[left][:, :2]
    right_xy = coords_by_anchor[right][:, :2]
    widths = np.linalg.norm(left_xy - right_xy, axis=1)
    width_mean = float(np.nanmean(widths)) if len(widths) else 0.0
    balance_value = _support_width_normalized_imbalance(
        xy_drift_by_anchor.get(left, 0.0),
        xy_drift_by_anchor.get(right, 0.0),
        width_mean,
    )
    records.append(
        FeatureRecord(
            feature_id=f"spatial.role_alignment.left_right.support_consistency_xy_drift.{left}_{right}",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(balance_value, 4),
            unit="dimensionless",
            source_fields=support_fields
            + [
                "feature_domains.spatial",
                "support_consistency.recording_view_xy",
                "support_consistency.left_right_drift_role_alignment",
            ],
            note=(
                "Recording-view left/right support-consistency role-alignment proxy. "
                "Compares support-point x/y drift difference normalized by "
                "support width and does not use monocular depth."
            ),
            depth_dependency="none",
        )
    )
    if np.isfinite(width_mean) and width_mean > 1e-9:
        width_cv = float(np.nanstd(widths) / width_mean)
        records.append(
            FeatureRecord(
                feature_id="spatial.support_consistency.width_variation_xy",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(width_cv, 4),
                unit="dimensionless_cv",
                source_fields=support_fields
                + ["feature_domains.spatial", "support_consistency.recording_view_xy"],
                note=(
                    "Recording-view base-of-support consistency proxy. Lower "
                    "values indicate more consistent bilateral support width."
                ),
                depth_dependency="none",
            )
        )

    support_center = (left_xy + right_xy) / 2.0
    records.append(
        FeatureRecord(
            feature_id="spatial.support_consistency.center_drift_xy",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(_max_xy_drift_from_median(support_center), 4),
            unit="torso_length_ratio",
            source_fields=support_fields
            + ["feature_domains.spatial", "support_consistency.recording_view_xy"],
            note=(
                "Recording-view support-center consistency proxy for bilateral "
                "closed-chain support."
            ),
            depth_dependency="none",
        )
    )

    return records


def _movement_path_axis_records(
    coords: np.ndarray,
    jname: str,
    *,
    exercise_id: str,
    rep_id: int | None,
    source_fields: list[str],
    assessed_axes: set[str] | None = None,
    variant_note: str | None = None,
    include_single_axis_diagnostics: bool = True,
) -> list[FeatureRecord]:
    diffs = np.diff(coords, axis=0)
    if len(diffs) == 0:
        return []

    assessed_axes = assessed_axes or {"xy", "xyz"}
    axis_values = {
        "xy": float(np.nansum(np.linalg.norm(diffs[:, :2], axis=1))),
        "xyz": float(np.nansum(np.linalg.norm(diffs, axis=1))),
        "x": float(np.nansum(np.abs(diffs[:, 0]))),
        "y": float(np.nansum(np.abs(diffs[:, 1]))),
        "z": float(np.nansum(np.abs(diffs[:, 2]))),
    }
    records: list[FeatureRecord] = []
    for axis, value in axis_values.items():
        if axis in {"x", "y", "z"} and not include_single_axis_diagnostics:
            continue
        is_assessed_axis = axis in assessed_axes
        axis_source_fields = source_fields + ["feature_domains.spatial"]
        if axis in {"x", "y", "z"}:
            axis_source_fields.append("spatial.movement_path.axis_diagnostic")
        elif axis == "xy":
            axis_source_fields.append("spatial.movement_path.recording_view_xy_scoring")
        elif axis == "xyz":
            axis_source_fields.append("spatial.movement_path.depth_sensitive_xyz")
        if variant_note is not None and axis in {"xy", "xyz"}:
            note = variant_note
        elif axis == "xy":
            note = "Recording-view movement-path scoring candidate."
        elif axis == "xyz":
            note = (
                "Mixed-axis movement-path evidence. Score with depth-sensitive "
                "gravity under monocular pose."
            )
        else:
            note = (
                "Report-only movement-path axis diagnostic. Use it to "
                "separate recording-view path evidence from "
                "monocular-depth path evidence before promoting "
                "movement-path metrics to scoring."
            )
        if axis in {"xy", "xyz"}:
            feature_id = f"spatial.movement_path.arc_length_{axis}.{jname}"
        else:
            feature_id = f"spatial.movement_path.axis_path_{axis}.{jname}"
        records.append(
            FeatureRecord(
                feature_id=feature_id,
                exercise_id=exercise_id,
                rep_id=rep_id,
                value=round(value, 4),
                unit="torso_length_ratio",
                source_fields=axis_source_fields,
                note=note,
                availability="assessed" if is_assessed_axis else "not_assessed",
                availability_reasons=(
                    []
                    if is_assessed_axis
                    else ["movement_path_axis_diagnostic_report_only"]
                ),
                depth_dependency="high" if axis in {"z", "xyz"} else "none",
            )
        )
    return records


def _included_angle_deg(
    p_prox: np.ndarray, p_vert: np.ndarray, p_dist: np.ndarray
) -> np.ndarray:
    """(T,) included angle in degrees at the vertex landmark."""
    v_p = p_prox - p_vert
    v_d = p_dist - p_vert
    norm_p = np.linalg.norm(v_p, axis=1)
    norm_d = np.linalg.norm(v_d, axis=1)
    denom = norm_p * norm_d
    safe = denom > 1e-9
    cos_a = np.where(
        safe, np.einsum("ij,ij->i", v_p, v_d) / np.where(safe, denom, 1.0), np.nan
    )
    cos_a = np.clip(cos_a, -1.0, 1.0)
    return np.where(safe, np.degrees(np.arccos(cos_a)), np.nan)


# ── Range of motion ───────────────────────────────────────────────────────────────


def compute_range_of_motion(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """Compute per-joint angle range (max − min included angle, degrees).

    Parameters
    ----------
    df : pd.DataFrame
        Normalized pose dataframe; single rep or full sequence.
    exercise_definition : ExerciseDefinition
        Joint triplets are read from the angle_definitions field.
    rep_id : int | None
        Rep number. None aggregates over the full sequence.

    Returns
    -------
    list[FeatureRecord]
    """
    angle_defs: dict[str, Any] = exercise_definition.angle_definitions or {}
    if not angle_defs:
        return []

    records: list[FeatureRecord] = []
    ex_id = exercise_definition.exercise_id

    for joint_name, triplet in angle_defs.items():
        prox = triplet.get("proximal") or triplet.get("prox")
        vert = triplet.get("vertex") or triplet.get("vert")
        dist = triplet.get("distal") or triplet.get("dist")

        # Resolve MediaPipe index format: {points: [i, j, k], vertex: j}
        if not (prox and vert and dist) and "points" in triplet:
            pts = triplet["points"]
            if len(pts) != 3:
                continue
            try:
                prox = LANDMARKS[pts[0]]
                vert = LANDMARKS[pts[1]]
                dist = LANDMARKS[pts[2]]
            except IndexError:
                continue

        if not (prox and vert and dist):
            continue

        landmark_ids = [str(prox), str(vert), str(dist)]
        source_fields = [
            "angle_definitions",
            f"angle_definitions.{joint_name}",
            f"angle_definitions.{joint_name}.proximal",
            f"angle_definitions.{joint_name}.vertex",
            f"angle_definitions.{joint_name}.distal",
            "feature_domains.spatial",
        ]

        try:
            xy_angles = _included_angle_deg(
                _norm_xy(df, prox), _norm_xy(df, vert), _norm_xy(df, dist)
            )
        except KeyError:
            xy_angles = np.array([])
        xy_valid = xy_angles[~np.isnan(xy_angles)]
        if len(xy_valid) > 0:
            records.append(
                FeatureRecord(
                    feature_id=f"spatial.range_of_motion.xy.{joint_name}",
                    exercise_id=ex_id,
                    rep_id=rep_id,
                    value=float(np.max(xy_valid) - np.min(xy_valid)),
                    unit="degree",
                    source_fields=source_fields
                    + ["spatial.range_of_motion.xy.recording_view"],
                    landmark_ids=landmark_ids,
                    depth_dependency="none",
                )
            )

        try:
            xyz_angles = _included_angle_deg(
                _norm_xyz(df, prox), _norm_xyz(df, vert), _norm_xyz(df, dist)
            )
        except KeyError:
            xyz_angles = np.array([])
        xyz_valid = xyz_angles[~np.isnan(xyz_angles)]
        if len(xyz_valid) > 0:
            records.append(
                FeatureRecord(
                    feature_id=f"spatial.range_of_motion.xyz.{joint_name}",
                    exercise_id=ex_id,
                    rep_id=rep_id,
                    value=float(np.max(xyz_valid) - np.min(xyz_valid)),
                    unit="degree",
                    source_fields=source_fields
                    + ["spatial.range_of_motion.xyz.depth_sensitive"],
                    landmark_ids=landmark_ids,
                    depth_dependency="moderate",
                )
            )

    return records


# ── Role alignment ──────────────────────────────────────────────────────────────


def compute_role_alignment(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """Compute left/right range-of-motion balance for paired joints.

    balance_index = |range_left - range_right| / ((range_left + range_right) / 2 + ε)

    0 = perfect role alignment. Unit: dimensionless_cv.
    """
    roms = compute_range_of_motion(df, exercise_definition, rep_id)
    rom_map: dict[str, float] = {
        r.feature_id.removeprefix("spatial.range_of_motion.xy."): r.value
        for r in roms
        if r.feature_id.startswith("spatial.range_of_motion.xy.")
    }

    records: list[FeatureRecord] = []
    ex_id = exercise_definition.exercise_id
    eps = 1e-9

    # Derive left/right pairs from angle_definitions (e.g. left_knee_angle ↔ right_knee_angle)
    angle_defs: dict = exercise_definition.angle_definitions or {}
    paired: list[tuple[str, str]] = []
    for key in angle_defs:
        if key.startswith("left_"):
            right_key = "right_" + key[5:]
            if right_key in angle_defs:
                paired.append((key, right_key))

    for lj, rj in paired:
        if lj in rom_map and rj in rom_map:
            rl, rr = rom_map[lj], rom_map[rj]
            si = abs(rl - rr) / ((rl + rr) / 2.0 + eps)
            # label: strip left_ prefix and _angle suffix (e.g. left_knee_angle → knee)
            label = lj.removeprefix("left_").removesuffix("_angle")
            records.append(
                FeatureRecord(
                    feature_id=(
                        "spatial.role_alignment.left_right."
                        f"range_of_motion_xy.{label}"
                    ),
                    exercise_id=ex_id,
                    rep_id=rep_id,
                    value=round(si, 4),
                    unit="dimensionless_cv",
                    source_fields=["angle_definitions", "feature_domains.spatial"],
                )
            )

    return records


# ── Movement path ─────────────────────────────────────────────────────────────


def compute_movement_path(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
    *,
    include_support_consistency_axis_diagnostics: bool = True,
    include_axis_diagnostics: bool = True,
) -> list[FeatureRecord]:
    """Compute movement-path length of primary joints in torso_length_ratio.

    Longer paths can indicate movement instability or compensatory motion.
    """
    primary_joints: list[str] = exercise_definition.landmarks.primary_joints or []
    if not primary_joints:
        return []

    records: list[FeatureRecord] = []
    ex_id = exercise_definition.exercise_id
    support = getattr(exercise_definition, "support_context", {}) or {}
    support_fields = _support_source_fields(support)
    support_landmarks = set(_support_landmarks(exercise_definition, primary_joints))

    for jname in primary_joints:
        try:
            coords = _norm_xyz(df, jname)
        except KeyError:
            continue
        is_support_landmark = jname in support_landmarks
        source_fields = ["landmarks.primary_joints", "feature_domains.spatial"]
        note = None
        if is_support_landmark:
            source_fields = _unique_preserve_order(source_fields + support_fields)
            note = (
                "Closed-chain support-landmark path evidence. Interpret as apparent "
                "support motion mixed with pose jitter/depth drift, not as direct "
                "proof that the support point moved."
            )
        records.extend(
            _movement_path_axis_records(
                coords,
                jname,
                exercise_id=ex_id,
                rep_id=rep_id,
                source_fields=source_fields,
                variant_note=note,
                include_single_axis_diagnostics=include_axis_diagnostics,
            )
        )
        if include_support_consistency_axis_diagnostics and is_support_landmark:
            records.extend(
                _support_consistency_axis_records(
                    coords,
                    jname,
                    exercise_id=ex_id,
                    rep_id=rep_id,
                    source_fields=support_fields,
                )
            )

    return records
