"""
CoM (Center of Mass) estimation — segment mass ratio × segment center position.

Input  : normalized coordinates (torso_length_ratio units).
Output : whole-body CoM position (T, 3) and a list of BiomechRecord.

Absolute units (kg, m) are not used. All distances are in torso_length_ratio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from movement.biomech import BiomechRecord
from movement.biomech.anthropometry import (
    SEGMENT_ENDPOINTS,
    get_segment_com_ratio,
    get_segment_mass_ratio,
)

if TYPE_CHECKING:
    from movement.definitions.exercise_definition import ExerciseDefinition


def compute_visibility_weights(
    df: pd.DataFrame,
    primary_joints: list[str],
    min_visibility_ratio: float = 0.5,
) -> np.ndarray:
    """Per-frame visibility weights for monocular data quality adjustment.

    Frames whose mean primary-joint visibility is below min_visibility_ratio
    receive weight = 0 and are excluded from downstream metric computation.
    This reduces the contribution of depth-estimation noise inherent in
    monocular pose data.

    Parameters
    ----------
    df : pd.DataFrame
    primary_joints : list[str]
        Landmark names whose visibility columns drive the weighting.
    min_visibility_ratio : float
        Frames with mean visibility below this threshold are excluded (weight = 0).

    Returns
    -------
    np.ndarray, shape (T,)
        Per-frame weights in [0, 1]. Returns all-ones if visibility columns
        are absent (no weighting applied).
    """
    T = len(df)
    vis_cols = [
        f"{lm}_visibility" for lm in primary_joints if f"{lm}_visibility" in df.columns
    ]
    if not vis_cols:
        return np.ones(T, dtype=float)

    vis_matrix = df[vis_cols].values.astype(float)  # (T, n_joints)
    mean_vis = np.nanmean(vis_matrix, axis=1)  # (T,)

    weights = mean_vis.copy()
    weights[mean_vis < min_visibility_ratio] = 0.0
    return weights


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
    weights: np.ndarray | None = None,
) -> list[BiomechRecord]:
    """Return CoM trajectory statistics as a list of BiomechRecord.

    Metrics produced:
      - com_range_x     : lateral displacement range (torso_length_ratio)
      - com_range_z     : vertical displacement range (torso_length_ratio)
      - com_path_length : CoM arc length over valid frames (torso_length_ratio)

    Parameters
    ----------
    weights : np.ndarray | None
        Per-frame visibility weights from compute_visibility_weights().
        Frames with weight = 0 are excluded from all metrics.
        None = include all frames (no visibility filtering).
    """
    ex_id = exercise_definition.exercise_id
    com_xyz = estimate_com(df)  # (T, 3)

    if np.all(np.isnan(com_xyz)):
        return []

    T = len(com_xyz)
    source_fields = [
        "biomechanical_focus.expected_com_motion",
        "biomechanical_focus.stability_requirement",
    ]

    # Apply visibility mask
    if weights is not None:
        valid_mask = weights > 0
        n_excluded = int(np.sum(~valid_mask))
        n_used = int(np.sum(valid_mask))
        vis_applied = True
        if n_used == 0:
            return []
        com_valid = com_xyz[valid_mask]
    else:
        n_excluded = 0
        n_used = T
        vis_applied = False
        com_valid = com_xyz

    def _record(metric_id: str, value: float) -> BiomechRecord:
        return BiomechRecord(
            metric_id=metric_id,
            exercise_id=ex_id,
            rep_id=rep_id,
            value=value,
            unit="torso_length_ratio",
            source_fields=source_fields,
            visibility_weight_applied=vis_applied,
            n_frames_used=n_used,
            n_frames_excluded_low_visibility=n_excluded,
        )

    records: list[BiomechRecord] = []

    # lateral range (x)
    x_vals = com_valid[:, 0]
    valid_x = x_vals[~np.isnan(x_vals)]
    if len(valid_x) > 0:
        records.append(
            _record(
                "biomech.com.range_x",
                round(float(np.max(valid_x) - np.min(valid_x)), 4),
            )
        )

    # vertical range (z = height)
    z_vals = com_valid[:, 2]
    valid_z = z_vals[~np.isnan(z_vals)]
    if len(valid_z) > 0:
        records.append(
            _record(
                "biomech.com.range_z",
                round(float(np.max(valid_z) - np.min(valid_z)), 4),
            )
        )

    # trajectory arc length (valid frames only — excludes low-visibility gaps)
    path = float(np.nansum(np.linalg.norm(np.diff(com_valid, axis=0), axis=1)))
    records.append(_record("biomech.com.path_length", round(path, 4)))

    return records
