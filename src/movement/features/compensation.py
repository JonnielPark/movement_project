"""
Compensation rule registry for control feature computation.

Each rule function:
    signature : (df: pd.DataFrame, ex_id: str, rep_id: int | None) -> list[FeatureRecord]
    unit      : torso_length_ratio (geometric) or degree (angular)

Axis convention follows the project-wide monocular pose policy:
    x/y : recording-view camera plane
    z   : model depth, low-confidence unless separately validated

Implemented rules:
    knee_valgus              frontal-plane medial knee deviation from hip-ankle line
    knee_varus               frontal-plane lateral knee deviation
    lateral_pelvic_shift     peak lateral pelvis-center displacement from rep baseline
    excessive_trunk_flexion  peak trunk lean angle from vertical (degrees)
    heel_lift                peak heel elevation relative to rep minimum
    pelvis_rotation          left-right hip depth asymmetry (transverse-plane proxy)

Not yet implemented (patterns accepted by YAML, no rule registered):
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


def _recording_view_knee_deviation(df: pd.DataFrame, side: str) -> np.ndarray:
    """
    Signed perpendicular distance of the knee from the hip-ankle line in the
    recording-view plane (x-y).

    Positive = medial/valgus proxy for the left side; negative = medial/valgus
    proxy for the right side. Returns (T,) in torso_length_ratio units. This is
    a camera-plane tracking proxy, not a calibrated anatomical frontal plane.
    """
    try:
        hip = _get_norm_xyz(df, f"{side}_hip")
        knee = _get_norm_xyz(df, f"{side}_knee")
        ankle = _get_norm_xyz(df, f"{side}_ankle")
    except KeyError:
        return np.full(len(df), np.nan)

    hip_xy = hip[:, [0, 1]]
    knee_xy = knee[:, [0, 1]]
    ankle_xy = ankle[:, [0, 1]]

    line_vec = ankle_xy - hip_xy
    knee_vec = knee_xy - hip_xy

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
    Peak medial deviation of each knee from the recording-view hip-ankle line.

    Positive = valgus (inward/medial collapse). Computed as the 95th percentile
    of the signed deviation across frames (robust peak estimate).
    Unit: torso_length_ratio.
    """
    records: list[FeatureRecord] = []
    # left: positive cross = medial; right: negate so positive = medial
    for side, valgus_sign in (("left", 1.0), ("right", -1.0)):
        signed_dist = _recording_view_knee_deviation(df, side)
        valgus_index = valgus_sign * signed_dist
        if np.all(np.isnan(valgus_index)):
            continue
        peak = float(np.nanpercentile(valgus_index, 95))
        records.append(
            FeatureRecord(
                feature_id=f"control.compensation.knee_valgus.xy.{side}",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(peak, 4),
                unit="torso_length_ratio",
                source_fields=[f"{side}_hip", f"{side}_knee", f"{side}_ankle"],
                note=(
                    "recording-view hip-knee-ankle medial deviation proxy; "
                    "positive = valgus-like inward collapse"
                ),
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
        signed_dist = _recording_view_knee_deviation(df, side)
        varus_index = varus_sign * signed_dist
        if np.all(np.isnan(varus_index)):
            continue
        peak = float(np.nanpercentile(varus_index, 95))
        records.append(
            FeatureRecord(
                feature_id=f"control.compensation.knee_varus.xy.{side}",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(peak, 4),
                unit="torso_length_ratio",
                source_fields=[f"{side}_hip", f"{side}_knee", f"{side}_ankle"],
                note=(
                    "recording-view hip-knee-ankle lateral deviation proxy; "
                    "positive = varus-like outward bow"
                ),
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
            feature_id="control.compensation.lateral_pelvic_shift.xy",
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
    Peak trunk-line angle from the recording-view vertical axis.

    Emits an `xy` recording-view feature and an `xyz` depth-mixed comparative
    feature. Both use the image vertical axis; the `xyz` variant adds model
    depth to the vector norm and therefore carries reduced default scoring weight.
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

    trunk_xy = trunk_vec[:, [0, 1]]
    trunk_xy_norm = np.linalg.norm(trunk_xy, axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        trunk_xy_unit = np.where(trunk_xy_norm > 1e-8, trunk_xy / trunk_xy_norm, np.nan)

    cos_xy = np.clip(np.abs(trunk_xy_unit[:, 1]), -1.0, 1.0)
    angle_xy_deg = np.degrees(np.arccos(cos_xy))

    trunk_xyz_norm = np.linalg.norm(trunk_vec, axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        trunk_xyz_unit = np.where(
            trunk_xyz_norm > 1e-8, trunk_vec / trunk_xyz_norm, np.nan
        )

    cos_xyz = np.clip(np.abs(trunk_xyz_unit[:, 1]), -1.0, 1.0)
    angle_xyz_deg = np.degrees(np.arccos(cos_xyz))

    peak_xy = float(np.nanpercentile(angle_xy_deg, 95))
    peak_xyz = float(np.nanpercentile(angle_xyz_deg, 95))

    return [
        FeatureRecord(
            feature_id="control.compensation.excessive_trunk_flexion.xy",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(peak_xy, 2),
            unit="degree",
            source_fields=["left_shoulder", "right_shoulder", "left_hip", "right_hip"],
            note=(
                "peak recording-view trunk-line angle from image vertical; "
                "larger = more apparent forward/lateral lean"
            ),
        ),
        FeatureRecord(
            feature_id="control.compensation.excessive_trunk_flexion.xyz",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(peak_xyz, 2),
            unit="degree",
            source_fields=["left_shoulder", "right_shoulder", "left_hip", "right_hip"],
            note=(
                "peak depth-mixed trunk-line angle from image vertical; "
                "comparative evidence only under monocular depth"
            ),
        ),
    ]


def _rule_heel_lift(
    df: pd.DataFrame, ex_id: str, rep_id: int | None
) -> list[FeatureRecord]:
    """
    Peak recording-view heel elevation above the rep support baseline.

    Non-zero values may indicate loss of heel contact with the ground. This
    intentionally uses the camera-plane vertical axis instead of monocular
    model depth; depth-sensitive heel-lift diagnostics need a separate feature.
    Unit: torso_length_ratio.
    """
    records: list[FeatureRecord] = []
    for side in ("left", "right"):
        try:
            heel = _get_norm_xyz(df, f"{side}_heel")
        except KeyError:
            continue

        heel_y = heel[:, 1]
        support_y = float(np.nanpercentile(heel_y, 95))
        lift = support_y - heel_y
        peak = float(np.nanpercentile(lift, 95))

        records.append(
            FeatureRecord(
                feature_id=f"control.compensation.heel_lift.xy.{side}",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(peak, 4),
                unit="torso_length_ratio",
                source_fields=[f"{side}_heel"],
                note=(
                    "peak recording-view heel elevation above rep support baseline; "
                    "non-zero = heel-lift compensation proxy"
                ),
            )
        )
    return records


def _rule_pelvis_rotation(
    df: pd.DataFrame, ex_id: str, rep_id: int | None
) -> list[FeatureRecord]:
    """
    Peak left-right hip depth asymmetry as a proxy for transverse-plane pelvic rotation.

    Computed as the absolute difference in model-depth z between the left and
    right hip. 95th-percentile peak across frames. This is depth-sensitive
    evidence and should remain low-weight/report-only unless validated.
    Unit: torso_length_ratio.
    """
    try:
        left_hip = _get_norm_xyz(df, "left_hip")
        right_hip = _get_norm_xyz(df, "right_hip")
    except KeyError:
        return []

    depth_diff = np.abs(left_hip[:, 2] - right_hip[:, 2])
    peak = float(np.nanpercentile(depth_diff, 95))

    return [
        FeatureRecord(
            feature_id="control.compensation.pelvis_rotation.xyz",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(peak, 4),
            unit="torso_length_ratio",
            source_fields=["left_hip", "right_hip"],
            note=(
                "peak left-right hip model-depth asymmetry; proxy for "
                "transverse-plane pelvic rotation"
            ),
        )
    ]


# ── Registry ──────────────────────────────────────────────────────────────────

COMPENSATION_RULES: dict[str, Callable] = {
    "knee_valgus": _rule_knee_valgus,
    "knee_varus": _rule_knee_varus,
    "lateral_pelvic_shift": _rule_lateral_pelvic_shift,
    "excessive_trunk_flexion": _rule_excessive_trunk_flexion,
    "heel_lift": _rule_heel_lift,
    "pelvis_rotation": _rule_pelvis_rotation,
}

_UNIMPLEMENTED: set[str] = {
    "asymmetric_depth",
    "foot_external_rotation_proxy",
    "tempo_instability",
}


def dispatch_compensation(
    pattern: str,
    df: pd.DataFrame,
    ex_id: str,
    rep_id: int | None,
) -> list[FeatureRecord]:
    """
    Look up pattern in COMPENSATION_RULES and compute.

    Unregistered patterns emit a UserWarning and return [].
    Registered rules that raise an exception emit a UserWarning and return [].
    """
    rule_fn = COMPENSATION_RULES.get(pattern)

    if rule_fn is None:
        if pattern not in _UNIMPLEMENTED:
            warnings.warn(
                f"[compensation] no rule registered for pattern '{pattern}' - skipped.",
                UserWarning,
                stacklevel=3,
            )
        return []

    try:
        return rule_fn(df, ex_id, rep_id)
    except Exception as exc:
        warnings.warn(
            f"[compensation] rule '{pattern}' raised an error: {exc}",
            UserWarning,
            stacklevel=3,
        )
        return []
