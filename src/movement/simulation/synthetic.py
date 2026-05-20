"""
Synthetic data generation and simulation condition injection.

Injects ROM restriction, Gaussian coordinate noise, occlusion, or velocity spikes into
a normal pose dataframe to produce synthetic variant datasets for robustness evaluation.

All functions return a modified copy; the original dataframe is not modified.
Each function also returns a simulation_log dict recording what was applied.

Units:
    noise σ             : torso_length_ratio
    velocity spike size : torso_length_ratio
    ROM restriction     : degree
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from movement.core.config import LANDMARKS


# Synthetic standing reference pose (image-normalized, y-down).
STANDING_POSE: dict[str, tuple[float, float, float]] = {
    "nose": (0.500, 0.180, 0.010),
    "left_eye_inner": (0.488, 0.170, 0.010),
    "left_eye": (0.482, 0.168, 0.010),
    "left_eye_outer": (0.476, 0.170, 0.010),
    "right_eye_inner": (0.512, 0.170, 0.010),
    "right_eye": (0.518, 0.168, 0.010),
    "right_eye_outer": (0.524, 0.170, 0.010),
    "left_ear": (0.470, 0.180, 0.020),
    "right_ear": (0.530, 0.180, 0.020),
    "mouth_left": (0.490, 0.205, 0.010),
    "mouth_right": (0.510, 0.205, 0.010),
    "left_shoulder": (0.430, 0.300, 0.010),
    "right_shoulder": (0.570, 0.300, 0.010),
    "left_elbow": (0.420, 0.430, -0.020),
    "right_elbow": (0.580, 0.430, -0.020),
    "left_wrist": (0.430, 0.540, -0.040),
    "right_wrist": (0.570, 0.540, -0.040),
    "left_pinky": (0.422, 0.560, -0.045),
    "right_pinky": (0.578, 0.560, -0.045),
    "left_index": (0.418, 0.555, -0.045),
    "right_index": (0.582, 0.555, -0.045),
    "left_thumb": (0.434, 0.555, -0.040),
    "right_thumb": (0.566, 0.555, -0.040),
    "left_hip": (0.460, 0.520, 0.000),
    "right_hip": (0.540, 0.520, 0.000),
    "left_knee": (0.460, 0.720, 0.000),
    "right_knee": (0.540, 0.720, 0.000),
    "left_ankle": (0.460, 0.920, 0.005),
    "right_ankle": (0.540, 0.920, 0.005),
    "left_heel": (0.460, 0.940, 0.020),
    "right_heel": (0.540, 0.940, 0.020),
    "left_foot_index": (0.460, 0.950, -0.020),
    "right_foot_index": (0.540, 0.950, -0.020),
}


BOTTOM_DELTAS: dict[str, tuple[float, float, float]] = {
    "nose": (0.000, 0.105, -0.020),
    "left_eye_inner": (0.000, 0.105, -0.020),
    "left_eye": (0.000, 0.105, -0.020),
    "left_eye_outer": (0.000, 0.105, -0.020),
    "right_eye_inner": (0.000, 0.105, -0.020),
    "right_eye": (0.000, 0.105, -0.020),
    "right_eye_outer": (0.000, 0.105, -0.020),
    "left_ear": (0.000, 0.105, -0.020),
    "right_ear": (0.000, 0.105, -0.020),
    "mouth_left": (0.000, 0.105, -0.020),
    "mouth_right": (0.000, 0.105, -0.020),
    "left_shoulder": (0.000, 0.110, -0.025),
    "right_shoulder": (0.000, 0.110, -0.025),
    "left_elbow": (0.000, 0.080, -0.060),
    "right_elbow": (0.000, 0.080, -0.060),
    "left_wrist": (0.000, 0.040, -0.090),
    "right_wrist": (0.000, 0.040, -0.090),
    "left_pinky": (0.000, 0.040, -0.090),
    "right_pinky": (0.000, 0.040, -0.090),
    "left_index": (0.000, 0.040, -0.090),
    "right_index": (0.000, 0.040, -0.090),
    "left_thumb": (0.000, 0.040, -0.090),
    "right_thumb": (0.000, 0.040, -0.090),
    "left_hip": (0.000, 0.130, 0.005),
    "right_hip": (0.000, 0.130, 0.005),
    "left_knee": (-0.005, 0.000, -0.060),
    "right_knee": (0.005, 0.000, -0.060),
    "left_ankle": (0.000, 0.000, 0.000),
    "right_ankle": (0.000, 0.000, 0.000),
    "left_heel": (0.000, 0.000, 0.000),
    "right_heel": (0.000, 0.000, 0.000),
    "left_foot_index": (0.000, 0.000, 0.000),
    "right_foot_index": (0.000, 0.000, 0.000),
}


# ── Internal helpers ─────────────────────────────────────────────────────────


def _xyz_cols(lm: str) -> list[str]:
    return [f"{lm}_x", f"{lm}_y", f"{lm}_z"]


def _get_torso_scale(df: pd.DataFrame) -> float:
    """Sequence-wise median torso length (raw scale corresponding to torso_length_ratio = 1.0)."""
    if "torso_length" in df.columns:
        return float(df["torso_length"].median())
    # Fallback: estimate from hip–shoulder distance if torso_length column is absent
    try:
        lhs = df[["left_shoulder_x", "left_shoulder_y", "left_shoulder_z"]].values
        rhs = df[["right_shoulder_x", "right_shoulder_y", "right_shoulder_z"]].values
        lhh = df[["left_hip_x", "left_hip_y", "left_hip_z"]].values
        rhh = df[["right_hip_x", "right_hip_y", "right_hip_z"]].values
        sc = (lhs + rhs) / 2.0
        hc = (lhh + rhh) / 2.0
        lengths = np.linalg.norm(sc - hc, axis=1)
        return float(np.median(lengths))
    except KeyError:
        return 1.0


def squat_phase(frame: int, start: int, end: int) -> float:
    """Map a frame inside a rep window to a smooth squat phase in [0, 1]."""
    t = (frame - start) / (end - start)
    return 0.5 * (1.0 - np.cos(2.0 * np.pi * t))


def build_frame(
    s: float, rng: np.random.Generator
) -> dict[str, tuple[float, float, float, float]]:
    """Build one synthetic squat frame as landmark x/y/z/visibility tuples."""
    out = {}
    for lm in LANDMARKS:
        x0, y0, z0 = STANDING_POSE[lm]
        dx, dy, dz = BOTTOM_DELTAS[lm]
        x = x0 + s * dx + rng.normal(0.0, 0.0015)
        y = y0 + s * dy + rng.normal(0.0, 0.0015)
        z = z0 + s * dz + rng.normal(0.0, 0.0015)
        vis = float(np.clip(rng.normal(0.96, 0.015), 0.6, 1.0))
        out[lm] = (round(x, 5), round(y, 5), round(z, 5), round(vis, 4))
    return out


# ── Public API ───────────────────────────────────────────────────────────────


def add_gaussian_noise(
    df: pd.DataFrame,
    sigma_torso_ratio: float,
    landmarks: list[str] | None = None,
    seed: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Add Gaussian noise to x/y/z coordinates of all (or specified) landmarks.

    Parameters
    ----------
    df : pd.DataFrame
        Input pose dataframe (not modified).
    sigma_torso_ratio : float
        Noise standard deviation in torso_length_ratio units.
        Example: 0.01 = 1% of torso length.
    landmarks : list[str], optional
        Landmark names to add noise to. None applies noise to all x/y/z columns.
    seed : int, optional
        Random seed for reproducibility.

    Returns
    -------
    (noisy_df, simulation_log)
    """
    rng = np.random.default_rng(seed)
    df_out = df.copy()
    scale = _get_torso_scale(df)
    sigma_raw = sigma_torso_ratio * scale

    if landmarks is None:
        coord_cols = [
            c
            for c in df.columns
            if c.endswith(("_x", "_y", "_z"))
            and not c.startswith(("left_norm", "right_norm"))
        ]
    else:
        coord_cols = [c for lm in landmarks for c in _xyz_cols(lm) if c in df.columns]

    noise = rng.normal(0.0, sigma_raw, size=(len(df_out), len(coord_cols)))
    df_out[coord_cols] += noise

    log: dict[str, Any] = {
        "simulation": "gaussian_noise",
        "sigma_torso_ratio": sigma_torso_ratio,
        "sigma_raw": round(sigma_raw, 6),
        "num_columns_affected": len(coord_cols),
        "seed": seed,
    }
    return df_out, log


