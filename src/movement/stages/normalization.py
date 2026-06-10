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
    <landmark>_norm_z

Pipeline position: after ④ preprocessing, before optional floor-relative normalization filter
and ⑥ segmentation.
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

    result[output_col] = np.sqrt(dx**2 + dy**2 + dz**2)

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


def build_corrected_3d_hypothesis_report(
    enabled: bool = False,
    output_family: str = "corrected_3d_hypothesis",
    downstream_coordinate_mode: str = "norm",
    feature_depth_gravity: float = 0.0,
    emit_sensitivity_report: bool = True,
    support_pair: List[str] | None = None,
    report_burden_before_feature_use: bool = True,
    require_feature_domain_declaration: bool = True,
) -> Dict[str, Any]:
    """
    Build the normalization policy report for corrected-3D-hypothesis candidates.

    Biomechanical meaning:
        Corrected coordinates are low-confidence structure hypotheses for
        burden review, not calibrated 3D evidence or movement-quality scores.
    """
    feature_depth_gravity = float(feature_depth_gravity)
    if not np.isfinite(feature_depth_gravity):
        raise ValueError("feature_depth_gravity must be finite.")
    if feature_depth_gravity < 0.0 or feature_depth_gravity > 1.0:
        raise ValueError("feature_depth_gravity must be between 0.0 and 1.0.")

    downstream_coordinate_mode = str(downstream_coordinate_mode)
    if downstream_coordinate_mode not in {"norm", "corrected_3d_hypothesis"}:
        raise ValueError(
            "downstream_coordinate_mode must be 'norm' or " "'corrected_3d_hypothesis'."
        )

    output_family = str(output_family).strip()
    if not output_family:
        raise ValueError("output_family must be a non-empty string.")

    support_pair = list(support_pair or ["left_ankle", "right_ankle"])
    if len(support_pair) != 2:
        raise ValueError("support_pair must contain exactly two landmarks.")

    used_for_features_or_scores = bool(
        enabled
        and downstream_coordinate_mode == "corrected_3d_hypothesis"
        and feature_depth_gravity > 0.0
    )

    return {
        "enabled": bool(enabled),
        "output_family": output_family,
        "downstream_coordinate_mode": downstream_coordinate_mode,
        "feature_depth_gravity": feature_depth_gravity,
        "emit_sensitivity_report": bool(emit_sensitivity_report),
        "support_pair": [str(item) for item in support_pair],
        "used_for_features_or_scores": used_for_features_or_scores,
        "require_feature_domain_declaration": bool(require_feature_domain_declaration),
        "report_burden_before_feature_use": bool(report_burden_before_feature_use),
        "depth_evidence_policy": (
            "excluded_from_scoring"
            if feature_depth_gravity == 0.0
            else "feature_gated_low_confidence"
        ),
    }


def normalize_pose_by_hip_torso(
    df: pd.DataFrame,
    landmarks: List[str],
    min_scale: float = 1e-6,
    keep_reference_columns: bool = True,
    model_depth_scale: float = 1.0,
    corrected_3d_hypothesis: Dict[str, Any] | None = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Normalize pose coordinates using hip-centered translation and
    sequence-wise median torso scale.

    Formula:
        x/y_norm_i(t) = (x/y_i(t) - hip_center_x/y(t)) / median_torso_length
        z_norm_i(t) = ((z_i(t) - hip_center_z(t)) * model_depth_scale) / median_torso_length

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
    corrected_3d_hypothesis:
        Optional report policy for a separate corrected-3D-hypothesis candidate
        family. This function records the policy but does not create corrected
        coordinates.

    Returns
    -------
    norm_df:
        Dataframe with normalized coordinate columns added.
    report:
        Normalization report dictionary.
    """
    _check_landmark_columns(df, landmarks)

    result = add_body_reference_columns(df)

    model_depth_scale = float(model_depth_scale)
    if not np.isfinite(model_depth_scale) or model_depth_scale <= 0:
        raise ValueError("model_depth_scale must be a positive finite number.")

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
            (result[raw_cols[2]] - result["hip_center_z"]) * model_depth_scale
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
        "model_depth_scale": model_depth_scale,
        "normalized_columns": [
            col for landmark in landmarks for col in _norm_coord_cols(landmark)
        ],
    }
    corrected_policy = corrected_3d_hypothesis or {}
    report["corrected_3d_hypothesis"] = build_corrected_3d_hypothesis_report(
        enabled=bool(corrected_policy.get("enabled", False)),
        output_family=corrected_policy.get(
            "output_family",
            "corrected_3d_hypothesis",
        ),
        downstream_coordinate_mode=corrected_policy.get(
            "downstream_coordinate_mode",
            "norm",
        ),
        feature_depth_gravity=corrected_policy.get("feature_depth_gravity", 0.0),
        emit_sensitivity_report=bool(
            corrected_policy.get("emit_sensitivity_report", True)
        ),
        support_pair=corrected_policy.get(
            "support_pair",
            ["left_ankle", "right_ankle"],
        ),
        report_burden_before_feature_use=bool(
            corrected_policy.get("report_burden_before_feature_use", True)
        ),
        require_feature_domain_declaration=bool(
            corrected_policy.get("require_feature_domain_declaration", True)
        ),
    )

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

    hip_center_norm_x = (norm_df["left_hip_norm_x"] + norm_df["right_hip_norm_x"]) / 2.0
    hip_center_norm_y = (norm_df["left_hip_norm_y"] + norm_df["right_hip_norm_y"]) / 2.0
    hip_center_norm_z = (norm_df["left_hip_norm_z"] + norm_df["right_hip_norm_z"]) / 2.0

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
    }
