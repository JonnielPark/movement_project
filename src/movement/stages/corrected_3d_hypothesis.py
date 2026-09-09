"""Corrected-3D-hypothesis analysis-evidence helpers.

Corrected coordinates are low-confidence structural hypotheses. This module
emits availability, quality gravity, and norm-vs-analysis sensitivity evidence.
Raw burden and residual values are retained as review diagnostics.
It does not create a good-movement template, calibrated 3D reconstruction, or
final-score contribution.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd


_VALID_AXES = {"x", "y", "z"}
_DEFAULT_SEGMENT_PAIRS = (
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
)
_QUALITY_GRAVITY_BY_CONFIDENCE = {
    "high": 1.0,
    "moderate": 0.5,
    "low": 0.1,
    "very_low": 0.05,
    "not_available": 0.0,
}


@dataclass(frozen=True)
class CorrectionPriorConfig:
    """Switch and merge metadata for one corrected-coordinate prior.

    The prior describes an engineering constraint that may improve monocular
    pose evidence. It does not encode a good-movement template or a score.
    """

    name: str
    enabled: bool = False
    scope: str = "all"
    priority: str = "secondary"
    weight: float = 1.0
    report_only: bool = False
    confidence_policy: str = "burden_penalty"


@dataclass(frozen=True)
class RadialXYRelaxationConfig:
    """Bounded radial xy candidate generator for weak lens-distortion evidence."""

    enabled: bool = False
    preset: str = "off"
    model: str = "radial_k1"
    direction: str = "pincushion"
    center_source: str = "frame_center"
    max_xy_shift_torso: float = 0.02
    radial_strength: float = 0.25
    max_iterations: int = 5
    convergence_epsilon: float = 0.001
    accept_only_if_residual_improves: bool = True


@dataclass(frozen=True)
class Corrected3DCoordinateSolverConfig:
    """Configuration for optional corrected-3D-hypothesis coordinate generation."""

    enabled: bool = False
    source_family: str = "norm"
    output_family: str = "corrected_3d_hypothesis"
    segment_pairs: tuple[tuple[str, str], ...] = _DEFAULT_SEGMENT_PAIRS
    default_segment_length_torso: float = 1.0
    segment_lengths_torso: Mapping[str, float] = field(default_factory=dict)
    max_depth_torso: float = 0.75
    max_z_correction_torso: float = 0.50
    confidence_threshold: float = 0.5
    correction_priors: tuple[CorrectionPriorConfig, ...] = field(default_factory=tuple)
    radial_xy_relaxation: RadialXYRelaxationConfig = field(
        default_factory=RadialXYRelaxationConfig
    )


@dataclass(frozen=True)
class SupportWidthStabilityConfig:
    """Configuration for support-width analysis-evidence sensitivity audit.

    The metric checks whether a closed-chain support pair stays stable across
    frames. The result is data-confidence evidence, not a movement-quality score
    contribution.
    """

    feature_id: str = "analysis.support_width_stability"
    evaluation_domain: str = "corrected_3d_hypothesis"
    norm_family: str = "norm"
    coordinate_family: str = "corrected_3d_hypothesis"
    support_pair: tuple[str, str] = ("left_ankle", "right_ankle")
    norm_axes: tuple[str, ...] = ("x", "y")
    coordinate_axes: tuple[str, ...] = ("x", "y", "z")
    low_percentile: float = 5.0
    high_percentile: float = 95.0
    high_burden_threshold: float = 0.80
    not_assessed_burden_threshold: float = 1.00


@dataclass
class Corrected3DHypothesisResult:
    """Container for corrected-3D-hypothesis review artifacts."""

    analysis_coordinate_df: pd.DataFrame
    burden_ledger: pd.DataFrame
    residual_report: dict[str, Any]
    norm_vs_corrected_sensitivity_report: pd.DataFrame
    readiness_provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return serializable review artifacts for pipeline reports."""
        return {
            "num_analysis_rows": int(len(self.analysis_coordinate_df)),
            "num_burden_rows": int(len(self.burden_ledger)),
            "residual_report": dict(self.residual_report),
            "norm_vs_corrected_sensitivity_report": (
                self.norm_vs_corrected_sensitivity_report.to_dict(orient="records")
            ),
            "num_sensitivity_rows": int(len(self.norm_vs_corrected_sensitivity_report)),
            "readiness_provenance": dict(self.readiness_provenance),
        }


def _validate_axes(axes: tuple[str, ...], name: str) -> None:
    invalid = [axis for axis in axes if axis not in _VALID_AXES]
    if invalid:
        raise ValueError(f"{name} contains invalid axes: {invalid}")


def _coordinate_column(landmark: str, family: str, axis: str) -> str:
    if family == "raw":
        return f"{landmark}_{axis}"
    return f"{landmark}_{family}_{axis}"


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _coerce_segment_pairs(value: Any) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for item in value or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            pairs.append((str(item[0]), str(item[1])))
    return tuple(pairs)


