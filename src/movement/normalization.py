"""
Coordinate normalization utilities for pose landmark data.

This module converts raw pose coordinates into a body-relative coordinate system.

Current method:
    - Translation reference: frame-wise hip center
    - Scale reference: sequence-wise median torso length

Raw coordinates are preserved.
Normalized coordinates are added as new columns:
    <landmark>_norm_x
    <landmark>_norm_y
    <landmark>_norm_z
"""

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


def _coord_cols(landmark: str) -> List[str]:
    """
    Return x, y, z coordinate column names for a landmark.
    """
    return [
        "{}_x".format(landmark),
        "{}_y".format(landmark),
        "{}_z".format(landmark),
    ]


def _norm_coord_cols(landmark: str) -> List[str]:
    """
    Return normalized x, y, z coordinate column names for a landmark.
    """
    return [
        "{}_norm_x".format(landmark),
        "{}_norm_y".format(landmark),
        "{}_norm_z".format(landmark),
    ]


def _check_landmark_columns(
    df: pd.DataFrame,
    landmarks: List[str],
) -> None:
    """
    Raise ValueError if required landmark coordinate columns are missing.
    """
    missing_columns = []

    for landmark in landmarks:
        for col in _coord_cols(landmark):
            if col not in df.columns:
                missing_columns.append(col)

    if missing_columns:
        raise ValueError(
            "Missing landmark coordinate columns: {}".format(missing_columns)
        )


def compute_midpoint(
    df: pd.DataFrame,
    landmark_a: str,
    landmark_b: str,
    output_prefix: str,
) -> pd.DataFrame:
    """
    Compute midpoint between two landmarks and add it to the dataframe.

    Output columns:
        <output_prefix>_x
        <output_prefix>_y
        <output_prefix>_z
    """
    result = df.copy()

    a_cols = _coord_cols(landmark_a)
    b_cols = _coord_cols(landmark_b)

    for axis, a_col, b_col in zip(("x", "y", "z"), a_cols, b_cols):
        result["{}_{}".format(output_prefix, axis)] = (
            result[a_col] + result[b_col]
        ) / 2.0

    return result


def compute_distance_between_prefixes(
    df: pd.DataFrame,
    prefix_a: str,
    prefix_b: str,
    output_col: str,
) -> pd.DataFrame:
    """
    Compute Euclidean distance between two 3D points defined by column prefixes.

    Example:
        prefix_a = "hip_center"
        prefix_b = "shoulder_center"

        Required columns:
            hip_center_x, hip_center_y, hip_center_z
            shoulder_center_x, shoulder_center_y, shoulder_center_z
    """
    result = df.copy()

    dx = result["{}_x".format(prefix_a)] - result["{}_x".format(prefix_b)]
    dy = result["{}_y".format(prefix_a)] - result["{}_y".format(prefix_b)]
    dz = result["{}_z".format(prefix_a)] - result["{}_z".format(prefix_b)]

    result[output_col] = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

    return result


