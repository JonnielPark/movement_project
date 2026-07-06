"""
⑩ Biomarker Scoring — Movement Quality Composite Score

Z-score deduction model anchored to a synthetic-normal baseline stored in
data/reference/baseline_zscore.json. Scores are relative to the baseline
and do not represent clinical thresholds.

Domain weights:
    Defaults are equal across score domains for the current validation pass.
    Relative weights can be overridden by config or caller input, then are
    normalized to sum to 1.0 before computing the final score.

Score bounds:
    Defaults preserve 0–100 scoring. Custom bounds linearly scale the same
    Z-score deduction method instead of changing the scoring logic.

Dynamic floor (per domain):
    floor_dynamic =
        score_min + 0.50 × score_span × clamp(mandatory_range_of_motion_ratio, 0.0, 1.0)
    No domain score may fall below this floor due to compensation deductions.
    Example: achieving 80 % of expected ROM → floor = 40 pts.

Score formula (per domain d):
    Score_d =
        max(floor_dynamic, score_max − Σ_i (score_span / 100) · w_i · g_i · |Z_i|)

    where w_i = 1 / n_features_in_domain (equal within-domain weight),
    g_i = 1.0 for assessed evidence and a configured low-confidence gravity,
    Z_i = (value_i − μ_i) / σ_i against the synthetic-normal baseline.

Composite:
    Score_final = Σ_d W_d · Score_d,
    W defaults to equal normalized weights across score domains.
"""

from __future__ import annotations

import json
import warnings
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from movement.record_metadata import (
    COMMON_RECORD_METADATA_FIELDS,
    classify_feature_family,
)

if TYPE_CHECKING:
    from movement.biomech import BiomechRecord
    from movement.definitions.exercise_definition import ExerciseDefinition
    from movement.features import FeatureRecord


# Project root: src/movement/biomarker/scoring.py → 4 levels up
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCORE_DOMAIN_ORDER: tuple[str, ...] = ("spatial", "temporal", "control", "biomech")

DOMAIN_WEIGHTS: dict[str, float] = {
    "spatial": 0.25,
    "temporal": 0.25,
    "control": 0.25,
    "biomech": 0.25,
}
DEFAULT_LOW_CONFIDENCE_SCORE_WEIGHTS: dict[str, float] = {
    "spatial": 0.0,
    "temporal": 0.0,
    "control": 0.0,
    "biomech": 0.1,
}
DEFAULT_DEPTH_DEPENDENCY_SCORE_WEIGHTS: dict[str, float] = {
    "none": 1.0,
    "low": 1.0,
    "moderate": 0.5,
    "high": 0.1,
    "unknown": 0.3,
}
DEFAULT_SCORING_FOCUS_WEIGHTS: dict[str, float] = {
    "primary": 1.0,
    "secondary": 0.45,
    "context_constraint": 0.6,
    "compensation": 0.5,
    "diagnostic": 0.0,
}
DEFAULT_FEATURE_SCORE_WEIGHT_OVERRIDES: dict[str, float] = {}
DEFAULT_FEATURE_SCORE_DIRECTION_OVERRIDES: dict[str, str] = {}
DEFAULT_DOMAIN_FEATURE_FAMILY_WEIGHTS: dict[str, dict[str, float]] = {}
DEFAULT_SCORE_BOUNDS: dict[str, float] = {
    "min": 0.0,
    "max": 100.0,
}
_DEFAULT_DOMAIN_WEIGHT_UNITS: dict[str, float] = {
    domain: 1.0 for domain in _SCORE_DOMAIN_ORDER
}
BASELINE_STATUSES: tuple[str, ...] = ("provisional", "reviewed", "locked")
FEATURE_SCORE_DIRECTIONS: tuple[str, ...] = (
    "two_sided",
    "upper_bound_only",
    "lower_bound_only",
)
SCORING_FOCUS_TIERS: tuple[str, ...] = (
    "primary",
    "secondary",
    "context_constraint",
    "compensation",
    "diagnostic",
)

# Minimum σ applied at Z-score computation time (not stored in baseline):
#   σ_eff = max(σ_baseline, STD_FLOOR_RATIO × |μ|, STD_ABS_FLOOR)
# STD_ABS_FLOOR = 0.01 gives a meaningful floor for near-zero features
# (e.g. lateral_pelvic_shift ≈ 0 in symmetric synthetic data → σ_eff = 0.01 TLR,
# so a 1 % torso-length deviation yields Z ≈ 1 rather than Z → ∞).
_STD_FLOOR_RATIO: float = 0.10
_STD_ABS_FLOOR: float = 0.01


