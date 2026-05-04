"""
② Annotation

Merges pre-labelled segment metadata into the pose dataframe.
Does not perform automatic rep detection or segmentation.
Does not modify coordinates.

Annotation hierarchy:  recording → set → rep → phase

Output columns added to the pose dataframe:
    use_for_analysis : bool
    segment_type     : str    (full_sequence | baseline | idle | rep | rest | transition | excluded)
    set_id           : Int64  (nullable)
    rep_id           : Int64  (nullable)
    phase            : object (nullable, reserved for future use)

Pipeline position: after ① validation, before ③ exercise definition loading.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


# ── Constants ─────────────────────────────────────────────────────────────────

ANNOTATION_REQUIRED_COLUMNS: list[str] = [
    "segment_type",
    "set_id",
    "rep_id",
    "start_frame",
    "end_frame",
    "use_for_analysis",
]

ANNOTATION_OPTIONAL_COLUMNS: list[str] = [
    "exercise_type",
    "pattern",
    "starting_side",
    "phase",
    "note",
]

VALID_SEGMENT_TYPES: frozenset[str] = frozenset({
    "full_sequence",
    "baseline",
    "idle",
    "rep",
    "rest",
    "transition",
    "excluded",
})

ANNOTATION_OUTPUT_COLUMNS: list[str] = [
    "use_for_analysis",
    "segment_type",
    "set_id",
    "rep_id",
    "phase",
    "exercise_type",
    "pattern",
    "starting_side",
]


# ── Loader ────────────────────────────────────────────────────────────────────

def load_annotation_csv(path: Path | str) -> pd.DataFrame:
    """
    Load and normalize an annotation CSV file.

    Required columns:
        segment_type, set_id, rep_id, start_frame, end_frame, use_for_analysis

    Normalizations applied:
        - use_for_analysis → bool  (handles "true"/"false" strings)
        - set_id, rep_id   → Int64 (nullable integer; empty cells become pd.NA)
        - start_frame, end_frame → int

    Parameters
    ----------
    path : Path | str

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If required columns are missing.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Annotation file not found: {path}")

    ann = pd.read_csv(path)

    missing = [col for col in ANNOTATION_REQUIRED_COLUMNS if col not in ann.columns]
    if missing:
        raise ValueError(f"Annotation CSV missing required columns: {missing}")

    ann["use_for_analysis"] = ann["use_for_analysis"].apply(
        lambda x: str(x).strip().lower() in ("true", "1", "yes")
        if pd.notna(x)
        else False
    )
    ann["set_id"] = ann["set_id"].astype("Int64")
    ann["rep_id"] = ann["rep_id"].astype("Int64")
    ann["start_frame"] = ann["start_frame"].astype(int)
    ann["end_frame"] = ann["end_frame"].astype(int)

    return ann


# ── Validation ────────────────────────────────────────────────────────────────

def _detect_overlaps(ann_df: pd.DataFrame) -> list[tuple[int, int]]:
    """
    Return (row_i, row_j) index pairs whose frame ranges overlap.

    Frame ranges are inclusive: [start_frame, end_frame].
    """
    overlaps: list[tuple[int, int]] = []
    idx = ann_df.index.tolist()
    starts = ann_df["start_frame"].astype(int).tolist()
    ends = ann_df["end_frame"].astype(int).tolist()

    for i in range(len(idx)):
        for j in range(i + 1, len(idx)):
            if starts[i] <= ends[j] and starts[j] <= ends[i]:
                overlaps.append((idx[i], idx[j]))

    return overlaps


def validate_annotation(
    ann_df: pd.DataFrame,
    pose_df: pd.DataFrame,
    frame_col: str = "frame",
) -> dict[str, Any]:
    """
    Validate annotation table against a pose dataframe.

    Checks:
        1. Required columns present
        2. start_frame <= end_frame for every row
        3. Frame ranges within the pose sequence range
        4. No overlapping segments
        5. segment_type values are in VALID_SEGMENT_TYPES

    Parameters
    ----------
    ann_df : pd.DataFrame
        Annotation table (output of load_annotation_csv).
    pose_df : pd.DataFrame
        Pose dataframe being annotated.
    frame_col : str
        Name of the frame column in pose_df.

    Returns
    -------
    dict
        Validation report with "passed" key.
    """
    report: dict[str, Any] = {}

    missing_cols = [c for c in ANNOTATION_REQUIRED_COLUMNS if c not in ann_df.columns]
    report["missing_required_columns"] = missing_cols
    if missing_cols:
        report["passed"] = False
        return report

    invalid_range_rows = ann_df.index[
        ann_df["start_frame"] > ann_df["end_frame"]
    ].tolist()
    report["invalid_range_rows"] = invalid_range_rows

    pose_min = int(pose_df[frame_col].min())
    pose_max = int(pose_df[frame_col].max())
    out_of_bounds_rows = ann_df.index[
        (ann_df["start_frame"] < pose_min) | (ann_df["end_frame"] > pose_max)
    ].tolist()
    report["pose_frame_range"] = [pose_min, pose_max]
    report["out_of_bounds_rows"] = out_of_bounds_rows

    overlapping_pairs = _detect_overlaps(ann_df)
    report["overlapping_pairs"] = overlapping_pairs

    known = ann_df["segment_type"].dropna()
    unknown_types = known[~known.isin(VALID_SEGMENT_TYPES)].unique().tolist()
    report["unknown_segment_types"] = unknown_types

    report["passed"] = (
        len(missing_cols) == 0
        and len(invalid_range_rows) == 0
        and len(out_of_bounds_rows) == 0
        and len(overlapping_pairs) == 0
        and len(unknown_types) == 0
    )

    return report


