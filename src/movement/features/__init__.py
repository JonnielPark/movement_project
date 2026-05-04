"""
⑦ Feature Extraction

Computes spatial, temporal, and control domain features from normalized pose data.
Each feature is returned as a FeatureRecord with (value, unit, source_fields)
so that downstream biomarker derivation (⑨) can trace provenance.

Submodules:
    features.spatial   → ROM, left/right symmetry, trajectory shape
    features.temporal  → tempo, inter-rep variability
    features.control   → CoM stability, compensation movements

Coordinate convention : (T, J, 3) = (frame, joint_index, xyz).
Column convention     : <landmark>_norm_x/y/z (normalized coordinates).
Unit convention       : torso_length_ratio (dimensionless) or degree.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FeatureRecord:
    """Single feature computation result.

    Parameters
    ----------
    feature_id    : unique identifier (e.g. 'spatial.rom.left_knee')
    exercise_id   : exercise identifier
    rep_id        : rep number (None = sequence-level feature)
    value         : feature value
    unit          : torso_length_ratio | degree | second | dimensionless_cv
    source_fields : exercise definition fields that drove this feature (provenance)
    note          : optional interpretation note
    """
    feature_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str] = field(default_factory=list)
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.source_fields:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': source_fields is empty. "
                "Provenance fields from the exercise definition must be specified."
            )


__all__ = ["FeatureRecord"]
