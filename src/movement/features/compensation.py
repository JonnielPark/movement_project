"""
Compensation rule registry for control feature computation.

Each rule function:
    signature : (df: pd.DataFrame, ex_id: str, rep_id: int | None) -> list[FeatureRecord]
    unit      : torso_length_ratio (geometric) or degree (angular)

Axis convention (normalized coordinates):
    x : lateral  — positive toward subject's right
    y : sagittal — positive forward (depth)
    z : vertical — positive upward

Implemented rules:
    knee_valgus              frontal-plane medial knee deviation from hip-ankle line
    knee_varus               frontal-plane lateral knee deviation
    lateral_pelvic_shift     peak lateral pelvis-center displacement from rep baseline
    excessive_trunk_flexion  peak trunk lean angle from vertical (degrees)
    heel_lift                peak heel elevation relative to rep minimum
    pelvic_rotation          left-right hip depth asymmetry (transverse-plane proxy)

Not yet implemented (candidates accepted by YAML, no rule registered):
    asymmetric_depth, foot_external_rotation_proxy, tempo_instability
"""

from __future__ import annotations

import warnings
from typing import Callable

import numpy as np
import pandas as pd

from movement.features import FeatureRecord


# ── Coordinate helpers ────────────────────────────────────────────────────────


def _get_norm_xyz(df: pd.DataFrame, landmark: str) -> np.ndarray:
    """Return (T, 3) float array for landmark. Prefers _norm_ columns."""
    ncols = [f"{landmark}_norm_x", f"{landmark}_norm_y", f"{landmark}_norm_z"]
    if all(c in df.columns for c in ncols):
        return df[ncols].values.astype(float)
    cols = [f"{landmark}_x", f"{landmark}_y", f"{landmark}_z"]
    return df[cols].values.astype(float)


def _frontal_knee_deviation(df: pd.DataFrame, side: str) -> np.ndarray:
    """
    Signed perpendicular distance of the knee from the hip-ankle line in the frontal
    plane (x-z). Positive = medial (valgus) for the left side; negative = medial
    (valgus) for the right side. Returns (T,) array in torso_length_ratio units.
    """
    try:
        hip = _get_norm_xyz(df, f"{side}_hip")
        knee = _get_norm_xyz(df, f"{side}_knee")
        ankle = _get_norm_xyz(df, f"{side}_ankle")
    except KeyError:
        return np.full(len(df), np.nan)

    # Frontal plane slices: column 0 = x (lateral), column 2 = z (vertical)
    hip_xz = hip[:, [0, 2]]
    knee_xz = knee[:, [0, 2]]
    ankle_xz = ankle[:, [0, 2]]

    line_vec = ankle_xz - hip_xz  # hip → ankle
    knee_vec = knee_xz - hip_xz  # hip → knee

    # 2D signed cross product (perpendicular distance × |line_vec|)
    cross = line_vec[:, 0] * knee_vec[:, 1] - line_vec[:, 1] * knee_vec[:, 0]
    line_norm = np.linalg.norm(line_vec, axis=1)

    with np.errstate(invalid="ignore", divide="ignore"):
        signed_dist = np.where(line_norm > 1e-8, cross / line_norm, np.nan)

    return signed_dist


# ── Rule functions ─────────────────────────────────────────────────────────────


def _rule_knee_valgus(
    df: pd.DataFrame, ex_id: str, rep_id: int | None
) -> list[FeatureRecord]:
    """
    Peak medial deviation of each knee from the frontal-plane hip-ankle line.

    Positive = valgus (inward/medial collapse). Computed as the 95th percentile
    of the signed deviation across frames (robust peak estimate).
    Unit: torso_length_ratio.
    """
    records: list[FeatureRecord] = []
    # left: positive cross = medial; right: negate so positive = medial
    for side, valgus_sign in (("left", 1.0), ("right", -1.0)):
        signed_dist = _frontal_knee_deviation(df, side)
        valgus_index = valgus_sign * signed_dist
        if np.all(np.isnan(valgus_index)):
            continue
        peak = float(np.nanpercentile(valgus_index, 95))
        records.append(
            FeatureRecord(
                feature_id=f"control.compensation.knee_valgus.{side}",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(peak, 4),
                unit="torso_length_ratio",
                source_fields=[f"{side}_hip", f"{side}_knee", f"{side}_ankle"],
                note="frontal-plane medial knee deviation; positive = valgus (inward collapse)",
            )
        )
    return records


