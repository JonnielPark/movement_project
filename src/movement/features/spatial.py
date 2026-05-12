"""
⑥ Spatial Features

Computes ROM (joint range of motion), left/right symmetry index, and trajectory shape.

Unit convention:
  angle-based features : degree
  distance-based features : torso_length_ratio

Input: normalized pose dataframe (norm columns) and ExerciseDefinition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from movement.core.config import LANDMARKS
from movement.features import FeatureRecord

if TYPE_CHECKING:
    from movement.definitions.exercise_definition import ExerciseDefinition


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
    cos_a = np.where(
        safe, np.einsum("ij,ij->i", v_p, v_d) / np.where(safe, denom, 1.0), np.nan
    )
    cos_a = np.clip(cos_a, -1.0, 1.0)
    return np.where(safe, np.degrees(np.arccos(cos_a)), np.nan)


# ── ROM ───────────────────────────────────────────────────────────────────────


def compute_rom(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """Compute per-joint ROM (max − min included angle, degrees).

    Parameters
    ----------
    df : pd.DataFrame
        Normalized pose dataframe; single rep or full sequence.
    exercise_definition : ExerciseDefinition
        Joint triplets are read from the angle_definitions field.
    rep_id : int | None
        Rep number. None aggregates over the full sequence.

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

        # Resolve MediaPipe index format: {points: [i, j, k], vertex: j}
        if not (prox and vert and dist) and "points" in triplet:
            pts = triplet["points"]
            if len(pts) != 3:
                continue
            try:
                prox = LANDMARKS[pts[0]]
                vert = LANDMARKS[pts[1]]
                dist = LANDMARKS[pts[2]]
            except IndexError:
                continue

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
        records.append(
            FeatureRecord(
                feature_id=f"spatial.rom.{joint_name}",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=rom_deg,
                unit="degree",
                source_fields=["angle_definitions", "feature_domains.spatial"],
            )
        )

    return records


# ── Left/right symmetry ───────────────────────────────────────────────────────


def compute_symmetry(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """Compute ROM symmetry index for paired left/right joints.

    symmetry_index = |ROM_left - ROM_right| / ((ROM_left + ROM_right) / 2 + ε)

    0 = perfect symmetry. Unit: dimensionless_cv.
    """
    roms = compute_rom(df, exercise_definition, rep_id)
    rom_map: dict[str, float] = {r.feature_id.split(".")[-1]: r.value for r in roms}

    records: list[FeatureRecord] = []
    ex_id = exercise_definition.exercise_id
    eps = 1e-9

    # Derive left/right pairs from angle_definitions (e.g. left_knee_angle ↔ right_knee_angle)
    angle_defs: dict = exercise_definition.angle_definitions or {}
    paired: list[tuple[str, str]] = []
    for key in angle_defs:
        if key.startswith("left_"):
            right_key = "right_" + key[5:]
            if right_key in angle_defs:
                paired.append((key, right_key))

    for lj, rj in paired:
        if lj in rom_map and rj in rom_map:
            rl, rr = rom_map[lj], rom_map[rj]
            si = abs(rl - rr) / ((rl + rr) / 2.0 + eps)
            # label: strip left_ prefix and _angle suffix (e.g. left_knee_angle → knee)
            label = lj.removeprefix("left_").removesuffix("_angle")
            records.append(
                FeatureRecord(
                    feature_id=f"spatial.symmetry.{label}",
                    exercise_id=ex_id,
                    rep_id=rep_id,
                    value=round(si, 4),
                    unit="dimensionless_cv",
                    source_fields=["angle_definitions", "feature_domains.spatial"],
                )
            )

    return records


# ── Trajectory shape ──────────────────────────────────────────────────────────


def compute_shape(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    rep_id: int | None = None,
) -> list[FeatureRecord]:
    """Compute arc length of primary joint trajectories in torso_length_ratio.

    Longer trajectories indicate movement instability or compensatory motion.
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
        records.append(
            FeatureRecord(
                feature_id=f"spatial.shape.arc_length.{jname}",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(arc, 4),
                unit="torso_length_ratio",
                source_fields=["landmarks.primary_joints", "feature_domains.spatial"],
            )
        )

    return records
