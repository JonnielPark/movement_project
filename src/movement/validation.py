# src/movement/validation.py

from __future__ import annotations

import pandas as pd


def validate_required_columns(
    df: pd.DataFrame,
    required_columns: list[str],
) -> dict:
    """
    Check whether all required columns exist in the dataframe.
    """
    missing = [col for col in required_columns if col not in df.columns]

    return {
        "passed": len(missing) == 0,
        "missing_columns": missing,
        "num_missing_columns": len(missing),
    }


def validate_frame_continuity(
    df: pd.DataFrame,
    frame_col: str = "frame",
) -> dict:
    """
    Check whether frame indices are continuous.
    """
    if frame_col not in df.columns:
        return {
            "passed": False,
            "error": f"Missing frame column: {frame_col}",
        }

    frames = df[frame_col].dropna().astype(int).sort_values().to_list()

    if len(frames) == 0:
        return {
            "passed": False,
            "error": "No valid frame values.",
        }

    expected = list(range(frames[0], frames[-1] + 1))
    missing_frames = sorted(set(expected) - set(frames))
    duplicated_frames = (
        df[frame_col][df[frame_col].duplicated()]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    return {
        "passed": len(missing_frames) == 0 and len(duplicated_frames) == 0,
        "start_frame": frames[0],
        "end_frame": frames[-1],
        "num_frames": len(frames),
        "num_missing_frames": len(missing_frames),
        "missing_frames": missing_frames,
        "num_duplicated_frames": len(duplicated_frames),
        "duplicated_frames": duplicated_frames,
    }


def validate_timestamp(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
) -> dict:
    """
    Check whether timestamps are monotonic and estimate FPS.
    """
    if timestamp_col not in df.columns:
        return {
            "passed": False,
            "error": f"Missing timestamp column: {timestamp_col}",
        }

    timestamps = df[timestamp_col].dropna().astype(float)

    if len(timestamps) < 2:
        return {
            "passed": False,
            "error": "Not enough timestamp values.",
        }

    diffs = timestamps.diff().dropna()

    non_positive = diffs[diffs <= 0]

    median_dt = float(diffs.median())
    estimated_fps = 1.0 / median_dt if median_dt > 0 else None

    return {
        "passed": len(non_positive) == 0,
        "num_timestamps": len(timestamps),
        "median_dt": median_dt,
        "estimated_fps": estimated_fps,
        "min_dt": float(diffs.min()),
        "max_dt": float(diffs.max()),
        "num_non_positive_diffs": int(len(non_positive)),
    }


def validate_missing_values(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict:
    """
    Check missing value ratio for selected columns.
    """
    target = df if columns is None else df[columns]

    missing_counts = target.isna().sum()
    missing_ratios = target.isna().mean()

    return {
        "passed": bool((missing_ratios < 0.05).all()),
        "num_columns": len(target.columns),
        "total_missing_values": int(missing_counts.sum()),
        "missing_ratio_by_column": missing_ratios.to_dict(),
    }


def validate_visibility(
    df: pd.DataFrame,
    visibility_columns: list[str],
    threshold: float = 0.5,
) -> dict:
    """
    Check landmark visibility quality.
    """
    existing_cols = [col for col in visibility_columns if col in df.columns]
    missing_cols = [col for col in visibility_columns if col not in df.columns]

    if len(existing_cols) == 0:
        return {
            "passed": False,
            "error": "No visibility columns found.",
            "missing_visibility_columns": missing_cols,
        }

    visibility = df[existing_cols].astype(float)
    low_visibility_ratio = (visibility < threshold).mean()

    return {
        "passed": bool((low_visibility_ratio < 0.2).all()),
        "threshold": threshold,
        "num_visibility_columns": len(existing_cols),
        "missing_visibility_columns": missing_cols,
        "low_visibility_ratio_by_column": low_visibility_ratio.to_dict(),
    }


def run_basic_validation(
    df: pd.DataFrame,
    required_columns: list[str],
    coordinate_columns: list[str],
    visibility_columns: list[str] | None = None,
) -> dict:
    """
    Run basic validation checks for pose dataframe.
    """
    report = {}

    report["required_columns"] = validate_required_columns(
        df=df,
        required_columns=required_columns,
    )

    report["frame_continuity"] = validate_frame_continuity(df=df)

    report["timestamp"] = validate_timestamp(df=df)

    report["missing_values"] = validate_missing_values(
        df=df,
        columns=coordinate_columns,
    )

    if visibility_columns is not None:
        report["visibility"] = validate_visibility(
            df=df,
            visibility_columns=visibility_columns,
        )

    report["passed"] = all(
        section.get("passed", False)
        for section in report.values()
        if isinstance(section, dict)
    )

    return report