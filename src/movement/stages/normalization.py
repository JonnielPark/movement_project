"""
⑤ Normalization

Converts raw pose coordinates into a body-relative coordinate system,
removing camera position, subject position, and body size effects.

Method (hip_torso):
    Translation reference : frame-wise hip center
Scale reference       : sequence-wise median torso length
Model-depth gain      : optional z residual scale before torso normalization

Raw coordinates are preserved. Normalized coordinates are added as new columns:
    <landmark>_norm_x
    <landmark>_norm_y
    <landmark>_norm_z  (NaN placeholder when z evidence is unavailable)

Pipeline position: after ④ preprocessing, before optional ⑤-1 canonicalization
filters and ⑥ segmentation.
"""

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from movement.pose_data_state import (
    NORM_COORDINATE_FAMILY,
    NORMALIZED_POSE_DATA,
    RAW_COORDINATE_FAMILY,
    get_coordinate_axes,
    get_coordinate_families,
    get_pose_data_state,
    set_pose_data_state,
)

_AXES_XY = ("x", "y")
_AXES_XYZ = ("x", "y", "z")


def _coord_cols(landmark: str, axes: tuple[str, ...] = _AXES_XYZ) -> List[str]:
    """
    Return coordinate column names for a landmark.
    """
    return [f"{landmark}_{axis}" for axis in axes]


def _norm_coord_cols(landmark: str, axes: tuple[str, ...] = _AXES_XYZ) -> List[str]:
    """
    Return normalized coordinate column names for a landmark.
    """
    return [f"{landmark}_norm_{axis}" for axis in axes]


def _available_axes(
    df: pd.DataFrame,
    landmarks: list[str],
    z_source: str,
) -> tuple[str, ...]:
    axes: list[str] = []
    for axis in _AXES_XYZ:
        columns = [f"{landmark}_{axis}" for landmark in landmarks]
        if not all(column in df.columns for column in columns):
            continue
        if axis == "z":
            if z_source != "model_depth":
                continue
            values = df[columns].astype(float).to_numpy()
            if not np.isfinite(values).any():
                continue
        axes.append(axis)
    return tuple(axes)


def _ensure_raw_z_placeholders(
    df: pd.DataFrame,
    landmarks: list[str],
) -> pd.DataFrame:
    """Return a copy with missing raw z columns added as NaN placeholders."""

    missing = [f"{landmark}_z" for landmark in landmarks if f"{landmark}_z" not in df]
    if not missing:
        return df.copy()
    result = df.copy()
    for column in missing:
        result[column] = np.nan
    return result


def _raw_z_source(
    df: pd.DataFrame,
    landmarks: list[str],
) -> str:
    attr_z_source = getattr(df, "attrs", {}).get("z_source")
    if isinstance(attr_z_source, dict):
        source = attr_z_source.get(RAW_COORDINATE_FAMILY)
        if source in {"absent", "model_depth", "partial_model_depth"}:
            return str(source)

    z_columns = [f"{landmark}_z" for landmark in landmarks]
    existing_z = [column for column in z_columns if column in df.columns]
    if not existing_z:
        return "absent"
    values = df[existing_z].astype(float).to_numpy()
    if not np.isfinite(values).any():
        return "absent"
    if len(existing_z) == len(z_columns):
        return "model_depth"
    return "partial_model_depth"


def _resolve_coordinate_axes(
    df: pd.DataFrame,
    landmarks: list[str],
    coordinate_axes: str = "auto",
    z_source: str = "absent",
) -> tuple[str, ...]:
    mode = str(coordinate_axes or "auto").lower()
    if mode not in {"auto", "xy", "xyz"}:
        raise ValueError("coordinate_axes must be one of: auto, xy, xyz.")

    available = _available_axes(df, landmarks, z_source)
    if mode == "xy":
        axes = _AXES_XY
    elif mode == "xyz":
        if z_source != "model_depth" or "z" not in available:
            raise ValueError(
                "coordinate_axes='xyz' requires finite backend-provided z evidence."
            )
        axes = _AXES_XYZ
    elif all(axis in available for axis in _AXES_XYZ):
        axes = _AXES_XYZ
    elif all(axis in available for axis in _AXES_XY):
        axes = _AXES_XY
    else:
        raise ValueError(
            "Cannot resolve normalization coordinate axes from input columns."
        )

    missing = [
        f"{landmark}_{axis}"
        for landmark in landmarks
        for axis in axes
        if f"{landmark}_{axis}" not in df.columns
    ]
    if missing:
        raise ValueError(
            "Missing landmark coordinate columns for coordinate_axes={}: {}".format(
                mode,
                missing,
            )
        )
    return axes


