"""
④ 전처리 (Preprocessing)

단일 비전 포즈 데이터의 신뢰도 탐지, 좌우 교차(swap) 보정,
단기 결손 보간, 선택적 평활화를 수행한다.
입력 데이터프레임을 직접 수정하지 않고 보정된 복사본을 반환한다.

Pipeline position: ③ exercise_definition 로딩 이후, ⑤ normalization 이전.

좌표 규약: 컬럼명 <landmark>_{x,y,z}. 입력 shape: (T, columns).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from movement.exercise_definition import ExerciseDefinition


# ── Module-level constants (D1) ───────────────────────────────────────────────

# Included-angle bounds in degrees (min, max) at each named joint vertex.
# Conservative: only anatomically implausible configurations are flagged.
_JOINT_ANGLE_BOUNDS_DEG: dict[str, tuple[float, float]] = {
    "left_knee":   (10.0, 180.0),   # proximal: left_hip,      distal: left_ankle
    "right_knee":  (10.0, 180.0),
    "left_elbow":  (10.0, 180.0),   # proximal: left_shoulder, distal: left_wrist
    "right_elbow": (10.0, 180.0),
    "left_hip":    (20.0, 180.0),   # proximal: left_shoulder, distal: left_knee
    "right_hip":   (20.0, 180.0),
}

# (proximal, vertex, distal) landmark triplets for joint angle computation
_JOINT_ANGLE_TRIPLETS: dict[str, tuple[str, str, str]] = {
    "left_knee":   ("left_hip",       "left_knee",   "left_ankle"),
    "right_knee":  ("right_hip",      "right_knee",  "right_ankle"),
    "left_elbow":  ("left_shoulder",  "left_elbow",  "left_wrist"),
    "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_hip":    ("left_shoulder",  "left_hip",    "left_knee"),
    "right_hip":   ("right_shoulder", "right_hip",   "right_knee"),
}

# Skeleton segments for per-frame length consistency (landmark name pairs).
# Hip-to-knee (thigh) is intentionally excluded: in monocular 3D pose estimation
# the apparent thigh length varies >40% during squat due to depth estimation
# uncertainty as the joint moves through depth. Shank (knee-ankle), torso, and
# arm segments are stable enough for consistency checking.
_SKELETON_SEGMENTS: list[tuple[str, str]] = [
    ("left_shoulder",  "left_elbow"),
    ("right_shoulder", "right_elbow"),
    ("left_elbow",     "left_wrist"),
    ("right_elbow",    "right_wrist"),
    ("left_shoulder",  "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip",       "right_hip"),
    ("left_shoulder",  "right_shoulder"),
    ("left_knee",      "left_ankle"),
    ("right_knee",     "right_ankle"),
]

# Paired landmark names for L/R swap detection
_SWAP_PAIRS: list[tuple[str, str]] = [
    ("left_shoulder", "right_shoulder"),
    ("left_elbow",    "right_elbow"),
    ("left_wrist",    "right_wrist"),
    ("left_hip",      "right_hip"),
    ("left_knee",     "right_knee"),
    ("left_ankle",    "right_ankle"),
]


# ── Pure coordinate helpers ───────────────────────────────────────────────────

def _xyz(df: pd.DataFrame, lm: str) -> np.ndarray:
    """Return (T, 3) float array of xyz coordinates for a landmark."""
    return df[[f"{lm}_x", f"{lm}_y", f"{lm}_z"]].values.astype(float)


def _segment_length(df: pd.DataFrame, lm1: str, lm2: str) -> np.ndarray:
    """Return (T,) per-frame Euclidean distance between two landmarks."""
    return np.linalg.norm(_xyz(df, lm1) - _xyz(df, lm2), axis=1)


def _joint_angle_deg(
    df: pd.DataFrame, prox: str, vert: str, dist: str
) -> np.ndarray:
    """
    Return (T,) included angle in degrees at the vertex landmark.

    Degenerate frames (zero-length bone) return NaN so no bound is violated.
    """
    v_prox = _xyz(df, prox) - _xyz(df, vert)   # (T, 3)
    v_dist = _xyz(df, dist) - _xyz(df, vert)   # (T, 3)
    norm_p = np.linalg.norm(v_prox, axis=1)    # (T,)
    norm_d = np.linalg.norm(v_dist, axis=1)
    denom = norm_p * norm_d
    safe = denom > 1e-9
    cos_a = np.where(safe, np.sum(v_prox * v_dist, axis=1) / np.where(safe, denom, 1.0), np.nan)
    cos_a = np.clip(cos_a, -1.0, 1.0)
    return np.where(safe, np.degrees(np.arccos(cos_a)), np.nan)


def _compute_torso_length_median(df: pd.DataFrame, landmarks: list[str]) -> float:
    """
    Estimate sequence-level torso scale from raw coordinates (D2).

    Uses shoulder-to-hip segment. Falls back to 1.0 when landmarks absent.
    """
    segs: list[np.ndarray] = []
    for side in ("left", "right"):
        sh, hi = f"{side}_shoulder", f"{side}_hip"
        if sh in landmarks and hi in landmarks:
            segs.append(_segment_length(df, sh, hi))
    return float(np.median(np.concatenate(segs))) if segs else 1.0


def _estimate_fps(df: pd.DataFrame) -> float:
    """Estimate fps from timestamp column. Falls back to 30."""
    if "timestamp" not in df.columns or len(df) < 2:
        return 30.0
    diffs = np.diff(df["timestamp"].values.astype(float))
    diffs = diffs[diffs > 0]
    return float(1.0 / np.median(diffs)) if len(diffs) > 0 else 30.0


# ── Detection steps (all modify mask in-place) ────────────────────────────────

def _run_visibility_gating(
    df: pd.DataFrame,
    present: list[str],
    threshold: float,
    mask: np.ndarray,   # (T, len(present)), True = reliable; modified in-place
) -> dict[str, int]:
    """Flag landmarks below visibility threshold. Returns per-landmark low-vis frame counts."""
    counts: dict[str, int] = {}
    for i, lm in enumerate(present):
        vis_col = f"{lm}_visibility"
        if vis_col in df.columns:
            below = df[vis_col].values < threshold
            mask[:, i] &= ~below
            counts[lm] = int(np.sum(below))
        else:
            counts[lm] = 0
    return counts


def _run_segment_consistency(
    df: pd.DataFrame,
    present_set: set[str],
    present: list[str],
    tolerance: float,
    mask: np.ndarray,
) -> int:
    """Flag segment endpoints whose per-frame length deviates beyond tolerance. Returns violation count."""
    lm_idx = {lm: i for i, lm in enumerate(present)}
    total = 0
    for lm1, lm2 in _SKELETON_SEGMENTS:
        if lm1 not in present_set or lm2 not in present_set:
            continue
        lengths = _segment_length(df, lm1, lm2)
        median_len = float(np.median(lengths))
        if median_len < 1e-9:
            continue
        outlier = np.abs(lengths - median_len) / median_len > tolerance
        total += int(np.sum(outlier))
        mask[:, lm_idx[lm1]] &= ~outlier
        mask[:, lm_idx[lm2]] &= ~outlier
    return total


def _run_joint_angle_check(
    df: pd.DataFrame,
    present_set: set[str],
    present: list[str],
    mask: np.ndarray,
) -> int:
    """Flag vertex landmarks whose included angle is outside anatomical bounds. Returns violation count."""
    lm_idx = {lm: i for i, lm in enumerate(present)}
    total = 0
    for joint, (prox, vert, dist) in _JOINT_ANGLE_TRIPLETS.items():
        if not all(lm in present_set for lm in (prox, vert, dist)):
            continue
        if vert not in lm_idx:
            continue
        angles = _joint_angle_deg(df, prox, vert, dist)
        lo, hi = _JOINT_ANGLE_BOUNDS_DEG[joint]
        with np.errstate(invalid="ignore"):
            violation = (angles < lo) | (angles > hi)
        violation = np.nan_to_num(violation, nan=False).astype(bool)
        total += int(np.sum(violation))
        mask[:, lm_idx[vert]] &= ~violation
    return total


def _run_velocity_outlier(
    df: pd.DataFrame,
    present: list[str],
    torso_scale: float,
    fps: float,
    threshold_torso_per_sec: float,
    mask: np.ndarray,
) -> int:
    """Flag landmarks with frame-to-frame displacement exceeding velocity threshold. Returns count."""
    vel_threshold = threshold_torso_per_sec * torso_scale / max(fps, 1.0)
    total = 0
    for i, lm in enumerate(present):
        xyz = _xyz(df, lm)                                      # (T, 3)
        disp = np.linalg.norm(np.diff(xyz, axis=0), axis=1)    # (T-1,)
        velocity = np.concatenate([[0.0], disp])                # frame 0 has no prior
        outlier = velocity > vel_threshold
        total += int(np.sum(outlier & mask[:, i]))
        mask[:, i] &= ~outlier
    return total


# ── Swap detection ────────────────────────────────────────────────────────────

def _run_swap_detection(
    df: pd.DataFrame,
    present_set: set[str],
    swap_cfg: Any,      # SwapDetectionConfig
) -> tuple[np.ndarray, list[str], int, int]:
    """
    Temporal consistency L/R swap detection and correction.

    Returns
    -------
    swap_corrected : (T,) bool
    notes : list[str] of length T
    num_corrected : int
    num_orientation_disagree_reps : int
    """
    T = len(df)
    swap_corrected = np.zeros(T, dtype=bool)
    notes: list[str] = [""] * T

    active_pairs = [(l, r) for (l, r) in _SWAP_PAIRS if l in present_set and r in present_set]
    if not active_pairs:
        return swap_corrected, notes, 0, 0

    # Temporal consistency: vectorised vote per frame (D3 §Detection Heuristics)
    swap_votes = np.zeros(T, dtype=int)
    for lm_l, lm_r in active_pairs:
        xl = _xyz(df, lm_l)  # (T, 3)
        xr = _xyz(df, lm_r)
        d_LL = np.linalg.norm(xl[1:] - xl[:-1], axis=1)  # (T-1,)
        d_LR = np.linalg.norm(xl[1:] - xr[:-1], axis=1)
        d_RL = np.linalg.norm(xr[1:] - xl[:-1], axis=1)
        d_RR = np.linalg.norm(xr[1:] - xr[:-1], axis=1)
        swap_votes[1:] += ((d_LR < d_LL) & (d_RL < d_RR)).astype(int)

    suspected = swap_votes >= len(active_pairs) * 0.5

    # Apply label-only coordinate swap at suspected frames
    num_corrected = 0
    swap_frame_indices = np.where(suspected)[0]
    if len(swap_frame_indices) > 0:
        idx_labels = df.index[swap_frame_indices]
        for lm_l, lm_r in active_pairs:
            for ax in ("x", "y", "z"):
                col_l, col_r = f"{lm_l}_{ax}", f"{lm_r}_{ax}"
                if col_l in df.columns and col_r in df.columns:
                    tmp = df.loc[idx_labels, col_l].values.copy()
                    df.loc[idx_labels, col_l] = df.loc[idx_labels, col_r].values
                    df.loc[idx_labels, col_r] = tmp
            vis_l, vis_r = f"{lm_l}_visibility", f"{lm_r}_visibility"
            if vis_l in df.columns and vis_r in df.columns:
                tmp = df.loc[idx_labels, vis_l].values.copy()
                df.loc[idx_labels, vis_l] = df.loc[idx_labels, vis_r].values
                df.loc[idx_labels, vis_r] = tmp
        swap_corrected[swap_frame_indices] = True
        for t in swap_frame_indices:
            notes[t] = f"temporal_consistency swap at t={t} (vote={swap_votes[t]}/{len(active_pairs)})"
        num_corrected = len(swap_frame_indices)

    # Orientation prior (heuristic count only — no additional correction)
    num_orientation_disagree = 0
    if swap_cfg.orientation_prior and "left_hip" in present_set and "right_hip" in present_set:
        diff = df["left_hip_x"].values - df["right_hip_x"].values
        majority_sign = np.sign(float(np.median(diff)))
        if majority_sign != 0:
            disagree_ratio = float(np.mean(np.sign(diff) != majority_sign))
            if disagree_ratio > swap_cfg.orientation_disagree_ratio:
                num_orientation_disagree = 1

    return swap_corrected, notes, num_corrected, num_orientation_disagree


# ── Short-gap interpolation ───────────────────────────────────────────────────

def _find_false_runs(arr: np.ndarray) -> list[tuple[int, int]]:
    """Return (start, end) inclusive index pairs for contiguous False runs."""
    runs: list[tuple[int, int]] = []
    in_run = False
    start = 0
    for i, val in enumerate(arr):
        if not val and not in_run:
            in_run, start = True, i
        elif val and in_run:
            runs.append((start, i - 1))
            in_run = False
    if in_run:
        runs.append((start, len(arr) - 1))
    return runs


def _run_interpolation(
    df: pd.DataFrame,
    present: list[str],
    mask: np.ndarray,   # (T, len(present)); modified in-place to mark resolved gaps as reliable
    max_gap: int,
) -> tuple[int, int]:
    """
    Linearly interpolate coordinates over short unreliable gaps.

    Returns (num_short_gaps_interpolated, num_long_gaps_unresolved).
    """
    T = len(df)
    n_short = n_long = 0
    for i, lm in enumerate(present):
        for start, end in _find_false_runs(mask[:, i]):
            gap = end - start + 1
            has_left  = start > 0 and mask[start - 1, i]
            has_right = end < T - 1 and mask[end + 1, i]
            if gap <= max_gap and has_left and has_right:
                left_row  = df.index[start - 1]
                right_row = df.index[end + 1]
                for ax in ("x", "y", "z"):
                    col = f"{lm}_{ax}"
                    if col not in df.columns:
                        continue
                    v0 = float(df.at[left_row, col])
                    v1 = float(df.at[right_row, col])
                    for offset in range(gap):
                        alpha = (offset + 1) / (gap + 1)
                        df.at[df.index[start + offset], col] = v0 + alpha * (v1 - v0)
                mask[start: end + 1, i] = True
                n_short += 1
            else:
                n_long += 1
    return n_short, n_long


# ── Smoothing ─────────────────────────────────────────────────────────────────

def _run_smoothing(
    df: pd.DataFrame,
    present: list[str],
    method: str,
    window_size: int,
) -> list[str]:
    """Apply rolling smoothing to coordinate columns of reliable landmarks. Returns applied columns."""
    applied: list[str] = []
    for lm in present:
        for ax in ("x", "y", "z"):
            col = f"{lm}_{ax}"
            if col not in df.columns:
                continue
            s = df[col].astype(float)
            if method == "rolling_median":
                smoothed = s.rolling(window_size, center=True, min_periods=1).median()
            elif method == "moving_average":
                smoothed = s.rolling(window_size, center=True, min_periods=1).mean()
            else:
                continue
            df[col] = smoothed.values
            applied.append(col)
    return applied


# ── Main entry point ──────────────────────────────────────────────────────────

def preprocess_pose_dataframe(
    df: pd.DataFrame,
    landmarks: list[str],
    exercise_definition: "ExerciseDefinition | None",
    config: Any,    # PreprocessingConfig
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Reliability detection, swap correction, short-gap interpolation, and optional smoothing.

    Parameters
    ----------
    df : pd.DataFrame
        Pose dataframe after validation, annotation, and exercise_definition loading.
    landmarks : list[str]
        All landmark names (e.g. movement.config.LANDMARKS).
    exercise_definition : ExerciseDefinition | None
        Loaded exercise definition. None or generic fallback → conservative defaults (D6).
    config : PreprocessingConfig
        Preprocessing configuration.

    Returns
    -------
    pre_df : pd.DataFrame
        Input columns plus:
          <landmark>_reliable  (bool, per landmark per frame)
          preprocessing_valid  (bool, frame-level summary)
          preprocessing_note   (str,  reason string when swap applied)
          swap_corrected       (bool, frame-level)
    pre_report : dict[str, Any]
    """
    pre_df = df.copy()
    T = len(pre_df)

    # Landmarks that have coordinate columns in the dataframe
    present = [lm for lm in landmarks if f"{lm}_x" in pre_df.columns]
    present_set = set(present)

    # Laterality & swap decision (D6)
    laterality = ""
    is_generic = True
    max_gap_from_def = config.interpolation.max_gap_frames
    if exercise_definition is not None:
        laterality = exercise_definition.classification.get("laterality", "") or ""
        is_generic = exercise_definition.is_generic_fallback
        max_gap_from_def = exercise_definition.quality_rules.max_interpolation_gap_frames

    do_swap = (
        config.swap_detection.enabled
        and not is_generic
        and laterality not in ("bilateral_symmetric",)
    )

    # D2: torso scale for velocity threshold (computed from raw coords, before normalization)
    torso_scale = _compute_torso_length_median(pre_df, present)
    fps = _estimate_fps(pre_df)

    # ── Reliability mask: True = reliable ────────────────────────────────────
    mask = np.ones((T, len(present)), dtype=bool)

    # Step 1: Visibility gating
    vis_counts = _run_visibility_gating(
        pre_df, present, config.reliability.visibility_threshold, mask
    )

    # Step 2: Segment length consistency
    n_segment_violations = _run_segment_consistency(
        pre_df, present_set, present, config.reliability.segment_length_tolerance, mask
    )

    # Step 3: Velocity outlier
    n_velocity_outliers = _run_velocity_outlier(
        pre_df, present, torso_scale, fps,
        config.reliability.velocity_threshold_torso_per_sec, mask
    )

    # Step 4: Joint angle bounds
    n_angle_violations = 0
    if config.reliability.joint_angle_check:
        n_angle_violations = _run_joint_angle_check(pre_df, present_set, present, mask)

    num_unreliable_lm_frames = int(np.sum(~mask))

    # ── Per-landmark reliability columns ─────────────────────────────────────
    for i, lm in enumerate(present):
        pre_df[f"{lm}_reliable"] = mask[:, i]

    # ── Frame-level validity (before interpolation) ───────────────────────────
    frame_reliable = mask.all(axis=1)

    # ── Swap detection ────────────────────────────────────────────────────────
    swap_corrected = np.zeros(T, dtype=bool)
    swap_notes: list[str] = [""] * T
    num_temporal_swap = 0
    num_orient_disagree = 0

    if do_swap:
        swap_corrected, swap_notes, num_temporal_swap, num_orient_disagree = _run_swap_detection(
            pre_df, present_set, config.swap_detection
        )

    # ── Short-gap interpolation ───────────────────────────────────────────────
    n_short_gaps = n_long_gaps = 0
    if config.interpolation.enabled:
        n_short_gaps, n_long_gaps = _run_interpolation(
            pre_df, present, mask, max_gap_from_def
        )
        frame_reliable = mask.all(axis=1)   # recompute after gaps resolved

    # ── Smoothing ─────────────────────────────────────────────────────────────
    smoothing_applied: list[str] = []
    if config.smoothing.enabled:
        smoothing_applied = _run_smoothing(
            pre_df, present, config.smoothing.method, config.smoothing.window_size
        )

    # ── Output columns ────────────────────────────────────────────────────────
    pre_df["preprocessing_valid"] = frame_reliable
    pre_df["preprocessing_note"]  = swap_notes
    pre_df["swap_corrected"]      = swap_corrected

    # ── Report ────────────────────────────────────────────────────────────────
    exercise_type = str(pre_df["exercise_type"].iloc[0]) if "exercise_type" in pre_df.columns else None
    pattern       = str(pre_df["pattern"].iloc[0])       if "pattern"        in pre_df.columns else None

    num_invalid_frames = int(np.sum(~frame_reliable))

    pre_report: dict[str, Any] = {
        "method": "reliability_mask_v1",
        "exercise_type": exercise_type,
        "pattern": pattern,
        "laterality": laterality,
        "num_frames": T,
        "num_coordinate_columns": sum(
            1 for lm in present for ax in ("x", "y", "z") if f"{lm}_{ax}" in pre_df.columns
        ),
        "reliability_summary": {
            "visibility_threshold": config.reliability.visibility_threshold,
            "num_low_visibility_frames_per_landmark": vis_counts,
            "num_low_visibility_total": sum(vis_counts.values()),
            "num_segment_length_violations": n_segment_violations,
            "num_joint_angle_violations": n_angle_violations,
            "num_velocity_outliers": n_velocity_outliers,
            "num_unreliable_landmark_frames": num_unreliable_lm_frames,
        },
        "swap_detection_summary": {
            "enabled": do_swap,
            "num_temporal_swap_corrected": num_temporal_swap,
            "num_orientation_disagree_reps": num_orient_disagree,
        },
        "interpolation_summary": {
            "enabled": config.interpolation.enabled,
            "max_interpolation_gap": max_gap_from_def,
            "num_short_gaps_interpolated": n_short_gaps,
            "num_long_gaps_unresolved": n_long_gaps,
        },
        "smoothing_summary": {
            "enabled": config.smoothing.enabled,
            "method": config.smoothing.method,
            "window_size": config.smoothing.window_size,
            "applied_columns": smoothing_applied,
        },
        "num_invalid_frames": num_invalid_frames,
        "applied_columns": (
            [f"{lm}_reliable" for lm in present]
            + ["preprocessing_valid", "preprocessing_note", "swap_corrected"]
        ),
    }

    return pre_df, pre_report
