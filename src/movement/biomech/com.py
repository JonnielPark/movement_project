"""
CoM (Center of Mass) estimation — segment mass ratio × segment center position.

Input  : normalized coordinates (torso_length_ratio units).
Output : whole-body CoM position (T, 3) and a list of BiomechRecord.

Absolute units (kg, m) are not used. All distances are in torso_length_ratio.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from movement.biomech import BiomechRecord
from movement.biomech.anthropometry import (
    SEGMENT_ENDPOINTS,
    get_segment_com_ratio,
    get_segment_mass_ratio,
)

if TYPE_CHECKING:
    from movement.exercise_definition import ExerciseDefinition


def _norm_xyz(df: pd.DataFrame, lm: str) -> np.ndarray:
    ncols = [f"{lm}_norm_x", f"{lm}_norm_y", f"{lm}_norm_z"]
    if all(c in df.columns for c in ncols):
        return df[ncols].values.astype(float)
    return df[[f"{lm}_x", f"{lm}_y", f"{lm}_z"]].values.astype(float)


def estimate_com(
    df: pd.DataFrame,
    segments: list[str] | None = None,
) -> np.ndarray:
    """Estimate whole-body CoM position as a segment-mass-weighted average.

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe with normalized coordinates.
    segments : list[str], optional
        Segments to include. None uses all entries in SEGMENT_ENDPOINTS.

    Returns
    -------
    np.ndarray, shape (T, 3)
        Per-frame whole-body CoM position in torso_length_ratio units.
    """
    if segments is None:
        segments = list(SEGMENT_ENDPOINTS.keys())

    T = len(df)
    com_numerator = np.zeros((T, 3))
    total_mass = 0.0

    for seg_name in segments:
        if seg_name not in SEGMENT_ENDPOINTS:
            continue
        prox_lm, dist_lm = SEGMENT_ENDPOINTS[seg_name]

        try:
            p_prox = _norm_xyz(df, prox_lm)
            p_dist = _norm_xyz(df, dist_lm)
        except KeyError:
            continue

        try:
            mass_ratio = get_segment_mass_ratio(seg_name)
            com_ratio = get_segment_com_ratio(seg_name)
        except KeyError:
            continue

        # segment center = proximal + ratio × (distal - proximal)
        seg_com = p_prox + com_ratio * (p_dist - p_prox)
        com_numerator += mass_ratio * seg_com
        total_mass += mass_ratio

    if total_mass < 1e-9:
        return np.full((T, 3), np.nan)

    return com_numerator / total_mass


def compute_com_metrics(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[BiomechRecord]:
    """Return CoM trajectory statistics as a list of BiomechRecord.

    Metrics produced:
      - com_range_x     : lateral displacement range (torso_length_ratio)
      - com_range_z     : vertical displacement range (torso_length_ratio)
      - com_path_length : total arc length of CoM trajectory (torso_length_ratio)
    """
    ex_id = exercise_definition.exercise_id
    com_xyz = estimate_com(df)  # (T, 3)

    if np.all(np.isnan(com_xyz)):
        return []

    source_fields = [
        "biomechanical_focus.expected_com_motion",
        "biomechanical_focus.stability_requirement",
    ]

    records: list[BiomechRecord] = []

    # horizontal range (x)
    x_vals = com_xyz[:, 0]
    valid_x = x_vals[~np.isnan(x_vals)]
    if len(valid_x) > 0:
        records.append(BiomechRecord(
            metric_id="biomech.com.range_x",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(float(np.max(valid_x) - np.min(valid_x)), 4),
            unit="torso_length_ratio",
            source_fields=source_fields,
        ))

    # vertical range (z = height)
    z_vals = com_xyz[:, 2]
    valid_z = z_vals[~np.isnan(z_vals)]
    if len(valid_z) > 0:
        records.append(BiomechRecord(
            metric_id="biomech.com.range_z",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(float(np.max(valid_z) - np.min(valid_z)), 4),
            unit="torso_length_ratio",
            source_fields=source_fields,
        ))

    # trajectory arc length
    path = float(np.nansum(np.linalg.norm(np.diff(com_xyz, axis=0), axis=1)))
    records.append(BiomechRecord(
        metric_id="biomech.com.path_length",
        exercise_id=ex_id,
        rep_id=rep_id,
        value=round(path, 4),
        unit="torso_length_ratio",
        source_fields=source_fields,
    ))

    return records