def _check_landmark_columns(
    df: pd.DataFrame,
    landmarks: List[str],
    axes: tuple[str, ...] = _AXES_XYZ,
) -> None:
    """
    Raise ValueError if required landmark coordinate columns are missing.
    """
    missing_columns = []

    for landmark in landmarks:
        for col in _coord_cols(landmark, axes):
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
    axes: tuple[str, ...] = _AXES_XYZ,
) -> pd.DataFrame:
    """
    Compute midpoint between two landmarks and add it to the dataframe.

    Output columns:
        <output_prefix>_x
        <output_prefix>_y
        <output_prefix>_z when z is included in axes
    """
    result = df.copy()

    a_cols = _coord_cols(landmark_a, axes)
    b_cols = _coord_cols(landmark_b, axes)

    for axis, a_col, b_col in zip(axes, a_cols, b_cols):
        result["{}_{}".format(output_prefix, axis)] = (
            result[a_col] + result[b_col]
        ) / 2.0

    return result


def compute_distance_between_prefixes(
    df: pd.DataFrame,
    prefix_a: str,
    prefix_b: str,
    output_col: str,
    axes: tuple[str, ...] = _AXES_XYZ,
) -> pd.DataFrame:
    """
    Compute Euclidean distance between two points defined by column prefixes.

    Example:
        prefix_a = "hip_center"
        prefix_b = "shoulder_center"

        Required columns:
            hip_center_x/y(/z)
            shoulder_center_x/y(/z)
    """
    result = df.copy()

    distance_sq = np.zeros(len(result), dtype=float)
    for axis in axes:
        delta = result[f"{prefix_a}_{axis}"] - result[f"{prefix_b}_{axis}"]
        distance_sq += delta**2

    result[output_col] = np.sqrt(distance_sq)

    return result


