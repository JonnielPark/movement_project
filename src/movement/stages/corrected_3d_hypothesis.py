"""Corrected-3D-hypothesis analysis-evidence helpers.

Corrected coordinates are low-confidence structural hypotheses. This module
emits availability, quality gravity, and norm-vs-analysis sensitivity evidence.
Raw burden and residual values are retained as review diagnostics.
It does not create a good-movement template, calibrated 3D reconstruction, or
final-score contribution.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


_VALID_AXES = {"x", "y", "z"}


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
    return {
        "high": 1.0,
        "moderate": 0.5,
        "low": 0.1,
        "very_low": 0.05,
        "not_available": 0.0,
    }.get(str(confidence), 0.0)


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

    sensitivity_config = SupportWidthStabilityConfig(
        coordinate_family=coordinate_family,
        support_pair=(str(support_pair[0]), str(support_pair[1])),
    )
    sensitivity = build_support_width_stability_sensitivity_report(
        norm_pose_df,
        config=sensitivity_config,
        burden_ledger=burden_ledger,
    )
    readiness = {
        "status": "analysis_evidence",
        "used_for_features_or_scores": False,
        "downstream_coordinate_mode": "norm",
        "landmarks": list(landmarks or []),
        "has_common_subject_skeleton_profile": common_subject_skeleton_profile
        is not None,
        "has_exercise_support_context": exercise_support_context is not None,
    }
    return Corrected3DHypothesisResult(
        analysis_coordinate_df=norm_pose_df.copy(),
        burden_ledger=(
            burden_ledger.copy() if burden_ledger is not None else pd.DataFrame()
        ),
        residual_report=dict(residual_report or {}),
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
    "Corrected3DHypothesisResult",
    "SupportWidthStabilityConfig",
    "build_corrected_3d_hypothesis_evidence",
    "build_support_width_stability_sensitivity_report",
    "collect_corrected_3d_sensitivity_rows",
    "summarize_corrected_3d_sensitivity_reports",
]
