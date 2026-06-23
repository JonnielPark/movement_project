"""
④ Preprocessing

Reliability detection, left/right swap correction, short-gap interpolation,
and optional smoothing for monocular pose data.
Returns a corrected copy; does not modify the input dataframe.

Corrects data quality issues only. Does not alter movement quality patterns
(compensation movements, squat depth, etc.).

Pipeline position: after ③ exercise definition loading, before ⑤ normalization.

Coordinate convention: columns named <landmark>_{x,y,z}.  Input shape: (T, columns).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from movement.definitions.exercise_definition import ExerciseDefinition


# ── Module-level constants (D1) ───────────────────────────────────────────────

# Included-angle bounds in degrees (min, max) at each named joint vertex.
# Conservative: only anatomically implausible configurations are flagged.
_JOINT_ANGLE_BOUNDS_DEG: dict[str, tuple[float, float]] = {
    "left_knee": (10.0, 180.0),  # proximal: left_hip,      distal: left_ankle
    "right_knee": (10.0, 180.0),
    "left_elbow": (10.0, 180.0),  # proximal: left_shoulder, distal: left_wrist
    "right_elbow": (10.0, 180.0),
    "left_hip": (20.0, 180.0),  # proximal: left_shoulder, distal: left_knee
    "right_hip": (20.0, 180.0),
}

# (proximal, vertex, distal) landmark triplets for joint angle computation
_JOINT_ANGLE_TRIPLETS: dict[str, tuple[str, str, str]] = {
    "left_knee": ("left_hip", "left_knee", "left_ankle"),
    "right_knee": ("right_hip", "right_knee", "right_ankle"),
    "left_elbow": ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_hip": ("left_shoulder", "left_hip", "left_knee"),
    "right_hip": ("right_shoulder", "right_hip", "right_knee"),
}

# Skeleton segments for per-frame length consistency (landmark name pairs).
# Hip-to-knee (thigh) is intentionally excluded: in monocular 3D pose estimation
# the apparent thigh length varies >40% during squat due to depth estimation
# uncertainty as the joint moves through depth. Shank (knee-ankle), torso, and
# arm segments are stable enough for consistency checking.
_SKELETON_SEGMENTS: list[tuple[str, str]] = [
    ("left_shoulder", "left_elbow"),
    ("right_shoulder", "right_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_shoulder", "right_shoulder"),
    ("left_knee", "left_ankle"),
    ("right_knee", "right_ankle"),
]

# Paired landmark names for L/R swap detection
_SWAP_PAIRS: list[tuple[str, str]] = [
    ("left_shoulder", "right_shoulder"),
    ("left_elbow", "right_elbow"),
    ("left_wrist", "right_wrist"),
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
    ("left_ankle", "right_ankle"),
]

_SIDE_OR_OBLIQUE_ZONES = {"Z2", "Z3", "Z4", "Z6", "Z7", "Z8"}
_FRONTAL_ZONES = {"Z1", "Z5"}
_AVAILABILITY_STATES = {"assessed", "low_confidence", "not_assessed"}
_FAR_SIDE_JITTER_DEFAULT_VELOCITY_MULTIPLIER = 3.0


# ── Pure coordinate helpers ───────────────────────────────────────────────────


def _xyz(df: pd.DataFrame, lm: str) -> np.ndarray:
    """Return (T, 3) float array of xyz coordinates for a landmark."""
    return df[[f"{lm}_x", f"{lm}_y", f"{lm}_z"]].values.astype(float)


def _segment_length(df: pd.DataFrame, lm1: str, lm2: str) -> np.ndarray:
    """Return (T,) per-frame Euclidean distance between two landmarks."""
    return np.linalg.norm(_xyz(df, lm1) - _xyz(df, lm2), axis=1)


def _joint_angle_deg(df: pd.DataFrame, prox: str, vert: str, dist: str) -> np.ndarray:
    """
    Return (T,) included angle in degrees at the vertex landmark.

    Degenerate frames (zero-length bone) return NaN so no bound is violated.
    """
    v_prox = _xyz(df, prox) - _xyz(df, vert)  # (T, 3)
    v_dist = _xyz(df, dist) - _xyz(df, vert)  # (T, 3)
    norm_p = np.linalg.norm(v_prox, axis=1)  # (T,)
    norm_d = np.linalg.norm(v_dist, axis=1)
    denom = norm_p * norm_d
    safe = denom > 1e-9
    cos_a = np.where(
        safe, np.sum(v_prox * v_dist, axis=1) / np.where(safe, denom, 1.0), np.nan
    )
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
    mask: np.ndarray,  # (T, len(present)), True = reliable; modified in-place
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
        xyz = _xyz(df, lm)  # (T, 3)
        disp = np.linalg.norm(np.diff(xyz, axis=0), axis=1)  # (T-1,)
        velocity = np.concatenate([[0.0], disp])  # frame 0 has no prior
        outlier = velocity > vel_threshold
        total += int(np.sum(outlier & mask[:, i]))
        mask[:, i] &= ~outlier
    return total


# ── Swap detection ────────────────────────────────────────────────────────────


def _run_swap_detection(
    df: pd.DataFrame,
    present_set: set[str],
    swap_cfg: Any,  # SwapDetectionConfig
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

    active_pairs = [
        (left_landmark, right_landmark)
        for (left_landmark, right_landmark) in _SWAP_PAIRS
        if left_landmark in present_set and right_landmark in present_set
    ]
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
            notes[t] = (
                f"temporal_consistency swap at t={t} (vote={swap_votes[t]}/{len(active_pairs)})"
            )
        num_corrected = len(swap_frame_indices)

    # Orientation prior (heuristic count only — no additional correction)
    num_orientation_disagree = 0
    if (
        swap_cfg.orientation_prior
        and "left_hip" in present_set
        and "right_hip" in present_set
    ):
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


def _find_true_runs(arr: np.ndarray) -> list[tuple[int, int]]:
    """Return (start, end) inclusive index pairs for contiguous True runs."""
    return _find_false_runs(~arr.astype(bool))


def _run_interpolation(
    df: pd.DataFrame,
    present: list[str],
    mask: np.ndarray,  # (T, len(present)); modified in-place to mark resolved gaps as reliable
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
            has_left = start > 0 and mask[start - 1, i]
            has_right = end < T - 1 and mask[end + 1, i]
            if gap <= max_gap and has_left and has_right:
                left_row = df.index[start - 1]
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
                mask[start : end + 1, i] = True
                n_short += 1
            else:
                n_long += 1
    return n_short, n_long


def _run_post_interpolation_velocity_check(
    df: pd.DataFrame,
    present: list[str],
    torso_scale: float,
    fps: float,
    threshold_torso_per_sec: float,
    mask: np.ndarray,
    recovered_mask: np.ndarray,
) -> tuple[int, np.ndarray]:
    """
    Revoke interpolated landmark-frames that still create implausible velocity.

    Only frames recovered by interpolation are eligible. Original observations
    are not reclassified here because the observed reliability pass has already
    handled them.
    """
    vel_threshold = threshold_torso_per_sec * torso_scale / max(fps, 1.0)
    failed = np.zeros_like(mask, dtype=bool)
    T = len(df)
    if T == 0:
        return 0, failed
    for i, lm in enumerate(present):
        xyz = _xyz(df, lm)
        disp = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
        incoming = np.concatenate([[0.0], disp])
        outgoing = np.concatenate([disp, [0.0]])
        velocity_bad = (incoming > vel_threshold) | (outgoing > vel_threshold)
        eligible = recovered_mask[:, i] & mask[:, i]
        failed[:, i] = eligible & velocity_bad

    mask[failed] = False
    return int(np.sum(failed)), failed


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


# ── Far-side observation confidence ──────────────────────────────────────────


def _unique_strings(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    values = df[column].dropna().astype(str)
    return sorted({value for value in values if value})


def _representative_string(df: pd.DataFrame, column: str) -> str | None:
    """Return the most common meaningful non-null string while preserving tie order."""
    if column not in df.columns:
        return None
    counts: dict[str, int] = {}
    order: list[str] = []
    for value in df[column].tolist():
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except (TypeError, ValueError):
            pass
        text = str(value).strip()
        if not text or text.lower() in {"none", "nan", "nat"}:
            continue
        if text not in counts:
            counts[text] = 0
            order.append(text)
        counts[text] += 1
    if not order:
        return None
    return max(order, key=lambda item: counts[item])


def _frame_report_value(df: pd.DataFrame, row_index: int) -> int:
    """Return a JSON-friendly frame identifier for report summaries."""
    if "frame" not in df.columns:
        return int(row_index)
    value = df.iloc[row_index]["frame"]
    if pd.isna(value):
        return int(row_index)
    return int(value)


def _build_landmark_quality_summary(
    present: list[str],
    observed_mask: np.ndarray,
    usable_mask: np.ndarray,
    recovered_mask: np.ndarray,
    post_velocity_failed_mask: np.ndarray,
    visibility_counts: dict[str, int],
) -> list[dict[str, Any]]:
    """Summarize landmark-level preprocessing provenance for QC review."""
    summary: list[dict[str, Any]] = []
    for i, landmark in enumerate(present):
        observed_unreliable = int(np.sum(~observed_mask[:, i]))
        unusable = int(np.sum(~usable_mask[:, i]))
        recovered = int(np.sum(recovered_mask[:, i]))
        post_velocity_failed = int(np.sum(post_velocity_failed_mask[:, i]))
        summary.append(
            {
                "landmark": landmark,
                "low_visibility_frames": int(visibility_counts.get(landmark, 0)),
                "observed_unreliable_frames": observed_unreliable,
                "unusable_frames": unusable,
                "recovered_by_interpolation": recovered,
                "post_interpolation_velocity_failed": post_velocity_failed,
            }
        )
    return summary


def _top_landmark_quality(
    landmark_quality_summary: list[dict[str, Any]],
    key: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return the highest-count landmark QC rows for a given count key."""
    rows = [row for row in landmark_quality_summary if int(row.get(key, 0)) > 0]
    rows = sorted(rows, key=lambda row: (-int(row[key]), str(row["landmark"])))
    return rows[:limit]


