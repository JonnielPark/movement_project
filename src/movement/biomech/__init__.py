"""
⑨ Biomechanical Proxy Modeling

Applies simplified biomechanical rules to produce relative proxy metrics
from normalized pose data.

All outputs are in torso_length_ratio units (dimensionless).
Absolute force units (N, N·m, kg) are not used.

Submodules:
    biomech.anthropometry → segment mass and CoM ratios (Winter 1990)
    biomech.com           → CoM estimation (segment mass ratio × segment position)
    biomech.moment_arm    → joint moment arms (2D sagittal projection, torso_length_ratio)

Coordinate convention : (T, J, 3) = (frame, joint_index, xyz).
Column convention     : <landmark>_norm_x/y/z (normalized coordinates).
Unit restriction      : all outputs in torso_length_ratio; absolute units are a bug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from movement.definitions.exercise_definition import ExerciseDefinition


@dataclass
class BiomechRecord:
    """Single biomechanical proxy metric result.

    Parameters
    ----------
    metric_id                        : unique identifier (e.g. 'biomech.com.range_x')
    exercise_id                      : exercise identifier
    rep_id                           : rep number (None = sequence-level)
    value                            : metric value
    unit                             : must be torso_length_ratio or degree
    source_fields                    : exercise definition fields used (provenance)
    note                             : optional biomechanical interpretation note
    visibility_weight_applied        : True if low-visibility frames were excluded
    n_frames_used                    : number of frames included in the computation
    n_frames_excluded_low_visibility : frames excluded due to low visibility
    """

    metric_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str] = field(default_factory=list)
    note: str | None = None
    visibility_weight_applied: bool = False
    n_frames_used: int = 0
    n_frames_excluded_low_visibility: int = 0

    def __post_init__(self) -> None:
        if self.unit not in (
            "torso_length_ratio",
            "torso_length_ratio_per_rep",
            "degree",
            "dimensionless",
        ):
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': absolute units (N, kg, m) are not allowed. "
                f"unit='{self.unit}'. Use torso_length_ratio, torso_length_ratio_per_rep, or degree."
            )
        if not self.source_fields:
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': source_fields is empty. "
                "Provenance fields from the exercise definition must be specified."
            )


def extract_rep_biomech(
    df: "pd.DataFrame",
    exercise_definition: "ExerciseDefinition",
    *,
    use_visibility_weight: bool = True,
) -> "list[BiomechRecord]":
    """Compute CoM and moment-arm metrics per rep_id.

    Rep boundaries are read from annotation columns (segment_type, rep_id).
    When annotation columns are absent, metrics are computed at sequence level.

    When use_visibility_weight=True, frames whose mean primary-joint visibility
    falls below quality_rules.minimum_visible_landmark_ratio are excluded from
    all computations. This reduces the influence of depth-estimation noise from
    monocular vision on the proxy metrics.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized pose dataframe. Must contain <landmark>_norm_x/y/z columns.
    exercise_definition : ExerciseDefinition
    use_visibility_weight : bool
        True (default) — exclude low-visibility frames.
        False — include all frames (useful for A/B comparison).

    Returns
    -------
    list[BiomechRecord]
    """
    from movement.biomech.com import compute_com_metrics, compute_visibility_weights
    from movement.biomech.moment_arm import compute_moment_arms

    records: list[BiomechRecord] = []

    has_annotation = "segment_type" in df.columns and "rep_id" in df.columns
    rep_ids: list = []
    if has_annotation:
        rep_mask = df["segment_type"] == "rep"
        rep_ids = sorted(df.loc[rep_mask, "rep_id"].dropna().unique())

    primary_joints: list[str] = exercise_definition.landmarks.primary_joints or []
    min_vis_ratio: float = (
        exercise_definition.quality_rules.minimum_visible_landmark_ratio
    )

    def _weights_for(df_slice: "pd.DataFrame"):
        if not use_visibility_weight or not primary_joints:
            return None
        return compute_visibility_weights(df_slice, primary_joints, min_vis_ratio)

    moment_arm_records: list[BiomechRecord] = []

    if rep_ids:
        for rep_id in rep_ids:
            mask = (df["segment_type"] == "rep") & (df["rep_id"] == rep_id)
            df_rep = df.loc[mask]
            rid = int(rep_id)
            w = _weights_for(df_rep)
            records += compute_com_metrics(
                df_rep, exercise_definition, rep_id=rid, weights=w
            )
            ma = compute_moment_arms(df_rep, exercise_definition, rep_id=rid, weights=w)
            records += ma
            moment_arm_records += ma

        # Load-shift trend: requires ≥ 3 reps (slope is unreliable on fewer)
        if len(rep_ids) >= 3:
            from movement.biomech.load_shift import compute_load_shift

            records += compute_load_shift(moment_arm_records)
    else:
        w = _weights_for(df)
        records += compute_com_metrics(df, exercise_definition, weights=w)
        records += compute_moment_arms(df, exercise_definition, weights=w)

    return records


__all__ = ["BiomechRecord", "extract_rep_biomech", "compute_load_shift"]
