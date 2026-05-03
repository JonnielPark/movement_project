"""
모멘트 암 근사 (Moment Arm Proxy)

관절 축에서 하중 작용선까지의 수직 거리를 torso_length_ratio로 산출한다.

단일 비전 2D 근사:
  - 정면 또는 측면 투영 기준.
  - 절대값 힘·토크(N·m) 산출 불가. 상대적 경향성만 제공.
  - 분절 길이 정규화(torso_length_ratio)로 신체 크기 영향 제거.

출력 단위: torso_length_ratio (절대 단위 사용 금지).
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
    """2D 투영에서 점에서 직선까지의 수직 거리 (T,).

    Parameters
    ----------
    point      : (T, 3) 하중 작용 위치
    line_start : (T, 3) 관절 축 근위단
    line_end   : (T, 3) 관절 축 원위단
    plane      : 투영 평면 ('xz' = 시상면, 'xy' = 관상면)
    """
    if plane == "xz":
        idx = [0, 2]
    elif plane == "xy":
        idx = [0, 1]
    else:
        raise ValueError(f"지원하지 않는 plane: '{plane}'. 'xz' 또는 'xy' 사용.")

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
    """운동 정의의 main_load_regions 기반으로 모멘트 암을 산출한다.

    현재 지원하는 관절:
      knee  → CoM 투영점에서 무릎 관절축(ankle-knee 선)까지 거리 (시상면)
      hip   → CoM 투영점에서 고관절축(knee-hip 선)까지 거리 (시상면)

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

    # ── 무릎 모멘트 암 (시상면 xz) ───────────────────────────────────────────
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
                note="CoM에서 무릎 관절축(ankle-knee 선)까지 시상면 수직 거리 중간값",
            ))

    # ── 고관절 모멘트 암 (시상면 xz) ─────────────────────────────────────────
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
                note="CoM에서 고관절축(knee-hip 선)까지 시상면 수직 거리 중간값",
            ))

    return records