def _parse_prior_config(name: str, raw: Any) -> CorrectionPriorConfig:
    if raw is None:
        raw = {}
    if isinstance(raw, bool):
        raw = {"enabled": raw}
    if not isinstance(raw, Mapping):
        raise ValueError(f"correction prior {name!r} must be a mapping or boolean.")
    return CorrectionPriorConfig(
        name=str(raw.get("name", name)),
        enabled=_coerce_bool(raw.get("enabled"), False),
        scope=str(raw.get("scope", "all")),
        priority=str(raw.get("priority", "secondary")),
        weight=float(raw.get("weight", 1.0)),
        report_only=_coerce_bool(raw.get("report_only"), False),
        confidence_policy=str(raw.get("confidence_policy", "burden_penalty")),
    )


def _parse_prior_configs(raw: Any) -> tuple[CorrectionPriorConfig, ...]:
    if raw is None:
        return (
            CorrectionPriorConfig(
                name="anthropometric_segment_length",
                enabled=True,
                priority="primary",
            ),
        )
    if isinstance(raw, Mapping):
        return tuple(
            _parse_prior_config(str(name), config) for name, config in raw.items()
        )
    if isinstance(raw, list):
        configs: list[CorrectionPriorConfig] = []
        for index, item in enumerate(raw):
            if isinstance(item, str):
                configs.append(_parse_prior_config(item, {"enabled": True}))
            elif isinstance(item, Mapping):
                name = str(item.get("name", f"prior_{index}"))
                configs.append(_parse_prior_config(name, item))
            else:
                raise ValueError(
                    "correction_priors list entries must be strings or mappings."
                )
        return tuple(configs)
    raise ValueError("correction_priors must be a mapping, list, or null.")


def _radial_config_with_preset(raw: Any) -> RadialXYRelaxationConfig:
    if raw is None:
        raw = {}
    if isinstance(raw, bool):
        raw = {"enabled": raw}
    if not isinstance(raw, Mapping):
        raise ValueError("radial_xy_relaxation must be a mapping or boolean.")

    preset = str(raw.get("preset", "off"))
    preset_defaults: dict[str, Any]
    if preset == "off":
        preset_defaults = {"enabled": False, "max_xy_shift_torso": 0.0}
    elif preset == "smartphone_nominal":
        preset_defaults = {
            "enabled": True,
            "max_xy_shift_torso": 0.02,
            "radial_strength": 0.25,
            "max_iterations": 5,
        }
    elif preset == "strong_review":
        preset_defaults = {
            "enabled": True,
            "max_xy_shift_torso": 0.05,
            "radial_strength": 0.50,
            "max_iterations": 8,
        }
    elif preset == "custom":
        preset_defaults = {"enabled": bool(raw.get("enabled", False))}
    else:
        raise ValueError(
            "radial_xy_relaxation.preset must be one of: "
            "off, smartphone_nominal, strong_review, custom."
        )

    merged = {**preset_defaults, **dict(raw)}
    enabled = _coerce_bool(merged.get("enabled"), False) and preset != "off"
    return RadialXYRelaxationConfig(
        enabled=enabled,
        preset=preset,
        model=str(merged.get("model", "radial_k1")),
        direction=str(merged.get("direction", "pincushion")),
        center_source=str(merged.get("center_source", "frame_center")),
        max_xy_shift_torso=float(merged.get("max_xy_shift_torso", 0.02)),
        radial_strength=float(merged.get("radial_strength", 0.25)),
        max_iterations=int(merged.get("max_iterations", 5)),
        convergence_epsilon=float(merged.get("convergence_epsilon", 0.001)),
        accept_only_if_residual_improves=_coerce_bool(
            merged.get("accept_only_if_residual_improves"),
            True,
        ),
    )


def _coordinate_solver_config_from_dict(
    solver_config: Mapping[str, Any],
    *,
    output_family: str,
) -> Corrected3DCoordinateSolverConfig:
    raw_solver = solver_config.get("coordinate_solver", {})
    if raw_solver is None:
        raw_solver = {}
    if isinstance(raw_solver, bool):
        raw_solver = {"enabled": raw_solver}
    if not isinstance(raw_solver, Mapping):
        raise ValueError("coordinate_solver must be a mapping or boolean.")

    enabled = bool(
        raw_solver.get(
            "enabled",
            solver_config.get("coordinate_solver_enabled", False),
        )
    )
    segment_pairs = _coerce_segment_pairs(
        raw_solver.get("segment_pairs", solver_config.get("segment_pairs"))
    )
    if not segment_pairs:
        segment_pairs = _DEFAULT_SEGMENT_PAIRS
    radial_raw = raw_solver.get(
        "radial_xy_relaxation",
        solver_config.get("radial_xy_relaxation", {}),
    )
    priors_raw = raw_solver.get(
        "correction_priors",
        solver_config.get("correction_priors"),
    )
    lengths_raw = raw_solver.get(
        "segment_lengths_torso",
        solver_config.get("segment_lengths_torso", {}),
    )
    return Corrected3DCoordinateSolverConfig(
        enabled=enabled,
        source_family=str(
            raw_solver.get("source_family", solver_config.get("source_family", "norm"))
        ),
        output_family=str(
            raw_solver.get(
                "output_family", solver_config.get("output_family", output_family)
            )
        ),
        segment_pairs=tuple(segment_pairs),
        default_segment_length_torso=float(
            raw_solver.get(
                "default_segment_length_torso",
                solver_config.get("default_segment_length_torso", 1.0),
            )
        ),
        segment_lengths_torso={
            str(key): float(value) for key, value in dict(lengths_raw or {}).items()
        },
        max_depth_torso=float(
            raw_solver.get(
                "max_depth_torso", solver_config.get("max_depth_torso", 0.75)
            )
        ),
        max_z_correction_torso=float(
            raw_solver.get(
                "max_z_correction_torso",
                solver_config.get("max_z_correction_torso", 0.50),
            )
        ),
        confidence_threshold=float(
            raw_solver.get(
                "confidence_threshold",
                solver_config.get("confidence_threshold", 0.5),
            )
        ),
        correction_priors=_parse_prior_configs(priors_raw),
        radial_xy_relaxation=_radial_config_with_preset(radial_raw),
    )