# ── Application ───────────────────────────────────────────────────────────────

def _full_sequence_fallback(pose_df: pd.DataFrame) -> pd.DataFrame:
    """Add annotation columns with full-sequence defaults."""
    n = len(pose_df)
    result = pose_df.copy()
    result["use_for_analysis"] = True
    result["segment_type"] = "full_sequence"
    result["set_id"] = pd.array([pd.NA] * n, dtype="Int64")
    result["rep_id"] = pd.array([pd.NA] * n, dtype="Int64")
    result["phase"] = pd.array([pd.NA] * n, dtype=object)
    result["exercise_type"] = pd.array([None] * n, dtype=object)
    result["pattern"] = "bilateral"
    result["starting_side"] = pd.array([None] * n, dtype=object)
    return result


def apply_annotation(
    pose_df: pd.DataFrame,
    ann_df: pd.DataFrame | None,
    frame_col: str = "frame",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Apply annotation to a pose dataframe by adding metadata columns.

    Does not remove or reorder rows. Original frame indices are preserved.

    If ann_df is None, falls back to full-sequence mode:
        - all frames: use_for_analysis=True, segment_type='full_sequence'

    If ann_df is provided:
        - all frames start with use_for_analysis=False
        - frames inside annotated segments are updated per the annotation file
        - frames outside annotated ranges remain excluded

    Parameters
    ----------
    pose_df : pd.DataFrame
        Pose dataframe. Shape: (T, *). Must contain frame_col.
    ann_df : pd.DataFrame | None
        Annotation table (output of load_annotation_csv), or None.
    frame_col : str
        Name of the frame column in pose_df.

    Returns
    -------
    annotated_df : pd.DataFrame
        pose_df with columns added: use_for_analysis, segment_type, set_id, rep_id, phase.
    report : dict
        Annotation report.

    Raises
    ------
    ValueError
        If annotation validation fails.
    """
    num_total = len(pose_df)

    # ── No annotation provided ────────────────────────────────────────────────
    if ann_df is None:
        result = _full_sequence_fallback(pose_df)
        report: dict[str, Any] = {
            "annotation_provided": False,
            "policy": "use_full_sequence",
            "num_total_frames": num_total,
            "num_analysis_frames": num_total,
            "num_excluded_frames": 0,
        }
        return result, report

    # ── Annotation provided ───────────────────────────────────────────────────
    val_report = validate_annotation(ann_df, pose_df, frame_col=frame_col)
    if not val_report["passed"]:
        raise ValueError(f"Annotation validation failed:\n{val_report}")

    n = num_total
    result = pose_df.copy()
    result["use_for_analysis"] = False
    result["segment_type"] = pd.NA
    result["set_id"] = pd.array([pd.NA] * n, dtype="Int64")
    result["rep_id"] = pd.array([pd.NA] * n, dtype="Int64")
    result["phase"] = pd.array([pd.NA] * n, dtype=object)
    result["exercise_type"] = pd.array([None] * n, dtype=object)
    result["pattern"] = pd.array([None] * n, dtype=object)
    result["starting_side"] = pd.array([None] * n, dtype=object)

    frame_series = result[frame_col].astype(int)
    has_phase_col = "phase" in ann_df.columns

    for _, row in ann_df.iterrows():
        start = int(row["start_frame"])
        end = int(row["end_frame"])
        mask = (frame_series >= start) & (frame_series <= end)

        result.loc[mask, "use_for_analysis"] = bool(row["use_for_analysis"])
        result.loc[mask, "segment_type"] = str(row["segment_type"])

        set_val = row["set_id"]
        result.loc[mask, "set_id"] = pd.NA if pd.isna(set_val) else int(set_val)

        rep_val = row["rep_id"]
        result.loc[mask, "rep_id"] = pd.NA if pd.isna(rep_val) else int(rep_val)

        phase_val = row["phase"] if has_phase_col else pd.NA
        result.loc[mask, "phase"] = None if pd.isna(phase_val) else str(phase_val)

        if "exercise_type" in ann_df.columns:
            ex_val = row["exercise_type"]
            result.loc[mask, "exercise_type"] = None if pd.isna(ex_val) else str(ex_val)

        if "pattern" in ann_df.columns:
            pat_val = row["pattern"]
            result.loc[mask, "pattern"] = None if pd.isna(pat_val) else str(pat_val)

        if "starting_side" in ann_df.columns:
            ss_val = row["starting_side"]
            result.loc[mask, "starting_side"] = None if pd.isna(ss_val) else str(ss_val)

    num_analysis = int(result["use_for_analysis"].sum())

    rep_rows = ann_df[ann_df["segment_type"] == "rep"]
    num_sets = int(rep_rows["set_id"].dropna().nunique())
    num_reps = int(len(rep_rows))

    report = {
        "annotation_provided": True,
        "policy": "annotation_mask",
        "num_total_frames": num_total,
        "num_analysis_frames": num_analysis,
        "num_excluded_frames": num_total - num_analysis,
        "num_annotated_rows": len(ann_df),
        "num_sets": num_sets,
        "num_reps": num_reps,
        "validation": val_report,
    }

    return result, report