def add_occlusion(
    df: pd.DataFrame,
    target_landmarks: list[str],
    frame_range: tuple[int, int],
    zero_visibility: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Simulate occlusion for specified landmarks over a frame range.

    Coordinates are replaced with NaN and visibility set to 0.0.

    Parameters
    ----------
    df : pd.DataFrame
    target_landmarks : list[str]
        Landmark names to occlude.
    frame_range : tuple[int, int]
        (start_frame, end_frame) inclusive.
    zero_visibility : bool
        If True, also set visibility columns to 0.0.

    Returns
    -------
    (occluded_df, simulation_log)
    """
    df_out = df.copy()
    start_f, end_f = frame_range
    mask = (df_out["frame"] >= start_f) & (df_out["frame"] <= end_f)
    num_frames = int(mask.sum())

    affected_cols: list[str] = []
    for lm in target_landmarks:
        for ax in ("x", "y", "z"):
            col = f"{lm}_{ax}"
            if col in df_out.columns:
                df_out.loc[mask, col] = np.nan
                affected_cols.append(col)
        if zero_visibility:
            vis_col = f"{lm}_visibility"
            if vis_col in df_out.columns:
                df_out.loc[mask, vis_col] = 0.0

    log: dict[str, Any] = {
        "simulation": "occlusion",
        "target_landmarks": target_landmarks,
        "frame_range": list(frame_range),
        "num_frames_affected": num_frames,
        "zero_visibility": zero_visibility,
        "affected_columns": affected_cols,
    }
    return df_out, log


def add_velocity_spike(
    df: pd.DataFrame,
    target_landmarks: list[str],
    spike_frames: list[int],
    spike_magnitude_torso_ratio: float = 0.5,
    seed: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Insert position jumps at specified frames to simulate velocity spikes.

    Used to verify ④ preprocessing velocity outlier detection.

    Parameters
    ----------
    df : pd.DataFrame
    target_landmarks : list[str]
    spike_frames : list[int]
        Frame numbers to insert a jump at.
    spike_magnitude_torso_ratio : float
        Jump size in torso_length_ratio units.
    seed : int, optional

    Returns
    -------
    (spiked_df, simulation_log)
    """
    rng = np.random.default_rng(seed)
    df_out = df.copy()
    scale = _get_torso_scale(df)
    magnitude_raw = spike_magnitude_torso_ratio * scale

    for lm in target_landmarks:
        for spike_f in spike_frames:
            mask = df_out["frame"] == spike_f
            if not mask.any():
                continue
            direction = rng.normal(0.0, 1.0, size=3)
            direction /= np.linalg.norm(direction) + 1e-9
            for i, ax in enumerate(("x", "y", "z")):
                col = f"{lm}_{ax}"
                if col in df_out.columns:
                    df_out.loc[mask, col] += direction[i] * magnitude_raw

    log: dict[str, Any] = {
        "simulation": "velocity_spike",
        "target_landmarks": target_landmarks,
        "spike_frames": spike_frames,
        "spike_magnitude_torso_ratio": spike_magnitude_torso_ratio,
        "spike_magnitude_raw": round(magnitude_raw, 6),
        "seed": seed,
    }
    return df_out, log


def restrict_rom(
    df: pd.DataFrame,
    joint: str,
    restriction_deg: float,
    landmarks_triplet: tuple[str, str, str],
    rep_frames: list[tuple[int, int]] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Artificially restrict joint range of motion.

    Adjusts the distal landmark position so that the included angle does not
    exceed restriction_deg in frames where the joint exceeds the limit.

    Parameters
    ----------
    df : pd.DataFrame
        Pose dataframe with normalized or raw coordinates.
    joint : str
        Joint name (used in simulation log only).
    restriction_deg : float
        Maximum allowed included angle in degrees.
        Example: 90.0 means knee cannot flex beyond 90°.
    landmarks_triplet : tuple[str, str, str]
        (proximal_lm, vertex_lm, distal_lm) landmark names.
    rep_frames : list[tuple[int, int]], optional
        Rep intervals to apply restriction. None applies to the full sequence.

    Returns
    -------
    (restricted_df, simulation_log)

    Notes
    -----
    Modifies raw coordinate columns (<lm>_x/y/z) directly.
    Normalized coordinates (<lm>_norm_x/y/z) must be recomputed if needed.
    """
    prox_lm, vert_lm, dist_lm = landmarks_triplet
    df_out = df.copy()

    limit_rad = np.radians(restriction_deg)
    num_restricted = 0

    def _xyz(row_df: pd.DataFrame, lm: str) -> np.ndarray:
        return row_df[[f"{lm}_x", f"{lm}_y", f"{lm}_z"]].values.astype(float)

    # determine frames to apply restriction
    if rep_frames is not None:
        apply_mask = pd.Series(False, index=df_out.index)
        for s, e in rep_frames:
            apply_mask |= (df_out["frame"] >= s) & (df_out["frame"] <= e)
    else:
        apply_mask = pd.Series(True, index=df_out.index)

    for idx in df_out.index[apply_mask]:
        row = df_out.loc[[idx]]
        p = _xyz(row, prox_lm)[0]
        v = _xyz(row, vert_lm)[0]
        d = _xyz(row, dist_lm)[0]

        vp = p - v
        vd = d - v
        norm_p = np.linalg.norm(vp)
        norm_d = np.linalg.norm(vd)

        if norm_p < 1e-9 or norm_d < 1e-9:
            continue

        cos_a = np.clip(np.dot(vp, vd) / (norm_p * norm_d), -1.0, 1.0)
        angle_rad = np.arccos(cos_a)

        # joint angle exceeds limit → adjust distal landmark to limit angle
        if angle_rad > limit_rad:
            # rotate distal direction vector to make limit_rad angle with proximal direction
            # 2D approximation: rotation within the proximal-vertex plane
            vp_unit = vp / norm_p
            # Gram-Schmidt: perpendicular direction within the plane
            perp = vd - np.dot(vd, vp_unit) * vp_unit
            perp_norm = np.linalg.norm(perp)
            if perp_norm < 1e-9:
                continue
            perp_unit = perp / perp_norm
            # new distal direction = cos(limit) * vp_unit + sin(limit) * perp_unit (flexion direction)
            new_vd_unit = np.cos(limit_rad) * vp_unit + np.sin(limit_rad) * perp_unit
            new_d = v + norm_d * new_vd_unit

            df_out.loc[idx, f"{dist_lm}_x"] = round(float(new_d[0]), 5)
            df_out.loc[idx, f"{dist_lm}_y"] = round(float(new_d[1]), 5)
            df_out.loc[idx, f"{dist_lm}_z"] = round(float(new_d[2]), 5)
            num_restricted += 1

    log: dict[str, Any] = {
        "simulation": "rom_restriction",
        "joint": joint,
        "restriction_deg": restriction_deg,
        "landmarks_triplet": list(landmarks_triplet),
        "num_frames_restricted": num_restricted,
        "rep_frames": rep_frames,
    }
    return df_out, log


# ── Synthetic squat data generation ─────────────────────────────────────────


def generate_squat_csv(out_dir, fps: int = 30, seed: int = 20260503) -> None:
    """Generate synthetic squat pose CSV files.

    Accepts out_dir to preserve the data/pose/sample/ directory path.

    Parameters
    ----------
    out_dir : Path-like
        Output directory (e.g. Path("data/pose/sample")).
    fps : int
    seed : int
    """
    import csv as _csv
    from pathlib import Path as _Path

    out_dir = _Path(out_dir)
    rng = np.random.default_rng(seed=seed)

    SEGMENTS = [
        ("baseline", 0, 14, False, 1, None),
        ("rep", 15, 59, True, 1, 1),
        ("transition", 60, 74, False, None, None),
        ("rep", 75, 119, True, 1, 2),
    ]
    n_frames = SEGMENTS[-1][2] + 1

    pose_path = out_dir / "mediapipe_squat_synthetic.csv"
    pose_path.parent.mkdir(parents=True, exist_ok=True)
    header = ["frame", "timestamp"]
    for lm in LANDMARKS:
        header += [f"{lm}_x", f"{lm}_y", f"{lm}_z", f"{lm}_visibility"]

    with pose_path.open("w", newline="", encoding="utf-8") as f:
        writer = _csv.writer(f)
        writer.writerow(header)
        for frame_idx in range(n_frames):
            s = 0.0
            for kind, start, end, _use, _set, _rep in SEGMENTS:
                if start <= frame_idx <= end:
                    s = squat_phase(frame_idx, start, end) if kind == "rep" else 0.0
                    break
            row = [frame_idx, round(frame_idx / fps, 4)]
            fd = build_frame(s, rng)
            for lm in LANDMARKS:
                row += list(fd[lm])
            writer.writerow(row)

    ann_path = out_dir / "mediapipe_squat_synthetic_annotation.csv"
    with ann_path.open("w", newline="", encoding="utf-8") as f:
        writer = _csv.writer(f)
        writer.writerow(
            [
                "segment_type",
                "set_id",
                "rep_id",
                "start_frame",
                "end_frame",
                "use_for_analysis",
                "exercise_type",
                "pattern",
                "note",
            ]
        )
        for kind, start, end, use, set_id, rep_id in SEGMENTS:
            note = {
                "baseline": "standing posture before movement",
                "rep": f"descent and ascent cycle {rep_id}",
                "transition": "brief pause between reps",
            }.get(kind, "")
            writer.writerow(
                [
                    kind,
                    set_id if set_id is not None else "",
                    rep_id if rep_id is not None else "",
                    start,
                    end,
                    "true" if use else "false",
                    "squat",
                    "bilateral",
                    note,
                ]
            )