def _coordinate_columns(
    support_pair: tuple[str, str],
    family: str,
    axes: tuple[str, ...],
) -> list[str]:
    return [
        _coordinate_column(landmark, family, axis)
        for landmark in support_pair
        for axis in axes
    ]


def _missing_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column not in df.columns]


def _support_width(
    df: pd.DataFrame,
    *,
    support_pair: tuple[str, str],
    family: str,
    axes: tuple[str, ...],
) -> np.ndarray:
    left, right = support_pair
    delta_sq = np.zeros(len(df), dtype=float)
    for axis in axes:
        left_col = _coordinate_column(left, family, axis)
        right_col = _coordinate_column(right, family, axis)
        delta = df[right_col].to_numpy(dtype=float) - df[left_col].to_numpy(dtype=float)
        delta_sq += delta * delta
    return np.sqrt(delta_sq)


def _robust_range(
    values: np.ndarray,
    *,
    low_percentile: float,
    high_percentile: float,
) -> float:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return float("nan")
    high = np.percentile(finite, high_percentile)
    low = np.percentile(finite, low_percentile)
    return float(high - low)


def _burden_from_ledger(
    burden_ledger: pd.DataFrame | None,
    *,
    coordinate_family: str,
) -> tuple[float, list[str]]:
    if burden_ledger is None or burden_ledger.empty:
        return float("nan"), ["missing_burden_ledger"]

    ledger = burden_ledger
    if "coordinate_family" in ledger.columns:
        ledger = ledger[ledger["coordinate_family"] == coordinate_family]
    if ledger.empty:
        return float("nan"), ["missing_coordinate_family_burden"]

    if "cap_fraction" in ledger.columns:
        values = ledger["cap_fraction"].to_numpy(dtype=float)
    elif {"delta_torso_ratio", "cap_torso_ratio"}.issubset(ledger.columns):
        caps = ledger["cap_torso_ratio"].to_numpy(dtype=float)
        deltas = np.abs(ledger["delta_torso_ratio"].to_numpy(dtype=float))
        values = np.divide(
            deltas,
            caps,
            out=np.full_like(deltas, np.nan, dtype=float),
            where=caps > 0,
        )
    elif "correction_burden" in ledger.columns:
        values = ledger["correction_burden"].to_numpy(dtype=float)
    else:
        return float("nan"), ["missing_burden_field"]

    finite = np.abs(values[np.isfinite(values)])
    if finite.size == 0:
        return float("nan"), ["nonfinite_burden"]
    return float(np.max(finite)), []


def _availability_from_burden(
    burden: float,
    reasons: list[str],
    config: SupportWidthStabilityConfig,
) -> tuple[str, str, list[str]]:
    if not np.isfinite(burden):
        return "low_confidence", "low", reasons
    if burden >= config.not_assessed_burden_threshold:
        return "not_assessed", "very_low", reasons + ["correction_burden_too_high"]
    if burden >= config.high_burden_threshold:
        return "low_confidence", "low", reasons + ["correction_burden_high"]
    return "assessed", "very_low", reasons


def _quality_gravity_from_availability_confidence(
    availability: str,
    confidence: str,
) -> float:
    """Return a quality-trust summary, not a score-contribution decision."""
    if availability == "not_assessed":
        return 0.0
    return _QUALITY_GRAVITY_BY_CONFIDENCE.get(str(confidence), 0.0)


def _prior_by_name(
    config: Corrected3DCoordinateSolverConfig,
    name: str,
) -> CorrectionPriorConfig:
    for prior in config.correction_priors:
        if prior.name == name:
            return prior
    return CorrectionPriorConfig(name=name, enabled=False)


def _segment_key(proximal: str, distal: str) -> str:
    return f"{proximal}|{distal}"


def _target_segment_length(
    config: Corrected3DCoordinateSolverConfig,
    proximal: str,
    distal: str,
) -> float:
    keys = (
        _segment_key(proximal, distal),
        _segment_key(distal, proximal),
        f"{proximal}_{distal}",
        f"{distal}_{proximal}",
    )
    for key in keys:
        if key in config.segment_lengths_torso:
            return float(config.segment_lengths_torso[key])
    return float(config.default_segment_length_torso)


