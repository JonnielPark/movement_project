"""
⑥ Phase Segmentation (semi-automatic)

Splits each annotated rep into kinematic phases (e.g., Descent / Ascent or
Lift / Tap / Return) based on the smoothed reference-landmark trajectory along
the exercise-specific reference axis declared in the exercise definition's
`phase_segmentation` block.

Input  : pose dataframe with `<landmark>_norm_{x,y,z}` columns,
         annotation columns (rep_id, segment_type, phase),
         and an ExerciseDefinition with a non-null `phase_segmentation`.
Output : the same dataframe with the `phase` column populated for rows where
         `segment_type == 'rep'`. Rows outside reps are left as NA.
         Expert-provided phase values (non-NA on entry) are never overwritten.

Pipeline position: after ⑤ Normalization, before ⑦ Motion Attribution.

Phase labels are kinematic (trajectory-based), not kinetic (muscle-action-based).
They describe the reference-landmark trajectory direction, not muscle activation
patterns. The biomechanical interpretation of each phase is supplied separately
by the exercise definition.

Coordinate convention (inherited from normalization):
    x = medial_lateral   (positive = right)
    y = anterior_posterior
    z = vertical         (positive = up)
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

# scipy is a required dependency for smoothing and peak detection
try:
    from scipy import signal as _scipy_signal
    _HAS_SCIPY = True
except ImportError:  # pragma: no cover
    _HAS_SCIPY = False


# ── Axis resolver ─────────────────────────────────────────────────────────────
# Maps phase_segmentation.reference_axis → normalized coordinate column suffix

_AXIS_TO_SUFFIX: dict[str, str] = {
    "vertical":            "norm_z",
    "anterior_posterior":  "norm_y",
    "medial_lateral":      "norm_x",
}

# Virtual landmarks resolved to the midpoint of two named landmarks
_VIRTUAL_LANDMARKS: dict[str, tuple[str, str]] = {
    "hip_center":      ("left_hip",      "right_hip"),
    "shoulder_center": ("left_shoulder", "right_shoulder"),
}


# ── Report dataclass ──────────────────────────────────────────────────────────

@dataclass
class PhaseSegmentationReport:
    """
    Per-rep outcome of the phase segmentation step.

    phase_assignments maps each phase name to the inclusive (start_frame, end_frame)
    span in the original dataframe frame column.
    """
    rep_id: int
    phase_assignments: dict[str, tuple[int, int]] = field(default_factory=dict)
    inflection_frames: list[int] = field(default_factory=list)
    smoothing_method: str = "none"
    fps_used: float = 30.0
    multi_inflection_collapsed: bool = False
    rejected_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "rep_id": self.rep_id,
            "phase_assignments": {
                k: list(v) for k, v in self.phase_assignments.items()
            },
            "inflection_frames": self.inflection_frames,
            "smoothing_method": self.smoothing_method,
            "fps_used": self.fps_used,
            "multi_inflection_collapsed": self.multi_inflection_collapsed,
            "rejected_reason": self.rejected_reason,
        }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _resolve_landmark_trace(
    df: pd.DataFrame,
    landmark: str,
    axis_suffix: str,
    starting_side: str | None = None,
) -> np.ndarray:
    """
    Return a 1-D float array of the landmark trajectory along the given axis.

    Virtual landmarks (hip_center, shoulder_center) are computed as the
    midpoint of the corresponding left/right pair.  For plank_shoulder_tap the
    `right_wrist` / `left_wrist` reference is resolved from `starting_side`.
    """
    # Side-keyed landmark (plank_shoulder_tap uses starting_side for wrist reference)
    if landmark in ("right_wrist", "left_wrist") and starting_side is not None:
        side_landmark = f"{starting_side}_wrist"
        col = f"{side_landmark}_{axis_suffix}"
        if col in df.columns:
            return df[col].to_numpy(dtype=float)

    # Virtual midpoint landmark
    if landmark in _VIRTUAL_LANDMARKS:
        l_name, r_name = _VIRTUAL_LANDMARKS[landmark]
        l_col = f"{l_name}_{axis_suffix}"
        r_col = f"{r_name}_{axis_suffix}"
        if l_col in df.columns and r_col in df.columns:
            return ((df[l_col] + df[r_col]) / 2.0).to_numpy(dtype=float)
        # Fallback to whichever side is available
        for col in [l_col, r_col]:
            if col in df.columns:
                return df[col].to_numpy(dtype=float)
        raise KeyError(
            f"Cannot resolve virtual landmark '{landmark}': "
            f"columns '{l_col}' and '{r_col}' not found."
        )

    # Direct landmark
    col = f"{landmark}_{axis_suffix}"
    if col not in df.columns:
        raise KeyError(f"Column '{col}' not found in dataframe.")
    return df[col].to_numpy(dtype=float)


def _smooth_trace(
    trace: np.ndarray,
    method: str,
    window_frames: int,
    polyorder: int,
    fps: float,
) -> tuple[np.ndarray, str]:
    """
    Apply smoothing to a 1-D trajectory array.

    Returns (smoothed_trace, method_used).
    Falls back gracefully when scipy is unavailable or trace is too short.
    """
    n = len(trace)

    if not _HAS_SCIPY or n < 4:
        return trace.copy(), "none"

    if method == "savitzky_golay":
        # window_frames must be odd and < n
        w = min(window_frames, n)
        w = w if w % 2 == 1 else max(1, w - 1)
        if w >= polyorder + 1:
            try:
                return _scipy_signal.savgol_filter(trace, w, polyorder), "savitzky_golay"
            except Exception:
                pass  # fall through to Butterworth

    # Butterworth low-pass fallback
    try:
        cutoff_hz = 6.0
        nyq = fps / 2.0
        wn = min(cutoff_hz / nyq, 0.99)
        b, a = _scipy_signal.butter(4, wn, btype="low")
        return _scipy_signal.filtfilt(b, a, trace), "butterworth"
    except Exception:
        pass

    return trace.copy(), "none"


def _detect_inflections(trace: np.ndarray, split_logic: str) -> np.ndarray:
    """
    Return local-index positions of inflection candidates within the trace.

    split_logic options:
        local_minimum   : find_peaks on the negated trace
        local_maximum   : find_peaks on the trace
        zero_crossing   : sign change of the first derivative
    """
    if not _HAS_SCIPY:
        return np.array([], dtype=int)

    if split_logic == "local_minimum":
        peaks, _ = _scipy_signal.find_peaks(-trace)
        return peaks
    elif split_logic == "local_maximum":
        peaks, _ = _scipy_signal.find_peaks(trace)
        return peaks
    elif split_logic == "zero_crossing":
        grad = np.gradient(trace)
        return np.where(np.diff(np.sign(grad)))[0]
    return np.array([], dtype=int)


def _apply_inflection_policy(
    candidates: np.ndarray,
    trace: np.ndarray,
    split_logic: str,
    policy: str,
) -> tuple[list[int], bool]:
    """
    Resolve multiple candidates to a single inflection frame.

    Returns (chosen_frames, was_collapsed).
    Empty return means the rep should be rejected.
    """
    if len(candidates) == 0:
        return [], False
    if len(candidates) == 1:
        return [int(candidates[0])], False

    if policy == "global_extremum":
        if split_logic == "local_minimum":
            idx = int(candidates[np.argmin(trace[candidates])])
        else:
            idx = int(candidates[np.argmax(trace[candidates])])
        return [idx], True
    elif policy == "first":
        return [int(candidates[0])], True
    elif policy == "reject_rep":
        return [], True  # collapsed=True, but empty → reject

    # Unknown policy: default to global extremum
    if split_logic == "local_minimum":
        idx = int(candidates[np.argmin(trace[candidates])])
    else:
        idx = int(candidates[np.argmax(trace[candidates])])
    return [idx], True


def _assign_simple_labels(
    n_frames: int,
    inflection_local: int,
    phase_sequence: list[str],
    bottom_hold_enabled: bool,
    half_window: int,
) -> dict[int, str]:
    """
    Assign phase labels for the simple two-phase (Descent/Ascent) case.

    Returns a mapping {local_frame_index: phase_label}.
    When bottom_hold_enabled, frames within ±half_window of the inflection
    are labeled 'Bottom_Hold', sandwiched between the two phases.
    """
    label_map: dict[int, str] = {}
    if len(phase_sequence) < 2:
        return label_map

    p0, p1 = phase_sequence[0], phase_sequence[-1]

    if bottom_hold_enabled and half_window > 0:
        hold_start = max(0, inflection_local - half_window)
        hold_end = min(n_frames - 1, inflection_local + half_window)
        for i in range(hold_start):
            label_map[i] = p0
        for i in range(hold_start, hold_end + 1):
            label_map[i] = "Bottom_Hold"
        for i in range(hold_end + 1, n_frames):
            label_map[i] = p1
    else:
        for i in range(inflection_local):
            label_map[i] = p0
        for i in range(inflection_local, n_frames):
            label_map[i] = p1

    return label_map


def _assign_multi_labels(
    n_frames: int,
    inflection_locals: list[int],
    phase_sequence: list[str],
) -> dict[int, str]:
    """
    Assign phase labels when multiple inflection frames divide the rep into N+1 phases.

    inflection_locals must be sorted in ascending order.
    len(inflection_locals) should equal len(phase_sequence) - 1.
    """
    label_map: dict[int, str] = {}
    if not phase_sequence:
        return label_map

    # Build boundary list: [0, i1, i2, ..., n_frames]
    boundaries = sorted(set(inflection_locals))
    spans = list(zip(
        [0] + boundaries,
        boundaries + [n_frames],
    ))

    for phase_idx, (start, end) in enumerate(spans):
        label = phase_sequence[phase_idx] if phase_idx < len(phase_sequence) else phase_sequence[-1]
        for i in range(start, end):
            label_map[i] = label

    return label_map


# ── Public API ────────────────────────────────────────────────────────────────

def segment_phases(
    df: pd.DataFrame,
    exercise_definition: "Any",
    *,
    fps: float | None = None,
    fps_default: float = 30.0,
) -> tuple[pd.DataFrame, list[PhaseSegmentationReport]]:
    """
    Fill the `phase` column for each annotated rep using kinematic inflection detection.

    The reference-landmark trajectory (e.g., hip-center vertical position) is
    smoothed with a Savitzky-Golay filter, then the local minimum (or maximum)
    frame is detected as the turn-around point.  Frames before the inflection
    are labeled with the first element of `phase_sequence` (e.g., 'Descent'),
    frames after with the last (e.g., 'Ascent').  An optional `Bottom_Hold`
    window is inserted around the inflection.

    Frames that already have explicit phase annotations are honored as ground
    truth and are not overwritten.

    Parameters
    ----------
    df : pd.DataFrame
        Pose dataframe with normalized coordinate columns
        (<landmark>_norm_x/y/z) and annotation columns (segment_type, rep_id, phase).
    exercise_definition : ExerciseDefinition
        Must have a non-null `phase_segmentation` attribute.
    fps : float, optional
        Frames per second.  Uses df.attrs["fps"] if present, then fps_default.
    fps_default : float
        Fallback fps when not set in df.attrs.

    Returns
    -------
    df_out : pd.DataFrame
        Copy of df with `phase` column populated for rep frames.
    reports : list[PhaseSegmentationReport]
        One report per rep_id; rejected reps have rejected_reason set and
        phase_assignments empty.
    """
    ps = getattr(exercise_definition, "phase_segmentation", None)
    if ps is None:
        return df.copy(), []

    result = df.copy()
    reports: list[PhaseSegmentationReport] = []

    if "segment_type" not in df.columns or "rep_id" not in df.columns:
        warnings.warn(
            "[Step ⑥] Phase Segmentation: annotation columns (segment_type, rep_id) "
            "not found — skipped.",
            stacklevel=2,
        )
        return result, reports

    if "phase" not in result.columns:
        result["phase"] = pd.array([pd.NA] * len(result), dtype=object)

    # Resolve FPS
    if fps is None:
        fps = float(df.attrs.get("fps", fps_default))

    axis_suffix = _AXIS_TO_SUFFIX.get(ps.reference_axis, "norm_z")
    split_logics = ps.split_logic if isinstance(ps.split_logic, list) else [ps.split_logic]
    n_inflections_needed = len(ps.phase_sequence) - 1

    rep_mask = df["segment_type"] == "rep"
    rep_ids = sorted(df.loc[rep_mask, "rep_id"].dropna().unique())

    for rep_id in rep_ids:
        rid = int(rep_id)
        mask = (df["segment_type"] == "rep") & (df["rep_id"] == rep_id)
        df_rep = df.loc[mask]
        n_frames = len(df_rep)

        # Skip too-short reps
        if n_frames < ps.minimum_rep_length_frames:
            reports.append(PhaseSegmentationReport(
                rep_id=rid,
                rejected_reason=f"rep too short: {n_frames} < {ps.minimum_rep_length_frames} frames",
            ))
            continue

        # Honor explicit annotation overrides: skip if any non-NA phase exists
        if "phase" in df_rep.columns and df_rep["phase"].notna().any():
            reports.append(PhaseSegmentationReport(
                rep_id=rid,
                smoothing_method="none",
                fps_used=fps,
                rejected_reason="explicit annotation override: phase column already populated",
            ))
            continue

        # Detect starting_side for side-keyed landmarks
        starting_side: str | None = None
        if "starting_side" in df_rep.columns:
            ss_vals = df_rep["starting_side"].dropna().unique()
            if len(ss_vals) == 1:
                starting_side = str(ss_vals[0])

        # Resolve reference landmark trajectory
        try:
            trace_raw = _resolve_landmark_trace(
                df_rep, ps.reference_landmark, axis_suffix, starting_side
            )
        except KeyError as exc:
            reports.append(PhaseSegmentationReport(
                rep_id=rid,
                fps_used=fps,
                rejected_reason=str(exc),
            ))
            continue

        # Interpolate NaN before smoothing (monocular data may have gaps)
        trace_clean = (
            pd.Series(trace_raw)
            .interpolate(method="linear")
            .ffill()
            .bfill()
            .to_numpy(dtype=float)
        )

        smoothed, smoothing_method_used = _smooth_trace(
            trace_clean,
            method=ps.smoothing.method,
            window_frames=ps.smoothing.window_frames,
            polyorder=ps.smoothing.polyorder,
            fps=fps,
        )

        # ── Simple two-phase case (1 inflection needed) ───────────────────────
        if n_inflections_needed == 1:
            logic = split_logics[0]
            candidates = _detect_inflections(smoothed, logic)

            if len(candidates) == 0:
                reports.append(PhaseSegmentationReport(
                    rep_id=rid,
                    smoothing_method=smoothing_method_used,
                    fps_used=fps,
                    rejected_reason="no inflection detected",
                ))
                continue

            chosen, collapsed = _apply_inflection_policy(
                candidates, smoothed, logic, ps.multi_inflection_policy
            )

            if not chosen:
                reports.append(PhaseSegmentationReport(
                    rep_id=rid,
                    smoothing_method=smoothing_method_used,
                    fps_used=fps,
                    multi_inflection_collapsed=True,
                    rejected_reason="reject_rep policy: multiple inflections",
                ))
                continue

            inflection_local = chosen[0]
            label_map = _assign_simple_labels(
                n_frames, inflection_local,
                ps.phase_sequence,
                ps.bottom_hold.enabled, ps.bottom_hold.half_window_frames,
            )

        # ── Multi-phase case (≥2 inflections needed) ─────────────────────────
        else:
            # Detect one inflection per split_logic, in temporal order
            inflection_locals: list[int] = []
            collapsed = False

            for logic_idx, logic in enumerate(split_logics[:n_inflections_needed]):
                # Search only in the remaining trace portion (after the previous inflection)
                search_start = inflection_locals[-1] + 1 if inflection_locals else 0
                sub_trace = smoothed[search_start:]
                sub_candidates = _detect_inflections(sub_trace, logic)

                if len(sub_candidates) == 0:
                    inflection_locals = []
                    break

                sub_candidates_global = sub_candidates + search_start
                sub_chosen, sub_collapsed = _apply_inflection_policy(
                    sub_candidates_global, smoothed, logic, ps.multi_inflection_policy
                )
                if sub_collapsed:
                    collapsed = True
                if not sub_chosen:
                    inflection_locals = []
                    break
                inflection_locals.append(sub_chosen[0])

            if len(inflection_locals) < n_inflections_needed:
                reports.append(PhaseSegmentationReport(
                    rep_id=rid,
                    smoothing_method=smoothing_method_used,
                    fps_used=fps,
                    multi_inflection_collapsed=collapsed,
                    rejected_reason=(
                        f"could not detect {n_inflections_needed} inflections "
                        f"(found {len(inflection_locals)})"
                    ),
                ))
                continue

            label_map = _assign_multi_labels(n_frames, inflection_locals, ps.phase_sequence)

        # ── Write labels back into result ─────────────────────────────────────
        frame_vals: list[int] = df_rep["frame"].tolist() if "frame" in df_rep.columns else []
        df_rep_idx = df_rep.index.tolist()

        for local_i, lbl in label_map.items():
            if local_i < len(df_rep_idx):
                result.loc[df_rep_idx[local_i], "phase"] = lbl

        # Build phase_assignments in original frame numbers
        phase_assignments: dict[str, tuple[int, int]] = {}
        if frame_vals:
            all_labels = sorted(set(label_map.values()))
            for phase_name in all_labels:
                local_indices = [i for i, l in label_map.items() if l == phase_name]
                if local_indices:
                    phase_assignments[phase_name] = (
                        frame_vals[local_indices[0]],
                        frame_vals[local_indices[-1]],
                    )

        inflection_frames_global = (
            [frame_vals[i] for i in ([inflection_local] if n_inflections_needed == 1 else inflection_locals)
             if i < len(frame_vals)]
        )

        reports.append(PhaseSegmentationReport(
            rep_id=rid,
            phase_assignments=phase_assignments,
            inflection_frames=inflection_frames_global,
            smoothing_method=smoothing_method_used,
            fps_used=fps,
            multi_inflection_collapsed=collapsed,
            rejected_reason=None,
        ))

    return result, reports


__all__ = ["PhaseSegmentationReport", "segment_phases"]
