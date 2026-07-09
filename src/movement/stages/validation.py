"""
① Validation

Checks structural integrity of pose landmark data and returns a diagnostic report.
Schema harmonization helpers may return a dataframe copy with missing z columns
added as NaN placeholders; integrity checks themselves do not invent evidence.

Note: "validation" here means data integrity checking only.
      This is distinct from robustness evaluation (synthetic data simulation tests).

Pipeline position: first step; guarantees input quality for all downstream steps.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def harmonize_pose_schema(
    df: pd.DataFrame,
    landmarks: list[str],
    coordinate_axes: str = "auto",
) -> tuple[pd.DataFrame, dict]:
    """Return an xyz-shaped pose dataframe and schema harmonization report.

    YOLO-style 2D pose backends usually provide x/y without z. This helper adds
    missing raw z columns as NaN placeholders so downstream stages can share an
    xyz schema while still treating z as non-evaluable evidence.
    """

    mode = str(coordinate_axes or "auto").lower()
    if mode not in {"auto", "xy", "xyz"}:
        raise ValueError("coordinate_axes must be one of: auto, xy, xyz.")

    missing_xy = [
        f"{landmark}_{axis}"
        for landmark in landmarks
        for axis in ("x", "y")
        if f"{landmark}_{axis}" not in df.columns
    ]
    if missing_xy:
        raise ValueError(
            "Cannot harmonize pose schema without required x/y columns: "
            f"{missing_xy[:10]}"
        )

    result = df.copy()
    mapped_backend_alias_columns: list[dict[str, str]] = []
    dropped_backend_alias_columns: list[str] = []
    for landmark in landmarks:
        confidence_col = f"{landmark}_confidence"
        backend_confidence_alias_col = f"{landmark}_visibility"
        if (
            confidence_col not in result.columns
            and backend_confidence_alias_col in result.columns
        ):
            result[confidence_col] = result[backend_confidence_alias_col]
            mapped_backend_alias_columns.append(
                {
                    "backend_alias": backend_confidence_alias_col,
                    "canonical_column": confidence_col,
                }
            )
        if backend_confidence_alias_col in result.columns:
            result = result.drop(columns=[backend_confidence_alias_col])
            dropped_backend_alias_columns.append(backend_confidence_alias_col)

    z_columns = [f"{landmark}_z" for landmark in landmarks]
    existing_z = [column for column in z_columns if column in result.columns]
    missing_z = [column for column in z_columns if column not in result.columns]
    added_z_columns: list[str] = []
    for column in missing_z:
        result[column] = np.nan
        added_z_columns.append(column)

    z_values = result[z_columns].astype(float).to_numpy()
    finite_z = bool(np.isfinite(z_values).any())
    observed_axes = ["x", "y"] + (["z"] if existing_z and finite_z else [])
    coordinate_shape = ["x", "y", "z"]

    if not existing_z or not finite_z:
        z_source = "absent"
    elif len(existing_z) == len(z_columns):
        z_source = "model_depth"
    else:
        z_source = "partial_model_depth"

    z_evaluable = mode != "xy" and z_source == "model_depth"
    if mode == "xyz" and not z_evaluable:
        raise ValueError(
            "coordinate_axes='xyz' requires finite backend-provided z for all "
            "configured landmarks."
        )

    validation_axes = (
        ["x", "y", "z"]
        if mode == "xyz" or (mode == "auto" and z_evaluable)
        else ["x", "y"]
    )

    result.attrs["coordinate_shape"] = {"raw": coordinate_shape}
    result.attrs["observed_coordinate_axes"] = {"raw": observed_axes}
    result.attrs["z_source"] = {"raw": z_source}
    result.attrs["z_evaluable"] = {"raw": z_evaluable}
    result.attrs["z_fill_policy"] = {
        "raw": "provided_by_backend" if z_source == "model_depth" else "nan_placeholder"
    }

    report = {
        "status": "applied" if added_z_columns else "unchanged",
        "coordinate_shape": coordinate_shape,
        "observed_axes": observed_axes,
        "validation_axes": validation_axes,
        "added_z_columns": added_z_columns,
        "num_added_z_columns": len(added_z_columns),
        "z_source": z_source,
        "z_fill_policy": result.attrs["z_fill_policy"]["raw"],
        "z_evaluable": z_evaluable,
        "coordinate_axes_config": mode,
        "confidence_schema": {
            "canonical_suffix": "confidence",
            "mapped_backend_alias_columns": mapped_backend_alias_columns,
            "dropped_backend_alias_columns": dropped_backend_alias_columns,
        },
    }
    return result, report


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
        df[frame_col][df[frame_col].duplicated()].dropna().astype(int).unique().tolist()
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


def validate_confidence(
    df: pd.DataFrame,
    confidence_columns: list[str],
    threshold: float = 0.5,
) -> dict:
    """
    Check landmark confidence quality.
    """
    existing_cols = [col for col in confidence_columns if col in df.columns]
    missing_cols = [col for col in confidence_columns if col not in df.columns]

    if len(existing_cols) == 0:
        return {
            "passed": False,
            "severity": "warning",
            "policy": "warning_provenance_only",
            "error": "No confidence columns found.",
            "missing_confidence_columns": missing_cols,
        }

    confidence = df[existing_cols].astype(float)
    low_confidence_ratio = (confidence < threshold).mean()

    passed = bool((low_confidence_ratio < 0.2).all())

    return {
        "passed": passed,
        "severity": "ok" if passed else "warning",
        "policy": "warning_provenance_only",
        "threshold": threshold,
        "num_confidence_columns": len(existing_cols),
        "missing_confidence_columns": missing_cols,
        "low_confidence_ratio_by_column": low_confidence_ratio.to_dict(),
    }


def run_basic_validation(
    df: pd.DataFrame,
    required_columns: list[str],
    coordinate_columns: list[str],
    confidence_columns: list[str] | None = None,
    confidence_threshold: float = 0.5,
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

    if confidence_columns is not None:
        report["confidence"] = validate_confidence(
            df=df,
            confidence_columns=confidence_columns,
            threshold=confidence_threshold,
        )

    structural_checks = (
        "required_columns",
        "frame_continuity",
        "timestamp",
        "missing_values",
    )
    report["structural_passed"] = all(
        report[name].get("passed", False) for name in structural_checks
    )
    report["passed"] = report["structural_passed"]
    report["warnings"] = []

    confidence_report = report.get("confidence")
    if isinstance(confidence_report, dict) and not confidence_report.get(
        "passed", True
    ):
        report["warnings"].append(
            {
                "check": "confidence",
                "severity": confidence_report.get("severity", "warning"),
                "policy": confidence_report.get("policy", "warning_provenance_only"),
                "message": "Low or unavailable landmark confidence is handled by downstream reliability gates.",
            }
        )

    return report
