"""
⑨ Biomarker Derivation

Integrates ⑦ feature extraction and ⑧ biomechanical proxy modeling results
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
    """
    biomarker_id: str
    exercise_id: str
    definition_version: str
    source_fields: list[str]
    rep_id: int | None
    value: float
    unit: str
    note: str | None = None

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


__all__ = ["BiomarkerRecord", "from_feature_record", "from_biomech_record"]
