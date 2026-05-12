"""Floor-relative normalization filter for static support-contact exercises.

This module estimates an apparent pseudo-floor inside the normalized pose
coordinate system and attenuates only the floor-tilt component. It does not
calibrate the camera, recover an absolute floor plane, or force foot landmarks
to remain on the floor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


_DEFAULT_SUPPORT_LANDMARKS = [
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]


@dataclass
class FloorReferenceConfig:
    """Configuration for the floor-relative normalization filter.

    The output is a relative coordinate-standardization layer in
    torso-length-normalized pose space. It preserves raw/norm coordinates and
    emits diagnostic floor-height residuals so possible true heel lift or
    contact changes are not erased. Camera pitch/roll values define the target
    pose-coordinate pseudo-floor slope to preserve; they are not calibrated
    camera extrinsics.
    """

    enabled: bool = False
    method: str = "support_contact_plane"
    coordinate_mode: str = "norm"
    vertical_axis: str = "y"
    support_landmarks: list[str] = field(default_factory=list)
    diagnostic_landmarks: list[str] = field(default_factory=list)
    visibility_threshold: float = 0.7
    stability_window_frames: int = 5
    max_anchor_residual_torso: float = 0.08
    correction_transform: str = "rigid_rotation"
    camera_pitch_deg: float = 0.0
    camera_roll_deg: float = 0.0
    correction_strength: float = 1.0
    max_correction_torso: float = 0.25


@dataclass
class FloorReferenceReport:
    """Summary of the pseudo-floor fit and correction magnitude."""

    method: str = "support_contact_plane"
    enabled: bool = False
    status: str = "disabled"
    coordinate_mode: str = "norm"
    vertical_axis: str = "y"
    support_landmarks: list[str] = field(default_factory=list)
    diagnostic_landmarks: list[str] = field(default_factory=list)
    correction_transform: str = "rigid_rotation"
    num_anchor_points: int = 0
    num_anchor_frames: int = 0
    plane_coefficients: dict[str, float] = field(default_factory=dict)
    target_plane_coefficients: dict[str, float] = field(default_factory=dict)
    camera_pitch_deg: float = 0.0
    camera_roll_deg: float = 0.0
    correction_strength: float = 0.0
    effective_correction_strength: float = 0.0
    max_abs_correction: float = 0.0
    median_abs_correction: float = 0.0
    anchor_residual_summary: dict[str, float] = field(default_factory=dict)
    excluded_anchor_reasons: dict[str, list[str]] = field(default_factory=dict)
    confidence_notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "enabled": self.enabled,
            "status": self.status,
            "coordinate_mode": self.coordinate_mode,
            "vertical_axis": self.vertical_axis,
            "support_landmarks": self.support_landmarks,
            "diagnostic_landmarks": self.diagnostic_landmarks,
            "correction_transform": self.correction_transform,
            "num_anchor_points": self.num_anchor_points,
            "num_anchor_frames": self.num_anchor_frames,
            "plane_coefficients": self.plane_coefficients,
            "target_plane_coefficients": self.target_plane_coefficients,
            "camera_pitch_deg": self.camera_pitch_deg,
            "camera_roll_deg": self.camera_roll_deg,
            "correction_strength": self.correction_strength,
            "effective_correction_strength": self.effective_correction_strength,
            "max_abs_correction": self.max_abs_correction,
            "median_abs_correction": self.median_abs_correction,
            "anchor_residual_summary": self.anchor_residual_summary,
            "excluded_anchor_reasons": self.excluded_anchor_reasons,
            "confidence_notes": self.confidence_notes,
        }


def _coord_columns(landmark: str, coordinate_mode: str) -> dict[str, str]:
    if coordinate_mode == "raw":
        prefix = landmark
    elif coordinate_mode == "norm":
        prefix = f"{landmark}_norm"
    else:
        raise ValueError(
            "Floor-relative correction currently supports coordinate_mode "
            f"'raw' or 'norm', got '{coordinate_mode}'."
        )
    return {axis: f"{prefix}_{axis}" for axis in ("x", "y", "z")}


def _available_landmarks(
    df: pd.DataFrame,
    landmarks: list[str],
    coordinate_mode: str,
) -> list[str]:
    available = []
    for landmark in landmarks:
        cols = _coord_columns(landmark, coordinate_mode)
        if all(col in df.columns for col in cols.values()):
            available.append(landmark)
    return available


def _resolve_support_landmarks(
    df: pd.DataFrame,
    landmarks: list[str],
    config: FloorReferenceConfig,
) -> tuple[list[str], list[str]]:
    support = config.support_landmarks or [
        landmark for landmark in _DEFAULT_SUPPORT_LANDMARKS if landmark in landmarks
    ]
    diagnostic = config.diagnostic_landmarks or support
    support = _available_landmarks(df, support, config.coordinate_mode)
    diagnostic = _available_landmarks(df, diagnostic, config.coordinate_mode)
    return support, diagnostic


def _horizontal_axes(vertical_axis: str) -> tuple[str, str]:
    if vertical_axis not in {"x", "y", "z"}:
        raise ValueError(
            f"Unsupported vertical_axis='{vertical_axis}'. Use one of x, y, z."
        )
    axes = [axis for axis in ("x", "y", "z") if axis != vertical_axis]
    return axes[0], axes[1]


def _fit_plane(
    points: np.ndarray,
    vertical_axis: str,
) -> tuple[np.ndarray, np.ndarray]:
    h1_axis, h2_axis = _horizontal_axes(vertical_axis)
    axis_index = {"x": 0, "y": 1, "z": 2}
    h1 = points[:, axis_index[h1_axis]]
    h2 = points[:, axis_index[h2_axis]]
    v = points[:, axis_index[vertical_axis]]
    design = np.column_stack([np.ones(len(points)), h1, h2])
    coeffs, *_ = np.linalg.lstsq(design, v, rcond=None)
    residuals = v - design @ coeffs
    return coeffs.astype(float), residuals.astype(float)


def _plane_values(
    h1_values: np.ndarray,
    h2_values: np.ndarray,
    coeffs: np.ndarray,
) -> np.ndarray:
    return coeffs[0] + coeffs[1] * h1_values + coeffs[2] * h2_values


def _plane_normal(coeffs: np.ndarray, vertical_axis: str) -> np.ndarray:
    h1_axis, h2_axis = _horizontal_axes(vertical_axis)
    axis_index = {"x": 0, "y": 1, "z": 2}
    normal = np.zeros(3, dtype=float)
    normal[axis_index[vertical_axis]] = 1.0
    normal[axis_index[h1_axis]] = -float(coeffs[1])
    normal[axis_index[h2_axis]] = -float(coeffs[2])
    norm = np.linalg.norm(normal)
    if norm == 0:
        raise ValueError("Cannot compute pseudo-floor normal from zero vector.")
    return normal / norm


def _angle_deg_to_slope(angle_deg: float, name: str) -> float:
    angle = float(angle_deg)
    if not np.isfinite(angle):
        raise ValueError(f"{name} must be finite, got {angle_deg!r}.")
    if abs(angle) >= 89.0:
        raise ValueError(
            f"{name}={angle} is too steep for floor-relative correction. "
            "Use a value between -89 and 89 degrees."
        )
    return float(np.tan(np.deg2rad(angle)))


def _target_plane_coefficients(
    intercept: float,
    config: FloorReferenceConfig,
) -> np.ndarray:
    """Return the pose-coordinate floor target implied by camera-angle priors."""
    # For the default vertical_axis="y", h1 is x (roll) and h2 is z (pitch).
    return np.asarray(
        [
            float(intercept),
            _angle_deg_to_slope(config.camera_roll_deg, "camera_roll_deg"),
            _angle_deg_to_slope(config.camera_pitch_deg, "camera_pitch_deg"),
        ],
        dtype=float,
    )


def _rotation_matrix_between(
    source_normal: np.ndarray,
    target_normal: np.ndarray,
    strength: float,
) -> np.ndarray:
    source = source_normal / np.linalg.norm(source_normal)
    target = target_normal / np.linalg.norm(target_normal)
    dot = float(np.clip(np.dot(source, target), -1.0, 1.0))

    if np.isclose(dot, 1.0):
        return np.eye(3)

    axis = np.cross(source, target)
    axis_norm = float(np.linalg.norm(axis))
    if np.isclose(axis_norm, 0.0):
        basis = np.eye(3)
        axis = basis[int(np.argmin(np.abs(source)))]
        axis = axis - source * np.dot(axis, source)
        axis_norm = float(np.linalg.norm(axis))

    axis = axis / axis_norm
    angle = float(np.arccos(dot)) * float(strength)
    kx = np.asarray(
        [
            [0.0, -axis[2], axis[1]],
            [axis[2], 0.0, -axis[0]],
            [-axis[1], axis[0], 0.0],
        ],
        dtype=float,
    )
    return np.eye(3) + np.sin(angle) * kx + (1.0 - np.cos(angle)) * (kx @ kx)


def _plane_origin_pivot(coeffs: np.ndarray, vertical_axis: str) -> np.ndarray:
    axis_index = {"x": 0, "y": 1, "z": 2}
    pivot = np.zeros(3, dtype=float)
    pivot[axis_index[vertical_axis]] = float(coeffs[0])
    return pivot


def _summarize_abs(values: np.ndarray) -> dict[str, float]:
    if len(values) == 0:
        return {"median": 0.0, "p90": 0.0, "max": 0.0}
    abs_values = np.abs(values)
    return {
        "median": float(np.nanmedian(abs_values)),
        "p90": float(np.nanpercentile(abs_values, 90)),
        "max": float(np.nanmax(abs_values)),
    }


def _safe_nanmax(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return 0.0
    return float(np.max(finite))


def _empty_report(config: FloorReferenceConfig, status: str) -> FloorReferenceReport:
    return FloorReferenceReport(
        method=config.method,
        enabled=config.enabled,
        status=status,
        coordinate_mode=config.coordinate_mode,
        vertical_axis=config.vertical_axis,
        support_landmarks=list(config.support_landmarks),
        diagnostic_landmarks=list(config.diagnostic_landmarks),
        correction_transform=config.correction_transform,
        camera_pitch_deg=float(config.camera_pitch_deg),
        camera_roll_deg=float(config.camera_roll_deg),
        correction_strength=float(config.correction_strength),
        effective_correction_strength=float(config.correction_strength),
    )


def _collect_anchor_points(
    df: pd.DataFrame,
    support_landmarks: list[str],
    config: FloorReferenceConfig,
) -> tuple[np.ndarray, np.ndarray, dict[str, list[str]], list[str]]:
    points: list[list[float]] = []
    frame_ids: list[int] = []
    excluded: dict[str, list[str]] = {}
    notes: list[str] = []

    for landmark in support_landmarks:
        cols = _coord_columns(landmark, config.coordinate_mode)
        values = df[[cols["x"], cols["y"], cols["z"]]].astype(float)
        valid = values.notna().all(axis=1)

        visibility_col = f"{landmark}_visibility"
        if visibility_col in df.columns:
            valid &= df[visibility_col].astype(float) >= config.visibility_threshold
        else:
            notes.append(
                f"{landmark}: visibility column missing; visibility filter skipped"
            )

        if not bool(valid.any()):
            excluded.setdefault(landmark, []).append("no_visible_frames")
            continue

        selected = values.loc[valid]
        points.extend(selected.to_numpy(dtype=float).tolist())
        frame_ids.extend(selected.index.to_list())

    if not points:
        return np.empty((0, 3), dtype=float), np.array([], dtype=int), excluded, notes

    return (
        np.asarray(points, dtype=float),
        np.asarray(frame_ids, dtype=int),
        excluded,
        notes,
    )


def apply_floor_relative_correction(
    df: pd.DataFrame,
    landmarks: list[str],
    config: FloorReferenceConfig | None = None,
) -> tuple[pd.DataFrame, FloorReferenceReport]:
    """Apply optional support-contact pseudo-floor correction.

    Parameters
    ----------
    df : pd.DataFrame
        Pose dataframe after ⑤ Normalization when coordinate_mode="norm".
    landmarks : list[str]
        Landmark names to receive `<landmark>_floor_x/y/z` columns. The
        fitted support-contact plane is applied to every requested landmark,
        not only to the foot anchors used for fitting.
    config : FloorReferenceConfig, optional
        Correction settings. Disabled configs return a copy with a disabled report.

    Returns
    -------
    df : pd.DataFrame
        Copy of the input with floor coordinate and diagnostic columns if applied.
    report : FloorReferenceReport
        Fit status, plane coefficients, correction magnitude, and confidence notes.
    """
    if config is None:
        config = FloorReferenceConfig()

    result = df.copy()
    if not config.enabled:
        return result, _empty_report(config, "disabled")

    if config.method != "support_contact_plane":
        raise ValueError(
            "Unsupported floor-relative correction method: "
            f"{config.method!r}. Use 'support_contact_plane'."
        )
    if config.correction_transform not in {"rigid_rotation", "vertical_shear"}:
        raise ValueError(
            "Unsupported floor-relative correction_transform: "
            f"{config.correction_transform!r}. Use 'rigid_rotation' or "
            "'vertical_shear'."
        )

    support_landmarks, diagnostic_landmarks = _resolve_support_landmarks(
        result, landmarks, config
    )
    report = FloorReferenceReport(
        method=config.method,
        enabled=True,
        status="skipped",
        coordinate_mode=config.coordinate_mode,
        vertical_axis=config.vertical_axis,
        support_landmarks=support_landmarks,
        diagnostic_landmarks=diagnostic_landmarks,
        correction_transform=config.correction_transform,
        camera_pitch_deg=float(config.camera_pitch_deg),
        camera_roll_deg=float(config.camera_roll_deg),
        correction_strength=float(config.correction_strength),
        effective_correction_strength=float(config.correction_strength),
    )

    if not support_landmarks:
        report.confidence_notes.append(
            "No support landmarks with required coordinates."
        )
        return result, report

    missing_for_all = []
    for landmark in landmarks:
        cols = _coord_columns(landmark, config.coordinate_mode)
        missing_for_all.extend(
            col for col in cols.values() if col not in result.columns
        )
    if missing_for_all:
        raise ValueError(
            "Floor-relative correction requires complete coordinate columns for all "
            f"requested landmarks. Missing: {missing_for_all[:10]}"
        )

    points, frame_ids, excluded, notes = _collect_anchor_points(
        result, support_landmarks, config
    )
    report.excluded_anchor_reasons = excluded
    report.confidence_notes.extend(notes)

    if len(points) < 3:
        report.confidence_notes.append("Too few valid anchor points for plane fitting.")
        return result, report

    coeffs_initial, residuals_initial = _fit_plane(points, config.vertical_axis)
    keep = np.abs(residuals_initial) <= config.max_anchor_residual_torso
    n_high_residual = int((~keep).sum())
    if n_high_residual:
        report.excluded_anchor_reasons.setdefault("_residual_filter", []).append(
            f"{n_high_residual} anchor points exceeded max_anchor_residual_torso"
        )

    if int(keep.sum()) >= 3:
        points_fit = points[keep]
        frame_ids_fit = frame_ids[keep]
        coeffs, residuals = _fit_plane(points_fit, config.vertical_axis)
    else:
        points_fit = points
        frame_ids_fit = frame_ids
        coeffs = coeffs_initial
        residuals = residuals_initial
        report.confidence_notes.append(
            "Initial residual filter left too few anchors; used unfiltered fit."
        )

    h1_axis, h2_axis = _horizontal_axes(config.vertical_axis)
    target_coeffs = _target_plane_coefficients(float(coeffs[0]), config)
    report.num_anchor_points = int(len(points_fit))
    report.num_anchor_frames = int(len(set(frame_ids_fit.tolist())))
    report.plane_coefficients = {
        "b0": float(coeffs[0]),
        f"b{h1_axis}": float(coeffs[1]),
        f"b{h2_axis}": float(coeffs[2]),
    }
    report.target_plane_coefficients = {
        "b0": float(target_coeffs[0]),
        f"b{h1_axis}": float(target_coeffs[1]),
        f"b{h2_axis}": float(target_coeffs[2]),
    }
    report.anchor_residual_summary = _summarize_abs(residuals)

    axis_index = {"x": 0, "y": 1, "z": 2}
    vertical_axis = config.vertical_axis
    alpha = float(config.correction_strength)
    max_correction = float(config.max_correction_torso)
    all_abs_corrections: list[np.ndarray] = []
    frame_abs_correction = np.zeros(len(result), dtype=float)
    output_columns: dict[str, Any] = {}

    if config.correction_transform == "vertical_shear":
        report.effective_correction_strength = alpha
        for landmark in landmarks:
            cols = _coord_columns(landmark, config.coordinate_mode)
            coords = result[[cols["x"], cols["y"], cols["z"]]].to_numpy(dtype=float)
            h1 = coords[:, axis_index[h1_axis]]
            h2 = coords[:, axis_index[h2_axis]]
            observed_plane = _plane_values(h1, h2, coeffs)
            target_plane = _plane_values(h1, h2, target_coeffs)
            tilt = observed_plane - target_plane
            correction = alpha * tilt
            correction_clipped = np.clip(correction, -max_correction, max_correction)

            if _safe_nanmax(np.abs(correction)) > max_correction:
                report.status = "warning"

            corrected = coords.copy()
            corrected[:, axis_index[vertical_axis]] = (
                corrected[:, axis_index[vertical_axis]] - correction_clipped
            )

            for axis in ("x", "y", "z"):
                output_columns[f"{landmark}_floor_{axis}"] = corrected[
                    :, axis_index[axis]
                ]

            abs_correction = np.abs(correction_clipped)
            all_abs_corrections.append(abs_correction)
            frame_abs_correction = np.maximum(frame_abs_correction, abs_correction)
    else:
        rotation_strength = float(np.clip(alpha, 0.0, 1.0))
        if not np.isclose(rotation_strength, alpha):
            report.confidence_notes.append(
                "Rigid rotation correction_strength was clipped to [0, 1]."
            )

        observed_normal = _plane_normal(coeffs, vertical_axis)
        target_normal = _plane_normal(target_coeffs, vertical_axis)
        pivot = _plane_origin_pivot(coeffs, vertical_axis)

        def _rotated_outputs(
            strength: float,
        ) -> tuple[dict[str, np.ndarray], list[np.ndarray], np.ndarray]:
            rotation = _rotation_matrix_between(
                observed_normal,
                target_normal,
                strength,
            )
            corrected_by_landmark: dict[str, np.ndarray] = {}
            abs_by_landmark: list[np.ndarray] = []
            frame_abs = np.zeros(len(result), dtype=float)

            for name in landmarks:
                cols = _coord_columns(name, config.coordinate_mode)
                coords = result[[cols["x"], cols["y"], cols["z"]]].to_numpy(dtype=float)
                corrected = (coords - pivot) @ rotation.T + pivot
                vertical_delta = (
                    coords[:, axis_index[vertical_axis]]
                    - corrected[:, axis_index[vertical_axis]]
                )
                abs_correction = np.abs(vertical_delta)
                corrected_by_landmark[name] = corrected
                abs_by_landmark.append(abs_correction)
                frame_abs = np.maximum(frame_abs, abs_correction)

            return corrected_by_landmark, abs_by_landmark, frame_abs

        corrected_by_landmark, all_abs_corrections, frame_abs_correction = (
            _rotated_outputs(rotation_strength)
        )
        correction_values_preview = np.concatenate(all_abs_corrections)
        max_preview = _safe_nanmax(correction_values_preview)
        if max_preview > max_correction:
            report.status = "warning"
            if max_correction > 0.0 and rotation_strength > 0.0:
                rotation_strength *= max_correction / max_preview
                corrected_by_landmark, all_abs_corrections, frame_abs_correction = (
                    _rotated_outputs(rotation_strength)
                )
                report.confidence_notes.append(
                    "Rigid rotation strength was reduced to respect "
                    "max_correction_torso."
                )
            else:
                rotation_strength = 0.0
                corrected_by_landmark, all_abs_corrections, frame_abs_correction = (
                    _rotated_outputs(rotation_strength)
                )
                report.confidence_notes.append(
                    "Rigid rotation skipped because max_correction_torso is zero."
                )

        report.effective_correction_strength = float(rotation_strength)
        for landmark, corrected in corrected_by_landmark.items():
            for axis in ("x", "y", "z"):
                output_columns[f"{landmark}_floor_{axis}"] = corrected[
                    :, axis_index[axis]
                ]

    for landmark in diagnostic_landmarks:
        cols = _coord_columns(landmark, config.coordinate_mode)
        coords = result[[cols["x"], cols["y"], cols["z"]]].to_numpy(dtype=float)
        h1 = coords[:, axis_index[h1_axis]]
        h2 = coords[:, axis_index[h2_axis]]
        plane = _plane_values(h1, h2, coeffs)
        output_columns[f"{landmark}_floor_height"] = (
            coords[:, axis_index[vertical_axis]] - plane
        )

    correction_values = np.concatenate(all_abs_corrections)
    finite_corrections = correction_values[np.isfinite(correction_values)]
    report.max_abs_correction = _safe_nanmax(correction_values)
    report.median_abs_correction = (
        float(np.median(finite_corrections)) if len(finite_corrections) else 0.0
    )
    if report.status != "warning":
        report.status = "applied"
    else:
        report.confidence_notes.append(
            "Correction exceeded max_correction_torso and was clipped."
        )

    output_columns["floor_reference_valid"] = report.status in {"applied", "warning"}
    output_columns["floor_reference_note"] = "; ".join(report.confidence_notes)
    output_columns["floor_correction_applied"] = True
    output_columns["floor_correction_transform"] = config.correction_transform
    output_columns["floor_correction_strength"] = alpha
    output_columns["floor_correction_effective_strength"] = (
        report.effective_correction_strength
    )
    output_columns["floor_correction_max_abs"] = report.max_abs_correction
    output_columns["floor_correction_abs_frame"] = frame_abs_correction

    result = pd.concat(
        [result, pd.DataFrame(output_columns, index=result.index)], axis=1
    )

    return result, report
