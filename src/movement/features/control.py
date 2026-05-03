"""
⑦-제어 특징 (Control Features)

CoM(신체 중심) 수평 이동 안정성과 보상 움직임 후보 지표를 산출한다.

Unit convention:
  stability : torso_length_ratio  (CoM 수평 변위의 표준편차)
  compensation : torso_length_ratio (보상 후보 관절의 arc length)

Input: ⑤ 정규화 후 데이터프레임 (norm 컬럼 포함), ExerciseDefinition.
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
    """CoM 수평 이동 안정성을 산출한다.

    CoM 근사: hip_center(norm) 의 수평 좌표 표준편차.
    (⑧ 생체역학적 근사 모델링이 구현되면 com.py의 CoM 추정값으로 대체.)

    Unit: torso_length_ratio. 값이 작을수록 안정적이다.
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
    """보상 움직임 후보 관절의 arc length를 산출한다.

    compensation_candidates 필드에 정의된 관절에 대해 궤적 길이를 산출한다.
    값이 클수록 해당 부위에서 보상 움직임이 발생했을 가능성이 높다.

    Unit: torso_length_ratio.
    """
    candidates: list[str] = exercise_definition.compensation_candidates or []
    if not candidates:
        return []

    ex_id = exercise_definition.exercise_id
    records: list[FeatureRecord] = []

    for jname in candidates:
        try:
            coords = _norm_xyz(df, jname)
        except KeyError:
            continue
        arc = float(np.nansum(np.linalg.norm(np.diff(coords, axis=0), axis=1)))
        records.append(FeatureRecord(
            feature_id=f"control.compensation.arc_length.{jname}",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(arc, 4),
            unit="torso_length_ratio",
            source_fields=["compensation_candidates", "feature_domains.control"],
        ))

    return records
