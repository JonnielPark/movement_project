"""
⑩ Biomarker Derivation

Integrates ⑧ feature extraction and ⑨ biomechanical proxy modeling results
into interpretable digital biomarkers (BiomarkerRecord).

Every BiomarkerRecord must include source_fields (provenance).
Raises ValueError if source_fields is empty.

Unit convention  : torso_length_ratio | degree | dimensionless_cv | second.
Absolute units (N, kg, m, N·m) are not used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BiomarkerRecord:
    """Single digital biomarker.

    Parameters
    ----------
    biomarker_id      : unique identifier (e.g. 'biomarker.rom.left_knee')
    exercise_id       : exercise identifier
    definition_version: exercise definition version this record references (provenance)
    source_fields     : exercise definition fields that drove this biomarker (provenance)
    rep_id            : rep number (None = sequence-level)
    value             : biomarker value
    unit              : torso_length_ratio | degree | dimensionless_cv | second
    note              : optional biomechanical interpretation note
    view_reliability  : optional camera-zone reliability inherited from FeatureRecord
    availability      : optional scoring availability inherited from FeatureRecord
    availability_reasons : machine-readable reasons for availability decision
    camera_zone       : recording camera zone used for availability decision
    """

    biomarker_id: str
    exercise_id: str
    definition_version: str
    source_fields: list[str]
    rep_id: int | None
    value: float
    unit: str
    note: str | None = None
    view_reliability: str | None = None
    availability: str | None = None
    availability_reasons: list[str] = field(default_factory=list)
    camera_zone: str | None = None

    def __post_init__(self) -> None:
        if not self.source_fields:
            raise ValueError(
                f"BiomarkerRecord '{self.biomarker_id}': source_fields is empty. "
                "Provenance fields from the exercise definition must be specified."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "biomarker_id": self.biomarker_id,
            "exercise_id": self.exercise_id,
            "definition_version": self.definition_version,
            "source_fields": self.source_fields,
            "rep_id": self.rep_id,
            "value": self.value,
            "unit": self.unit,
            "note": self.note,
            "view_reliability": self.view_reliability,
            "availability": self.availability,
            "availability_reasons": self.availability_reasons,
            "camera_zone": self.camera_zone,
        }


def from_feature_record(
    feature,
    definition_version: str,
    biomarker_id: str | None = None,
    note: str | None = None,
) -> BiomarkerRecord:
    """Convert a FeatureRecord to a BiomarkerRecord.

    Parameters
    ----------
    feature            : FeatureRecord
    definition_version : exercise definition version string
    biomarker_id       : override biomarker id; defaults to feature.feature_id
    note               : optional biomechanical interpretation note
    """
    return BiomarkerRecord(
        biomarker_id=biomarker_id or feature.feature_id,
        exercise_id=feature.exercise_id,
        definition_version=definition_version,
        source_fields=feature.source_fields,
        rep_id=feature.rep_id,
        value=feature.value,
        unit=feature.unit,
        note=note,
        view_reliability=getattr(feature, "view_reliability", None),
        availability=getattr(feature, "availability", None),
        availability_reasons=list(getattr(feature, "availability_reasons", []) or []),
        camera_zone=getattr(feature, "camera_zone", None),
    )


def from_biomech_record(
    biomech,
    definition_version: str,
    biomarker_id: str | None = None,
    note: str | None = None,
) -> BiomarkerRecord:
    """Convert a BiomechRecord to a BiomarkerRecord."""
    return BiomarkerRecord(
        biomarker_id=biomarker_id or biomech.metric_id,
        exercise_id=biomech.exercise_id,
        definition_version=definition_version,
        source_fields=biomech.source_fields,
        rep_id=biomech.rep_id,
        value=biomech.value,
        unit=biomech.unit,
        note=note or biomech.note,
    )


def derive_biomarkers(
    feat_records,
    biomech_records,
    exercise_definition,
    definition_version: str,
    *,
    baseline_path=None,
    domain_weights=None,
    score_bounds=None,
):
    """Convenience re-export of biomarker.scoring.derive_biomarkers.

    See biomarker/scoring.py for full documentation.
    Returns (list[BiomarkerRecord], list[BiomarkerScoreRecord]).
    """
    from movement.biomarker.scoring import derive_biomarkers as _derive

    return _derive(
        feat_records,
        biomech_records,
        exercise_definition,
        definition_version,
        baseline_path=baseline_path,
        domain_weights=domain_weights,
        score_bounds=score_bounds,
    )


def derive_interpretations(score, biomech_records=None, rules_dir=None):
    """Convenience re-export of biomarker.interpretation.derive_interpretations.

    See biomarker/interpretation.py for full documentation.
    Returns list[InterpretationRecord].
    """
    from movement.biomarker.interpretation import (
        derive_interpretations as _derive,
    )

    return _derive(score, biomech_records=biomech_records, rules_dir=rules_dir)


__all__ = [
    "BiomarkerRecord",
    "from_feature_record",
    "from_biomech_record",
    "derive_biomarkers",
    "derive_interpretations",
]