def _confidence_pair_valid(
    row: pd.Series,
    proximal: str,
    distal: str,
    threshold: float,
) -> bool:
    for landmark in (proximal, distal):
        column = f"{landmark}_confidence"
        if column not in row.index:
            continue
        value = float(row[column])
        if not np.isfinite(value) or value < threshold:
            return False
    return True


def _segment_residual(length_xy: float, dz: float, target: float) -> float:
    if not np.isfinite(length_xy) or not np.isfinite(dz) or target <= 0:
        return float("nan")
    return float(abs(np.sqrt(length_xy * length_xy + dz * dz) - target))


def _choose_depth_solution(
    proximal_z: float,
    distal_z: float,
    dz_abs: float,
) -> float:
    positive = proximal_z + dz_abs
    negative = proximal_z - dz_abs
    if np.isfinite(distal_z):
        if abs(positive - distal_z) <= abs(negative - distal_z):
            return float(positive)
        return float(negative)
    return float(positive)


def _confidence_from_burden(burden: float) -> str:
    if not np.isfinite(burden):
        return "not_available"
    if burden <= 0.25:
        return "high"
    if burden <= 0.50:
        return "moderate"
    if burden < 1.00:
        return "low"
    return "very_low"


def _frame_center(
    df: pd.DataFrame,
    frame_index: int,
    *,
    config: RadialXYRelaxationConfig,
) -> np.ndarray:
    if config.center_source == "metadata":
        if {"frame_center_x", "frame_center_y"}.issubset(df.columns):
            return np.array(
                [
                    float(df.iloc[frame_index]["frame_center_x"]),
                    float(df.iloc[frame_index]["frame_center_y"]),
                ],
                dtype=float,
            )
    return np.array([0.0, 0.0], dtype=float)


def _radial_direction_signs(config: RadialXYRelaxationConfig) -> tuple[float, ...]:
    if config.direction == "pincushion":
        return (-1.0,)
    if config.direction == "barrel":
        return (1.0,)
    if config.direction == "auto_candidate":
        return (-1.0, 1.0)
    raise ValueError(
        "radial_xy_relaxation.direction must be one of: "
        "pincushion, barrel, auto_candidate."
    )


def _radial_xy_candidate(
    xy: np.ndarray,
    *,
    center: np.ndarray,
    shift: float,
    sign: float,
) -> np.ndarray:
    vector = xy - center
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 0.0:
        return xy.copy()
    return xy + sign * float(shift) * vector / norm


def _copy_source_family_to_output(
    df: pd.DataFrame,
    *,
    landmarks: list[str],
    source_family: str,
    output_family: str,
) -> tuple[pd.DataFrame, list[str]]:
    updated = df.copy()
    missing: list[str] = []
    for landmark in landmarks:
        for axis in ("x", "y", "z"):
            source = _coordinate_column(landmark, source_family, axis)
            target = _coordinate_column(landmark, output_family, axis)
            if source not in df.columns:
                missing.append(source)
                continue
            updated[target] = pd.to_numeric(df[source], errors="coerce")
    return updated, missing


