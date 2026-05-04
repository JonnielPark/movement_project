"""
Moment Arm Proxy

Perpendicular distance from the joint axis to the load line of action,
expressed in torso_length_ratio units.

Monocular 2D approximation:
  - Sagittal or frontal plane projection.
  - Absolute force/torque (N·m) cannot be estimated; relative tendencies only.
  - Segment-length normalization (torso_length_ratio) removes body-size effects.

Output unit: torso_length_ratio (absolute units are forbidden).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from movement.biomech import BiomechRecord

if TYPE_CHECKING:
    from movement.exercise_definition import ExerciseDefinition


def _norm_xyz(df: pd.DataFrame, lm: str) -> np.ndarray:
    ncols = [f"{lm}_norm_x", f"{lm}_norm_y", f"{lm}_norm_z"]
    if all(c in df.columns for c in ncols):
        return df[ncols].values.astype(float)
    return df[[f"{lm}_x", f"{lm}_y", f"{lm}_z"]].values.astype(float)


def _point_to_line_dist_2d(
    point: np.ndarray,
    line_start: np.ndarray,
    line_end: np.ndarray,
    plane: str = "xz",
) -> np.ndarray:
    """Perpendicular distance from a point to a line in 2D projection, shape (T,).

    Parameters
    ----------
    point      : (T, 3) load application position
    line_start : (T, 3) proximal end of joint axis
    line_end   : (T, 3) distal end of joint axis
    plane      : projection plane ('xz' = sagittal, 'xy' = frontal)
    """
    if plane == "xz":
        idx = [0, 2]
    elif plane == "xy":
        idx = [0, 1]
    else:
        raise ValueError(f"Unsupported plane: '{plane}'. Use 'xz' or 'xy'.")

    p = point[:, idx]
    a = line_start[:, idx]
    b = line_end[:, idx]

    ab = b - a
    ab_norm = np.linalg.norm(ab, axis=1, keepdims=True)
    safe = ab_norm[:, 0] > 1e-9
    ab_unit = np.where(safe[:, np.newaxis], ab / np.where(ab_norm > 1e-9, ab_norm, 1.0), 0.0)

    ap = p - a
    proj = np.einsum("ij,ij->i", ap, ab_unit)
    foot = a + proj[:, np.newaxis] * ab_unit
    dist = np.linalg.norm(p - foot, axis=1)
    return np.where(safe, dist, np.nan)


def compute_moment_arms(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[BiomechRecord]:
    """Compute moment arms based on main_load_regions in the exercise definition.

    Supported joints:
      knee  → perpendicular distance from CoM projection to knee axis (ankle-knee line), sagittal
      hip   → perpendicular distance from CoM projection to hip axis (knee-hip line), sagittal

    Parameters
    ----------
    df : pd.DataFrame
    exercise_definition : ExerciseDefinition
    rep_id : int | None

    Returns
    -------
    list[BiomechRecord]
    """
    from movement.biomech.com import estimate_com

    load_regions: list[str] = (
        exercise_definition.biomechanical_focus.main_load_regions or []
    )
    if not load_regions:
        return []

    ex_id = exercise_definition.exercise_id
    source_fields = [
        "biomechanical_focus.main_load_regions",
        "biomechanical_focus.expected_com_motion",
    ]

    com_xyz = estimate_com(df)  # (T, 3)
    records: list[BiomechRecord] = []

    # ── knee moment arm (sagittal plane xz) ──────────────────────────────────
    if any("knee" in r for r in load_regions):
        for side in ("left", "right"):
            try:
                ankle = _norm_xyz(df, f"{side}_ankle")
                knee  = _norm_xyz(df, f"{side}_knee")
            except KeyError:
                continue
            dist = _point_to_line_dist_2d(com_xyz, ankle, knee, plane="xz")
            median_dist = float(np.nanmedian(dist))
            records.append(BiomechRecord(
                metric_id=f"biomech.moment_arm.knee.{side}.median",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(median_dist, 4),
                unit="torso_length_ratio",
                source_fields=source_fields,
                note=f"Median sagittal perpendicular distance from CoM to {side} knee axis (ankle-knee line)",
            ))

    # ── hip moment arm (sagittal plane xz) ───────────────────────────────────
    if any("hip" in r for r in load_regions):
        for side in ("left", "right"):
            try:
                knee = _norm_xyz(df, f"{side}_knee")
                hip  = _norm_xyz(df, f"{side}_hip")
            except KeyError:
                continue
            dist = _point_to_line_dist_2d(com_xyz, knee, hip, plane="xz")
            median_dist = float(np.nanmedian(dist))
            records.append(BiomechRecord(
                metric_id=f"biomech.moment_arm.hip.{side}.median",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(median_dist, 4),
                unit="torso_length_ratio",
                source_fields=source_fields,
                note=f"Median sagittal perpendicular distance from CoM to {side} hip axis (knee-hip line)",
            ))

    return records