def _frames_with_many_unusable_landmarks(
    df: pd.DataFrame,
    usable_mask: np.ndarray,
    present: list[str],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return frames with the largest number of unusable landmarks."""
    if not present:
        return []
    unusable_counts = np.sum(~usable_mask, axis=1)
    rows: list[dict[str, Any]] = []
    for row_index, count in enumerate(unusable_counts):
        count = int(count)
        if count <= 0:
            continue
        rows.append(
            {
                "frame": _frame_report_value(df, row_index),
                "unusable_landmark_count": count,
                "unusable_landmark_ratio": float(count / len(present)),
            }
        )
    rows.sort(key=lambda row: (-int(row["unusable_landmark_count"]), row["frame"]))
    return rows[:limit]


def _supports_camera_side_inference(zones: list[str]) -> bool:
    """Return whether camera-side inference is meaningful for the observed zones."""
    if not zones:
        return True
    zone_set = set(zones)
    if zone_set and zone_set.issubset(_FRONTAL_ZONES):
        return False
    return bool(zone_set & _SIDE_OR_OBLIQUE_ZONES)


def _landmark_visibility(
    df: pd.DataFrame,
    landmark: str,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    vis_col = f"{landmark}_visibility"
    if vis_col not in df.columns:
        visibility = np.ones(len(df), dtype=float)
    else:
        visibility = df[vis_col].astype(float).to_numpy()
        visibility = np.where(np.isfinite(visibility), visibility, 0.0)
    low_visibility = visibility < threshold
    return visibility, low_visibility


def _landmark_jitter_score(
    df: pd.DataFrame,
    landmark: str,
    *,
    torso_scale: float,
    fps: float,
    velocity_threshold: float,
    acceleration_threshold: float,
    visibility_threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    coords = _xyz(df, landmark)
    scale = max(float(torso_scale), 1e-9)
    safe_fps = max(float(fps), 1.0)

    disp = np.linalg.norm(np.diff(coords, axis=0), axis=1)
    velocity = np.concatenate([[0.0], disp * safe_fps / scale])

    if len(coords) >= 3:
        accel_vec = coords[2:] - 2.0 * coords[1:-1] + coords[:-2]
        accel = np.concatenate(
            [[0.0, 0.0], np.linalg.norm(accel_vec, axis=1) * safe_fps**2 / scale]
        )
    else:
        accel = np.zeros(len(df), dtype=float)

    _, low_visibility = _landmark_visibility(
        df, landmark, visibility_threshold
    )

    score = np.maximum.reduce(
        [
            velocity / max(velocity_threshold, 1e-9),
            accel / max(acceleration_threshold, 1e-9),
        ]
    )
    return score, low_visibility


def _assign_pair_camera_side(
    df: pd.DataFrame,
    left: str,
    right: str,
    *,
    depth_axis: str,
    near_depth_sign: str,
    min_depth_offset: float,
    allow_inference: bool,
) -> tuple[np.ndarray, np.ndarray]:
    left_side = np.full(len(df), "unknown", dtype=object)
    right_side = np.full(len(df), "unknown", dtype=object)
    left_col = f"{left}_{depth_axis}"
    right_col = f"{right}_{depth_axis}"
    if not allow_inference or left_col not in df.columns or right_col not in df.columns:
        return left_side, right_side

    left_depth = df[left_col].astype(float).to_numpy()
    right_depth = df[right_col].astype(float).to_numpy()
    finite = np.isfinite(left_depth) & np.isfinite(right_depth)

    if near_depth_sign == "positive":
        left_near = finite & (left_depth > right_depth + min_depth_offset)
        right_near = finite & (right_depth > left_depth + min_depth_offset)
    else:
        left_near = finite & (left_depth + min_depth_offset < right_depth)
        right_near = finite & (right_depth + min_depth_offset < left_depth)

    left_side[left_near] = "near_side"
    right_side[left_near] = "far_side"
    left_side[right_near] = "far_side"
    right_side[right_near] = "near_side"
    return left_side, right_side


def _interpolate_or_smooth_unstable_frames(
    df: pd.DataFrame,
    landmark: str,
    unstable: np.ndarray,
    *,
    max_gap: int,
    smoothing_method: str,
    smoothing_window_size: int,
) -> tuple[int, int, int]:
    num_interpolated_gaps = 0
    num_unresolved_gaps = 0
    num_smoothed_values = 0

    if not bool(unstable.any()):
        return num_interpolated_gaps, num_unresolved_gaps, num_smoothed_values

    for start, end in _find_true_runs(unstable):
        gap = end - start + 1
        has_left = start > 0 and not unstable[start - 1]
        has_right = end < len(df) - 1 and not unstable[end + 1]
        if gap <= max_gap and has_left and has_right:
            left_row = df.index[start - 1]
            right_row = df.index[end + 1]
            can_interpolate = True
            for ax in ("x", "y", "z"):
                col = f"{landmark}_{ax}"
                can_interpolate &= col in df.columns
                if can_interpolate:
                    can_interpolate &= np.isfinite(float(df.at[left_row, col]))
                    can_interpolate &= np.isfinite(float(df.at[right_row, col]))
            if can_interpolate:
                for ax in ("x", "y", "z"):
                    col = f"{landmark}_{ax}"
                    v0 = float(df.at[left_row, col])
                    v1 = float(df.at[right_row, col])
                    for offset in range(gap):
                        alpha = (offset + 1) / (gap + 1)
                        df.at[df.index[start + offset], col] = v0 + alpha * (v1 - v0)
                num_interpolated_gaps += 1
                continue

        num_unresolved_gaps += 1
        run_mask = np.zeros(len(df), dtype=bool)
        run_mask[start : end + 1] = True
        for ax in ("x", "y", "z"):
            col = f"{landmark}_{ax}"
            if col not in df.columns:
                continue
            values = df[col].astype(float)
            if smoothing_method == "rolling_median":
                smoothed = values.rolling(
                    smoothing_window_size,
                    center=True,
                    min_periods=1,
                ).median()
            elif smoothing_method == "moving_average":
                smoothed = values.rolling(
                    smoothing_window_size,
                    center=True,
                    min_periods=1,
                ).mean()
            else:
                continue
            df.loc[df.index[run_mask], col] = smoothed.loc[df.index[run_mask]].values
            num_smoothed_values += int(run_mask.sum())

    return num_interpolated_gaps, num_unresolved_gaps, num_smoothed_values


def _view_metric_reliability_for_zones(
    exercise_definition: "ExerciseDefinition | None",
    zones: list[str],
    metric_keys: list[str],
) -> str | None:
    if exercise_definition is None:
        return None
    view_map = getattr(exercise_definition, "view_metric_reliability", {}) or {}
    zone_map = view_map.get("zones") or {}
    for zone in zones:
        values = zone_map.get(zone) or {}
        for metric_key in metric_keys:
            reliability = values.get(metric_key)
            if reliability in {"high", "moderate", "low", "not_assessed"}:
                return str(reliability)
    return None


def _feature_availability_summary(
    *,
    laterality: str,
    zones: list[str],
    num_high_jitter_far_side: int,
    exercise_definition: "ExerciseDefinition | None",
) -> dict[str, Any]:
    low_confidence: list[str] = []
    not_assessed: list[str] = []
    reasons: dict[str, list[str]] = {}

    is_bilateral = laterality == "bilateral_symmetric"
    metric_keys = (
        ["bilateral_symmetry", "side_to_side_comparison"]
        if is_bilateral
        else ["side_to_side_comparison", "frontal_alignment"]
    )
    reliability = _view_metric_reliability_for_zones(
        exercise_definition, zones, metric_keys
    )

    if reliability == "not_assessed":
        not_assessed.append("spatial.symmetry.*")
        reasons.setdefault("spatial.symmetry.*", []).append(
            "view_metric_reliability_not_assessed"
        )
    elif reliability == "low":
        low_confidence.append("spatial.symmetry.*")
        reasons.setdefault("spatial.symmetry.*", []).append(
            "view_metric_reliability_low"
        )
    elif is_bilateral and zones and set(zones).issubset({"Z3", "Z7"}):
        low_confidence.append("spatial.symmetry.*")
        reasons.setdefault("spatial.symmetry.*", []).append(
            "side_view_low_left_right_reliability"
        )

    if num_high_jitter_far_side > 0:
        low_confidence.append("spatial.symmetry.*")
        reasons.setdefault("spatial.symmetry.*", []).append("far_side_jitter_present")

    low_confidence = sorted(set(low_confidence))
    not_assessed = sorted(set(not_assessed))
    return {
        "symmetry_gate_ready": not low_confidence and not not_assessed,
        "low_confidence_feature_families": low_confidence,
        "not_assessed_feature_families": not_assessed,
        "view_metric_reliability": reliability,
        "reasons": reasons,
    }


def _run_far_side_stabilization(
    df: pd.DataFrame,
    observed_df: pd.DataFrame,
    present: list[str],
    present_set: set[str],
    mask: np.ndarray,
    observed_mask: np.ndarray,
    *,
    torso_scale: float,
    fps: float,
    laterality: str,
    exercise_definition: "ExerciseDefinition | None",
    config: Any,
    swap_corrected: np.ndarray,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str], dict[str, Any]]:
    far_cfg = getattr(config, "far_side_stabilization", None)
    if far_cfg is None or not far_cfg.enabled:
        return None, None, [], {}

    zones = _unique_strings(df, "camera_zone")
    allow_inference = bool(
        far_cfg.camera_side_inference
    ) and _supports_camera_side_inference(zones)
    velocity_threshold = (
        float(far_cfg.jitter_threshold_torso_per_sec)
        if far_cfg.jitter_threshold_torso_per_sec is not None
        else float(config.reliability.velocity_threshold_torso_per_sec)
        * _FAR_SIDE_JITTER_DEFAULT_VELOCITY_MULTIPLIER
    )
    acceleration_threshold = (
        float(far_cfg.acceleration_threshold_torso_per_sec2)
        if far_cfg.acceleration_threshold_torso_per_sec2 is not None
        else velocity_threshold * max(float(fps), 1.0)
    )
    min_depth_offset = float(far_cfg.min_depth_offset_torso) * max(torso_scale, 1e-9)

    landmark_side: dict[str, np.ndarray] = {
        lm: np.full(len(df), "unknown", dtype=object) for lm in present
    }
    for left, right in _SWAP_PAIRS:
        if left not in present_set or right not in present_set:
            continue
        left_side, right_side = _assign_pair_camera_side(
            df,
            left,
            right,
            depth_axis=far_cfg.depth_axis,
            near_depth_sign=far_cfg.near_depth_sign,
            min_depth_offset=min_depth_offset,
            allow_inference=allow_inference,
        )
        landmark_side[left] = left_side
        landmark_side[right] = right_side

    applied_columns: list[str] = []
    num_near = 0
    num_far = 0
    num_unknown = 0
    num_observed_low_confidence_far = 0
    num_observed_high_jitter_far = 0
    num_post_low_confidence_far = 0
    num_post_high_jitter_far = 0
    num_far_gaps_interpolated = 0
    num_far_gaps_unresolved = 0
    num_far_values_smoothed = 0
    frame_low_confidence = np.zeros(len(df), dtype=bool)
    present_index = {lm: idx for idx, lm in enumerate(present)}
    output_columns: dict[str, Any] = {}

    for landmark in present:
        side = landmark_side[landmark]
        observed_score, observed_low_visibility = _landmark_jitter_score(
            observed_df,
            landmark,
            torso_scale=torso_scale,
            fps=fps,
            velocity_threshold=velocity_threshold,
            acceleration_threshold=acceleration_threshold,
            visibility_threshold=float(far_cfg.visibility_threshold),
        )
        score, low_visibility = _landmark_jitter_score(
            df,
            landmark,
            torso_scale=torso_scale,
            fps=fps,
            velocity_threshold=velocity_threshold,
            acceleration_threshold=acceleration_threshold,
            visibility_threshold=float(far_cfg.visibility_threshold),
        )
        lm_mask = mask[:, present_index[landmark]]
        observed_lm_mask = observed_mask[:, present_index[landmark]]
        observed_low_confidence_far = (side == "far_side") & (
            observed_low_visibility | ~observed_lm_mask | swap_corrected
        )
        observed_high_jitter_far = (side == "far_side") & (
            observed_score >= 1.0
        ) & observed_low_confidence_far
        post_low_confidence_far = (side == "far_side") & (
            low_visibility | ~lm_mask | swap_corrected
        )
        post_high_jitter_far = (side == "far_side") & (
            score >= 1.0
        ) & post_low_confidence_far
        unstable_far = post_low_confidence_far | post_high_jitter_far

        (
            interpolated,
            unresolved,
            smoothed,
        ) = _interpolate_or_smooth_unstable_frames(
            df,
            landmark,
            unstable_far,
            max_gap=int(far_cfg.max_gap_frames),
            smoothing_method=far_cfg.smoothing_method,
            smoothing_window_size=int(far_cfg.smoothing_window_size),
        )

        confidence_note = np.full(len(df), "", dtype=object)
        confidence_note[unstable_far] = "far_side_low_confidence"
        confidence_note[post_high_jitter_far] = "far_side_jitter_low_confidence"
        if interpolated:
            confidence_note[unstable_far] = "far_side_stabilized"

        output_columns[f"{landmark}_camera_side"] = side
        output_columns[f"{landmark}_jitter_score"] = score
        output_columns[f"{landmark}_confidence_note"] = confidence_note
        applied_columns.extend(
            [
                f"{landmark}_camera_side",
                f"{landmark}_jitter_score",
                f"{landmark}_confidence_note",
            ]
        )

        num_near += int(np.sum(side == "near_side"))
        num_far += int(np.sum(side == "far_side"))
        num_unknown += int(np.sum(side == "unknown"))
        num_observed_low_confidence_far += int(np.sum(observed_low_confidence_far))
        num_observed_high_jitter_far += int(np.sum(observed_high_jitter_far))
        num_post_low_confidence_far += int(np.sum(post_low_confidence_far))
        num_post_high_jitter_far += int(np.sum(post_high_jitter_far))
        num_far_gaps_interpolated += interpolated
        num_far_gaps_unresolved += unresolved
        num_far_values_smoothed += smoothed
        frame_low_confidence |= unstable_far

    output_columns["preprocessing_confidence"] = np.where(
        frame_low_confidence,
        "low_confidence",
        "assessed",
    )
    applied_columns.append("preprocessing_confidence")

    summary = {
        "enabled": True,
        "camera_side_inference": {
            "enabled": bool(far_cfg.camera_side_inference),
            "observed_zones": zones,
            "allow_inference": allow_inference,
            "depth_axis": far_cfg.depth_axis,
            "near_depth_sign": far_cfg.near_depth_sign,
            "min_depth_offset_torso": float(far_cfg.min_depth_offset_torso),
        },
        "num_near_side_landmark_frames": num_near,
        "num_far_side_landmark_frames": num_far,
        "num_unknown_side_landmark_frames": num_unknown,
        "num_observed_low_confidence_far_side_landmark_frames": (
            num_observed_low_confidence_far
        ),
        "num_observed_high_jitter_far_side_landmark_frames": (
            num_observed_high_jitter_far
        ),
        "num_post_preprocessing_low_confidence_far_side_landmark_frames": (
            num_post_low_confidence_far
        ),
        "num_post_preprocessing_high_jitter_far_side_landmark_frames": (
            num_post_high_jitter_far
        ),
        "num_far_side_gaps_interpolated": num_far_gaps_interpolated,
        "num_far_side_gaps_unresolved": num_far_gaps_unresolved,
        "num_far_side_values_smoothed": num_far_values_smoothed,
        "velocity_threshold_torso_per_sec": velocity_threshold,
        "acceleration_threshold_torso_per_sec2": acceleration_threshold,
        "jitter_detection_policy": (
            "conservative_motion_spike_with_low_confidence_context"
        ),
    }
    availability = _feature_availability_summary(
        laterality=laterality,
        zones=zones,
        num_high_jitter_far_side=num_post_high_jitter_far,
        exercise_definition=exercise_definition,
    )
    return summary, availability, applied_columns, output_columns


# ── Main entry point ──────────────────────────────────────────────────────────


def preprocess_pose_dataframe(
    df: pd.DataFrame,
    landmarks: list[str],
    exercise_definition: "ExerciseDefinition | None",
    config: Any,  # PreprocessingConfig
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
          <landmark>_observed_reliable
                                (bool, source observation quality before repair)
          <landmark>_usable    (bool, usable by the next stage after short-gap repair)
          <landmark>_preprocessing_source
                                (str, observed | short_gap_interpolated | unusable)
          <landmark>_camera_side / _jitter_score / _confidence_note
                                (when far_side_stabilization is enabled)
          preprocessing_valid  (bool, frame-level summary)
          preprocessing_note   (str,  reason string when swap applied)
          preprocessing_confidence
                                (when far_side_stabilization is enabled)
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
        max_gap_from_def = (
            exercise_definition.quality_rules.max_interpolation_gap_frames
        )

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
        pre_df,
        present,
        torso_scale,
        fps,
        config.reliability.velocity_threshold_torso_per_sec,
        mask,
    )

    # Step 4: Joint angle bounds
    n_angle_violations = 0
    if config.reliability.joint_angle_check:
        n_angle_violations = _run_joint_angle_check(pre_df, present_set, present, mask)

    observed_mask = mask.copy()
    observed_df_for_far_side = pre_df.copy()
    num_observed_unreliable_lm_frames = int(np.sum(~observed_mask))

    # ── Frame-level validity (before interpolation) ───────────────────────────
    frame_reliable = mask.all(axis=1)

    # ── Swap detection ────────────────────────────────────────────────────────
    swap_corrected = np.zeros(T, dtype=bool)
    swap_notes: list[str] = [""] * T
    num_temporal_swap = 0
    num_orient_disagree = 0

    if do_swap:
        swap_corrected, swap_notes, num_temporal_swap, num_orient_disagree = (
            _run_swap_detection(pre_df, present_set, config.swap_detection)
        )

    # ── Short-gap interpolation ───────────────────────────────────────────────
    n_short_gaps = n_long_gaps = 0
    n_post_velocity_rejected = 0
    post_velocity_failed_mask = np.zeros_like(mask, dtype=bool)
    if config.interpolation.enabled:
        n_short_gaps, n_long_gaps = _run_interpolation(
            pre_df, present, mask, max_gap_from_def
        )
        recovered_after_interpolation = (~observed_mask) & mask
        if config.interpolation.post_velocity_check:
            n_post_velocity_rejected, post_velocity_failed_mask = (
                _run_post_interpolation_velocity_check(
                    pre_df,
                    present,
                    torso_scale,
                    fps,
                    config.reliability.velocity_threshold_torso_per_sec,
                    mask,
                    recovered_after_interpolation,
                )
            )
        frame_reliable = mask.all(axis=1)  # recompute after gaps resolved

    recovered_mask = (~observed_mask) & mask
    num_recovered_lm_frames = int(np.sum(recovered_mask))
    num_unusable_lm_frames = int(np.sum(~mask))
    landmark_quality_summary = _build_landmark_quality_summary(
        present,
        observed_mask=observed_mask,
        usable_mask=mask,
        recovered_mask=recovered_mask,
        post_velocity_failed_mask=post_velocity_failed_mask,
        visibility_counts=vis_counts,
    )
    rule_contribution_summary = {
        "low_visibility_landmark_frames": int(sum(vis_counts.values())),
        "segment_length_violation_events": int(n_segment_violations),
        "velocity_outlier_landmark_frames": int(n_velocity_outliers),
        "joint_angle_violation_events": int(n_angle_violations),
        "observed_unreliable_landmark_frames": num_observed_unreliable_lm_frames,
        "unusable_landmark_frames_after_interpolation": num_unusable_lm_frames,
        "landmark_frames_recovered_by_interpolation": num_recovered_lm_frames,
        "post_interpolation_velocity_rejected_landmark_frames": (
            n_post_velocity_rejected
        ),
        "note": (
            "Rule counts are QC provenance and may overlap; they are not "
            "movement-quality scores."
        ),
    }
    worst_landmarks_by_observed_unreliable = _top_landmark_quality(
        landmark_quality_summary, "observed_unreliable_frames"
    )
    worst_landmarks_by_unusable = _top_landmark_quality(
        landmark_quality_summary, "unusable_frames"
    )
    frames_with_many_unusable_landmarks = _frames_with_many_unusable_landmarks(
        pre_df, mask, present
    )

    (
        far_side_summary,
        feature_availability_summary,
        far_side_applied_columns,
        far_side_output_columns,
    ) = _run_far_side_stabilization(
        pre_df,
        observed_df_for_far_side,
        present,
        present_set,
        mask,
        observed_mask,
        torso_scale=torso_scale,
        fps=fps,
        laterality=laterality,
        exercise_definition=exercise_definition,
        config=config,
        swap_corrected=swap_corrected,
    )

    # ── Smoothing ─────────────────────────────────────────────────────────────
    smoothing_applied: list[str] = []
    if config.smoothing.enabled:
        smoothing_applied = _run_smoothing(
            pre_df, present, config.smoothing.method, config.smoothing.window_size
        )

    # ── Per-landmark observed/usable columns ─────────────────────────────────
    status_columns: dict[str, Any] = {}
    for i, lm in enumerate(present):
        status_columns[f"{lm}_observed_reliable"] = observed_mask[:, i]
        status_columns[f"{lm}_usable"] = mask[:, i]
        status_columns[f"{lm}_preprocessing_source"] = np.where(
            observed_mask[:, i],
            "observed",
            np.where(
                post_velocity_failed_mask[:, i],
                "post_interpolation_velocity_failed",
                np.where(mask[:, i], "short_gap_interpolated", "unusable"),
            ),
        )

    # ── Output columns ────────────────────────────────────────────────────────
    status_columns["preprocessing_valid"] = frame_reliable
    status_columns["preprocessing_note"] = swap_notes
    status_columns["swap_corrected"] = swap_corrected
    status_columns.update(far_side_output_columns)
    pre_df = pd.concat(
        [pre_df, pd.DataFrame(status_columns, index=pre_df.index)], axis=1
    )

    # ── Report ────────────────────────────────────────────────────────────────
    exercise_id = (
        exercise_definition.exercise_id if exercise_definition is not None else None
    )
    movement_template_id = (
        exercise_definition.classification.get("movement_template_id")
        if exercise_definition is not None
        else None
    )
    execution_pattern = _representative_string(pre_df, "execution_pattern")

    num_invalid_frames = int(np.sum(~frame_reliable))

    pre_report: dict[str, Any] = {
        "method": "reliability_mask_v1",
        "exercise_id": exercise_id,
        "movement_template_id": movement_template_id,
        "execution_pattern": execution_pattern,
        "laterality": laterality,
        "num_frames": T,
        "num_coordinate_columns": sum(
            1
            for lm in present
            for ax in ("x", "y", "z")
            if f"{lm}_{ax}" in pre_df.columns
        ),
        "reliability_summary": {
            "visibility_threshold": config.reliability.visibility_threshold,
            "num_low_visibility_frames_per_landmark": vis_counts,
            "num_low_visibility_total": sum(vis_counts.values()),
            "num_segment_length_violations": n_segment_violations,
            "num_joint_angle_violations": n_angle_violations,
            "num_velocity_outliers": n_velocity_outliers,
            "num_observed_unreliable_landmark_frames": (
                num_observed_unreliable_lm_frames
            ),
            "num_unusable_landmark_frames": num_unusable_lm_frames,
        },
        "landmark_quality_summary": landmark_quality_summary,
        "rule_contribution_summary": rule_contribution_summary,
        "worst_landmarks_by_observed_unreliable": (
            worst_landmarks_by_observed_unreliable
        ),
        "worst_landmarks_by_unusable": worst_landmarks_by_unusable,
        "frames_with_many_unusable_landmarks": frames_with_many_unusable_landmarks,
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
            "num_landmark_frames_recovered": num_recovered_lm_frames,
            "post_velocity_check_enabled": (
                config.interpolation.enabled
                and config.interpolation.post_velocity_check
            ),
            "num_post_velocity_rejected_landmark_frames": (
                n_post_velocity_rejected
            ),
        },
        "smoothing_summary": {
            "enabled": config.smoothing.enabled,
            "method": config.smoothing.method,
            "window_size": config.smoothing.window_size,
            "applied_columns": smoothing_applied,
        },
        "far_side_stabilization_summary": far_side_summary,
        "feature_availability_summary": feature_availability_summary,
        "num_invalid_frames": num_invalid_frames,
        "applied_columns": (
            [f"{lm}_observed_reliable" for lm in present]
            + [f"{lm}_usable" for lm in present]
            + [f"{lm}_preprocessing_source" for lm in present]
            + ["preprocessing_valid", "preprocessing_note", "swap_corrected"]
            + far_side_applied_columns
        ),
    }

    return pre_df, pre_report
