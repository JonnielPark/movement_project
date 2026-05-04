"""
⑦ Control Features

Computes CoM (Center of Mass) horizontal displacement stability and
compensation movement candidate metrics.

Unit convention:
  stability    : torso_length_ratio  (std of CoM horizontal displacement)
  compensation : torso_length_ratio  (arc length of compensation candidate joint)

Input: normalized pose dataframe (norm columns) and ExerciseDefinition.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from movement.features import FeatureRecord

if TYPE_CHECKING:
    from movement.exercise_definition import ExerciseDefinition


def _norm_xyz(df: pd.DataFrame, lm: str) -> np.ndarray:
    ncols = [f"{lm}_norm_x", f"{lm}_norm_y", f"{lm}_norm_z"]
    if all(c in df.columns for c in ncols):
        return df[ncols].values.astype(float)
    return df[[f"{lm}_x", f"{lm}_y", f"{lm}_z"]].values.astype(float)


def compute_stability(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """Compute CoM horizontal displacement stability.

    CoM approximation: standard deviation of hip_center(norm) horizontal coordinates.
    (To be replaced by com.py estimate once ⑧ biomech proxy is implemented.)

    Unit: torso_length_ratio. Smaller values indicate greater stability.
    """
    ex_id = exercise_definition.exercise_id

    try:
        left_hip = _norm_xyz(df, "left_hip")
        right_hip = _norm_xyz(df, "right_hip")
    except KeyError:
        return []

    hip_center_x = (left_hip[:, 0] + right_hip[:, 0]) / 2.0
    hip_center_z = (left_hip[:, 2] + right_hip[:, 2]) / 2.0  # z = height

    std_x = float(np.nanstd(hip_center_x))
    std_z = float(np.nanstd(hip_center_z))

    return [
        FeatureRecord(
            feature_id="control.stability.hip_center_x_std",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(std_x, 4),
            unit="torso_length_ratio",
            source_fields=["biomechanical_focus.stability_requirement", "feature_domains.control"],
        ),
        FeatureRecord(
            feature_id="control.stability.hip_center_z_std",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(std_z, 4),
            unit="torso_length_ratio",
            source_fields=["biomechanical_focus.stability_requirement", "feature_domains.control"],
        ),
    ]


def compute_compensation(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """Dispatch compensation candidates to the rule registry.

    Each candidate name in exercise_definition.compensation_candidates is
    looked up in COMPENSATION_RULES (features/compensation.py). Registered
    candidates are computed and returned as FeatureRecord list. Unregistered
    candidates emit a UserWarning and are skipped.

    See features/compensation.py for implemented rules and axis conventions.
    """
    from movement.features.compensation import dispatch_compensation

    candidates: list[str] = exercise_definition.compensation_candidates or []
    if not candidates:
        return []

    ex_id = exercise_definition.exercise_id
    records: list[FeatureRecord] = []

    for candidate in candidates:
        records.extend(dispatch_compensation(candidate, df, ex_id, rep_id))

    return records
