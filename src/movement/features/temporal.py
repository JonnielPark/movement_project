"""
⑦-시간 특징 (Temporal Features)

tempo(반복 소요 시간), 반복 간 변동성(CV)을 산출한다.

Unit convention:
  tempo       : second
  variability : dimensionless_cv  (표준편차 / 평균, 무차원)

Input: ⑤ 정규화 후 데이터프레임 (annotation 컬럼 포함), ExerciseDefinition.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from movement.features import FeatureRecord

if TYPE_CHECKING:
    from movement.exercise_definition import ExerciseDefinition


def compute_tempo(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """반복 소요 시간(초)을 산출한다.

    annotation 컬럼 segment_type == 'rep' + rep_id를 이용해 반복 경계를 결정한다.
    tempo = timestamp[end] - timestamp[start] (초).

    Parameters
    ----------
    df : pd.DataFrame
        annotation 컬럼(segment_type, rep_id, timestamp)이 필요하다.
    exercise_definition : ExerciseDefinition
    rep_id : int | None
        특정 반복만 산출. None이면 해당 데이터프레임 전체.

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
        [rep_id] if rep_id is not None
        else sorted(df.loc[rep_mask, "rep_id"].dropna().unique())
    )

    for rid in target_ids:
        mask = (df["segment_type"] == "rep") & (df["rep_id"] == rid)
        ts = df.loc[mask, "timestamp"]
        if len(ts) < 2:
            continue
        duration = float(ts.iloc[-1] - ts.iloc[0])
        records.append(FeatureRecord(
            feature_id=f"temporal.tempo.rep_{int(rid)}",
            exercise_id=ex_id,
            rep_id=int(rid),
            value=round(duration, 3),
            unit="second",
            source_fields=["feature_domains.temporal"],
        ))

    return records


def compute_variability(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
) -> list[FeatureRecord]:
    """반복 간 tempo 변동성(CV = std / mean)을 산출한다.

    최소 2개 반복이 있어야 의미 있는 값이 산출된다.
    단위: dimensionless_cv.
    """
    ex_id = exercise_definition.exercise_id
    tempo_records = compute_tempo(df, exercise_definition)
    if len(tempo_records) < 2:
        return []

    values = [r.value for r in tempo_records]
    mean_v = float(np.mean(values))
    std_v = float(np.std(values, ddof=1))
    cv = std_v / (mean_v + 1e-9)

    return [FeatureRecord(
        feature_id="temporal.variability.tempo_cv",
        exercise_id=ex_id,
        rep_id=None,
        value=round(cv, 4),
        unit="dimensionless_cv",
        source_fields=["feature_domains.temporal"],
    )]