def add_body_reference_columns(
    df: pd.DataFrame,
    axes: tuple[str, ...] = _AXES_XYZ,
) -> pd.DataFrame:
    """
    Add hip center, shoulder center, and torso length columns.

    Added columns:
        hip_center_x/y(/z)
        shoulder_center_x/y(/z)
        torso_length
    """
    required = [
        "left_hip",
        "right_hip",
        "left_shoulder",
        "right_shoulder",
    ]
    _check_landmark_columns(df, required, axes)

    result = df.copy()

    result = compute_midpoint(
        result,
        landmark_a="left_hip",
        landmark_b="right_hip",
        output_prefix="hip_center",
        axes=axes,
    )

    result = compute_midpoint(
        result,
        landmark_a="left_shoulder",
        landmark_b="right_shoulder",
        output_prefix="shoulder_center",
        axes=axes,
    )

    result = compute_distance_between_prefixes(
        result,
        prefix_a="hip_center",
        prefix_b="shoulder_center",
        output_col="torso_length",
        axes=axes,
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
        raise ValueError("Missing torso length column: {}".format(torso_length_col))

    torso = df[torso_length_col].astype(float)

    valid_mask = torso.notna() & np.isfinite(torso) & (torso > min_scale)

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
    model_depth_scale: float = 1.0,
    coordinate_axes: str = "auto",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Normalize pose coordinates using hip-centered translation and
    sequence-wise median torso scale.

    Formula:
        x/y_norm_i(t) = (x/y_i(t) - hip_center_x/y(t)) / median_torso_length
        z_norm_i(t) = ((z_i(t) - hip_center_z(t)) * model_depth_scale) / median_torso_length
        when z exists in the selected input axes.

    Biomechanical meaning:
        Keeps coordinates body-relative while allowing review runs to attenuate
        low-confidence monocular model depth without changing recording-plane
        x/y evidence.

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
    model_depth_scale:
        Multiplicative gain for translated model-depth residuals. Default 1.0
        preserves legacy behavior; values below 1.0 attenuate <landmark>_norm_z.
    coordinate_axes:
        auto, xy, or xyz. xy keeps x/y as the selected evidence axes and emits
        <landmark>_norm_z as a NaN placeholder.
    Returns
    -------
    norm_df:
        Dataframe with normalized coordinate columns added.
    report:
        Normalization report dictionary.
    """
    z_source = _raw_z_source(df, landmarks)
    df = _ensure_raw_z_placeholders(df, landmarks)
    evidence_axes = _resolve_coordinate_axes(
        df,
        landmarks,
        coordinate_axes,
        z_source=z_source,
    )
    output_axes = _AXES_XYZ
    _check_landmark_columns(df, landmarks, output_axes)
    input_pose_data_state = get_pose_data_state(df)
    input_coordinate_families = get_coordinate_families(df)
    input_coordinate_axes = get_coordinate_axes(df)
    if RAW_COORDINATE_FAMILY not in input_coordinate_axes:
        input_coordinate_axes[RAW_COORDINATE_FAMILY] = list(output_axes)

    result = add_body_reference_columns(df, evidence_axes)

    model_depth_scale = float(model_depth_scale)
    if not np.isfinite(model_depth_scale) or model_depth_scale <= 0:
        raise ValueError("model_depth_scale must be a positive finite number.")

    scale_value, scale_report = compute_sequence_median_scale(
        result,
        torso_length_col="torso_length",
        min_scale=min_scale,
    )

    normalized_data = {}
    z_evaluable = "z" in evidence_axes and z_source == "model_depth"

    for landmark in landmarks:
        raw_cols = _coord_cols(landmark, output_axes)
        norm_cols = _norm_coord_cols(landmark, output_axes)

        normalized_data[norm_cols[0]] = (
            result[raw_cols[0]] - result["hip_center_x"]
        ) / scale_value

        normalized_data[norm_cols[1]] = (
            result[raw_cols[1]] - result["hip_center_y"]
        ) / scale_value

        if "z" in evidence_axes:
            normalized_data[norm_cols[2]] = (
                (result[raw_cols[2]] - result["hip_center_z"]) * model_depth_scale
            ) / scale_value
        else:
            normalized_data[norm_cols[2]] = np.nan

    normalized_df = pd.DataFrame(
        normalized_data,
        index=result.index,
    )

    result = pd.concat([result, normalized_df], axis=1)
    result = result.copy()
    output_coordinate_families = list(input_coordinate_families)
    if NORM_COORDINATE_FAMILY not in output_coordinate_families:
        output_coordinate_families.append(NORM_COORDINATE_FAMILY)
    output_coordinate_axes = dict(input_coordinate_axes)
    output_coordinate_axes[RAW_COORDINATE_FAMILY] = list(output_axes)
    output_coordinate_axes[NORM_COORDINATE_FAMILY] = list(output_axes)
    set_pose_data_state(
        result,
        NORMALIZED_POSE_DATA,
        output_coordinate_families,
        output_coordinate_axes,
    )

    if not keep_reference_columns:
        reference_columns = (
            [f"hip_center_{axis}" for axis in evidence_axes]
            + [f"shoulder_center_{axis}" for axis in evidence_axes]
            + ["torso_length"]
        )
        result = result.drop(columns=reference_columns, errors="ignore")
        set_pose_data_state(
            result,
            NORMALIZED_POSE_DATA,
            output_coordinate_families,
            output_coordinate_axes,
        )

    report = {
        "method": "hip_centered_sequence_median_torso_scale",
        "input_pose_data_state": input_pose_data_state,
        "output_pose_data_state": NORMALIZED_POSE_DATA,
        "input_coordinate_families": input_coordinate_families,
        "output_coordinate_families": output_coordinate_families,
        "input_coordinate_axes": input_coordinate_axes,
        "output_coordinate_axes": output_coordinate_axes,
        "added_coordinate_family": NORM_COORDINATE_FAMILY,
        "normalized_axes": list(output_axes),
        "normalized_evidence_axes": list(evidence_axes),
        "z_axis_policy": (
            "preserved_model_depth" if "z" in evidence_axes else "nan_placeholder"
        ),
        "z_source": z_source,
        "z_evaluable": z_evaluable,
        "num_frames": int(len(df)),
        "num_normalized_landmarks": int(len(landmarks)),
        "model_depth_scale": model_depth_scale,
        "normalized_columns": [
            col
            for landmark in landmarks
            for col in _norm_coord_cols(landmark, output_axes)
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
    z_cols = [
        "left_hip_norm_z",
        "right_hip_norm_z",
        "left_shoulder_norm_z",
        "right_shoulder_norm_z",
    ]
    has_z_columns = all(col in norm_df.columns for col in z_cols)
    has_z_evidence = False
    if has_z_columns:
        z_values = norm_df[z_cols].astype(float).to_numpy()
        has_z_evidence = bool(np.isfinite(z_values).any())
    required_cols = [
        "left_hip_norm_x",
        "left_hip_norm_y",
        "right_hip_norm_x",
        "right_hip_norm_y",
        "left_shoulder_norm_x",
        "left_shoulder_norm_y",
        "right_shoulder_norm_x",
        "right_shoulder_norm_y",
    ]
    if has_z_columns:
        required_cols.extend(z_cols)

    missing = [col for col in required_cols if col not in norm_df.columns]

    if missing:
        return {
            "passed": False,
            "error": "Missing normalized columns.",
            "missing_columns": missing,
        }

    hip_center_norm_x = (norm_df["left_hip_norm_x"] + norm_df["right_hip_norm_x"]) / 2.0
    hip_center_norm_y = (norm_df["left_hip_norm_y"] + norm_df["right_hip_norm_y"]) / 2.0
    if has_z_evidence:
        hip_center_norm_z = (
            norm_df["left_hip_norm_z"] + norm_df["right_hip_norm_z"]
        ) / 2.0
    else:
        hip_center_norm_z = pd.Series(0.0, index=norm_df.index)

    shoulder_center_norm_x = (
        norm_df["left_shoulder_norm_x"] + norm_df["right_shoulder_norm_x"]
    ) / 2.0
    shoulder_center_norm_y = (
        norm_df["left_shoulder_norm_y"] + norm_df["right_shoulder_norm_y"]
    ) / 2.0
    if has_z_evidence:
        shoulder_center_norm_z = (
            norm_df["left_shoulder_norm_z"] + norm_df["right_shoulder_norm_z"]
        ) / 2.0
    else:
        shoulder_center_norm_z = pd.Series(0.0, index=norm_df.index)

    dx = shoulder_center_norm_x - hip_center_norm_x
    dy = shoulder_center_norm_y - hip_center_norm_y
    dz = shoulder_center_norm_z - hip_center_norm_z

    norm_torso_length = np.sqrt(dx**2 + dy**2 + dz**2)

    max_abs_hip_center = float(
        pd.concat(
            [
                hip_center_norm_x.abs(),
                hip_center_norm_y.abs(),
                hip_center_norm_z.abs(),
            ],
            axis=1,
        )
        .max()
        .max()
    )

    median_norm_torso_length = float(norm_torso_length.median())

    return {
        "passed": bool(
            max_abs_hip_center < 1e-9 and abs(median_norm_torso_length - 1.0) < 1e-6
        ),
        "max_abs_hip_center": max_abs_hip_center,
        "median_normalized_torso_length": median_norm_torso_length,
        "min_normalized_torso_length": float(norm_torso_length.min()),
        "max_normalized_torso_length": float(norm_torso_length.max()),
        "normalized_axes": ["x", "y", "z"] if has_z_columns else ["x", "y"],
        "normalized_evidence_axes": (["x", "y", "z"] if has_z_evidence else ["x", "y"]),
    }
