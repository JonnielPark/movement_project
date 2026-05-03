"""
Generate a synthetic bodyweight squat pose CSV (MediaPipe 33-landmark format).

Design notes
------------
Camera convention (matches MediaPipe Pose 'world-style image' use here):
    x: image-right, normalized to roughly [0, 1]
    y: image-down,  normalized to roughly [0, 1]   (so head has small y, ankles large y)
    z: depth, smaller value = closer to camera; we use ~ +/- 0.05 around 0
    visibility: ~ N(0.95, 0.02), clipped to [0.6, 1.0]

Sequence (120 frames @ 30 fps = 4.0 s, two reps):
    0–14   baseline    standing posture
    15–59  rep 1       eccentric (descent) + concentric (ascent)
    60–74  transition  brief pause
    75–119 rep 2       eccentric + concentric

Bodyweight squat model (frontal-leaning view):
    - Hips drop vertically by ~0.13 (image units) at the bottom of the squat.
    - Knees translate slightly forward (z negative) and slightly outward.
    - Shoulders descend with the trunk; trunk leans forward modestly.
    - Ankles fixed (closed-chain assumption: feet remain on the floor).
    - Arms are held in front for balance and move slightly with the trunk.

Output: a CSV that satisfies validation in src/movement/validation.py and a
matching annotation CSV in the format src/movement/annotation.py expects.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


LANDMARKS = [
    "nose",
    "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear",
    "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_pinky", "right_pinky",
    "left_index", "right_index",
    "left_thumb", "right_thumb",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]


# ── standing reference pose (image-normalized, y-down) ───────────────────────
# carefully chosen so that segment lengths are anatomically plausible:
#   torso (shoulder→hip) ≈ 0.22
#   thigh (hip→knee)     ≈ 0.20
#   shank (knee→ankle)   ≈ 0.20

STANDING_POSE = {
    "nose":              (0.500, 0.180,  0.010),
    "left_eye_inner":    (0.488, 0.170,  0.010),
    "left_eye":          (0.482, 0.168,  0.010),
    "left_eye_outer":    (0.476, 0.170,  0.010),
    "right_eye_inner":   (0.512, 0.170,  0.010),
    "right_eye":         (0.518, 0.168,  0.010),
    "right_eye_outer":   (0.524, 0.170,  0.010),
    "left_ear":          (0.470, 0.180,  0.020),
    "right_ear":         (0.530, 0.180,  0.020),
    "mouth_left":        (0.490, 0.205,  0.010),
    "mouth_right":       (0.510, 0.205,  0.010),
    "left_shoulder":     (0.430, 0.300,  0.010),
    "right_shoulder":    (0.570, 0.300,  0.010),
    "left_elbow":        (0.420, 0.430, -0.020),  # arms slightly forward
    "right_elbow":       (0.580, 0.430, -0.020),
    "left_wrist":        (0.430, 0.540, -0.040),
    "right_wrist":       (0.570, 0.540, -0.040),
    "left_pinky":        (0.422, 0.560, -0.045),
    "right_pinky":       (0.578, 0.560, -0.045),
    "left_index":        (0.418, 0.555, -0.045),
    "right_index":       (0.582, 0.555, -0.045),
    "left_thumb":        (0.434, 0.555, -0.040),
    "right_thumb":       (0.566, 0.555, -0.040),
    "left_hip":          (0.460, 0.520,  0.000),
    "right_hip":         (0.540, 0.520,  0.000),
    "left_knee":         (0.460, 0.720,  0.000),
    "right_knee":        (0.540, 0.720,  0.000),
    "left_ankle":        (0.460, 0.920,  0.005),
    "right_ankle":       (0.540, 0.920,  0.005),
    "left_heel":         (0.460, 0.940,  0.020),
    "right_heel":        (0.540, 0.940,  0.020),
    "left_foot_index":   (0.460, 0.950, -0.020),
    "right_foot_index":  (0.540, 0.950, -0.020),
}


# ── motion deltas at full squat depth, expressed as offsets from standing ────
# convention: positive y = drops down (image-down), negative z = forward (toward camera)
# magnitudes chosen to roughly match: hip flex ~95°, knee flex ~100°, modest trunk lean

BOTTOM_DELTAS = {
    # head drops with trunk and leans forward slightly
    "nose":              (0.000,  0.105, -0.020),
    "left_eye_inner":    (0.000,  0.105, -0.020),
    "left_eye":          (0.000,  0.105, -0.020),
    "left_eye_outer":    (0.000,  0.105, -0.020),
    "right_eye_inner":   (0.000,  0.105, -0.020),
    "right_eye":         (0.000,  0.105, -0.020),
    "right_eye_outer":   (0.000,  0.105, -0.020),
    "left_ear":          (0.000,  0.105, -0.020),
    "right_ear":         (0.000,  0.105, -0.020),
    "mouth_left":        (0.000,  0.105, -0.020),
    "mouth_right":       (0.000,  0.105, -0.020),

    # shoulders drop with hip + slight forward lean of trunk
    "left_shoulder":     (0.000,  0.110, -0.025),
    "right_shoulder":    (0.000,  0.110, -0.025),

    # arms swing forward to counter-balance
    "left_elbow":        (0.000,  0.080, -0.060),
    "right_elbow":       (0.000,  0.080, -0.060),
    "left_wrist":        (0.000,  0.040, -0.090),
    "right_wrist":       (0.000,  0.040, -0.090),
    "left_pinky":        (0.000,  0.040, -0.090),
    "right_pinky":       (0.000,  0.040, -0.090),
    "left_index":        (0.000,  0.040, -0.090),
    "right_index":       (0.000,  0.040, -0.090),
    "left_thumb":        (0.000,  0.040, -0.090),
    "right_thumb":       (0.000,  0.040, -0.090),

    # hips drop
    "left_hip":          (0.000,  0.130,  0.005),
    "right_hip":         (0.000,  0.130,  0.005),

    # knees stay roughly at the same height but move forward
    "left_knee":         (-0.005,  0.000, -0.060),
    "right_knee":        ( 0.005,  0.000, -0.060),

    # ankles closed-chain anchored to floor
    "left_ankle":        (0.000,  0.000,  0.000),
    "right_ankle":       (0.000,  0.000,  0.000),
    "left_heel":         (0.000,  0.000,  0.000),
    "right_heel":        (0.000,  0.000,  0.000),
    "left_foot_index":   (0.000,  0.000,  0.000),
    "right_foot_index":  (0.000,  0.000,  0.000),
}


def squat_phase(frame: int, start: int, end: int) -> float:
    """
    Map a frame inside a rep window to s ∈ [0, 1].

    Uses a smooth half-cosine: s = (1 - cos(2π * t)) / 2,
    so s=0 at start (standing), s=1 at the midpoint (bottom of squat),
    and s=0 again at end (standing).
    """
    t = (frame - start) / (end - start)
    return 0.5 * (1.0 - np.cos(2.0 * np.pi * t))


def build_frame(s: float, rng: np.random.Generator) -> dict[str, tuple[float, float, float, float]]:
    """
    Build one frame's worth of (x, y, z, visibility) by interpolating
    standing -> bottom by factor s, then adding small Gaussian jitter.
    """
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


def main(out_dir: Path, fps: int = 30) -> None:
    rng = np.random.default_rng(seed=20260503)

    # Sequence layout (inclusive ranges)
    SEGMENTS = [
        ("baseline",   0,  14, False, 1, None),
        ("rep",       15,  59, True,  1, 1),
        ("transition",60,  74, False, None, None),
        ("rep",       75, 119, True,  1, 2),
    ]
    n_frames = SEGMENTS[-1][2] + 1

    # Pose CSV
    pose_path = out_dir / "mediapipe_squat_synthetic.csv"
    pose_path.parent.mkdir(parents=True, exist_ok=True)

    header = ["frame", "timestamp"]
    for lm in LANDMARKS:
        header += [f"{lm}_x", f"{lm}_y", f"{lm}_z", f"{lm}_visibility"]

    with pose_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for frame_idx in range(n_frames):
            # Find which segment this frame falls in
            s = 0.0
            for kind, start, end, _use, _set, _rep in SEGMENTS:
                if start <= frame_idx <= end:
                    if kind == "rep":
                        s = squat_phase(frame_idx, start, end)
                    else:
                        s = 0.0
                    break

            timestamp = round(frame_idx / fps, 4)
            frame_data = build_frame(s, rng)

            row = [frame_idx, timestamp]
            for lm in LANDMARKS:
                x, y, z, vis = frame_data[lm]
                row += [x, y, z, vis]
            writer.writerow(row)

    # Annotation CSV
    ann_path = out_dir / "mediapipe_squat_synthetic_annotation.csv"
    with ann_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["segment_type", "set_id", "rep_id", "start_frame",
                          "end_frame", "use_for_analysis", "exercise_type",
                          "pattern", "note"])
        for kind, start, end, use, set_id, rep_id in SEGMENTS:
            note = {
                "baseline":   "standing posture before movement",
                "rep":        f"descent and ascent cycle {rep_id}",
                "transition": "brief pause between reps",
            }.get(kind, "")
            writer.writerow([
                kind,
                set_id if set_id is not None else "",
                rep_id if rep_id is not None else "",
                start,
                end,
                "true" if use else "false",
                "squat",
                "bilateral",
                note,
            ])

    print(f"wrote pose CSV:        {pose_path} ({n_frames} frames)")
    print(f"wrote annotation CSV:  {ann_path}")


if __name__ == "__main__":
    out_dir = Path(__file__).parent
    main(out_dir)
