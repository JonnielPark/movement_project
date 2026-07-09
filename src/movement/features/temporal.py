"""
⑦ Temporal Features

Computes rep tempo (duration in seconds) and inter-rep variability (CV).

Unit convention:
  tempo       : second
  variability : dimensionless_cv  (std / mean, dimensionless)

Input: normalized pose dataframe (with annotation columns) and ExerciseDefinition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from movement.features import FeatureRecord

if TYPE_CHECKING:
    from movement.definitions.exercise_definition import ExerciseDefinition


def compute_tempo(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """Compute per-rep duration in seconds.

    Rep boundaries are determined from annotation columns (segment_type == 'rep' + rep_id).
    tempo = timestamp[end] - timestamp[start] (seconds).

    Parameters
    ----------
    df : pd.DataFrame
        Requires annotation columns: segment_type, rep_id, timestamp.
    exercise_definition : ExerciseDefinition
    rep_id : int | None
        Compute only for this rep. None computes for all reps in df.

    Returns
    -------
    list[FeatureRecord]
    """
    if "segment_type" not in df.columns or "rep_id" not in df.columns:
        return []
    if "timestamp" not in df.columns:
        return []

    ex_id = exercise_definition.exercise_id
    records: list[FeatureRecord] = []

    rep_mask = df["segment_type"] == "rep"
    if rep_id is not None:
        rep_mask = rep_mask & (df["rep_id"] == rep_id)

    target_ids = (
        [rep_id]
        if rep_id is not None
        else sorted(df.loc[rep_mask, "rep_id"].dropna().unique())
    )

    for rid in target_ids:
        mask = (df["segment_type"] == "rep") & (df["rep_id"] == rid)
        ts = df.loc[mask, "timestamp"]
        if len(ts) < 2:
            continue
        duration = float(ts.iloc[-1] - ts.iloc[0])
        records.append(
            FeatureRecord(
                feature_id="temporal.tempo.rep_duration",
                exercise_id=ex_id,
                rep_id=int(rid),
                value=round(duration, 3),
                unit="second",
                source_fields=[
                    "feature_domains.temporal.tempo",
                    "segmentation.rep_id",
                    "timestamp",
                ],
            )
        )

    return records


def compute_variability(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
) -> list[FeatureRecord]:
    """Compute inter-rep tempo variability (CV = std / mean).

    Requires at least 2 reps to produce a meaningful value.
    Unit: dimensionless_cv.
    """
    ex_id = exercise_definition.exercise_id
    tempo_records = compute_tempo(df, exercise_definition)
    if len(tempo_records) < 2:
        return []

    values = [r.value for r in tempo_records]
    mean_v = float(np.mean(values))
    std_v = float(np.std(values, ddof=1))
    cv = std_v / (mean_v + 1e-9)

    return [
        FeatureRecord(
            feature_id="temporal.variability.tempo_cv",
            exercise_id=ex_id,
            rep_id=None,
            value=round(cv, 4),
            unit="dimensionless_cv",
            source_fields=[
                "feature_domains.temporal.variability",
                "temporal.tempo.rep_duration",
            ],
        )
    ]
