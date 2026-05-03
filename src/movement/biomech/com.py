"""
CoM(신체 중심) 추정 — 분절 질량 비율 × 분절 중심 위치

입력: 정규화 좌표 (torso_length_ratio 기준).
출력: 전신 CoM 위치 (T, 3) 및 BiomechRecord 목록.

절대 단위(kg, m) 사용 불가. 모든 거리는 torso_length_ratio.
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
    """전신 CoM 위치를 분절 질량 가중 평균으로 추정한다.

    Parameters
    ----------
    df : pd.DataFrame
        정규화 좌표 포함 데이터프레임.
    segments : list[str], optional
        포함할 분절 목록. None이면 SEGMENT_ENDPOINTS 전체 사용.

    Returns
    -------
    np.ndarray, shape (T, 3)
        프레임별 전신 CoM 위치 (torso_length_ratio 단위).
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

        # 분절 중심 위치 = 근위단 + ratio × (원위단 - 근위단)
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
    """CoM 궤적 통계를 BiomechRecord 목록으로 반환한다.

    산출 지표:
      - com_range_x   : 수평 이동 범위 (좌우, torso_length_ratio)
      - com_range_z   : 수직 이동 범위 (높이, torso_length_ratio)
      - com_path_length : CoM 궤적 전체 호 길이 (torso_length_ratio)
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

    # 수평 범위 (x)
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

    # 수직 범위 (z = height)
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

    # 궤적 호 길이
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