def _rule_knee_varus(
    df: pd.DataFrame, ex_id: str, rep_id: int | None
) -> list[FeatureRecord]:
    """
    Peak lateral deviation of each knee (opposite direction of valgus).

    Positive = varus (outward bow). 95th-percentile peak across frames.
    Unit: torso_length_ratio.
    """
    records: list[FeatureRecord] = []
    # left: negative cross = lateral; right: positive cross = lateral
    for side, varus_sign in (("left", -1.0), ("right", 1.0)):
        signed_dist = _frontal_knee_deviation(df, side)
        varus_index = varus_sign * signed_dist
        if np.all(np.isnan(varus_index)):
            continue
        peak = float(np.nanpercentile(varus_index, 95))
        records.append(
            FeatureRecord(
                feature_id=f"control.compensation.knee_varus.{side}",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(peak, 4),
                unit="torso_length_ratio",
                source_fields=[f"{side}_hip", f"{side}_knee", f"{side}_ankle"],
                note="frontal-plane lateral knee deviation; positive = varus (outward bow)",
            )
        )
    return records


def _rule_lateral_pelvic_shift(
    df: pd.DataFrame, ex_id: str, rep_id: int | None
) -> list[FeatureRecord]:
    """
    Peak lateral displacement of the pelvis center from its rep-mean position.

    Pelvis center is the midpoint of left_hip and right_hip.
    Unit: torso_length_ratio.
    """
    try:
        left_hip = _get_norm_xyz(df, "left_hip")
        right_hip = _get_norm_xyz(df, "right_hip")
    except KeyError:
        return []

    pelvis_x = (left_hip[:, 0] + right_hip[:, 0]) / 2.0
    baseline_x = float(np.nanmean(pelvis_x))
    deviation = np.abs(pelvis_x - baseline_x)
    peak = float(np.nanpercentile(deviation, 95))

    return [
        FeatureRecord(
            feature_id="control.compensation.lateral_pelvic_shift",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(peak, 4),
            unit="torso_length_ratio",
            source_fields=["left_hip", "right_hip"],
            note="peak lateral pelvis displacement from rep-mean baseline",
        )
    ]


