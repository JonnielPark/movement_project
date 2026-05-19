"""
Recording-plane phase split helpers for real one-take pose reviews.

These functions create and validate annotation-adjacent phase split artifacts.
They are intended for offline QC workflows where MediaPipe depth is not treated
as vertical height. The default reference signal is raw image-space hip_center_y.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PHASE_SPLIT_REQUIRED_COLUMNS: list[str] = [
    "recording_id",
    "set_id",
    "rep_id",
    "phase",
    "start_frame",
    "end_frame",
    "bottom_frame_estimate",
    "camera_zone",
    "reference_signal",
    "phase_source",
    "status",
]

DEFAULT_RECORDING_PHASE_ORDER: list[str] = [
    "Descent",
    "Turnaround_Hold",
    "Ascent",
]


def expected_phase_order_from_exercise(exercise_definition: Any) -> list[str]:
    """
    Return the phase order implied by an exercise definition.

    For two-phase resistance exercises with turnaround_hold enabled, inserts
    Turnaround_Hold between the first and last configured phases.
    """
    ps = getattr(exercise_definition, "phase_segmentation", None)
    sequence = list(getattr(ps, "phase_sequence", None) or ["Descent", "Ascent"])
    hold = getattr(ps, "turnaround_hold", None)
    hold_enabled = bool(getattr(hold, "enabled", False))
    if hold_enabled and len(sequence) == 2 and "Turnaround_Hold" not in sequence:
        return [sequence[0], "Turnaround_Hold", sequence[-1]]
    return sequence


def _hip_center_y_trace(pose_df: pd.DataFrame, frame_col: str) -> pd.Series:
    required = [frame_col, "left_hip_y", "right_hip_y"]
    missing = [col for col in required if col not in pose_df.columns]
    if missing:
        raise ValueError(f"pose dataframe missing columns: {missing}")
    return pd.Series(
        ((pose_df["left_hip_y"] + pose_df["right_hip_y"]) / 2.0).to_numpy(dtype=float),
        index=pose_df[frame_col].astype(int),
        name="hip_center_y",
    )


def _smooth_trace(trace: pd.Series, window_frames: int) -> pd.Series:
    clean = trace.interpolate(method="linear").ffill().bfill()
    window = min(max(1, int(window_frames)), len(clean))
    if window % 2 == 0:
        window -= 1
    window = max(1, window)
    return clean.rolling(window=window, center=True, min_periods=1).median()


def generate_recording_plane_phase_split(
    pose_df: pd.DataFrame,
    rep_annotation_df: pd.DataFrame,
    *,
    recording_id: str,
    camera_zone: str,
    smooth_window_frames: int = 9,
    hold_half_window_frames: int = 3,
    manual_bottom_frame_overrides: dict[int, int] | None = None,
    frame_col: str = "frame",
    reference_signal: str = "hip_center_y_raw_image_space",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate a semi-automatic phase split from confirmed rep ranges.

    The split uses raw image-space hip_center_y and assumes larger y means lower
    pelvis in the recording. The output is a QC candidate, not a confirmed phase
    annotation until visual review promotes it.

    Returns
    -------
    phase_split_df, qc_df
        phase_split_df has one row per rep phase. qc_df has one row per rep with
        bottom-frame and duration diagnostics.
    """
    if rep_annotation_df is None or rep_annotation_df.empty:
        raise ValueError("rep_annotation_df is empty")

    manual_bottom_frame_overrides = manual_bottom_frame_overrides or {}
    hold_half_window_frames = max(0, int(hold_half_window_frames))
    trace_by_frame = _hip_center_y_trace(pose_df, frame_col)

    rep_rows = (
        rep_annotation_df[rep_annotation_df["segment_type"].eq("rep")]
        .copy()
        .sort_values("start_frame")
    )
    if rep_rows.empty:
        raise ValueError("rep_annotation_df has no rep rows")

    phase_rows: list[dict[str, Any]] = []
    qc_rows: list[dict[str, Any]] = []

    for _, row in rep_rows.iterrows():
        rep_id = int(row["rep_id"])
        set_id = int(row["set_id"]) if pd.notna(row["set_id"]) else pd.NA
        start = int(row["start_frame"])
        end = int(row["end_frame"])
        rep_trace = trace_by_frame.loc[
            (trace_by_frame.index >= start) & (trace_by_frame.index <= end)
        ].dropna()

        source = "recording_plane_semiauto"
        status = "ok"
        bottom_frame: int | None = None
        bottom_y = np.nan

        if rep_trace.empty:
            status = "no_trace"
        else:
            if rep_id in manual_bottom_frame_overrides:
                candidate = int(manual_bottom_frame_overrides[rep_id])
                if start <= candidate <= end:
                    bottom_frame = candidate
                    source = "manual_bottom_override"
                    if candidate in trace_by_frame.index:
                        bottom_y = float(trace_by_frame.loc[candidate])
                else:
                    status = "override_out_of_range"
            else:
                smoothed = _smooth_trace(rep_trace, smooth_window_frames)
                bottom_frame = int(smoothed.idxmax())
                if bottom_frame in rep_trace.index:
                    bottom_y = float(rep_trace.loc[bottom_frame])

        if bottom_frame is None:
            qc_rows.append(
                {
                    "rep_id": rep_id,
                    "start_frame": start,
                    "bottom_frame_estimate": pd.NA,
                    "end_frame": end,
                    "status": status,
                    "source": source,
                }
            )
            continue

        hold_start = max(start, bottom_frame - hold_half_window_frames)
        hold_end = min(end, bottom_frame + hold_half_window_frames)
        spans = [
            ("Descent", start, hold_start - 1),
            ("Turnaround_Hold", hold_start, hold_end),
            ("Ascent", hold_end + 1, end),
        ]

        for phase_name, phase_start, phase_end in spans:
            if phase_start > phase_end:
                continue
            phase_rows.append(
                {
                    "recording_id": recording_id,
                    "set_id": set_id,
                    "rep_id": rep_id,
                    "phase": phase_name,
                    "start_frame": int(phase_start),
                    "end_frame": int(phase_end),
                    "bottom_frame_estimate": bottom_frame,
                    "bottom_hip_center_y": (
                        round(bottom_y, 6) if np.isfinite(bottom_y) else np.nan
                    ),
                    "camera_zone": camera_zone,
                    "reference_signal": reference_signal,
                    "phase_source": source,
                    "smooth_window_frames": int(smooth_window_frames),
                    "hold_half_window_frames": hold_half_window_frames,
                    "status": status,
                    "note": (
                        "QC candidate; confirm visually before promoting to "
                        "phase annotation"
                    ),
                }
            )

        qc_rows.append(
            {
                "rep_id": rep_id,
                "start_frame": start,
                "bottom_frame_estimate": bottom_frame,
                "end_frame": end,
                "descent_frames": max(0, hold_start - start),
                "hold_frames": hold_end - hold_start + 1,
                "ascent_frames": max(0, end - hold_end),
                "status": status,
                "source": source,
            }
        )

    return pd.DataFrame(phase_rows), pd.DataFrame(qc_rows)