def normalize_domain_weights(
    domain_weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Return normalized score-domain weights.

    Supplied weights are relative units, not percentages. Missing domains keep
    the default unit weight, and a domain can be excluded by setting it to 0.
    Unknown domains are ignored with a warning.
    """
    weights = dict(_DEFAULT_DOMAIN_WEIGHT_UNITS)

    if domain_weights:
        for domain, value in domain_weights.items():
            if domain not in weights:
                warnings.warn(
                    f"[biomarker] Ignoring unknown score domain weight '{domain}'.",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            weight = float(value)
            if weight < 0:
                raise ValueError(
                    f"Score domain weight for '{domain}' must be >= 0; got {weight}."
                )
            weights[domain] = weight

    total = sum(weights.values())
    if total <= 0:
        raise ValueError("At least one score domain weight must be positive.")

    return {domain: weights[domain] / total for domain in _SCORE_DOMAIN_ORDER}


def normalize_score_bounds(
    score_bounds: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Return validated score bounds.

    The default preserves the current 0–100 scale. Custom bounds change the
    reporting scale and linearly scale deductions and dynamic floors.
    """
    bounds = dict(DEFAULT_SCORE_BOUNDS)

    if score_bounds:
        for name, value in score_bounds.items():
            if name not in bounds:
                warnings.warn(
                    f"[biomarker] Ignoring unknown score bound '{name}'.",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            bounds[name] = float(value)

    score_min = bounds["min"]
    score_max = bounds["max"]
    if not np.isfinite(score_min) or not np.isfinite(score_max):
        raise ValueError("Score bounds must be finite numbers.")
    if score_min < 0:
        raise ValueError(f"Score lower bound must be >= 0; got {score_min}.")
    if score_max <= score_min:
        raise ValueError(
            "Score upper bound must be greater than lower bound; "
            f"got min={score_min}, max={score_max}."
        )

    return {"min": score_min, "max": score_max}


def normalize_low_confidence_score_weights(
    low_confidence_score_weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Return per-domain scoring gravity for low-confidence records."""
    weights = dict(DEFAULT_LOW_CONFIDENCE_SCORE_WEIGHTS)

    if low_confidence_score_weights:
        for domain, value in low_confidence_score_weights.items():
            if domain not in weights:
                warnings.warn(
                    "[biomarker] Ignoring unknown low-confidence score "
                    f"domain '{domain}'.",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            weight = float(value)
            if weight < 0.0 or weight > 1.0:
                raise ValueError(
                    "Low-confidence score weight for "
                    f"'{domain}' must be between 0 and 1; got {weight}."
                )
            weights[domain] = weight

    return {domain: weights[domain] for domain in _SCORE_DOMAIN_ORDER}


def normalize_depth_dependency_score_weights(
    depth_dependency_score_weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Return scoring gravity by evidence depth-dependency class."""
    weights = dict(DEFAULT_DEPTH_DEPENDENCY_SCORE_WEIGHTS)

    if depth_dependency_score_weights:
        for depth_dependency, value in depth_dependency_score_weights.items():
            key = str(depth_dependency)
            if key not in weights:
                warnings.warn(
                    "[biomarker] Ignoring unknown depth-dependency score "
                    f"class '{key}'.",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            weight = float(value)
            if weight < 0.0 or weight > 1.0:
                raise ValueError(
                    "Depth-dependency score weight for "
                    f"'{key}' must be between 0 and 1; got {weight}."
                )
            weights[key] = weight

    return {key: weights[key] for key in DEFAULT_DEPTH_DEPENDENCY_SCORE_WEIGHTS}


def normalize_scoring_focus_weights(
    scoring_focus_weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Return scoring gravity by exercise-definition focus tier."""
    weights = dict(DEFAULT_SCORING_FOCUS_WEIGHTS)

    if scoring_focus_weights:
        for focus_tier, value in scoring_focus_weights.items():
            key = str(focus_tier)
            if key not in weights:
                warnings.warn(
                    f"[biomarker] Ignoring unknown scoring focus tier '{key}'.",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            weight = float(value)
            if weight < 0.0 or weight > 1.0:
                raise ValueError(
                    "Scoring focus weight for "
                    f"'{key}' must be between 0 and 1; got {weight}."
                )
            weights[key] = weight

    return {key: weights[key] for key in SCORING_FOCUS_TIERS}


def normalize_feature_score_weight_overrides(
    feature_score_weight_overrides: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Return validated feature-id scoring gravity overrides."""
    weights: dict[str, float] = {}

    if feature_score_weight_overrides:
        for feature_id, value in feature_score_weight_overrides.items():
            key = str(feature_id)
            weight = float(value)
            if weight < 0.0 or weight > 1.0:
                raise ValueError(
                    "Feature score weight override for "
                    f"'{key}' must be between 0 and 1; got {weight}."
                )
            weights[key] = weight

    return weights


def normalize_feature_score_direction_overrides(
    feature_score_direction_overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return validated feature-id scoring direction overrides."""
    directions: dict[str, str] = {}

    if feature_score_direction_overrides:
        for feature_id, direction in feature_score_direction_overrides.items():
            key = str(feature_id)
            value = str(direction)
            if value not in FEATURE_SCORE_DIRECTIONS:
                valid = ", ".join(FEATURE_SCORE_DIRECTIONS)
                raise ValueError(
                    "Feature score direction override for "
                    f"'{key}' must be one of {valid}; got {value!r}."
                )
            directions[key] = value

    return directions


def normalize_domain_feature_family_weights(
    domain_feature_family_weights: Mapping[str, Mapping[str, float]] | None = None,
) -> dict[str, dict[str, float]]:
    """Return normalized feature-family budgets by score domain.

    Family weights are relative units within each configured domain. Missing
    domains keep legacy equal-within-domain scoring. Within a configured domain,
    a missing family receives zero score budget rather than taking weight from
    another family.
    """
    normalized: dict[str, dict[str, float]] = {}

    if not domain_feature_family_weights:
        return normalized

    for domain, family_weights in domain_feature_family_weights.items():
        domain_key = str(domain)
        if domain_key not in _SCORE_DOMAIN_ORDER:
            warnings.warn(
                f"[biomarker] Ignoring unknown feature-family domain '{domain_key}'.",
                UserWarning,
                stacklevel=2,
            )
            continue
        if family_weights is None:
            continue
        domain_map: dict[str, float] = {}
        for family, value in family_weights.items():
            family_key = str(family)
            weight = float(value)
            if weight < 0.0:
                raise ValueError(
                    "Feature-family weight for "
                    f"'{domain_key}.{family_key}' must be >= 0; got {weight}."
                )
            domain_map[family_key] = weight
        total = sum(domain_map.values())
        if total <= 0.0:
            raise ValueError(
                f"At least one feature-family weight for '{domain_key}' must be "
                "positive."
            )
        normalized[domain_key] = {
            family: weight / total for family, weight in domain_map.items()
        }

    return normalized


# ── Output dataclass ──────────────────────────────────────────────────────────


@dataclass
class BiomarkerScoreRecord:
    """Composite movement quality score for one rep (or full sequence).

    Parameters
    ----------
    score_id           : always 'rep_quality_score'
    exercise_id        : exercise identifier
    definition_version : exercise YAML version this record references (provenance)
    rep_id             : rep number (None = sequence-level)
    domain_scores      : { 'spatial': 87.3, 'temporal': 92.1, ... }
    floor_applied      : { 'spatial': False, 'control': True, ... }
    deductions         : per-feature audit list
                         [{'feature_id', 'domain', 'value', 'baseline_mean',
                           'baseline_std', 'z', 'w', 'deduction'}, ...]
    withheld_features  : computed feature records excluded from composite scoring
                         because availability is low_confidence or not_assessed
    final_score        : weighted composite on the configured score scale
    source_fields      : exercise definition fields that drove the score
    domain_weights     : normalized domain weights used for final_score
    domain_feature_family_weights : normalized family budgets used inside each
        configured domain
    low_confidence_score_weights : per-domain gravity for low-confidence records
    depth_dependency_score_weights : gravity by record.depth_dependency class
    scoring_focus_weights : gravity by record.focus_tier class
    feature_score_weight_overrides : gravity overrides by exact feature id or
        `prefix.*` feature family
    feature_score_direction_overrides : one-sided scoring direction overrides
        by exact feature id or `prefix.*` feature family
    score_bounds       : score scale used for domain_scores and final_score
    """

    score_id: str
    exercise_id: str
    definition_version: str
    rep_id: int | None
    domain_scores: dict[str, float]
    floor_applied: dict[str, bool]
    final_score: float
    deductions: list[dict[str, Any]]
    withheld_features: list[dict[str, Any]] = field(default_factory=list)
    source_fields: list[str] = field(default_factory=list)
    domain_weights: dict[str, float] = field(
        default_factory=lambda: dict(DOMAIN_WEIGHTS)
    )
    domain_feature_family_weights: dict[str, dict[str, float]] = field(
        default_factory=lambda: dict(DEFAULT_DOMAIN_FEATURE_FAMILY_WEIGHTS)
    )
    low_confidence_score_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_LOW_CONFIDENCE_SCORE_WEIGHTS)
    )
    depth_dependency_score_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_DEPTH_DEPENDENCY_SCORE_WEIGHTS)
    )
    scoring_focus_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_SCORING_FOCUS_WEIGHTS)
    )
    feature_score_weight_overrides: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_FEATURE_SCORE_WEIGHT_OVERRIDES)
    )
    feature_score_direction_overrides: dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_FEATURE_SCORE_DIRECTION_OVERRIDES)
    )
    score_bounds: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_SCORE_BOUNDS)
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "score_id": self.score_id,
            "exercise_id": self.exercise_id,
            "definition_version": self.definition_version,
            "rep_id": self.rep_id,
            "domain_scores": self.domain_scores,
            "floor_applied": self.floor_applied,
            "final_score": self.final_score,
            "deductions": self.deductions,
            "withheld_features": self.withheld_features,
            "source_fields": self.source_fields,
            "domain_weights": self.domain_weights,
            "domain_feature_family_weights": self.domain_feature_family_weights,
            "low_confidence_score_weights": self.low_confidence_score_weights,
            "depth_dependency_score_weights": self.depth_dependency_score_weights,
            "scoring_focus_weights": self.scoring_focus_weights,
            "feature_score_weight_overrides": self.feature_score_weight_overrides,
            "feature_score_direction_overrides": (
                self.feature_score_direction_overrides
            ),
            "score_bounds": self.score_bounds,
        }


# ── Internal helpers ──────────────────────────────────────────────────────────


def _record_id(r: Any) -> str:
    return getattr(r, "feature_id", None) or getattr(r, "metric_id", "") or ""


def _classify_domain(record_id: str) -> str:
    for prefix, domain in (
        ("spatial.", "spatial"),
        ("temporal.", "temporal"),
        ("control.", "control"),
        ("biomech.", "biomech"),
    ):
        if record_id.startswith(prefix):
            return domain
    return "other"


def _classify_feature_family(record_id: str) -> str:
    return classify_feature_family(record_id)


def _record_feature_family(record: Any) -> str:
    family = getattr(record, "feature_family", None)
    if family not in {None, "", "unknown"}:
        return str(family)
    return _classify_feature_family(_record_id(record))


def _record_common_metadata(record: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for field in COMMON_RECORD_METADATA_FIELDS:
        if not hasattr(record, field):
            continue
        value = getattr(record, field, None)
        if value is None or value == "" or value == "unknown" or value == []:
            continue
        metadata[field] = value
    return metadata


def _record_availability(record: Any) -> str:
    availability = getattr(record, "availability", "assessed")
    return "assessed" if availability in {None, ""} else str(availability)


def _is_scoring_eligible(record: Any) -> bool:
    return _record_availability(record) == "assessed"


def _record_availability_gravity(
    record: Any,
    domain: str,
    low_confidence_score_weights: Mapping[str, float],
) -> float:
    availability = _record_availability(record)
    if availability == "assessed":
        return 1.0
    if availability == "low_confidence":
        return float(low_confidence_score_weights.get(domain, 0.0))
    return 0.0


def _record_depth_dependency(record: Any) -> str:
    depth_dependency = getattr(record, "depth_dependency", "unknown")
    if depth_dependency in {None, ""}:
        return "unknown"
    return str(depth_dependency)


def _record_depth_dependency_gravity(
    record: Any,
    depth_dependency_score_weights: Mapping[str, float],
) -> float:
    depth_dependency = _record_depth_dependency(record)
    return float(
        depth_dependency_score_weights.get(
            depth_dependency,
            depth_dependency_score_weights.get("unknown", 0.0),
        )
    )


def _record_focus_tier(record: Any) -> str:
    focus_tier = getattr(record, "focus_tier", "primary")
    if focus_tier in {None, ""}:
        return "primary"
    focus = str(focus_tier)
    return focus if focus in SCORING_FOCUS_TIERS else "primary"


def _record_focus_gravity(
    record: Any,
    scoring_focus_weights: Mapping[str, float],
) -> float:
    focus_tier = _record_focus_tier(record)
    return float(scoring_focus_weights.get(focus_tier, 1.0))


def _record_feature_score_gravity(
    record: Any,
    feature_score_weight_overrides: Mapping[str, float],
) -> float:
    record_id = _record_id(record)
    if record_id in feature_score_weight_overrides:
        return float(feature_score_weight_overrides[record_id])
    for pattern, weight in feature_score_weight_overrides.items():
        if not pattern.endswith(".*"):
            continue
        prefix = pattern[:-2]
        if record_id == prefix or record_id.startswith(prefix + "."):
            return float(weight)
    return 1.0


def _record_feature_score_direction(
    record: Any,
    feature_score_direction_overrides: Mapping[str, str],
) -> str:
    record_id = _record_id(record)
    if record_id in feature_score_direction_overrides:
        return str(feature_score_direction_overrides[record_id])
    for pattern, direction in feature_score_direction_overrides.items():
        if not pattern.endswith(".*"):
            continue
        prefix = pattern[:-2]
        if record_id == prefix or record_id.startswith(prefix + "."):
            return str(direction)
    return "two_sided"


def _apply_score_direction(z: float, score_direction: str) -> float:
    if score_direction == "upper_bound_only":
        return max(float(z), 0.0)
    if score_direction == "lower_bound_only":
        return min(float(z), 0.0)
    return float(z)


def _record_feature_family_weight(
    domain: str,
    feature_family: str,
    domain_feature_family_weights: Mapping[str, Mapping[str, float]],
) -> float | None:
    domain_weights = domain_feature_family_weights.get(domain)
    if not domain_weights:
        return None
    return float(domain_weights.get(feature_family, domain_weights.get("other", 0.0)))


def _record_scoring_gravity(
    record: Any,
    domain: str,
    low_confidence_score_weights: Mapping[str, float],
    depth_dependency_score_weights: Mapping[str, float],
    scoring_focus_weights: Mapping[str, float],
    feature_score_weight_overrides: Mapping[str, float],
) -> float:
    return (
        _record_availability_gravity(record, domain, low_confidence_score_weights)
        * _record_depth_dependency_gravity(record, depth_dependency_score_weights)
        * _record_focus_gravity(record, scoring_focus_weights)
        * _record_feature_score_gravity(record, feature_score_weight_overrides)
    )


def _withheld_score_reasons(
    availability_gravity: float,
    depth_gravity: float,
    focus_gravity: float,
    feature_gravity: float,
    family_weight: float | None = None,
) -> list[str]:
    reasons: list[str] = []
    if availability_gravity <= 0.0:
        reasons.append("availability_score_weight_zero")
    if depth_gravity <= 0.0:
        reasons.append("depth_dependency_score_weight_zero")
    if focus_gravity <= 0.0:
        reasons.append("scoring_focus_weight_zero")
    if feature_gravity <= 0.0:
        reasons.append("feature_score_weight_zero")
    if family_weight is not None and family_weight <= 0.0:
        reasons.append("feature_family_weight_zero")
    return reasons


def _withheld_feature_entry(
    record: Any,
    domain: str,
    scoring_reasons: Iterable[str] | None = None,
) -> dict[str, Any]:
    reasons = list(getattr(record, "availability_reasons", []) or [])
    for reason in scoring_reasons or []:
        if reason not in reasons:
            reasons.append(reason)
    entry = {
        "domain": domain,
        "feature_id": _record_id(record),
        "value": round(float(record.value), 4),
        "availability": _record_availability(record),
        "view_reliability": getattr(record, "view_reliability", None),
        "camera_zone": getattr(record, "camera_zone", None),
        "depth_dependency": getattr(record, "depth_dependency", None),
        "model_depth_reliability": getattr(record, "model_depth_reliability", None),
        "landmark_quality": getattr(record, "landmark_quality", None),
        "focus_tier": _record_focus_tier(record),
        "reasons": reasons,
    }
    entry.update(_record_common_metadata(record))
    return entry


# ── Baseline I/O ──────────────────────────────────────────────────────────────


def load_baseline(
    path: Path | str,
    exercise_id: str,
) -> dict[str, dict[str, float]]:
    """Load per-metric (mean, std) entries for one exercise from the baseline JSON.

    Returns an empty dict if the file is absent, malformed, or the exercise
    key is not present — so callers can always check `if not baseline`.
    """
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get(exercise_id, {})


def save_baseline(
    baseline_all: dict[str, dict[str, dict[str, float]]],
    path: Path | str,
) -> None:
    """Write the full baseline dict (all exercises) to JSON.

    baseline_all structure:
        { exercise_id: { feature_id: { "mean": float, "std": float } } }
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(baseline_all, f, indent=2, ensure_ascii=False)


def _record_value_is_finite(record: Any) -> bool:
    value = getattr(record, "value", None)
    if value is None:
        return False
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def build_baseline_from_records(
    feat_records: list["FeatureRecord"],
    biomech_records: list["BiomechRecord"],
    *,
    domain_feature_family_weights: Mapping[str, Mapping[str, float]] | None = None,
    low_confidence_score_weights: Mapping[str, float] | None = None,
    depth_dependency_score_weights: Mapping[str, float] | None = None,
    scoring_focus_weights: Mapping[str, float] | None = None,
    feature_score_weight_overrides: Mapping[str, float] | None = None,
    feature_score_direction_overrides: Mapping[str, str] | None = None,
) -> dict[str, dict[str, float]]:
    """Compute per-metric (mean, std) statistics from a set of normal-condition records.

    Intended to generate data/reference/baseline_zscore.json from the
    synthetic normal pipeline run. The returned dict is keyed by feature_id /
    metric_id and can be inserted under an exercise_id key before saving.

    σ is floored at max(σ_raw, _STD_FLOOR_RATIO × |μ|, _STD_ABS_FLOOR) to
    prevent near-zero division in the Z-score formula.
    """
    from collections import defaultdict

    score_weights = normalize_low_confidence_score_weights(low_confidence_score_weights)
    depth_weights = normalize_depth_dependency_score_weights(
        depth_dependency_score_weights
    )
    focus_weights = normalize_scoring_focus_weights(scoring_focus_weights)
    feature_weights = normalize_feature_score_weight_overrides(
        feature_score_weight_overrides
    )
    normalize_feature_score_direction_overrides(feature_score_direction_overrides)
    family_weights = normalize_domain_feature_family_weights(
        domain_feature_family_weights
    )
    values: dict[str, list[float]] = defaultdict(list)

    for r in feat_records:
        rid = _record_id(r)
        domain = _classify_domain(rid)
        family_weight = _record_feature_family_weight(
            domain, _record_feature_family(r), family_weights
        )
        if (
            _record_scoring_gravity(
                r, domain, score_weights, depth_weights, focus_weights, feature_weights
            )
            * (1.0 if family_weight is None else family_weight)
            <= 0.0
        ):
            continue
        if rid and r.value is not None and not np.isnan(float(r.value)):
            values[rid].append(float(r.value))
    for r in biomech_records:
        rid = _record_id(r)
        domain = _classify_domain(rid)
        family_weight = _record_feature_family_weight(
            domain, _record_feature_family(r), family_weights
        )
        if (
            _record_scoring_gravity(
                r, domain, score_weights, depth_weights, focus_weights, feature_weights
            )
            * (1.0 if family_weight is None else family_weight)
            <= 0.0
        ):
            continue
        if rid and r.value is not None and not np.isnan(float(r.value)):
            values[rid].append(float(r.value))

    baseline: dict[str, dict[str, float]] = {}
    for rid, vals in values.items():
        mu = float(np.mean(vals))
        sigma = float(np.std(vals, ddof=0 if len(vals) == 1 else 1))
        sigma = max(sigma, abs(mu) * _STD_FLOOR_RATIO, _STD_ABS_FLOOR)
        baseline[rid] = {"mean": round(mu, 6), "std": round(sigma, 6)}

    return baseline


def build_baseline_qc(
    feat_records: list["FeatureRecord"],
    biomech_records: list["BiomechRecord"],
    *,
    exercise_definition: "ExerciseDefinition",
    baseline_metrics: Mapping[str, Mapping[str, float]],
    baseline_status: str,
    source_type: str,
    pose_backend: str,
    coordinate_mode: str = "norm",
    recording_count: int = 1,
    source_files: list[str] | None = None,
    annotation_files: list[str] | None = None,
    manifest_path: str | None = None,
    pipeline_stages: list[str] | None = None,
    domain_feature_family_weights: Mapping[str, Mapping[str, float]] | None = None,
    low_confidence_score_weights: Mapping[str, float] | None = None,
    depth_dependency_score_weights: Mapping[str, float] | None = None,
    scoring_focus_weights: Mapping[str, float] | None = None,
    feature_score_weight_overrides: Mapping[str, float] | None = None,
    feature_score_direction_overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build QC/provenance metadata for baseline generation.

    The metric-statistics baseline remains backward compatible in
    ``baseline_zscore.json``. This QC payload records the baseline tier and
    the evidence that was included or withheld from baseline statistics.
    """

    if baseline_status not in BASELINE_STATUSES:
        valid = ", ".join(BASELINE_STATUSES)
        raise ValueError(
            f"baseline_status must be one of {valid}; got {baseline_status!r}."
        )
    if recording_count < 1:
        raise ValueError("recording_count must be >= 1.")

    score_weights = normalize_low_confidence_score_weights(low_confidence_score_weights)
    depth_weights = normalize_depth_dependency_score_weights(
        depth_dependency_score_weights
    )
    focus_weights = normalize_scoring_focus_weights(scoring_focus_weights)
    feature_weights = normalize_feature_score_weight_overrides(
        feature_score_weight_overrides
    )
    feature_directions = normalize_feature_score_direction_overrides(
        feature_score_direction_overrides
    )
    family_weights = normalize_domain_feature_family_weights(
        domain_feature_family_weights
    )
    records = list(feat_records) + list(biomech_records)
    availability_counts = Counter(_record_availability(record) for record in records)
    assessed_records = [
        record
        for record in records
        for domain in [_classify_domain(_record_id(record))]
        for family_weight in [
            _record_feature_family_weight(
                domain, _record_feature_family(record), family_weights
            )
        ]
        if _record_scoring_gravity(
            record,
            domain,
            score_weights,
            depth_weights,
            focus_weights,
            feature_weights,
        )
        * (1.0 if family_weight is None else family_weight)
        > 0.0
        and _record_value_is_finite(record)
    ]
    withheld_records = [
        record
        for record in records
        for domain in [_classify_domain(_record_id(record))]
        for family_weight in [
            _record_feature_family_weight(
                domain, _record_feature_family(record), family_weights
            )
        ]
        if _record_scoring_gravity(
            record,
            domain,
            score_weights,
            depth_weights,
            focus_weights,
            feature_weights,
        )
        * (1.0 if family_weight is None else family_weight)
        <= 0.0
        or not _record_value_is_finite(record)
    ]
    included_metric_ids = sorted(baseline_metrics.keys())
    withheld_metric_ids = sorted(
        {_record_id(record) for record in withheld_records if _record_id(record)}
    )
    rep_ids = sorted(
        {
            int(rep_id)
            for rep_id in (getattr(record, "rep_id", None) for record in records)
            if rep_id is not None
        }
    )
    included_domain_counts = Counter(
        _classify_domain(metric_id) for metric_id in included_metric_ids
    )
    withheld_availability_counts = Counter(
        _record_availability(record) for record in withheld_records
    )
    withheld_reason_counts = Counter(
        reason
        for record in withheld_records
        for reason in (getattr(record, "availability_reasons", []) or [])
    )

    return {
        "exercise_id": exercise_definition.exercise_id,
        "definition_version": str(exercise_definition.version),
        "baseline_status": baseline_status,
        "source_type": source_type,
        "pose_backend": pose_backend,
        "coordinate_mode": coordinate_mode,
        "recording_count": int(recording_count),
        "rep_count": len(rep_ids),
        "rep_ids": rep_ids,
        "record_count": len(records),
        "record_type_counts": {
            "feature": len(feat_records),
            "biomech": len(biomech_records),
        },
        "availability_counts": dict(sorted(availability_counts.items())),
        "included_record_count": len(assessed_records),
        "withheld_record_count": len(withheld_records),
        "included_metric_count": len(included_metric_ids),
        "withheld_metric_count": len(withheld_metric_ids),
        "included_metric_ids": included_metric_ids,
        "withheld_metric_ids": withheld_metric_ids,
        "included_domain_counts": dict(sorted(included_domain_counts.items())),
        "withheld_availability_counts": dict(
            sorted(withheld_availability_counts.items())
        ),
        "withheld_reason_counts": dict(sorted(withheld_reason_counts.items())),
        "source_files": list(source_files or []),
        "annotation_files": list(annotation_files or []),
        "manifest_path": manifest_path,
        "pipeline_stages": list(
            pipeline_stages
            or [
                "validation",
                "annotation",
                "exercise_definition",
                "preprocessing",
                "normalization",
                "canonicalization",
                "rep_segmentation",
                "phase_segmentation",
                "feature_extraction",
                "biomechanical_proxy",
            ]
        ),
        "low_confidence_score_weights": score_weights,
        "domain_feature_family_weights": family_weights,
        "depth_dependency_score_weights": depth_weights,
        "scoring_focus_weights": focus_weights,
        "feature_score_weight_overrides": feature_weights,
        "feature_score_direction_overrides": feature_directions,
    }


def save_baseline_qc(qc_payload: Mapping[str, Any], path: Path | str) -> None:
    """Write baseline QC/provenance metadata to JSON."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(qc_payload), f, indent=2, ensure_ascii=False)


# ── Scoring engine ────────────────────────────────────────────────────────────


def _mandatory_range_of_motion_ratio(
    feat_records: list["FeatureRecord"],
    exercise_definition: "ExerciseDefinition",
    baseline: dict[str, dict[str, float]],
) -> float:
    """Compute the fraction of expected primary-joint ROM achieved.

    Uses range-of-motion features whose feature_id contains the name of any landmark in
    exercise_definition.landmarks.primary_joints. Returns 1.0 when no ROM
    baseline data is available (no floor penalty applied).
    """
    primary_joints = set(exercise_definition.landmarks.primary_joints or [])
    ratios: list[float] = []

    range_of_motion_targets = _range_of_motion_target_rules(exercise_definition)

    for r in feat_records:
        if not _is_scoring_eligible(r):
            continue
        rid = _record_id(r)
        if not rid.startswith("spatial.range_of_motion.xy."):
            continue
        if not any(j in rid for j in primary_joints):
            continue
        target = _matching_range_of_motion_target(rid, range_of_motion_targets)
        if target is not None:
            expected = target.get("minimum_sufficient_deg")
        elif rid in baseline:
            expected = baseline[rid]["mean"]
        else:
            continue
        if expected < 1e-6:
            continue
        ratios.append(min(float(r.value) / expected, 1.0))

    return float(np.mean(ratios)) if ratios else 1.0


def _range_of_motion_target_rules(
    exercise_definition: "ExerciseDefinition",
) -> dict[str, dict[str, Any]]:
    quality_rules = getattr(exercise_definition, "quality_rules", None)
    raw_rules = getattr(quality_rules, "raw", {}) or {}
    targets = raw_rules.get("range_of_motion_targets") or {}
    if not isinstance(targets, Mapping):
        return {}

    parsed: dict[str, dict[str, Any]] = {}
    for feature_id, rule in targets.items():
        if not isinstance(rule, Mapping):
            continue
        if str(rule.get("scoring_mode", "")) != "minimum_sufficient_band":
            continue
        try:
            minimum = float(rule["minimum_sufficient_deg"])
            tolerance = max(float(rule.get("soft_tolerance_deg", 1.0)), 1e-6)
        except (KeyError, TypeError, ValueError):
            continue

        excessive_raw = rule.get("excessive_threshold_deg")
        excessive = None
        if excessive_raw is not None:
            try:
                excessive = float(excessive_raw)
            except (TypeError, ValueError):
                excessive = None

        suffixes = [
            str(item) for item in rule.get("apply_to_phase_suffixes", ["full_rep"])
        ]
        if not suffixes:
            suffixes = ["full_rep"]

        parsed[str(feature_id)] = {
            "scoring_mode": "minimum_sufficient_band",
            "minimum_sufficient_deg": minimum,
            "excessive_threshold_deg": excessive,
            "soft_tolerance_deg": tolerance,
            "excessive_penalty_scale": float(rule.get("excessive_penalty_scale", 1.0)),
            "apply_to_phase_suffixes": suffixes,
        }
    return parsed


def _matching_range_of_motion_target(
    record_id: str,
    range_of_motion_targets: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    for base_id, rule in range_of_motion_targets.items():
        if record_id == base_id:
            suffix = "full_rep"
        elif record_id.startswith(f"{base_id}."):
            suffix = record_id[len(base_id) + 1 :]
        else:
            continue

        allowed_suffixes = set(rule.get("apply_to_phase_suffixes") or ["full_rep"])
        if suffix not in allowed_suffixes:
            return None
        return dict(rule)
    return None


def _range_of_motion_target_band_z(value: float, rule: Mapping[str, Any]) -> float:
    minimum = float(rule["minimum_sufficient_deg"])
    tolerance = float(rule["soft_tolerance_deg"])
    excessive = rule.get("excessive_threshold_deg")

    if value < minimum:
        return (value - minimum) / tolerance
    if excessive is not None and value > float(excessive):
        scale = float(rule.get("excessive_penalty_scale", 1.0))
        return scale * (value - float(excessive)) / tolerance
    return 0.0


def _first_present(rule: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in rule:
            return rule[key]
    raise KeyError(keys[0])


def _temporal_tolerance_band_rules(
    exercise_definition: "ExerciseDefinition",
) -> dict[str, dict[str, Any]]:
    quality_rules = getattr(exercise_definition, "quality_rules", None)
    raw_rules = getattr(quality_rules, "raw", {}) or {}
    targets = raw_rules.get("temporal_tolerance_bands") or {}
    if not isinstance(targets, Mapping):
        return {}

    parsed: dict[str, dict[str, Any]] = {}
    for feature_id, rule in targets.items():
        if not isinstance(rule, Mapping):
            continue
        if str(rule.get("scoring_mode", "")) != "acceptable_duration_band":
            continue
        try:
            lower = float(
                _first_present(
                    rule,
                    "minimum_duration_s",
                    "min_duration_s",
                    "minimum_s",
                    "min_s",
                )
            )
            upper = float(
                _first_present(
                    rule,
                    "maximum_duration_s",
                    "max_duration_s",
                    "maximum_s",
                    "max_s",
                )
            )
            tolerance = max(float(rule.get("soft_tolerance_s", 0.1)), 1e-6)
        except (KeyError, TypeError, ValueError):
            continue
        if lower > upper:
            continue

        parsed[str(feature_id)] = {
            "scoring_mode": "acceptable_duration_band",
            "minimum_duration_s": lower,
            "maximum_duration_s": upper,
            "soft_tolerance_s": tolerance,
        }
    return parsed


def _matching_temporal_tolerance_band(
    record_id: str,
    temporal_tolerance_bands: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    if record_id in temporal_tolerance_bands:
        return dict(temporal_tolerance_bands[record_id])
    for pattern, rule in temporal_tolerance_bands.items():
        if pattern.endswith(".*") and record_id.startswith(pattern[:-1]):
            return dict(rule)
    return None


def _temporal_tolerance_band_z(value: float, rule: Mapping[str, Any]) -> float:
    lower = float(rule["minimum_duration_s"])
    upper = float(rule["maximum_duration_s"])
    tolerance = float(rule["soft_tolerance_s"])

    if value < lower:
        return (value - lower) / tolerance
    if value > upper:
        return (value - upper) / tolerance
    return 0.0


def _temporal_variability_band_rules(
    exercise_definition: "ExerciseDefinition",
) -> dict[str, dict[str, Any]]:
    quality_rules = getattr(exercise_definition, "quality_rules", None)
    raw_rules = getattr(quality_rules, "raw", {}) or {}
    targets = raw_rules.get("temporal_variability_bands") or {}
    if not isinstance(targets, Mapping):
        return {}

    parsed: dict[str, dict[str, Any]] = {}
    for feature_id, rule in targets.items():
        if not isinstance(rule, Mapping):
            continue
        if str(rule.get("scoring_mode", "")) != "maximum_sufficient_ceiling":
            continue
        try:
            maximum = float(_first_present(rule, "maximum_cv", "max_cv"))
            tolerance = max(float(rule.get("soft_tolerance_cv", 0.01)), 1e-6)
        except (KeyError, TypeError, ValueError):
            continue

        parsed[str(feature_id)] = {
            "scoring_mode": "maximum_sufficient_ceiling",
            "maximum_cv": maximum,
            "soft_tolerance_cv": tolerance,
        }
    return parsed


def _matching_temporal_variability_band(
    record_id: str,
    temporal_variability_bands: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    if record_id in temporal_variability_bands:
        return dict(temporal_variability_bands[record_id])
    for pattern, rule in temporal_variability_bands.items():
        if pattern.endswith(".*") and record_id.startswith(pattern[:-1]):
            return dict(rule)
    return None


def _temporal_variability_band_z(value: float, rule: Mapping[str, Any]) -> float:
    maximum = float(rule["maximum_cv"])
    tolerance = float(rule["soft_tolerance_cv"])

    if value > maximum:
        return (value - maximum) / tolerance
    return 0.0


def _temporal_phase_profile_band_rules(
    exercise_definition: "ExerciseDefinition",
) -> dict[str, dict[str, Any]]:
    quality_rules = getattr(exercise_definition, "quality_rules", None)
    raw_rules = getattr(quality_rules, "raw", {}) or {}
    targets = raw_rules.get("temporal_phase_profile_bands") or {}
    if not isinstance(targets, Mapping):
        return {}

    parsed: dict[str, dict[str, Any]] = {}
    for feature_id, rule in targets.items():
        if not isinstance(rule, Mapping):
            continue
        if str(rule.get("scoring_mode", "")) != "acceptable_ratio_band":
            continue
        try:
            lower = float(_first_present(rule, "minimum_ratio", "min_ratio"))
            upper = float(_first_present(rule, "maximum_ratio", "max_ratio"))
            tolerance = max(float(rule.get("soft_tolerance_ratio", 0.1)), 1e-6)
        except (KeyError, TypeError, ValueError):
            continue
        if lower > upper:
            continue

        parsed[str(feature_id)] = {
            "scoring_mode": "acceptable_ratio_band",
            "minimum_ratio": lower,
            "maximum_ratio": upper,
            "soft_tolerance_ratio": tolerance,
        }
    return parsed


def _matching_temporal_phase_profile_band(
    record_id: str,
    temporal_phase_profile_bands: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    if record_id in temporal_phase_profile_bands:
        return dict(temporal_phase_profile_bands[record_id])
    for pattern, rule in temporal_phase_profile_bands.items():
        if pattern.endswith(".*") and record_id.startswith(pattern[:-1]):
            return dict(rule)
    return None


def _temporal_phase_profile_band_z(value: float, rule: Mapping[str, Any]) -> float:
    lower = float(rule["minimum_ratio"])
    upper = float(rule["maximum_ratio"])
    tolerance = float(rule["soft_tolerance_ratio"])

    if value < lower:
        return (value - lower) / tolerance
    if value > upper:
        return (value - upper) / tolerance
    return 0.0


def _derive_domain_score(
    records: list[tuple[Any, float, float, float, float, str, float | None]],
    baseline: dict[str, dict[str, float]],
    floor_dynamic: float,
    score_bounds: dict[str, float],
    range_of_motion_targets: Mapping[str, Mapping[str, Any]] | None = None,
    temporal_tolerance_bands: Mapping[str, Mapping[str, Any]] | None = None,
    temporal_variability_bands: Mapping[str, Mapping[str, Any]] | None = None,
    temporal_phase_profile_bands: Mapping[str, Mapping[str, Any]] | None = None,
    feature_score_direction_overrides: Mapping[str, str] | None = None,
) -> tuple[float, bool, list[dict[str, Any]]]:
    """Compute one domain score via the Z-score deduction formula.

    Score = max(floor_dynamic, score_max − Σ_i scaled_deduction_i)
    When feature-family weights are configured, weights are assigned as
    family_weight / n_valid_records_in_family. Otherwise the function falls back
    to equal within-domain weights: w_i = 1 / n.

    Returns
    -------
    (score, floor_was_applied, deduction_details)
    """
    valid = [
        (
            record,
            availability_gravity,
            depth_gravity,
            focus_gravity,
            feature_gravity,
            feature_family,
            family_weight,
        )
        for (
            record,
            availability_gravity,
            depth_gravity,
            focus_gravity,
            feature_gravity,
            feature_family,
            family_weight,
        ) in records
        if availability_gravity * depth_gravity * focus_gravity * feature_gravity > 0.0
        and _record_id(record) in baseline
    ]
    if not valid:
        return score_bounds["max"], False, []

    family_counts: Counter[str] = Counter()
    for _, _, _, _, _, feature_family, family_weight in valid:
        if family_weight is not None:
            family_counts[feature_family] += 1

    n = len(valid)
    fallback_w_i = 1.0 / n
    score_span = score_bounds["max"] - score_bounds["min"]
    deduction_scale = score_span / 100.0
    deductions: list[dict[str, Any]] = []
    total_deduction = 0.0

    for (
        r,
        availability_gravity,
        depth_gravity,
        focus_gravity,
        feature_gravity,
        feature_family,
        family_weight,
    ) in valid:
        rid = _record_id(r)
        mu = baseline[rid]["mean"]
        sigma = max(
            baseline[rid]["std"],
            abs(mu) * _STD_FLOOR_RATIO,
            _STD_ABS_FLOOR,
        )
        value = float(r.value)
        range_of_motion_target = _matching_range_of_motion_target(
            rid, range_of_motion_targets or {}
        )
        temporal_tolerance_band = None
        temporal_variability_band = None
        temporal_phase_profile_band = None
        if range_of_motion_target is not None:
            z_raw = _range_of_motion_target_band_z(value, range_of_motion_target)
            scoring_mode = range_of_motion_target["scoring_mode"]
        else:
            temporal_tolerance_band = _matching_temporal_tolerance_band(
                rid, temporal_tolerance_bands or {}
            )
            if temporal_tolerance_band is not None:
                z_raw = _temporal_tolerance_band_z(value, temporal_tolerance_band)
                scoring_mode = temporal_tolerance_band["scoring_mode"]
            else:
                temporal_tolerance_band = None
                temporal_variability_band = _matching_temporal_variability_band(
                    rid, temporal_variability_bands or {}
                )
                if temporal_variability_band is not None:
                    z_raw = _temporal_variability_band_z(
                        value, temporal_variability_band
                    )
                    scoring_mode = temporal_variability_band["scoring_mode"]
                else:
                    temporal_variability_band = None
                    temporal_phase_profile_band = _matching_temporal_phase_profile_band(
                        rid, temporal_phase_profile_bands or {}
                    )
                    if temporal_phase_profile_band is not None:
                        z_raw = _temporal_phase_profile_band_z(
                            value, temporal_phase_profile_band
                        )
                        scoring_mode = temporal_phase_profile_band["scoring_mode"]
                    else:
                        z_raw = (value - mu) / sigma
                        scoring_mode = "baseline_zscore"
        score_direction = _record_feature_score_direction(
            r, feature_score_direction_overrides or {}
        )
        z = _apply_score_direction(z_raw, score_direction)
        gravity = availability_gravity * depth_gravity * focus_gravity * feature_gravity
        if family_weight is None:
            w_i = fallback_w_i
        else:
            w_i = family_weight / family_counts[feature_family]
        d = deduction_scale * w_i * abs(z) * gravity
        total_deduction += d
        deduction_entry = {
            "feature_id": rid,
            "value": round(value, 4),
            "scoring_mode": scoring_mode,
            "availability": _record_availability(r),
            "availability_weight": round(float(availability_gravity), 4),
            "depth_dependency": _record_depth_dependency(r),
            "depth_dependency_weight": round(float(depth_gravity), 4),
            "focus_tier": _record_focus_tier(r),
            "focus_weight": round(float(focus_gravity), 4),
            "feature_weight": round(float(feature_gravity), 4),
            "feature_family": feature_family,
            "feature_family_weight": (
                None if family_weight is None else round(float(family_weight), 4)
            ),
            "confidence_weight": round(float(gravity), 4),
            "baseline_mean": round(mu, 4),
            "baseline_std": round(sigma, 4),
            "score_direction": score_direction,
            "z_raw": round(z_raw, 3),
            "z": round(z, 3),
            "w": round(w_i, 4),
            "deduction": round(d, 4),
        }
        deduction_entry.update(_record_common_metadata(r))
        deductions.append(deduction_entry)
        if range_of_motion_target is not None:
            deductions[-1].update(
                {
                    "target_min": round(
                        float(range_of_motion_target["minimum_sufficient_deg"]), 4
                    ),
                    "target_excessive": (
                        None
                        if range_of_motion_target.get("excessive_threshold_deg") is None
                        else round(
                            float(range_of_motion_target["excessive_threshold_deg"]), 4
                        )
                    ),
                    "target_tolerance": round(
                        float(range_of_motion_target["soft_tolerance_deg"]), 4
                    ),
                }
            )
        if temporal_tolerance_band is not None:
            deductions[-1].update(
                {
                    "target_min_s": round(
                        float(temporal_tolerance_band["minimum_duration_s"]), 4
                    ),
                    "target_max_s": round(
                        float(temporal_tolerance_band["maximum_duration_s"]), 4
                    ),
                    "target_tolerance_s": round(
                        float(temporal_tolerance_band["soft_tolerance_s"]), 4
                    ),
                }
            )
        if temporal_variability_band is not None:
            deductions[-1].update(
                {
                    "target_max_cv": round(
                        float(temporal_variability_band["maximum_cv"]), 4
                    ),
                    "target_tolerance_cv": round(
                        float(temporal_variability_band["soft_tolerance_cv"]), 4
                    ),
                }
            )
        if temporal_phase_profile_band is not None:
            deductions[-1].update(
                {
                    "target_min_ratio": round(
                        float(temporal_phase_profile_band["minimum_ratio"]), 4
                    ),
                    "target_max_ratio": round(
                        float(temporal_phase_profile_band["maximum_ratio"]), 4
                    ),
                    "target_tolerance_ratio": round(
                        float(temporal_phase_profile_band["soft_tolerance_ratio"]),
                        4,
                    ),
                }
            )

    raw_score = max(score_bounds["min"], score_bounds["max"] - total_deduction)
    final_score = max(floor_dynamic, raw_score)
    floor_applied = raw_score < floor_dynamic

    return round(final_score, 2), floor_applied, deductions


def _score_one_rep(
    feat_rep: list["FeatureRecord"],
    biomech_rep: list["BiomechRecord"],
    exercise_definition: "ExerciseDefinition",
    definition_version: str,
    rep_id: int | None,
    baseline: dict[str, dict[str, float]],
    domain_weights: dict[str, float],
    domain_feature_family_weights: dict[str, dict[str, float]],
    low_confidence_score_weights: dict[str, float],
    depth_dependency_score_weights: dict[str, float],
    scoring_focus_weights: dict[str, float],
    feature_score_weight_overrides: dict[str, float],
    feature_score_direction_overrides: dict[str, str],
    score_bounds: dict[str, float],
) -> BiomarkerScoreRecord:
    """Compute BiomarkerScoreRecord for one rep (or the full sequence)."""
    domain_records: dict[
        str, list[tuple[Any, float, float, float, float, str, float | None]]
    ] = {d: [] for d in _SCORE_DOMAIN_ORDER}
    withheld_features: list[dict[str, Any]] = []

    for r in feat_rep:
        d = _classify_domain(_record_id(r))
        if d in domain_records:
            availability_gravity = _record_availability_gravity(
                r, d, low_confidence_score_weights
            )
            depth_gravity = _record_depth_dependency_gravity(
                r, depth_dependency_score_weights
            )
            focus_gravity = _record_focus_gravity(r, scoring_focus_weights)
            feature_gravity = _record_feature_score_gravity(
                r, feature_score_weight_overrides
            )
            feature_family = _record_feature_family(r)
            family_weight = _record_feature_family_weight(
                d, feature_family, domain_feature_family_weights
            )
            if (
                availability_gravity
                * depth_gravity
                * focus_gravity
                * feature_gravity
                * (1.0 if family_weight is None else family_weight)
                > 0.0
            ):
                domain_records[d].append(
                    (
                        r,
                        availability_gravity,
                        depth_gravity,
                        focus_gravity,
                        feature_gravity,
                        feature_family,
                        family_weight,
                    )
                )
            else:
                withheld_features.append(
                    _withheld_feature_entry(
                        r,
                        d,
                        _withheld_score_reasons(
                            availability_gravity,
                            depth_gravity,
                            focus_gravity,
                            feature_gravity,
                            family_weight,
                        ),
                    )
                )
    for r in biomech_rep:
        d = _classify_domain(_record_id(r))
        if d in domain_records:
            availability_gravity = _record_availability_gravity(
                r, d, low_confidence_score_weights
            )
            depth_gravity = _record_depth_dependency_gravity(
                r, depth_dependency_score_weights
            )
            focus_gravity = _record_focus_gravity(r, scoring_focus_weights)
            feature_gravity = _record_feature_score_gravity(
                r, feature_score_weight_overrides
            )
            feature_family = _record_feature_family(r)
            family_weight = _record_feature_family_weight(
                d, feature_family, domain_feature_family_weights
            )
            if (
                availability_gravity
                * depth_gravity
                * focus_gravity
                * feature_gravity
                * (1.0 if family_weight is None else family_weight)
                > 0.0
            ):
                domain_records[d].append(
                    (
                        r,
                        availability_gravity,
                        depth_gravity,
                        focus_gravity,
                        feature_gravity,
                        feature_family,
                        family_weight,
                    )
                )
            else:
                withheld_features.append(
                    _withheld_feature_entry(
                        r,
                        d,
                        _withheld_score_reasons(
                            availability_gravity,
                            depth_gravity,
                            focus_gravity,
                            feature_gravity,
                            family_weight,
                        ),
                    )
                )

    range_of_motion_ratio = _mandatory_range_of_motion_ratio(
        feat_rep, exercise_definition, baseline
    )
    range_of_motion_targets = _range_of_motion_target_rules(exercise_definition)
    temporal_tolerance_bands = _temporal_tolerance_band_rules(exercise_definition)
    temporal_variability_bands = _temporal_variability_band_rules(exercise_definition)
    temporal_phase_profile_bands = _temporal_phase_profile_band_rules(
        exercise_definition
    )
    score_span = score_bounds["max"] - score_bounds["min"]
    floor_dynamic = score_bounds["min"] + 0.50 * score_span * max(
        0.0, min(1.0, range_of_motion_ratio)
    )

    domain_scores: dict[str, float] = {}
    floor_applied: dict[str, bool] = {}
    all_deductions: list[dict[str, Any]] = []

    for domain in _SCORE_DOMAIN_ORDER:
        score_d, floor_d, ded_d = _derive_domain_score(
            domain_records[domain],
            baseline,
            floor_dynamic,
            score_bounds,
            range_of_motion_targets,
            temporal_tolerance_bands,
            temporal_variability_bands,
            temporal_phase_profile_bands,
            feature_score_direction_overrides,
        )
        domain_scores[domain] = score_d
        floor_applied[domain] = floor_d
        for item in ded_d:
            item["domain"] = domain
        all_deductions.extend(ded_d)

    final_score = sum(domain_weights[d] * domain_scores[d] for d in _SCORE_DOMAIN_ORDER)

    return BiomarkerScoreRecord(
        score_id="rep_quality_score",
        exercise_id=exercise_definition.exercise_id,
        definition_version=definition_version,
        rep_id=rep_id,
        domain_scores=domain_scores,
        floor_applied=floor_applied,
        deductions=all_deductions,
        final_score=round(final_score, 2),
        withheld_features=withheld_features,
        source_fields=["feature_domains", "biomechanical_focus", "quality_rules"],
        domain_weights=domain_weights,
        domain_feature_family_weights=domain_feature_family_weights,
        low_confidence_score_weights=low_confidence_score_weights,
        depth_dependency_score_weights=depth_dependency_score_weights,
        scoring_focus_weights=scoring_focus_weights,
        feature_score_weight_overrides=feature_score_weight_overrides,
        feature_score_direction_overrides=feature_score_direction_overrides,
        score_bounds=score_bounds,
    )


# ── Public entry point ────────────────────────────────────────────────────────


def derive_biomarkers(
    feat_records: list["FeatureRecord"],
    biomech_records: list["BiomechRecord"],
    exercise_definition: "ExerciseDefinition",
    definition_version: str,
    *,
    baseline_path: Path | str | None = None,
    domain_weights: Mapping[str, float] | None = None,
    domain_feature_family_weights: Mapping[str, Mapping[str, float]] | None = None,
    low_confidence_score_weights: Mapping[str, float] | None = None,
    depth_dependency_score_weights: Mapping[str, float] | None = None,
    scoring_focus_weights: Mapping[str, float] | None = None,
    feature_score_weight_overrides: Mapping[str, float] | None = None,
    feature_score_direction_overrides: Mapping[str, str] | None = None,
    score_bounds: Mapping[str, float] | None = None,
) -> tuple[list[Any], list[BiomarkerScoreRecord]]:
    """Main entry point for ⑩ Biomarker Derivation.

    Converts FeatureRecord and BiomechRecord into:
    1. BiomarkerRecord list — individual metrics with provenance (pass-through).
    2. BiomarkerScoreRecord list — per-rep composite movement quality scores.

    Scoring (step 2) requires a synthetic-normal baseline entry for the target
    exercise. If the file or exercise entry is absent, step 2 is skipped with a
    UserWarning. Generate or extend the baseline with scripts/compute_baseline.py.

    Parameters
    ----------
    feat_records       : output of features.extract_rep_features()
    biomech_records    : output of biomech.extract_rep_biomech()
    exercise_definition: loaded ExerciseDefinition
    definition_version : exercise YAML version (exercise_def.version)
    baseline_path      : path to baseline JSON.
                         None → data/reference/baseline_zscore.json
    domain_weights     : optional relative score-domain weights.
                         Defaults to equal normalized weights across domains.
    domain_feature_family_weights : optional relative feature-family budgets
                         within each configured score domain. Missing domains
                         fall back to equal within-domain weights.
    low_confidence_score_weights : optional per-domain gravity for low-confidence
                         records. Defaults to low biomech gravity and zero for
                         other low-confidence domains.
    depth_dependency_score_weights : optional gravity by depth-dependency class.
                         Defaults to recording-view-heavy scoring.
    scoring_focus_weights : optional gravity by exercise-definition focus tier.
                         Defaults to primary strongest, diagnostics withheld.
    feature_score_weight_overrides : optional exact feature-id or `prefix.*`
                         gravity overrides. Defaults to no feature-specific
                         override.
    feature_score_direction_overrides : optional exact feature-id or `prefix.*`
                         scoring direction overrides. Defaults to two-sided
                         baseline deviation.
    score_bounds       : optional score scale, e.g. {"min": 0, "max": 100}.
                         Defaults to 0–100.

    Returns
    -------
    (biomarker_records, score_records)
    """
    from movement.biomarker import from_biomech_record, from_feature_record

    # ── 1. Pass-through BiomarkerRecord ──────────────────────────────────────
    biomarker_records: list[Any] = []
    for r in feat_records:
        try:
            biomarker_records.append(from_feature_record(r, definition_version))
        except ValueError:
            pass
    for r in biomech_records:
        try:
            biomarker_records.append(from_biomech_record(r, definition_version))
        except ValueError:
            pass

    # ── 2. Composite score computation ───────────────────────────────────────
    if baseline_path is None:
        baseline_path = _PROJECT_ROOT / "data" / "reference" / "baseline_zscore.json"

    baseline = load_baseline(baseline_path, exercise_definition.exercise_id)

    if not baseline:
        warnings.warn(
            "[biomarker] Baseline entry unavailable for "
            f"exercise_id='{exercise_definition.exercise_id}' at '{baseline_path}'. "
            "BiomarkerScoreRecord computation skipped. "
            "Run scripts/compute_baseline.py to generate or extend the baseline.",
            UserWarning,
            stacklevel=2,
        )
        return biomarker_records, []

    normalized_domain_weights = normalize_domain_weights(domain_weights)
    normalized_domain_feature_family_weights = normalize_domain_feature_family_weights(
        domain_feature_family_weights
    )
    normalized_low_confidence_score_weights = normalize_low_confidence_score_weights(
        low_confidence_score_weights
    )
    normalized_depth_dependency_score_weights = (
        normalize_depth_dependency_score_weights(depth_dependency_score_weights)
    )
    normalized_scoring_focus_weights = normalize_scoring_focus_weights(
        scoring_focus_weights
    )
    normalized_feature_score_weight_overrides = (
        normalize_feature_score_weight_overrides(feature_score_weight_overrides)
    )
    normalized_feature_score_direction_overrides = (
        normalize_feature_score_direction_overrides(feature_score_direction_overrides)
    )
    normalized_score_bounds = normalize_score_bounds(score_bounds)

    rep_ids: set[int] = set()
    for r in feat_records:
        if r.rep_id is not None:
            rep_ids.add(int(r.rep_id))
    for r in biomech_records:
        if r.rep_id is not None:
            rep_ids.add(int(r.rep_id))

    score_records: list[BiomarkerScoreRecord] = []

    if rep_ids:
        sequence_temporal_records = [
            r
            for r in feat_records
            if r.rep_id is None and _record_id(r).startswith("temporal.variability.")
        ]
        for rep_id in sorted(rep_ids):
            feat_rep = [
                r for r in feat_records if r.rep_id == rep_id
            ] + sequence_temporal_records
            biomech_rep = [r for r in biomech_records if r.rep_id == rep_id]
            score_records.append(
                _score_one_rep(
                    feat_rep,
                    biomech_rep,
                    exercise_definition,
                    definition_version,
                    rep_id,
                    baseline,
                    normalized_domain_weights,
                    normalized_domain_feature_family_weights,
                    normalized_low_confidence_score_weights,
                    normalized_depth_dependency_score_weights,
                    normalized_scoring_focus_weights,
                    normalized_feature_score_weight_overrides,
                    normalized_feature_score_direction_overrides,
                    normalized_score_bounds,
                )
            )
    else:
        score_records.append(
            _score_one_rep(
                feat_records,
                biomech_records,
                exercise_definition,
                definition_version,
                None,
                baseline,
                normalized_domain_weights,
                normalized_domain_feature_family_weights,
                normalized_low_confidence_score_weights,
                normalized_depth_dependency_score_weights,
                normalized_scoring_focus_weights,
                normalized_feature_score_weight_overrides,
                normalized_feature_score_direction_overrides,
                normalized_score_bounds,
            )
        )

    return biomarker_records, score_records


__all__ = [
    "BiomarkerScoreRecord",
    "DOMAIN_WEIGHTS",
    "DEFAULT_LOW_CONFIDENCE_SCORE_WEIGHTS",
    "DEFAULT_DEPTH_DEPENDENCY_SCORE_WEIGHTS",
    "DEFAULT_SCORING_FOCUS_WEIGHTS",
    "DEFAULT_FEATURE_SCORE_WEIGHT_OVERRIDES",
    "DEFAULT_FEATURE_SCORE_DIRECTION_OVERRIDES",
    "DEFAULT_DOMAIN_FEATURE_FAMILY_WEIGHTS",
    "DEFAULT_SCORE_BOUNDS",
    "normalize_domain_weights",
    "normalize_score_bounds",
    "normalize_low_confidence_score_weights",
    "normalize_depth_dependency_score_weights",
    "normalize_scoring_focus_weights",
    "normalize_feature_score_weight_overrides",
    "normalize_feature_score_direction_overrides",
    "normalize_domain_feature_family_weights",
    "build_baseline_from_records",
    "build_baseline_qc",
    "save_baseline",
    "save_baseline_qc",
    "load_baseline",
    "derive_biomarkers",
]
