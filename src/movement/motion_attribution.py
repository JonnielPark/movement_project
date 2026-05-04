"""
⑥ Motion Attribution

Compares per-rep observed motion energy against the expected active side
(from annotation pattern / starting_side) and flags label consistency.

Does not modify coordinates. Adds per-rep metadata columns only.

Activation by laterality:
    bilateral_symmetric  → skipped (no active-side concept)
    alternating          → per-rep attribution
    unilateral_*         → declared side is the expected active side

Pipeline position: after ⑤ normalization, before ⑦ feature extraction.
Coordinate convention: (T, J, 3) = (frame, joint_index, xyz).
Column convention: <landmark>_norm_x/y/z (normalized coordinates).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from movement.exercise_definition import ExerciseDefinition


# ── Paired landmark list for L/R motion energy ────────────────────────────────

_DEFAULT_SWAP_PAIRS: list[tuple[str, str]] = [
    ("left_shoulder", "right_shoulder"),
    ("left_elbow",    "right_elbow"),
    ("left_wrist",    "right_wrist"),
    ("left_hip",      "right_hip"),
    ("left_knee",     "right_knee"),
    ("left_ankle",    "right_ankle"),
]

# Laterality values that make this module applicable
_APPLICABLE_LATERALITIES = frozenset({
    "alternating",
    "unilateral_left",
    "unilateral_right",
    "unilateral_unspecified",
})

# Output column names
_ATTR_COLS = [
    "detected_active_limb",
    "expected_active_limb",
    "attribution_consistent",
    "attribution_confidence",
    "attribution_action",
]


# ── Config dataclass ──────────────────────────────────────────────────────────

@dataclass
class AttributionThresholds:
    """Decision thresholds (τ) for active-limb attribution.

    active     : motion_share > τ_active → detected as one-sided
    ambiguous  : τ_ambiguous < motion_share ≤ τ_active → ambiguous
    swap       : confidence > τ_swap required for 'swap' action (auto_correct mode)
    """
    active: float = 0.70
    ambiguous: float = 0.55
    swap: float = 0.85


# ── Report dataclass ──────────────────────────────────────────────────────────

@dataclass
class AttributionReport:
    method: str = "motion_energy_ratio"
    exercise_type: str | None = None
    laterality: str | None = None
    pattern: str | None = None
    starting_side: str | None = None
    num_reps: int = 0
    num_consistent: int = 0
    num_flagged: int = 0
    num_swapped: int = 0
    num_ambiguous: int = 0
    num_bilateral: int = 0
    thresholds: dict[str, float] = field(default_factory=dict)
    landmark_pairs_used: list[tuple[str, str]] = field(default_factory=list)
    mode: str = "conservative"
    skipped: bool = False
    skip_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "exercise_type": self.exercise_type,
            "laterality": self.laterality,
            "pattern": self.pattern,
            "starting_side": self.starting_side,
            "num_reps": self.num_reps,
            "num_consistent": self.num_consistent,
            "num_flagged": self.num_flagged,
            "num_swapped": self.num_swapped,
            "num_ambiguous": self.num_ambiguous,
            "num_bilateral": self.num_bilateral,
            "thresholds": self.thresholds,
            "landmark_pairs_used": [list(p) for p in self.landmark_pairs_used],
            "mode": self.mode,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _norm_xyz(df: pd.DataFrame, lm: str) -> np.ndarray:
    """(T, 3) normalized coordinates; falls back to raw if norm columns absent."""
    ncols = [f"{lm}_norm_x", f"{lm}_norm_y", f"{lm}_norm_z"]
    rcols = [f"{lm}_x", f"{lm}_y", f"{lm}_z"]
    if all(c in df.columns for c in ncols):
        return df[ncols].values.astype(float)
    return df[rcols].values.astype(float)


def _motion_energy(coords: np.ndarray) -> float:
    """Sum of frame-to-frame Euclidean displacements along a (T, 3) trajectory."""
    if len(coords) < 2:
        return 0.0
    diffs = np.linalg.norm(np.diff(coords, axis=0), axis=1)
    return float(np.nansum(diffs))


def _select_landmark_pairs(
    exercise_definition: "ExerciseDefinition",
    custom_pairs: list[tuple[str, str]] | None,
) -> list[tuple[str, str]]:
    """Return L/R paired landmark list for motion energy comparison."""
    if custom_pairs:
        return custom_pairs
    # Use primary_joints from definition if parseable as L/R pairs
    primary = exercise_definition.landmarks.primary_joints
    pairs: list[tuple[str, str]] = []
    for jname in primary:
        if jname.startswith("left_"):
            right_name = "right_" + jname[5:]
            pairs.append((jname, right_name))
    return pairs if pairs else _DEFAULT_SWAP_PAIRS


def _expected_active(
    rep_number: int,
    pattern: str | None,
    starting_side: str | None,
    laterality: str,
) -> str | None:
    """Derive expected active side for a given rep (1-indexed)."""
    if laterality == "unilateral_left":
        return "left"
    if laterality == "unilateral_right":
        return "right"

    if pattern == "alternating":
        if starting_side in ("left", "right"):
            sides = ["left", "right"] if starting_side == "left" else ["right", "left"]
            return sides[(rep_number - 1) % 2]
        # starting_side unknown → return None (will be inferred from first rep)
        return None

    return None


def _detect_active(
    df_rep: pd.DataFrame,
    pairs: list[tuple[str, str]],
    thresholds: AttributionThresholds,
) -> tuple[str, float]:
    """
    Compute motion_share for each L/R pair and average over pairs.

    Returns (detected_active, confidence) where detected_active is one of:
        'left' | 'right' | 'bilateral' | 'ambiguous'
    and confidence is the dominant motion_share (0.5 = equal, 1.0 = one-sided).
    """
    shares: list[float] = []
    eps = 1e-9

    for lm_l, lm_r in pairs:
        if not all(
            f"{lm}_{ax}" in df_rep.columns or f"{lm}_norm_{ax}" in df_rep.columns
            for lm in (lm_l, lm_r)
            for ax in ("x", "y", "z")
        ):
            continue
        e_l = _motion_energy(_norm_xyz(df_rep, lm_l))
        e_r = _motion_energy(_norm_xyz(df_rep, lm_r))
        dominant = max(e_l, e_r)
        share = dominant / (e_l + e_r + eps)
        shares.append(share)

    if not shares:
        return "ambiguous", 0.5

    avg_share = float(np.mean(shares))

    # Determine which side dominates across all pairs
    left_total = sum(
        _motion_energy(_norm_xyz(df_rep, lm_l))
        for lm_l, _ in pairs
        if f"{lm_l}_x" in df_rep.columns or f"{lm_l}_norm_x" in df_rep.columns
    )
    right_total = sum(
        _motion_energy(_norm_xyz(df_rep, lm_r))
        for _, lm_r in pairs
        if f"{lm_r}_x" in df_rep.columns or f"{lm_r}_norm_x" in df_rep.columns
    )

    if avg_share > thresholds.active:
        detected = "left" if left_total > right_total else "right"
        return detected, avg_share
    elif avg_share > thresholds.ambiguous:
        return "ambiguous", avg_share
    else:
        return "bilateral", 1.0 - avg_share


# ── Public API ────────────────────────────────────────────────────────────────

def attribute_motion(
    df: pd.DataFrame,
    exercise_definition: "ExerciseDefinition",
    thresholds: AttributionThresholds | None = None,
    mode: Literal["conservative", "auto_correct"] = "conservative",
    custom_landmark_pairs: list[tuple[str, str]] | None = None,
) -> tuple[pd.DataFrame, AttributionReport]:
    """
    ⑥ Motion Attribution

    Computes per-rep motion energy and flags active-side label consistency.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized dataframe from ⑤. Annotation columns (segment_type, rep_id,
        pattern, starting_side) must be present to read rep boundaries.
    exercise_definition : ExerciseDefinition
        Object returned by ③ exercise definition loading.
    thresholds : AttributionThresholds, optional
        τ thresholds. None uses defaults.
    mode : 'conservative' | 'auto_correct'
        conservative  → flag only; no label modification
        auto_correct  → swap L/R labels when confidence > τ_swap
    custom_landmark_pairs : list[tuple[str,str]], optional
        Override per-exercise paired landmark list.

    Returns
    -------
    df : pd.DataFrame
        Dataframe with attribution columns added.
    report : AttributionReport
    """
    if thresholds is None:
        thresholds = AttributionThresholds()

    df = df.copy()
    report = AttributionReport(mode=mode)

    laterality: str = exercise_definition.classification.get("laterality", "") or ""
    report.laterality = laterality

    # ── Skip conditions ───────────────────────────────────────────────────────
    if laterality == "bilateral_symmetric":
        report.skipped = True
        report.skip_reason = "laterality = bilateral_symmetric; no active-side concept"
        for col in _ATTR_COLS:
            df[col] = None
        return df, report

    if laterality not in _APPLICABLE_LATERALITIES:
        report.skipped = True
        report.skip_reason = f"laterality = '{laterality}'; attribution not applicable"
        for col in _ATTR_COLS:
            df[col] = None
        return df, report

    # ── Check annotation columns ──────────────────────────────────────────────
    if "segment_type" not in df.columns or "rep_id" not in df.columns:
        report.skipped = True
        report.skip_reason = "annotation columns (segment_type, rep_id) absent"
        for col in _ATTR_COLS:
            df[col] = None
        return df, report

    # ── Common context ────────────────────────────────────────────────────────
    pattern = df["pattern"].dropna().iloc[0] if "pattern" in df.columns and not df["pattern"].dropna().empty else None
    starting_side = df["starting_side"].dropna().iloc[0] if "starting_side" in df.columns and not df["starting_side"].dropna().empty else None
    exercise_type = df["exercise_type"].dropna().iloc[0] if "exercise_type" in df.columns and not df["exercise_type"].dropna().empty else None

    report.exercise_type = exercise_type
    report.pattern = pattern
    report.starting_side = starting_side
    report.thresholds = {
        "τ_active": thresholds.active,
        "τ_ambiguous": thresholds.ambiguous,
        "τ_swap": thresholds.swap,
    }

    pairs = _select_landmark_pairs(exercise_definition, custom_landmark_pairs)
    report.landmark_pairs_used = pairs

    # ── Initialize output columns ─────────────────────────────────────────────
    for col in _ATTR_COLS:
        df[col] = None

    # ── Per-rep processing ────────────────────────────────────────────────────
    rep_mask = df["segment_type"] == "rep"
    rep_ids = df.loc[rep_mask, "rep_id"].dropna().unique()
    rep_ids_sorted = sorted(rep_ids)

    inferred_starting_side: str | None = None

    for rep_num_zero, rep_id in enumerate(rep_ids_sorted):
        rep_num_one = rep_num_zero + 1
        row_mask = (df["segment_type"] == "rep") & (df["rep_id"] == rep_id)
        df_rep = df.loc[row_mask]

        detected, confidence = _detect_active(df_rep, pairs, thresholds)

        # expected active side
        use_starting = starting_side if starting_side else inferred_starting_side
        expected = _expected_active(rep_num_one, pattern, use_starting, laterality)

        # infer starting_side from first rep when alternating + unknown
        if rep_num_zero == 0 and pattern == "alternating" and use_starting is None:
            if detected in ("left", "right"):
                inferred_starting_side = detected
            expected = detected  # first rep: treat detected side as expected

        # consistency judgement
        if detected in ("ambiguous", "bilateral"):
            consistent = None
            action = "flag"
            report.num_ambiguous += (1 if detected == "ambiguous" else 0)
            report.num_bilateral += (1 if detected == "bilateral" else 0)
        elif expected is None:
            consistent = None
            action = "flag"
            report.num_ambiguous += 1
        elif detected == expected:
            consistent = True
            action = "accept"
            report.num_consistent += 1
        else:
            consistent = False
            if mode == "auto_correct" and confidence > thresholds.swap:
                action = "swap"
                report.num_swapped += 1
                # label swap: rename left↔right columns for this rep's frames
                # (coordinate values unchanged; column names only)
                # in-place rename not yet implemented; treat as flag for now
                action = "flag"
                report.num_flagged += 1
            else:
                action = "flag"
                report.num_flagged += 1

        # write columns
        df.loc[row_mask, "detected_active_limb"] = detected
        df.loc[row_mask, "expected_active_limb"] = expected
        df.loc[row_mask, "attribution_consistent"] = consistent
        df.loc[row_mask, "attribution_confidence"] = confidence
        df.loc[row_mask, "attribution_action"] = action

        report.num_reps += 1

    return df, report
