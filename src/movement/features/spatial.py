"""
⑦-공간 특징 (Spatial Features)

ROM(관절 가동범위), 좌우 대칭성 지수, 궤적 형태를 산출한다.

Unit convention:
  각도 기반 특징 : degree
  거리 기반 특징 : torso_length_ratio

Input: ⑤ 정규화 후 데이터프레임 (norm 컬럼 포함), ExerciseDefinition.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from movement.features import FeatureRecord

if TYPE_CHECKING:
    from movement.exercise_definition import ExerciseDefinition


def _norm_xyz(df: pd.DataFrame, lm: str) -> np.ndarray:
    """(T, 3) normalized coordinates; falls back to raw if norm columns absent."""
    ncols = [f"{lm}_norm_x", f"{lm}_norm_y", f"{lm}_norm_z"]
    if all(c in df.columns for c in ncols):
        return df[ncols].values.astype(float)
    return df[[f"{lm}_x", f"{lm}_y", f"{lm}_z"]].values.astype(float)


def _included_angle_deg(
    p_prox: np.ndarray, p_vert: np.ndarray, p_dist: np.ndarray
) -> np.ndarray:
    """(T,) included angle in degrees at the vertex landmark."""
    v_p = p_prox - p_vert
    v_d = p_dist - p_vert
    norm_p = np.linalg.norm(v_p, axis=1)
    norm_d = np.linalg.norm(v_d, axis=1)
    denom = norm_p * norm_d
    safe = denom > 1e-9
    cos_a = np.where(safe, np.einsum("ij,ij->i", v_p, v_d) / np.where(safe, denom, 1.0), np.nan)
    cos_a = np.clip(cos_a, -1.0, 1.0)
    return np.where(safe, np.degrees(np.arccos(cos_a)), np.nan)


# ── ROM ───────────────────────────────────────────────────────────────────────

def compute_rom(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """관절별 ROM(최대 - 최소 included angle, 도 단위)을 산출한다.

    Parameters
    ----------
    df : pd.DataFrame
        정규화된 포즈 데이터프레임. 단일 반복 또는 전체 시퀀스.
    exercise_definition : ExerciseDefinition
        angle_definitions 필드에서 관절 triplet을 읽는다.
    rep_id : int | None
        반복 번호. None이면 시퀀스 단위 집계.

    Returns
    -------
    list[FeatureRecord]
    """
    angle_defs: dict[str, Any] = exercise_definition.angle_definitions or {}
    if not angle_defs:
        return []

    records: list[FeatureRecord] = []
    ex_id = exercise_definition.exercise_id

    for joint_name, triplet in angle_defs.items():
        prox = triplet.get("proximal") or triplet.get("prox")
        vert = triplet.get("vertex") or triplet.get("vert")
        dist = triplet.get("distal") or triplet.get("dist")
        if not (prox and vert and dist):
            continue

        try:
            angles = _included_angle_deg(
                _norm_xyz(df, prox), _norm_xyz(df, vert), _norm_xyz(df, dist)
            )
        except KeyError:
            continue

        valid = angles[~np.isnan(angles)]
        if len(valid) == 0:
            continue

        rom_deg = float(np.max(valid) - np.min(valid))
        records.append(FeatureRecord(
            feature_id=f"spatial.rom.{joint_name}",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=rom_deg,
            unit="degree",
            source_fields=["angle_definitions", "feature_domains.spatial"],
        ))

    return records


# ── 좌우 대칭성 ──────────────────────────────────────────────────────────────

def compute_symmetry(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """좌우 paired 관절의 ROM 대칭성 지수를 산출한다.

    symmetry_index = |ROM_left - ROM_right| / ((ROM_left + ROM_right) / 2 + ε)

    0에 가까울수록 좌우 대칭. 단위: dimensionless_cv.
    """
    roms = compute_rom(df, exercise_definition, rep_id)
    rom_map: dict[str, float] = {r.feature_id.split(".")[-1]: r.value for r in roms}

    records: list[FeatureRecord] = []
    ex_id = exercise_definition.exercise_id
    eps = 1e-9

    paired_joints = [
        ("left_knee", "right_knee"),
        ("left_hip", "right_hip"),
        ("left_elbow", "right_elbow"),
        ("left_shoulder", "right_shoulder"),
    ]

    for lj, rj in paired_joints:
        if lj in rom_map and rj in rom_map:
            rl, rr = rom_map[lj], rom_map[rj]
            si = abs(rl - rr) / ((rl + rr) / 2.0 + eps)
            records.append(FeatureRecord(
                feature_id=f"spatial.symmetry.{lj.replace('left_', '')}",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(si, 4),
                unit="dimensionless_cv",
                source_fields=["angle_definitions", "feature_domains.spatial"],
            ))

    return records


# ── 궤적 형태 ─────────────────────────────────────────────────────────────────

def compute_shape(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """대표 관절의 궤적 길이(arc length)를 torso_length_ratio로 산출한다.

    궤적이 길수록 움직임이 불안정하거나 보상 움직임이 있음을 시사한다.
    """
    primary_joints: list[str] = exercise_definition.landmarks.primary_joints or []
    if not primary_joints:
        return []

    records: list[FeatureRecord] = []
    ex_id = exercise_definition.exercise_id

    for jname in primary_joints:
        try:
            coords = _norm_xyz(df, jname)
        except KeyError:
            continue
        arc = float(np.nansum(np.linalg.norm(np.diff(coords, axis=0), axis=1)))
        records.append(FeatureRecord(
            feature_id=f"spatial.shape.arc_length.{jname}",
            exercise_id=ex_id,
            rep_id=rep_id,
            value=round(arc, 4),
            unit="torso_length_ratio",
            source_fields=["landmarks.primary_joints", "feature_domains.spatial"],
        ))

    return records
