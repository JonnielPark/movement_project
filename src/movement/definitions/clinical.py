"""
Clinical Cross-Mapping Utilities

Loads movement-quality crosswalk metadata from data/definitions/clinical/fms_mapping.yaml
and converts biomarker composite scores into dashboard-ready traffic-light
labels. The mapping is interpretive support only: it does not reproduce FMS
scoring text and does not make medical conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_FMS_MAPPING_PATH = (
    _PROJECT_ROOT / "data" / "definitions" / "clinical" / "fms_mapping.yaml"
)


@dataclass(frozen=True)
class TrafficLightBand:
    """Score interval for a dashboard traffic-light label.

    The interval is based on the project's 0-100 biomarker score and provides
    a quick review cue for movement-quality patterns; it is not an FMS score.
    """

    label: str
    meaning: str
    score_range: tuple[float, float]

    def contains(self, score: float) -> bool:
        low, high = self.score_range
        return low <= score <= high


@dataclass(frozen=True)
class FmsCriterionMapping:
    """One feature-domain crosswalk entry for FMS-like movement observation."""

    id: str
    domain: str
    feature_id_prefix: str
    rationale: str


@dataclass(frozen=True)
class FmsExerciseMapping:
    """FMS-like crosswalk metadata for one exercise."""

    exercise_id: str
    reference_screen: str
    fms_test: str
    traffic_light_mapping: dict[str, TrafficLightBand] = field(default_factory=dict)
    linked_criteria: list[FmsCriterionMapping] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    source_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TrafficLightLabel:
    """Resolved traffic-light label for one biomarker score."""

    exercise_id: str
    label: str
    meaning: str
    score: float
    score_range: tuple[float, float]
    source_fields: list[str] = field(default_factory=list)


def _parse_band(label: str, raw: dict[str, Any]) -> TrafficLightBand:
    score_range = raw.get("score_range")
    if not isinstance(score_range, list) or len(score_range) != 2:
        raise ValueError(
            f"traffic_light_mapping.{label}.score_range must contain two values"
        )
    return TrafficLightBand(
        label=label,
        meaning=str(raw.get("meaning", "")),
        score_range=(float(score_range[0]), float(score_range[1])),
    )


def _parse_mapping(
    exercise_id: str, raw: dict[str, Any], source_path: Path
) -> FmsExerciseMapping:
    required = (
        "reference_screen",
        "fms_test",
        "traffic_light_mapping",
        "linked_criteria",
    )
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(
            f"{exercise_id}: missing required field(s): {', '.join(missing)}"
        )

    bands = {
        label: _parse_band(label, band_raw or {})
        for label, band_raw in (raw.get("traffic_light_mapping") or {}).items()
    }
    for label in ("green", "yellow", "red"):
        if label not in bands:
            raise ValueError(
                f"{exercise_id}: traffic_light_mapping.{label} is required"
            )

    criteria = [
        FmsCriterionMapping(
            id=str(item.get("id", "")),
            domain=str(item.get("domain", "")),
            feature_id_prefix=str(item.get("feature_id_prefix", "")),
            rationale=str(item.get("rationale", "")),
        )
        for item in (raw.get("linked_criteria") or [])
    ]
    if len(criteria) < 3:
        raise ValueError(
            f"{exercise_id}: at least three linked_criteria entries are required"
        )
    for criterion in criteria:
        if not all(
            (
                criterion.id,
                criterion.domain,
                criterion.feature_id_prefix,
                criterion.rationale,
            )
        ):
            raise ValueError(
                f"{exercise_id}: linked_criteria entries require id/domain/feature_id_prefix/rationale"
            )

    try:
        source_ref = source_path.resolve().relative_to(_PROJECT_ROOT).as_posix()
    except ValueError:
        source_ref = source_path.as_posix()

    return FmsExerciseMapping(
        exercise_id=exercise_id,
        reference_screen=str(raw["reference_screen"]),
        fms_test=str(raw["fms_test"]),
        traffic_light_mapping=bands,
        linked_criteria=criteria,
        references=list(raw.get("references") or []),
        source_fields=[f"{source_ref}#{exercise_id}"],
    )


def load_fms_mapping(path: Path | str | None = None) -> dict[str, FmsExerciseMapping]:
    """Load all FMS-like crosswalk entries from YAML.

    Returns
    -------
    dict[str, FmsExerciseMapping]
        Mapping keyed by exercise_id.

    Raises
    ------
    FileNotFoundError
        If the mapping file is absent.
    ValueError
        If required mapping fields are missing or malformed.
    """
    mapping_path = Path(path) if path is not None else _DEFAULT_FMS_MAPPING_PATH
    if not mapping_path.exists():
        raise FileNotFoundError(f"FMS mapping file not found: {mapping_path}")

    with open(mapping_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    mappings: dict[str, FmsExerciseMapping] = {}
    for exercise_id, raw in data.items():
        if str(exercise_id).startswith("_"):
            continue
        if not isinstance(raw, dict):
            raise ValueError(f"{exercise_id}: mapping entry must be a dictionary")
        mappings[str(exercise_id)] = _parse_mapping(str(exercise_id), raw, mapping_path)
    return mappings


def traffic_light_for_score(
    score: float | Any,
    exercise_id: str | None = None,
    *,
    mapping_path: Path | str | None = None,
) -> TrafficLightLabel:
    """Convert a 0-100 biomarker score into a traffic-light label.

    `score` may be a numeric value or a BiomarkerScoreRecord-like object with
    `final_score` and `exercise_id` attributes. The output keeps YAML
    provenance so dashboard views can trace where the label came from.
    """
    if hasattr(score, "final_score"):
        value = float(score.final_score)
        exercise = exercise_id or getattr(score, "exercise_id", None)
    else:
        value = float(score)
        exercise = exercise_id

    if not exercise:
        raise ValueError("exercise_id is required when score is numeric")

    mappings = load_fms_mapping(mapping_path)
    if exercise not in mappings:
        raise KeyError(f"FMS mapping for exercise_id '{exercise}' was not found")

    clipped = max(0.0, min(100.0, value))
    mapping = mappings[exercise]
    for label in ("green", "yellow", "red"):
        band = mapping.traffic_light_mapping[label]
        if band.contains(clipped):
            return TrafficLightLabel(
                exercise_id=exercise,
                label=band.label,
                meaning=band.meaning,
                score=clipped,
                score_range=band.score_range,
                source_fields=mapping.source_fields
                + [
                    f"data/definitions/clinical/fms_mapping.yaml#{exercise}.traffic_light_mapping.{label}"
                ],
            )

    raise ValueError(
        f"No traffic-light interval matched score {clipped} for {exercise}"
    )


__all__ = [
    "FmsCriterionMapping",
    "FmsExerciseMapping",
    "TrafficLightBand",
    "TrafficLightLabel",
    "load_fms_mapping",
    "traffic_light_for_score",
]
