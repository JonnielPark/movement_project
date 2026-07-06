"""
⑦ Segmentation (semi-automatic)

Confirms repetition boundaries with the exercise definition's `rep_segmentation`
block, then splits each confirmed rep into kinematic phases (e.g., Descent /
Ascent or Lift / Tap / Return) with the existing `phase_segmentation` block.

Input  : pose dataframe with `<landmark>_norm_{x,y,z}` columns,
         optional annotation columns (rep_id, segment_type, phase),
         and an ExerciseDefinition with segmentation specs.
Output : the same dataframe with the `phase` column populated for rows where
         `segment_type == 'rep'`. Rows outside reps are left as NA.
         Expert-provided phase values (non-NA on entry) are never overwritten.

Pipeline position: after ⑥ Canonicalization, before ⑧ Feature Extraction.

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
# Maps rep_segmentation/phase_segmentation reference coordinate settings to
# dataframe coordinate suffixes.

_REFERENCE_AXIS_TO_SUFFIX: dict[str, dict[str, str]] = {
    "norm": {
        "vertical": "norm_z",
        "anterior_posterior": "norm_y",
        "medial_lateral": "norm_x",
    },
    "recording_view_raw": {
        "image_x": "x",
        "image_y": "y",
        "model_depth": "z",
    },
}

# Virtual landmarks resolved to the midpoint of two named landmarks
_VIRTUAL_LANDMARKS: dict[str, tuple[str, str]] = {
    "hip_center": ("left_hip", "right_hip"),
    "shoulder_center": ("left_shoulder", "right_shoulder"),
}
_MIN_TRACE_RANGE_FOR_REP_DETECTION: float = 1e-9


# ── Report dataclasses ────────────────────────────────────────────────────────


@dataclass
class RepSegmentationReport:
    """
    Whole-sequence outcome of the repetition-boundary segmentation step.

    rep_assignments maps each generated rep_id to the inclusive
    (start_frame, end_frame) span in the original dataframe frame column.
    """

    rep_assignments: dict[int, tuple[int, int]] = field(default_factory=dict)
    boundary_frames: list[int] = field(default_factory=list)
    smoothing_method: str = "none"
    fps_used: float = 30.0
    status: str = "not_run"
    source: str = "semi_auto"
    failure_points: list[dict[str, Any]] = field(default_factory=list)
    rejected_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "rep_assignments": {
                str(k): list(v) for k, v in self.rep_assignments.items()
            },
            "boundary_frames": self.boundary_frames,
            "smoothing_method": self.smoothing_method,
            "fps_used": self.fps_used,
            "status": self.status,
            "source": self.source,
            "failure_points": self.failure_points,
            "rejected_reason": self.rejected_reason,
        }


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
    coordinate_family: str,
    reference_axis: str,
    starting_side: str | None = None,
) -> np.ndarray:
    """
    Return a 1-D float array of the landmark trajectory along the given axis.

    Virtual landmarks (hip_center, shoulder_center) are computed as the
    midpoint of the corresponding left/right pair.  For plank_shoulder_tap the
    `right_wrist` / `left_wrist` reference is resolved from `starting_side`.
    """
    family = coordinate_family or "norm"
    try:
        axis_suffix = _REFERENCE_AXIS_TO_SUFFIX[family][reference_axis]
    except KeyError as exc:
        raise KeyError(
            f"Unsupported segmentation reference: "
            f"coordinate_family='{family}', reference_axis='{reference_axis}'."
        ) from exc

    # Side-keyed landmark (plank_shoulder_tap uses starting_side for wrist reference)
    if landmark in ("right_wrist", "left_wrist") and starting_side is not None:
        side_landmark = f"{starting_side}_wrist"
        col = f"{side_landmark}_{axis_suffix}"
        if col in df.columns:
            return df[col].to_numpy(dtype=float)

    # Direct reference columns may already exist after normalization or midpoint
    # preparation (e.g., hip_center_y, shoulder_center_norm_z).
    direct_col = f"{landmark}_{axis_suffix}"
    if direct_col in df.columns:
        return df[direct_col].to_numpy(dtype=float)

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

    raise KeyError(f"Column '{direct_col}' not found in dataframe.")


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
    trace = np.asarray(trace, dtype=float)
    n = len(trace)
    finite_count = int(np.isfinite(trace).sum())

    if not _HAS_SCIPY or n < 4 or finite_count < max(4, polyorder + 2):
        return trace.copy(), "none"
    if finite_count < n:
        return trace.copy(), "none"

    if method == "savitzky_golay":
        # window_frames must be odd and < n
        w = min(window_frames, n)
        w = w if w % 2 == 1 else max(1, w - 1)
        if w >= polyorder + 1:
            try:
                return (
                    _scipy_signal.savgol_filter(trace, w, polyorder),
                    "savitzky_golay",
                )
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


def _filter_min_distance(candidates: np.ndarray, distance: int) -> np.ndarray:
    """Greedily keep candidates at least `distance` frames apart."""
    if len(candidates) == 0:
        return np.array([], dtype=int)
    distance = max(1, int(distance))
    kept: list[int] = []
    for cand in sorted(int(c) for c in candidates):
        if not kept or cand - kept[-1] >= distance:
            kept.append(cand)
    return np.array(kept, dtype=int)


def _detect_rep_boundaries(
    trace: np.ndarray,
    boundary_logic: str,
    min_distance_frames: int,
    prominence: float | None,
) -> np.ndarray:
    """
    Return local-index positions of repetition-boundary candidates.

    Endpoint insertion is handled by segment_reps(); this helper returns only
    interior candidates detected from the smoothed trajectory.
    """
    if not _HAS_SCIPY:
        return np.array([], dtype=int)

    kwargs: dict[str, Any] = {"distance": max(1, int(min_distance_frames))}
    if prominence is not None and prominence > 0:
        kwargs["prominence"] = float(prominence)

    if boundary_logic == "local_minimum":
        peaks, _ = _scipy_signal.find_peaks(-trace, **kwargs)
        return peaks
    if boundary_logic == "local_maximum":
        peaks, _ = _scipy_signal.find_peaks(trace, **kwargs)
        return peaks
    if boundary_logic == "zero_crossing":
        grad = np.gradient(trace)
        candidates = np.where(np.diff(np.sign(grad)))[0]
        return _filter_min_distance(candidates, min_distance_frames)

    return np.array([], dtype=int)


def _make_failure_point(
    failure_id: str,
    *,
    start_frame: int,
    end_frame: int,
    reason: str,
    candidate_frame: int | None = None,
    pipeline_action: str = "wait_for_manual_override",
) -> dict[str, Any]:
    """Build a rep-boundary segmentation failure-point record."""
    return {
        "failure_id": failure_id,
        "failure_level": "rep_boundary",
        "set_id": None,
        "rep_id": None,
        "start_frame": int(start_frame),
        "end_frame": int(end_frame),
        "candidate_frame": None if candidate_frame is None else int(candidate_frame),
        "reason": reason,
        "confidence": None,
        "pipeline_action": pipeline_action,
        "resolved": False,
        "resolution_note": None,
    }


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
    turnaround_hold_enabled: bool,
    half_window: int,
) -> dict[int, str]:
    """
    Assign phase labels for a simple two-phase exercise-defined sequence.

    Returns a mapping {local_frame_index: phase_label}.
    When turnaround_hold_enabled, frames within ±half_window of the inflection
    are labeled 'Turnaround_Hold', sandwiched between the two configured phases.
    """
    label_map: dict[int, str] = {}
    if len(phase_sequence) < 2:
        return label_map

    p0, p1 = phase_sequence[0], phase_sequence[-1]

    if turnaround_hold_enabled and half_window > 0:
        hold_start = max(0, inflection_local - half_window)
        hold_end = min(n_frames - 1, inflection_local + half_window)
        for i in range(hold_start):
            label_map[i] = p0
        for i in range(hold_start, hold_end + 1):
            label_map[i] = "Turnaround_Hold"
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
    spans = list(
        zip(
            [0] + boundaries,
            boundaries + [n_frames],
        )
    )

    for phase_idx, (start, end) in enumerate(spans):
        label = (
            phase_sequence[phase_idx]
            if phase_idx < len(phase_sequence)
            else phase_sequence[-1]
        )
        for i in range(start, end):
            label_map[i] = label

    return label_map


# ── Public API ────────────────────────────────────────────────────────────────


def segment_reps(
    df: pd.DataFrame,
    exercise_definition: "Any",
    *,
    fps: float | None = None,
    fps_default: float = 30.0,
) -> tuple[pd.DataFrame, RepSegmentationReport]:
    """
    Fill `rep_id` by detecting repetition boundaries from a reference trajectory.

    Existing manual/annotation rep labels are treated as confirmed labels and
    are not overwritten. When automatic boundary detection is unclear, the
    function records rep-boundary failure points and leaves `rep_id` unset for
    the affected range.

    Parameters
    ----------
    df : pd.DataFrame
        Pose dataframe with normalized coordinate columns (<landmark>_norm_x/y/z).
    exercise_definition : ExerciseDefinition
        Must have a non-null `rep_segmentation` attribute.
    fps : float, optional
        Frames per second. Uses df.attrs["fps"] if present, then fps_default.
    fps_default : float
        Fallback fps when not set in df.attrs.

    Returns
    -------
    df_out : pd.DataFrame
        Copy of df with `rep_id` and rep segmentation metadata populated.
    report : RepSegmentationReport
        Whole-sequence report including boundary frames and failure points.
    """
    rs = getattr(exercise_definition, "rep_segmentation", None)
    result = df.copy()

    if fps is None:
        fps = float(df.attrs.get("fps", fps_default))

    report = RepSegmentationReport(fps_used=fps)
    if rs is None:
        report.status = "skipped"
        report.source = "fallback"
        report.rejected_reason = "exercise definition has no rep_segmentation block"
        return result, report

    n = len(result)
    if "use_for_analysis" not in result.columns:
        result["use_for_analysis"] = True
    if "segment_type" not in result.columns:
        result["segment_type"] = "full_sequence"
    if "set_id" not in result.columns:
        result["set_id"] = pd.array([pd.NA] * n, dtype="Int64")
    if "rep_id" not in result.columns:
        result["rep_id"] = pd.array([pd.NA] * n, dtype="Int64")
    if "rep_segmentation_status" not in result.columns:
        result["rep_segmentation_status"] = "not_run"
    if "rep_segmentation_source" not in result.columns:
        result["rep_segmentation_source"] = pd.array([None] * n, dtype=object)
    if "rep_segmentation_failure_id" not in result.columns:
        result["rep_segmentation_failure_id"] = pd.array([None] * n, dtype=object)

    manual_rep_mask = (result["segment_type"] == "rep") & result["rep_id"].notna()
    if manual_rep_mask.any():
        result.loc[manual_rep_mask, "rep_segmentation_status"] = "manual_override"
        result.loc[manual_rep_mask, "rep_segmentation_source"] = "annotation"
        rep_assignments: dict[int, tuple[int, int]] = {}
        for rep_id in sorted(result.loc[manual_rep_mask, "rep_id"].dropna().unique()):
            mask = manual_rep_mask & (result["rep_id"] == rep_id)
            frames = result.loc[mask, "frame"].astype(int).tolist()
            if frames:
                rep_assignments[int(rep_id)] = (frames[0], frames[-1])
        report.rep_assignments = rep_assignments
        report.status = "manual_override"
        report.source = "annotation"
        report.rejected_reason = "existing rep_id labels were preserved"
        return result, report

    analysis_mask = result["use_for_analysis"].fillna(False).astype(bool)
    analysis_indices = result.index[analysis_mask].tolist()
    if not analysis_indices:
        report.status = "failed"
        report.rejected_reason = "no frames marked use_for_analysis"
        return result, report

    df_analysis = result.loc[analysis_indices]
    frame_vals = (
        df_analysis["frame"].astype(int).tolist()
        if "frame" in df_analysis.columns
        else list(range(len(df_analysis)))
    )

    starting_side: str | None = None
    if "starting_side" in df_analysis.columns:
        ss_vals = df_analysis["starting_side"].dropna().unique()
        if len(ss_vals) == 1:
            starting_side = str(ss_vals[0])
    try:
        trace_raw = _resolve_landmark_trace(
            df_analysis,
            rs.reference_landmark,
            rs.reference_coordinate_family,
            rs.reference_axis,
            starting_side,
        )
    except KeyError as exc:
        failure = _make_failure_point(
            "rep_boundary_001",
            start_frame=frame_vals[0],
            end_frame=frame_vals[-1],
            reason="missing_reference_landmark",
        )
        result.loc[analysis_indices, "rep_segmentation_status"] = "failed"
        result.loc[analysis_indices, "rep_segmentation_failure_id"] = failure[
            "failure_id"
        ]
        report.status = "failed"
        report.failure_points = [failure]
        report.rejected_reason = str(exc)
        return result, report

    trace_clean = (
        pd.Series(trace_raw)
        .interpolate(method="linear")
        .ffill()
        .bfill()
        .to_numpy(dtype=float)
    )
    finite_trace = trace_clean[np.isfinite(trace_clean)]

    if len(finite_trace) == 0:
        failure = _make_failure_point(
            "rep_boundary_001",
            start_frame=frame_vals[0],
            end_frame=frame_vals[-1],
            reason="no_finite_reference_trace",
        )
        result.loc[analysis_indices, "rep_segmentation_status"] = "failed"
        result.loc[analysis_indices, "rep_segmentation_failure_id"] = failure[
            "failure_id"
        ]
        report.status = "failed"
        report.failure_points = [failure]
        report.rejected_reason = "reference trajectory has no finite values"
        return result, report

    smoothed, smoothing_method_used = _smooth_trace(
        trace_clean,
        method=rs.smoothing.method,
        window_frames=rs.smoothing.window_frames,
        polyorder=rs.smoothing.polyorder,
        fps=fps,
    )
    report.smoothing_method = smoothing_method_used

    if (
        float(np.max(finite_trace) - np.min(finite_trace))
        <= _MIN_TRACE_RANGE_FOR_REP_DETECTION
    ):
        failure = _make_failure_point(
            "rep_boundary_001",
            start_frame=frame_vals[0],
            end_frame=frame_vals[-1],
            reason="insufficient_reps",
        )
        result.loc[analysis_indices, "rep_segmentation_status"] = "failed"
        result.loc[analysis_indices, "rep_segmentation_failure_id"] = failure[
            "failure_id"
        ]
        report.status = "failed"
        report.failure_points = [failure]
        report.rejected_reason = (
            "reference trajectory is flat; "
            f"detected 0 reps < required {rs.minimum_reps}"
        )
        return result, report

    interior = _detect_rep_boundaries(
        smoothed,
        boundary_logic=rs.boundary_logic,
        min_distance_frames=rs.minimum_boundary_distance_frames,
        prominence=rs.boundary_prominence,
    )
    boundary_locals = [int(x) for x in interior]
    if rs.include_endpoints:
        boundary_locals.extend([0, len(df_analysis) - 1])
    boundary_locals = sorted(set(boundary_locals))
    report.boundary_frames = [frame_vals[i] for i in boundary_locals]

    if len(boundary_locals) < 2:
        failure = _make_failure_point(
            "rep_boundary_001",
            start_frame=frame_vals[0],
            end_frame=frame_vals[-1],
            reason="missing_candidate",
        )
        result.loc[analysis_indices, "rep_segmentation_status"] = "failed"
        result.loc[analysis_indices, "rep_segmentation_failure_id"] = failure[
            "failure_id"
        ]
        report.status = "failed"
        report.failure_points = [failure]
        report.rejected_reason = "fewer than two boundary candidates"
        return result, report

    intervals: list[tuple[int, int]] = []
    failures: list[dict[str, Any]] = []
    for i, start_local in enumerate(boundary_locals[:-1]):
        next_boundary = boundary_locals[i + 1]
        end_local = (
            next_boundary if i == len(boundary_locals) - 2 else next_boundary - 1
        )
        n_frames = end_local - start_local + 1
        if n_frames < rs.minimum_rep_length_frames:
            failure_id = f"rep_boundary_{len(failures) + 1:03d}"
            failures.append(
                _make_failure_point(
                    failure_id,
                    start_frame=frame_vals[start_local],
                    end_frame=frame_vals[max(start_local, end_local)],
                    reason="rep_too_short",
                    candidate_frame=frame_vals[next_boundary],
                    pipeline_action="exclude_range",
                )
            )
            failed_indices = analysis_indices[start_local : end_local + 1]
            result.loc[failed_indices, "rep_segmentation_status"] = "failed"
            result.loc[failed_indices, "rep_segmentation_failure_id"] = failure_id
            result.loc[failed_indices, "rep_segmentation_source"] = "semi_auto"
            continue
        intervals.append((start_local, end_local))

    if len(intervals) < rs.minimum_reps:
        failure_id = f"rep_boundary_{len(failures) + 1:03d}"
        failures.append(
            _make_failure_point(
                failure_id,
                start_frame=frame_vals[0],
                end_frame=frame_vals[-1],
                reason="insufficient_reps",
            )
        )
        result.loc[analysis_indices, "rep_segmentation_status"] = "failed"
        result.loc[analysis_indices, "rep_segmentation_failure_id"] = failure_id
        report.status = "failed"
        report.failure_points = failures
        report.rejected_reason = (
            f"detected {len(intervals)} reps < required {rs.minimum_reps}"
        )
        return result, report

    rep_assignments: dict[int, tuple[int, int]] = {}
    for rep_num, (start_local, end_local) in enumerate(intervals, start=1):
        rep_indices = analysis_indices[start_local : end_local + 1]
        result.loc[rep_indices, "segment_type"] = "rep"
        result.loc[rep_indices, "rep_id"] = rep_num
        result.loc[rep_indices, "rep_segmentation_status"] = "success"
        result.loc[rep_indices, "rep_segmentation_source"] = "semi_auto"
        if result.loc[rep_indices, "set_id"].isna().all():
            result.loc[rep_indices, "set_id"] = 1
        rep_assignments[rep_num] = (frame_vals[start_local], frame_vals[end_local])

    report.rep_assignments = rep_assignments
    report.failure_points = failures
    report.status = "success"
    report.source = "semi_auto"
    return result, report


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
    are labeled with the first element of `phase_sequence`, frames after with
    the last configured element.  An optional `Turnaround_Hold` window is
    inserted around the motion-reversal frame.

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
            "[Step ⑦] Phase Segmentation: annotation columns (segment_type, rep_id) "
            "not found — skipped.",
            stacklevel=2,
        )
        return result, reports

    if "phase" not in result.columns:
        result["phase"] = pd.array([pd.NA] * len(result), dtype=object)

    # Resolve FPS
    if fps is None:
        fps = float(df.attrs.get("fps", fps_default))

    split_logics = (
        ps.split_logic if isinstance(ps.split_logic, list) else [ps.split_logic]
    )
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
            reports.append(
                PhaseSegmentationReport(
                    rep_id=rid,
                    rejected_reason=f"rep too short: {n_frames} < {ps.minimum_rep_length_frames} frames",
                )
            )
            continue

        # Honor explicit annotation overrides: skip if any non-NA phase exists
        if "phase" in df_rep.columns and df_rep["phase"].notna().any():
            reports.append(
                PhaseSegmentationReport(
                    rep_id=rid,
                    smoothing_method="none",
                    fps_used=fps,
                    rejected_reason="explicit annotation override: phase column already populated",
                )
            )
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
                df_rep,
                ps.reference_landmark,
                ps.reference_coordinate_family,
                ps.reference_axis,
                starting_side,
            )
        except KeyError as exc:
            reports.append(
                PhaseSegmentationReport(
                    rep_id=rid,
                    fps_used=fps,
                    rejected_reason=str(exc),
                )
            )
            continue

        # Interpolate NaN before smoothing (monocular data may have gaps)
        trace_clean = (
            pd.Series(trace_raw)
            .interpolate(method="linear")
            .ffill()
            .bfill()
            .to_numpy(dtype=float)
        )
        if not np.isfinite(trace_clean).any():
            reports.append(
                PhaseSegmentationReport(
                    rep_id=rid,
                    fps_used=fps,
                    rejected_reason="reference trajectory has no finite values",
                )
            )
            continue

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
                reports.append(
                    PhaseSegmentationReport(
                        rep_id=rid,
                        smoothing_method=smoothing_method_used,
                        fps_used=fps,
                        rejected_reason="no inflection detected",
                    )
                )
                continue

            chosen, collapsed = _apply_inflection_policy(
                candidates, smoothed, logic, ps.multi_inflection_policy
            )

            if not chosen:
                reports.append(
                    PhaseSegmentationReport(
                        rep_id=rid,
                        smoothing_method=smoothing_method_used,
                        fps_used=fps,
                        multi_inflection_collapsed=True,
                        rejected_reason="reject_rep policy: multiple inflections",
                    )
                )
                continue

            inflection_local = chosen[0]
            label_map = _assign_simple_labels(
                n_frames,
                inflection_local,
                ps.phase_sequence,
                ps.turnaround_hold.enabled,
                ps.turnaround_hold.half_window_frames,
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
                reports.append(
                    PhaseSegmentationReport(
                        rep_id=rid,
                        smoothing_method=smoothing_method_used,
                        fps_used=fps,
                        multi_inflection_collapsed=collapsed,
                        rejected_reason=(
                            f"could not detect {n_inflections_needed} inflections "
                            f"(found {len(inflection_locals)})"
                        ),
                    )
                )
                continue

            label_map = _assign_multi_labels(
                n_frames, inflection_locals, ps.phase_sequence
            )

        # ── Write labels back into result ─────────────────────────────────────
        frame_vals: list[int] = (
            df_rep["frame"].tolist() if "frame" in df_rep.columns else []
        )
        df_rep_idx = df_rep.index.tolist()

        for local_i, lbl in label_map.items():
            if local_i < len(df_rep_idx):
                result.loc[df_rep_idx[local_i], "phase"] = lbl

        # Build phase_assignments in original frame numbers
        phase_assignments: dict[str, tuple[int, int]] = {}
        if frame_vals:
            all_labels = sorted(set(label_map.values()))
            for phase_name in all_labels:
                local_indices = [
                    i for i, label in label_map.items() if label == phase_name
                ]
                if local_indices:
                    phase_assignments[phase_name] = (
                        frame_vals[local_indices[0]],
                        frame_vals[local_indices[-1]],
                    )

        inflection_frames_global = [
            frame_vals[i]
            for i in (
                [inflection_local] if n_inflections_needed == 1 else inflection_locals
            )
            if i < len(frame_vals)
        ]

        reports.append(
            PhaseSegmentationReport(
                rep_id=rid,
                phase_assignments=phase_assignments,
                inflection_frames=inflection_frames_global,
                smoothing_method=smoothing_method_used,
                fps_used=fps,
                multi_inflection_collapsed=collapsed,
                rejected_reason=None,
            )
        )

    return result, reports


__all__ = [
    "RepSegmentationReport",
    "PhaseSegmentationReport",
    "segment_reps",
    "segment_phases",
]