def validate_phase_split_for_promotion(
    phase_df: pd.DataFrame,
    rep_annotation_df: pd.DataFrame,
    *,
    expected_phase_order: list[str] | None = None,
    expected_camera_zone: str | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """
    Validate whether a phase split candidate can be promoted after visual QC.

    Validation is structural/provenance only. It does not decide whether the
    visual QC itself passed; that must be confirmed by the researcher.
    """
    expected_phase_order = expected_phase_order or DEFAULT_RECORDING_PHASE_ORDER
    errors: list[str] = []
    warnings: list[str] = []
    detail_rows: list[dict[str, Any]] = []

    if phase_df is None or phase_df.empty:
        return {
            "passed": False,
            "errors": ["phase split is empty"],
            "warnings": warnings,
            "expected_phase_order": expected_phase_order,
            "num_annotation_reps": 0,
            "num_phase_reps": 0,
        }, pd.DataFrame()

    if rep_annotation_df is None or rep_annotation_df.empty:
        return {
            "passed": False,
            "errors": ["annotation is empty"],
            "warnings": warnings,
            "expected_phase_order": expected_phase_order,
            "num_annotation_reps": 0,
            "num_phase_reps": 0,
        }, pd.DataFrame()

    rep_rows = (
        rep_annotation_df[rep_annotation_df["segment_type"].eq("rep")]
        .copy()
        .sort_values("rep_id")
    )
    if rep_rows.empty:
        errors.append("annotation has no rep rows")
        return {
            "passed": False,
            "errors": errors,
            "warnings": warnings,
            "expected_phase_order": expected_phase_order,
            "num_annotation_reps": 0,
            "num_phase_reps": 0,
        }, pd.DataFrame()

    missing = [
        col for col in PHASE_SPLIT_REQUIRED_COLUMNS if col not in phase_df.columns
    ]
    if missing:
        phase_rep_count = (
            int(phase_df["rep_id"].dropna().nunique())
            if "rep_id" in phase_df.columns
            else 0
        )
        errors.append(f"phase split missing required columns: {missing}")
        return {
            "passed": False,
            "errors": errors,
            "warnings": warnings,
            "expected_phase_order": expected_phase_order,
            "num_annotation_reps": int(rep_rows["rep_id"].dropna().nunique()),
            "num_phase_reps": phase_rep_count,
        }, pd.DataFrame()

    rep_rows["rep_id"] = rep_rows["rep_id"].astype(int)
    phase_work = phase_df.dropna(subset=["rep_id"]).copy()
    phase_work["rep_id"] = phase_work["rep_id"].astype(int)

    ann_rep_ids = set(rep_rows["rep_id"].tolist())
    phase_rep_ids = set(phase_work["rep_id"].tolist())
    missing_reps = sorted(ann_rep_ids - phase_rep_ids)
    extra_reps = sorted(phase_rep_ids - ann_rep_ids)
    if missing_reps:
        errors.append(f"phase split missing reps: {missing_reps}")
    if extra_reps:
        errors.append(f"phase split has reps not in annotation: {extra_reps}")

    for rep_id in sorted(ann_rep_ids & phase_rep_ids):
        ann_row = rep_rows[rep_rows["rep_id"].eq(rep_id)].iloc[0]
        rep_start = int(ann_row["start_frame"])
        rep_end = int(ann_row["end_frame"])
        sub = (
            phase_work[phase_work["rep_id"].eq(rep_id)]
            .copy()
            .sort_values("start_frame")
        )
        sub["start_frame"] = sub["start_frame"].astype(int)
        sub["end_frame"] = sub["end_frame"].astype(int)
        phases = sub["phase"].astype(str).tolist()

        if phases != expected_phase_order:
            errors.append(
                f"rep {rep_id}: phase order {phases} != expected {expected_phase_order}"
            )

        first_start = int(sub["start_frame"].iloc[0])
        last_end = int(sub["end_frame"].iloc[-1])
        if first_start != rep_start or last_end != rep_end:
            errors.append(
                f"rep {rep_id}: phase coverage {first_start}-{last_end} "
                f"does not match rep range {rep_start}-{rep_end}"
            )

        starts = sub["start_frame"].astype(int).tolist()
        ends = sub["end_frame"].astype(int).tolist()
        for idx in range(len(sub) - 1):
            if ends[idx] + 1 != starts[idx + 1]:
                errors.append(
                    f"rep {rep_id}: gap/overlap between {phases[idx]} and "
                    f"{phases[idx + 1]} ({ends[idx]} -> {starts[idx + 1]})"
                )

        for _, phase_row in sub.iterrows():
            phase_start = int(phase_row["start_frame"])
            phase_end = int(phase_row["end_frame"])
            if phase_start < rep_start or phase_end > rep_end:
                errors.append(
                    f"rep {rep_id}: {phase_row['phase']} range {phase_start}-{phase_end} "
                    f"outside rep {rep_start}-{rep_end}"
                )
            if phase_start > phase_end:
                errors.append(
                    f"rep {rep_id}: invalid phase range {phase_start}-{phase_end}"
                )

        bottom_values = (
            sub["bottom_frame_estimate"].dropna().astype(int).unique().tolist()
        )
        bottom_frame = bottom_values[0] if bottom_values else None
        if len(bottom_values) != 1:
            errors.append(
                f"rep {rep_id}: expected one bottom_frame_estimate, got {bottom_values}"
            )

        hold_rows = sub[sub["phase"].eq("Turnaround_Hold")]
        bottom_in_hold = False
        if bottom_frame is not None and not hold_rows.empty:
            hold_start = int(hold_rows["start_frame"].iloc[0])
            hold_end = int(hold_rows["end_frame"].iloc[0])
            bottom_in_hold = hold_start <= bottom_frame <= hold_end
            if not bottom_in_hold:
                errors.append(
                    f"rep {rep_id}: bottom_frame_estimate {bottom_frame} outside "
                    f"Turnaround_Hold {hold_start}-{hold_end}"
                )
        elif bottom_frame is not None:
            errors.append(f"rep {rep_id}: Turnaround_Hold phase is missing")

        bad_status = sorted(
            set(
                sub.loc[
                    ~sub["status"].isin(["ok", "visually_confirmed"]), "status"
                ].astype(str)
            )
        )
        if bad_status:
            errors.append(f"rep {rep_id}: non-promotable phase statuses {bad_status}")

        if expected_camera_zone is not None:
            camera_zones = sorted(set(sub["camera_zone"].dropna().astype(str).tolist()))
            if camera_zones != [expected_camera_zone]:
                errors.append(
                    f"rep {rep_id}: camera_zone {camera_zones} != expected {expected_camera_zone}"
                )

        detail_rows.append(
            {
                "rep_id": rep_id,
                "rep_range": f"{rep_start}-{rep_end}",
                "phase_order": " -> ".join(phases),
                "bottom_frame_estimate": bottom_frame,
                "bottom_in_hold": bottom_in_hold,
                "num_phase_rows": len(sub),
            }
        )

    report = {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "expected_phase_order": expected_phase_order,
        "num_annotation_reps": len(ann_rep_ids),
        "num_phase_reps": len(phase_rep_ids),
    }
    return report, pd.DataFrame(detail_rows)


def promote_phase_split_to_annotation(
    phase_df: pd.DataFrame,
    rep_annotation_df: pd.DataFrame,
    *,
    visual_qc_confirmed: bool,
    expected_phase_order: list[str] | None = None,
    expected_camera_zone: str | None = None,
    source_phase_split_file: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    """
    Promote a validated phase split candidate to a confirmed annotation dataframe.

    Raises ValueError unless visual_qc_confirmed is True and structural promotion
    validation passes.
    """
    if not visual_qc_confirmed:
        raise ValueError("visual_qc_confirmed must be True before promotion")

    report, detail_df = validate_phase_split_for_promotion(
        phase_df,
        rep_annotation_df,
        expected_phase_order=expected_phase_order,
        expected_camera_zone=expected_camera_zone,
    )
    if not report["passed"]:
        raise ValueError(f"phase split promotion validation failed: {report['errors']}")

    promoted = phase_df.copy()
    promoted["split_status"] = promoted.get("status", "")
    promoted["status"] = "visually_confirmed"
    promoted["confirmation_source"] = "researcher_visual_qc"
    if source_phase_split_file is not None:
        promoted["source_phase_split_file"] = Path(source_phase_split_file).name
    return promoted, report, detail_df


__all__ = [
    "DEFAULT_RECORDING_PHASE_ORDER",
    "PHASE_SPLIT_REQUIRED_COLUMNS",
    "expected_phase_order_from_exercise",
    "generate_recording_plane_phase_split",
    "promote_phase_split_to_annotation",
    "validate_phase_split_for_promotion",
]