def _rule_excessive_trunk_flexion(
    df: pd.DataFrame, ex_id: str, rep_id: int | None
) -> list[FeatureRecord]:
    """
    Peak forward lean angle of the trunk from the vertical axis (z-axis).

    Trunk vector = shoulder-center minus hip-center. Angle computed as
    arccos of the normalized trunk vector's z-component.
    Unit: degree.
    """
    try:
        left_shoulder = _get_norm_xyz(df, "left_shoulder")
        right_shoulder = _get_norm_xyz(df, "right_shoulder")
        left_hip = _get_norm_xyz(df, "left_hip")
        right_hip = _get_norm_xyz(df, "right_hip")
    except KeyError:
        return []

    shoulder_center = (left_shoulder + right_shoulder) / 2.0
    hip_center = (left_hip + right_hip) / 2.0
    trunk_vec = shoulder_center - hip_center  # (T, 3), points upward

    trunk_norm = np.linalg.norm(trunk_vec, axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        trunk_unit = np.where(trunk_norm > 1e-8, trunk_vec / trunk_norm, np.nan)

    cos_angle = np.clip(trunk_unit[:, 2], -1.0, 1.0)
    angle_deg = np.degrees(np.arccos(cos_angle))

    peak = float(np.nanpercentile(angle_deg, 95))

    return [
        FeatureRecord(
            feature_id="control.compensation.excessive_trunk_flexion",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(peak, 2),
            unit="degree",
            source_fields=["left_shoulder", "right_shoulder", "left_hip", "right_hip"],
            note="peak trunk lean from vertical (z-axis); larger = more forward lean",
        )
    ]


def _rule_heel_lift(
    df: pd.DataFrame, ex_id: str, rep_id: int | None
) -> list[FeatureRecord]:
    """
    Peak heel elevation above the rep-minimum heel height.

    Non-zero values indicate loss of heel contact with the ground.
    Unit: torso_length_ratio.
    """
    records: list[FeatureRecord] = []
    for side in ("left", "right"):
        try:
            heel = _get_norm_xyz(df, f"{side}_heel")
        except KeyError:
            continue

        heel_z = heel[:, 2]
        min_z = float(np.nanmin(heel_z))
        lift = heel_z - min_z
        peak = float(np.nanpercentile(lift, 95))

        records.append(
            FeatureRecord(
                feature_id=f"control.compensation.heel_lift.{side}",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(peak, 4),
                unit="torso_length_ratio",
                source_fields=[f"{side}_heel"],
                note="peak heel elevation above rep-minimum; non-zero = heel-lift compensation",
            )
        )
    return records


def _rule_pelvic_rotation(
    df: pd.DataFrame, ex_id: str, rep_id: int | None
) -> list[FeatureRecord]:
    """
    Peak left-right hip depth asymmetry as a proxy for transverse-plane pelvic rotation.

    Computed as the absolute difference in y-axis (sagittal depth) between the
    left and right hip. 95th-percentile peak across frames.
    Unit: torso_length_ratio.
    """
    try:
        left_hip = _get_norm_xyz(df, "left_hip")
        right_hip = _get_norm_xyz(df, "right_hip")
    except KeyError:
        return []

    depth_diff = np.abs(left_hip[:, 1] - right_hip[:, 1])
    peak = float(np.nanpercentile(depth_diff, 95))

    return [
        FeatureRecord(
            feature_id="control.compensation.pelvic_rotation",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(peak, 4),
            unit="torso_length_ratio",
            source_fields=["left_hip", "right_hip"],
            note="peak left-right hip depth asymmetry; proxy for transverse-plane pelvic rotation",
        )
    ]


# ── Registry ──────────────────────────────────────────────────────────────────

COMPENSATION_RULES: dict[str, Callable] = {
    "knee_valgus": _rule_knee_valgus,
    "knee_varus": _rule_knee_varus,
    "lateral_pelvic_shift": _rule_lateral_pelvic_shift,
    "excessive_trunk_flexion": _rule_excessive_trunk_flexion,
    "heel_lift": _rule_heel_lift,
    "pelvis_rotation": _rule_pelvic_rotation,
}

_UNIMPLEMENTED: set[str] = {
    "asymmetric_depth",
    "foot_external_rotation_proxy",
    "tempo_instability",
}


def dispatch_compensation(
    candidate: str,
    df: pd.DataFrame,
    ex_id: str,
    rep_id: int | None,
) -> list[FeatureRecord]:
    """
    Look up candidate in COMPENSATION_RULES and compute.

    Unregistered candidates emit a UserWarning and return [].
    Registered rules that raise an exception emit a UserWarning and return [].
    """
    rule_fn = COMPENSATION_RULES.get(candidate)

    if rule_fn is None:
        if candidate not in _UNIMPLEMENTED:
            warnings.warn(
                f"[compensation] no rule registered for candidate '{candidate}' — skipped.",
                UserWarning,
                stacklevel=3,
            )
        return []

    try:
        return rule_fn(df, ex_id, rep_id)
    except Exception as exc:
        warnings.warn(
            f"[compensation] rule '{candidate}' raised an error: {exc}",
            UserWarning,
            stacklevel=3,
        )
        return []