def add_body_reference_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add hip center, shoulder center, and torso length columns.

    Added columns:
        hip_center_x, hip_center_y, hip_center_z
        shoulder_center_x, shoulder_center_y, shoulder_center_z
        torso_length
    """
    required = [
        "left_hip",
        "right_hip",
        "left_shoulder",
        "right_shoulder",
    ]
    _check_landmark_columns(df, required)

    result = df.copy()

    result = compute_midpoint(
        result,
        landmark_a="left_hip",
        landmark_b="right_hip",
        output_prefix="hip_center",
    )

    result = compute_midpoint(
        result,
        landmark_a="left_shoulder",
        landmark_b="right_shoulder",
        output_prefix="shoulder_center",
    )

    result = compute_distance_between_prefixes(
        result,
        prefix_a="hip_center",
        prefix_b="shoulder_center",
        output_col="torso_length",
    )

    return result


def compute_sequence_median_scale(
    df: pd.DataFrame,
    torso_length_col: str = "torso_length",
    min_scale: float = 1e-6,
) -> Tuple[float, Dict[str, Any]]:
    """
    Compute sequence-wise median torso length.

    Invalid torso lengths are:
        - NaN
        - infinite
        - <= min_scale
    """
    if torso_length_col not in df.columns:
        raise ValueError(
            "Missing torso length column: {}".format(torso_length_col)
        )

    torso = df[torso_length_col].astype(float)

    valid_mask = (
        torso.notna()
        & np.isfinite(torso)
        & (torso > min_scale)
    )

    valid_torso = torso[valid_mask]

    if len(valid_torso) == 0:
        raise ValueError(
            "No valid torso length values available for scale normalization."
        )

    scale_value = float(valid_torso.median())

    report = {
        "scale_method": "sequence_median_torso_length",
        "scale_value": scale_value,
        "min_torso_length": float(valid_torso.min()),
        "max_torso_length": float(valid_torso.max()),
        "median_torso_length": scale_value,
        "num_invalid_torso_frames": int((~valid_mask).sum()),
        "num_valid_torso_frames": int(valid_mask.sum()),
    }

    return scale_value, report


def normalize_pose_by_hip_torso(
    df: pd.DataFrame,
    landmarks: List[str],
    min_scale: float = 1e-6,
    keep_reference_columns: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Normalize pose coordinates using hip-centered translation and
    sequence-wise median torso scale.

    Formula:
        p_norm_i(t) = (p_i(t) - hip_center(t)) / median_torso_length

    Parameters
    ----------
    df:
        Input pose dataframe.
    landmarks:
        List of landmark names.
    min_scale:
        Minimum valid torso length.
    keep_reference_columns:
        If True, keep hip_center, shoulder_center, and torso_length columns.

    Returns
    -------
    norm_df:
        Dataframe with normalized coordinate columns added.
    report:
        Normalization report dictionary.
    """
    _check_landmark_columns(df, landmarks)

    result = add_body_reference_columns(df)

    scale_value, scale_report = compute_sequence_median_scale(
        result,
        torso_length_col="torso_length",
        min_scale=min_scale,
    )

    normalized_data = {}

    for landmark in landmarks:
        raw_cols = _coord_cols(landmark)
        norm_cols = _norm_coord_cols(landmark)

        normalized_data[norm_cols[0]] = (
            result[raw_cols[0]] - result["hip_center_x"]
        ) / scale_value

        normalized_data[norm_cols[1]] = (
            result[raw_cols[1]] - result["hip_center_y"]
        ) / scale_value

        normalized_data[norm_cols[2]] = (
            result[raw_cols[2]] - result["hip_center_z"]
        ) / scale_value

    normalized_df = pd.DataFrame(
        normalized_data,
        index=result.index,
    )

    result = pd.concat([result, normalized_df], axis=1)
    result = result.copy()

    if not keep_reference_columns:
        result = result.drop(
            columns=[
                "hip_center_x",
                "hip_center_y",
                "hip_center_z",
                "shoulder_center_x",
                "shoulder_center_y",
                "shoulder_center_z",
                "torso_length",
            ],
            errors="ignore",
        )

    report = {
        "method": "hip_centered_sequence_median_torso_scale",
        "num_frames": int(len(df)),
        "num_normalized_landmarks": int(len(landmarks)),
        "normalized_columns": [
            col
            for landmark in landmarks
            for col in _norm_coord_cols(landmark)
        ],
    }

    report.update(scale_report)

    return result, report


def check_normalization_result(
    norm_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Check basic properties of normalized pose data.

    Expected:
        - hip center should be approximately zero
        - median normalized torso length should be approximately 1
    """
    required_cols = [
        "left_hip_norm_x",
        "left_hip_norm_y",
        "left_hip_norm_z",
        "right_hip_norm_x",
        "right_hip_norm_y",
        "right_hip_norm_z",
        "left_shoulder_norm_x",
        "left_shoulder_norm_y",
        "left_shoulder_norm_z",
        "right_shoulder_norm_x",
        "right_shoulder_norm_y",
        "right_shoulder_norm_z",
    ]

    missing = [col for col in required_cols if col not in norm_df.columns]

    if missing:
        return {
            "passed": False,
            "error": "Missing normalized columns.",
            "missing_columns": missing,
        }

    hip_center_norm_x = (
        norm_df["left_hip_norm_x"] + norm_df["right_hip_norm_x"]
    ) / 2.0
    hip_center_norm_y = (
        norm_df["left_hip_norm_y"] + norm_df["right_hip_norm_y"]
    ) / 2.0
    hip_center_norm_z = (
        norm_df["left_hip_norm_z"] + norm_df["right_hip_norm_z"]
    ) / 2.0

    shoulder_center_norm_x = (
        norm_df["left_shoulder_norm_x"] + norm_df["right_shoulder_norm_x"]
    ) / 2.0
    shoulder_center_norm_y = (
        norm_df["left_shoulder_norm_y"] + norm_df["right_shoulder_norm_y"]
    ) / 2.0
    shoulder_center_norm_z = (
        norm_df["left_shoulder_norm_z"] + norm_df["right_shoulder_norm_z"]
    ) / 2.0

    dx = shoulder_center_norm_x - hip_center_norm_x
    dy = shoulder_center_norm_y - hip_center_norm_y
    dz = shoulder_center_norm_z - hip_center_norm_z

    norm_torso_length = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

    max_abs_hip_center = float(
        pd.concat(
            [
                hip_center_norm_x.abs(),
                hip_center_norm_y.abs(),
                hip_center_norm_z.abs(),
            ],
            axis=1,
        ).max().max()
    )

    median_norm_torso_length = float(norm_torso_length.median())

    return {
        "passed": bool(
            max_abs_hip_center < 1e-9
            and abs(median_norm_torso_length - 1.0) < 1e-6
        ),
        "max_abs_hip_center": max_abs_hip_center,
        "median_normalized_torso_length": median_norm_torso_length,
        "min_normalized_torso_length": float(norm_torso_length.min()),
        "max_normalized_torso_length": float(norm_torso_length.max()),
    }