def _solver_disabled_result(
    df: pd.DataFrame,
    *,
    config: Corrected3DCoordinateSolverConfig,
    reason: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    return (
        df.copy(),
        pd.DataFrame(),
        {
            "enabled": bool(config.enabled),
            "status": "disabled" if not config.enabled else "skipped",
            "reason": reason,
            "coordinate_family": config.output_family,
            "source_family": config.source_family,
            "applied_priors": [],
            "skipped_priors": {},
            "quality_diagnostics": {},
        },
    )


def build_corrected_3d_coordinate_hypothesis(
    norm_pose_df: pd.DataFrame,
    *,
    landmarks: list[str],
    config: Corrected3DCoordinateSolverConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Create optional corrected-3D-hypothesis coordinates from weak priors.

    The solver preserves source coordinates by writing a separate coordinate
    family. Corrections are engineering evidence with burden/residual audit
    fields, not a calibrated 3D reconstruction.
    """

    if not config.enabled:
        return _solver_disabled_result(
            norm_pose_df,
            config=config,
            reason="coordinate_solver_disabled",
        )

    anthropometric_prior = _prior_by_name(config, "anthropometric_segment_length")
    radial_prior = _prior_by_name(config, "radial_xy_relaxation")
    if not anthropometric_prior.enabled:
        return _solver_disabled_result(
            norm_pose_df,
            config=config,
            reason="anthropometric_segment_length_prior_disabled",
        )
    if anthropometric_prior.report_only:
        return _solver_disabled_result(
            norm_pose_df,
            config=config,
            reason="anthropometric_segment_length_report_only",
        )
    if config.default_segment_length_torso <= 0:
        return _solver_disabled_result(
            norm_pose_df,
            config=config,
            reason="default_segment_length_torso_must_be_positive",
        )

    updated, missing = _copy_source_family_to_output(
        norm_pose_df,
        landmarks=landmarks,
        source_family=config.source_family,
        output_family=config.output_family,
    )
    ledger_rows: list[dict[str, Any]] = []
    rejection_counts: dict[str, int] = {}
    applied_priors: set[str] = set()
    radial_enabled = (
        config.radial_xy_relaxation.enabled
        and radial_prior.enabled
        and not radial_prior.report_only
    )

    def reject(reason: str) -> None:
        rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

    if missing:
        rejection_counts["missing_source_coordinate_columns"] = len(missing)

    for proximal, distal in config.segment_pairs:
        if proximal not in landmarks or distal not in landmarks:
            continue
        target = _target_segment_length(config, proximal, distal)
        if target <= 0:
            reject("nonpositive_segment_target")
            continue

        p_cols = {
            axis: _coordinate_column(proximal, config.output_family, axis)
            for axis in ("x", "y", "z")
        }
        d_cols = {
            axis: _coordinate_column(distal, config.output_family, axis)
            for axis in ("x", "y", "z")
        }
        if any(
            column not in updated.columns
            for column in (*p_cols.values(), *d_cols.values())
        ):
            reject("missing_pair_coordinate_columns")
            continue

        for frame_pos in range(len(updated)):
            row = updated.iloc[frame_pos]
            if not _confidence_pair_valid(
                norm_pose_df.iloc[frame_pos],
                proximal,
                distal,
                config.confidence_threshold,
            ):
                reject("confidence_below_threshold")
                continue

            p_xyz = np.array([float(row[p_cols[axis]]) for axis in ("x", "y", "z")])
            d_xyz = np.array([float(row[d_cols[axis]]) for axis in ("x", "y", "z")])
            if not np.isfinite(p_xyz).all() or not np.isfinite(d_xyz).all():
                reject("nonfinite_source_coordinate")
                continue

            p_xy = p_xyz[:2]
            d_xy = d_xyz[:2]
            d_xy_length = float(np.linalg.norm(d_xy - p_xy))
            before_residual = _segment_residual(
                d_xy_length,
                float(d_xyz[2] - p_xyz[2]),
                target,
            )
            candidate_prior = "anthropometric_segment_length"
            candidate_p_xy = p_xy
            candidate_d_xy = d_xy
            candidate_xy_length = d_xy_length

            if candidate_xy_length > target and radial_enabled:
                radial_config = config.radial_xy_relaxation
                center = _frame_center(norm_pose_df, frame_pos, config=radial_config)
                best: tuple[float, np.ndarray, np.ndarray, float] | None = None
                max_iterations = max(int(radial_config.max_iterations), 1)
                for iteration in range(1, max_iterations + 1):
                    shift = (
                        float(radial_config.max_xy_shift_torso)
                        * float(radial_config.radial_strength)
                        * iteration
                        / max_iterations
                    )
                    if shift <= 0:
                        continue
                    for sign in _radial_direction_signs(radial_config):
                        p_candidate = _radial_xy_candidate(
                            p_xy,
                            center=center,
                            shift=shift,
                            sign=sign,
                        )
                        d_candidate = _radial_xy_candidate(
                            d_xy,
                            center=center,
                            shift=shift,
                            sign=sign,
                        )
                        length = float(np.linalg.norm(d_candidate - p_candidate))
                        residual = max(length - target, 0.0)
                        if best is None or residual < best[0]:
                            best = (residual, p_candidate, d_candidate, length)
                        if residual <= radial_config.convergence_epsilon:
                            break
                    if (
                        best is not None
                        and best[0] <= radial_config.convergence_epsilon
                    ):
                        break
                if best is not None and best[3] <= target:
                    _, candidate_p_xy, candidate_d_xy, candidate_xy_length = best
                    candidate_prior = "radial_xy_relaxation"

            if candidate_xy_length > target:
                reject("projected_length_exceeds_segment_prior")
                continue

            dz_abs = float(np.sqrt(max(target * target - candidate_xy_length**2, 0.0)))
            if dz_abs > config.max_depth_torso:
                reject("depth_solution_exceeds_cap")
                continue
            candidate_z = _choose_depth_solution(
                float(p_xyz[2]), float(d_xyz[2]), dz_abs
            )
            z_shift = abs(candidate_z - float(d_xyz[2]))
            if z_shift > config.max_z_correction_torso:
                reject("z_correction_exceeds_cap")
                continue

            after_residual = _segment_residual(
                candidate_xy_length,
                candidate_z - float(p_xyz[2]),
                target,
            )
            radial_config = config.radial_xy_relaxation
            if (
                candidate_prior == "radial_xy_relaxation"
                and radial_config.accept_only_if_residual_improves
                and np.isfinite(before_residual)
                and np.isfinite(after_residual)
                and after_residual >= before_residual
            ):
                reject("radial_candidate_did_not_improve_residual")
                continue

            xy_shift = float(
                max(
                    np.linalg.norm(candidate_p_xy - p_xy),
                    np.linalg.norm(candidate_d_xy - d_xy),
                )
            )
            xy_burden = (
                xy_shift / config.radial_xy_relaxation.max_xy_shift_torso
                if config.radial_xy_relaxation.max_xy_shift_torso > 0
                else 0.0
            )
            z_burden = z_shift / config.max_z_correction_torso
            burden = float(max(xy_burden, z_burden))
            confidence = _confidence_from_burden(burden)
            quality_gravity = _QUALITY_GRAVITY_BY_CONFIDENCE.get(confidence, 0.0)

            updated.iat[frame_pos, updated.columns.get_loc(p_cols["x"])] = (
                candidate_p_xy[0]
            )
            updated.iat[frame_pos, updated.columns.get_loc(p_cols["y"])] = (
                candidate_p_xy[1]
            )
            updated.iat[frame_pos, updated.columns.get_loc(d_cols["x"])] = (
                candidate_d_xy[0]
            )
            updated.iat[frame_pos, updated.columns.get_loc(d_cols["y"])] = (
                candidate_d_xy[1]
            )
            updated.iat[frame_pos, updated.columns.get_loc(d_cols["z"])] = candidate_z
            applied_priors.add("anthropometric_segment_length")
            if candidate_prior == "radial_xy_relaxation":
                applied_priors.add("radial_xy_relaxation")

            prior_config = (
                radial_prior
                if candidate_prior == "radial_xy_relaxation"
                else anthropometric_prior
            )
            ledger_rows.append(
                {
                    "frame": (
                        norm_pose_df.iloc[frame_pos]["frame"]
                        if "frame" in norm_pose_df.columns
                        else norm_pose_df.index[frame_pos]
                    ),
                    "frame_index": int(frame_pos),
                    "coordinate_family": config.output_family,
                    "stage": "corrected_3d_hypothesis",
                    "prior": candidate_prior,
                    "segment_pair": _segment_key(proximal, distal),
                    "landmark": distal,
                    "priority": prior_config.priority,
                    "weight": float(prior_config.weight),
                    "report_only": bool(prior_config.report_only),
                    "delta_xy_torso_ratio": xy_shift,
                    "delta_z_torso_ratio": z_shift,
                    "delta_torso_ratio": max(xy_shift, z_shift),
                    "cap_torso_ratio": max(
                        config.radial_xy_relaxation.max_xy_shift_torso,
                        config.max_z_correction_torso,
                    ),
                    "cap_fraction": burden,
                    "correction_burden": burden,
                    "residual_before_torso": before_residual,
                    "residual_after_torso": after_residual,
                    "residual_improvement_torso": (
                        before_residual - after_residual
                        if np.isfinite(before_residual) and np.isfinite(after_residual)
                        else float("nan")
                    ),
                    "confidence": confidence,
                    "quality_gravity": quality_gravity,
                }
            )

    ledger = pd.DataFrame(ledger_rows)
    accepted = int(len(ledger))
    status = "applied" if accepted else "skipped"
    report: dict[str, Any] = {
        "enabled": True,
        "status": status,
        "coordinate_family": config.output_family,
        "source_family": config.source_family,
        "segment_pairs": [list(pair) for pair in config.segment_pairs],
        "default_segment_length_torso": float(config.default_segment_length_torso),
        "segment_lengths_torso": dict(config.segment_lengths_torso),
        "max_depth_torso": float(config.max_depth_torso),
        "max_z_correction_torso": float(config.max_z_correction_torso),
        "confidence_threshold": float(config.confidence_threshold),
        "correction_priors": [asdict(prior) for prior in config.correction_priors],
        "radial_xy_relaxation": asdict(config.radial_xy_relaxation),
        "applied_priors": sorted(applied_priors),
        "skipped_priors": {
            prior.name: "disabled" if not prior.enabled else "not_applied"
            for prior in config.correction_priors
            if prior.name not in applied_priors
        },
        "num_accepted_corrections": accepted,
        "num_rejected_candidates": int(sum(rejection_counts.values())),
        "rejection_reasons": rejection_counts,
        "quality_diagnostics": {},
    }
    if not ledger.empty:
        burden_values = ledger["correction_burden"].to_numpy(dtype=float)
        residual_before = ledger["residual_before_torso"].to_numpy(dtype=float)
        residual_after = ledger["residual_after_torso"].to_numpy(dtype=float)
        quality_values = ledger["quality_gravity"].to_numpy(dtype=float)
        report["quality_diagnostics"] = {
            "max_correction_burden": float(np.nanmax(burden_values)),
            "median_correction_burden": float(np.nanmedian(burden_values)),
            "median_residual_before_torso": float(np.nanmedian(residual_before)),
            "median_residual_after_torso": float(np.nanmedian(residual_after)),
            "median_quality_gravity": float(np.nanmedian(quality_values)),
        }
    return updated, ledger, report


def build_support_width_stability_sensitivity_report(
    norm_pose_df: pd.DataFrame,
    *,
    config: SupportWidthStabilityConfig | None = None,
    burden_ledger: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the first report-only norm-vs-analysis sensitivity row.

    The support-width value is a robust range of the left/right support distance
    in torso-length ratio units. The norm side uses recording-plane x/y axes;
    the corrected side may include depth, but remains review evidence.
    """

    config = config or SupportWidthStabilityConfig()
    _validate_axes(config.norm_axes, "norm_axes")
    _validate_axes(config.coordinate_axes, "coordinate_axes")

    reasons: list[str] = []
    norm_columns = _coordinate_columns(
        config.support_pair, config.norm_family, config.norm_axes
    )
    corrected_columns = _coordinate_columns(
        config.support_pair, config.coordinate_family, config.coordinate_axes
    )
    missing_norm = _missing_columns(norm_pose_df, norm_columns)
    missing_corrected = _missing_columns(norm_pose_df, corrected_columns)

    norm_value = float("nan")
    corrected_value = float("nan")
    if missing_norm:
        reasons.append("missing_norm_columns")
    else:
        norm_value = _robust_range(
            _support_width(
                norm_pose_df,
                support_pair=config.support_pair,
                family=config.norm_family,
                axes=config.norm_axes,
            ),
            low_percentile=config.low_percentile,
            high_percentile=config.high_percentile,
        )

    if missing_corrected:
        reasons.append("missing_corrected_columns")
    else:
        corrected_value = _robust_range(
            _support_width(
                norm_pose_df,
                support_pair=config.support_pair,
                family=config.coordinate_family,
                axes=config.coordinate_axes,
            ),
            low_percentile=config.low_percentile,
            high_percentile=config.high_percentile,
        )

    if not np.isfinite(norm_value):
        reasons.append("nonfinite_norm_value")
    if not np.isfinite(corrected_value):
        reasons.append("nonfinite_corrected_value")

    burden, burden_reasons = _burden_from_ledger(
        burden_ledger, coordinate_family=config.coordinate_family
    )
    if burden_reasons:
        reasons.extend(burden_reasons)

    if missing_norm or missing_corrected or not np.isfinite(norm_value):
        availability = "not_assessed"
        confidence = "very_low"
    elif not np.isfinite(corrected_value):
        availability = "not_assessed"
        confidence = "very_low"
    else:
        availability, confidence, reasons = _availability_from_burden(
            burden, reasons, config
        )
    quality_gravity = _quality_gravity_from_availability_confidence(
        availability,
        confidence,
    )

    delta = (
        float(corrected_value - norm_value)
        if np.isfinite(corrected_value) and np.isfinite(norm_value)
        else float("nan")
    )
    delta_abs = float(abs(delta)) if np.isfinite(delta) else float("nan")

    row = {
        "feature_id": config.feature_id,
        "evaluation_domain": config.evaluation_domain,
        "source_evidence": (
            "norm support-pair width versus corrected coordinate family"
        ),
        "coordinate_family": config.coordinate_family,
        "support_pair": "|".join(config.support_pair),
        "norm_axes": "|".join(config.norm_axes),
        "coordinate_axes": "|".join(config.coordinate_axes),
        "norm_value": norm_value,
        "corrected_value": corrected_value,
        "delta": delta,
        "delta_abs": delta_abs,
        "correction_burden": burden,
        "residual": delta_abs,
        "availability": availability,
        "confidence": confidence,
        "quality_gravity": quality_gravity,
        "availability_reasons": "|".join(dict.fromkeys(reasons)),
    }
    return pd.DataFrame([row])


def build_corrected_3d_hypothesis_evidence(
    norm_pose_df: pd.DataFrame,
    *,
    landmarks: list[str] | None = None,
    common_subject_skeleton_profile: dict[str, Any] | None = None,
    exercise_support_context: dict[str, Any] | None = None,
    solver_config: dict[str, Any] | None = None,
    burden_ledger: pd.DataFrame | None = None,
    residual_report: dict[str, Any] | None = None,
) -> Corrected3DHypothesisResult:
    """Build corrected-3D-hypothesis analysis-evidence artifacts.

    This first extraction does not alter coordinates. It verifies that the
    required evidence surface can be generated before any solver is considered
    by later scoring policy.
    """

    solver_config = dict(solver_config or {})
    coordinate_family = str(
        solver_config.get("output_family", "corrected_3d_hypothesis")
    )
    support_pair = tuple(
        solver_config.get("support_pair", ("left_ankle", "right_ankle"))
    )
    if len(support_pair) != 2:
        raise ValueError("support_pair must contain exactly two landmarks.")

    coordinate_solver_config = _coordinate_solver_config_from_dict(
        solver_config,
        output_family=coordinate_family,
    )
    analysis_df = norm_pose_df.copy()
    solver_ledger = pd.DataFrame()
    solver_report: dict[str, Any] = {
        "enabled": False,
        "status": "disabled",
        "reason": "coordinate_solver_disabled",
    }
    if coordinate_solver_config.enabled:
        analysis_df, solver_ledger, solver_report = (
            build_corrected_3d_coordinate_hypothesis(
                norm_pose_df,
                landmarks=list(landmarks or []),
                config=coordinate_solver_config,
            )
        )

    ledgers = [
        item
        for item in (
            burden_ledger.copy() if burden_ledger is not None else pd.DataFrame(),
            solver_ledger,
        )
        if not item.empty
    ]
    combined_ledger = (
        pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame()
    )

    sensitivity_config = SupportWidthStabilityConfig(
        coordinate_family=coordinate_family,
        support_pair=(str(support_pair[0]), str(support_pair[1])),
    )
    sensitivity = build_support_width_stability_sensitivity_report(
        analysis_df,
        config=sensitivity_config,
        burden_ledger=combined_ledger,
    )
    readiness = {
        "status": "analysis_evidence",
        "used_for_features_or_scores": False,
        "downstream_coordinate_mode": "norm",
        "landmarks": list(landmarks or []),
        "has_common_subject_skeleton_profile": common_subject_skeleton_profile
        is not None,
        "has_exercise_support_context": exercise_support_context is not None,
        "coordinate_solver_status": solver_report.get("status", "disabled"),
        "coordinate_solver_enabled": bool(coordinate_solver_config.enabled),
    }
    merged_residual_report = dict(residual_report or {})
    merged_residual_report["coordinate_solver"] = solver_report
    return Corrected3DHypothesisResult(
        analysis_coordinate_df=analysis_df,
        burden_ledger=combined_ledger,
        residual_report=merged_residual_report,
        norm_vs_corrected_sensitivity_report=sensitivity,
        readiness_provenance=readiness,
    )


def _review_blocks_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    review = report.get("corrected_3d_hypothesis_review")
    if isinstance(review, dict):
        return [review]
    reviews = report.get("corrected_3d_hypothesis_reviews")
    if isinstance(reviews, list):
        return [item for item in reviews if isinstance(item, dict)]
    return []


def collect_corrected_3d_sensitivity_rows(
    reports: Iterable[dict[str, Any]],
) -> pd.DataFrame:
    """Collect corrected-3D analysis-evidence rows from multiple reports."""

    rows: list[dict[str, Any]] = []
    for index, report in enumerate(reports):
        exercise = report.get("exercise_definition", {}) or {}
        recording_id = report.get("recording_id", f"report_{index}")
        exercise_id = exercise.get("exercise_id", "unknown")
        for review in _review_blocks_from_report(report):
            for row in review.get("norm_vs_corrected_sensitivity_report", []) or []:
                if not isinstance(row, dict):
                    continue
                item = dict(row)
                item.setdefault("recording_id", recording_id)
                item.setdefault("exercise_id", exercise_id)
                rows.append(item)
    return pd.DataFrame(rows)


def summarize_corrected_3d_sensitivity_reports(
    reports: Iterable[dict[str, Any]],
) -> pd.DataFrame:
    """Summarize corrected-3D sensitivity rows across recordings/exercises."""

    rows = collect_corrected_3d_sensitivity_rows(reports)
    if rows.empty:
        return pd.DataFrame(
            columns=[
                "feature_id",
                "exercise_id",
                "n_recordings",
                "n_rows",
                "n_assessed",
                "n_low_confidence",
                "n_not_assessed",
                "median_norm_value",
                "median_corrected_value",
                "median_delta_abs",
                "max_correction_burden",
                "median_quality_gravity",
            ]
        )

    summaries: list[dict[str, Any]] = []
    for (feature_id, exercise_id), group in rows.groupby(
        ["feature_id", "exercise_id"], dropna=False
    ):
        availability = group.get("availability", pd.Series(dtype=object)).astype(str)
        summaries.append(
            {
                "feature_id": feature_id,
                "exercise_id": exercise_id,
                "n_recordings": int(group["recording_id"].nunique()),
                "n_rows": int(len(group)),
                "n_assessed": int((availability == "assessed").sum()),
                "n_low_confidence": int((availability == "low_confidence").sum()),
                "n_not_assessed": int((availability == "not_assessed").sum()),
                "median_norm_value": float(
                    pd.to_numeric(group.get("norm_value"), errors="coerce").median()
                ),
                "median_corrected_value": float(
                    pd.to_numeric(
                        group.get("corrected_value"), errors="coerce"
                    ).median()
                ),
                "median_delta_abs": float(
                    pd.to_numeric(group.get("delta_abs"), errors="coerce").median()
                ),
                "max_correction_burden": float(
                    pd.to_numeric(group.get("correction_burden"), errors="coerce").max()
                ),
                "median_quality_gravity": float(
                    pd.to_numeric(
                        group.get("quality_gravity"), errors="coerce"
                    ).median()
                ),
            }
        )
    return pd.DataFrame(summaries)


__all__ = [
    "Corrected3DCoordinateSolverConfig",
    "Corrected3DHypothesisResult",
    "CorrectionPriorConfig",
    "RadialXYRelaxationConfig",
    "SupportWidthStabilityConfig",
    "build_corrected_3d_coordinate_hypothesis",
    "build_corrected_3d_hypothesis_evidence",
    "build_support_width_stability_sensitivity_report",
    "collect_corrected_3d_sensitivity_rows",
    "summarize_corrected_3d_sensitivity_reports",
]
