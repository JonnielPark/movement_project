"""
⑧ Biomechanical Proxy Modeling

Applies simplified biomechanical rules to produce relative proxy metrics
from normalized pose data.

All outputs are in torso_length_ratio units (dimensionless).
Absolute force units (N, N·m, kg) are not used.

Submodules:
    biomech.anthropometry → segment mass and CoM ratios (Winter 1990)
    biomech.com           → CoM estimation (segment mass ratio × segment position)
    biomech.moment_arm    → joint moment arms (2D sagittal projection, torso_length_ratio)

Coordinate convention : (T, J, 3) = (frame, joint_index, xyz).
Column convention     : <landmark>_norm_x/y/z (normalized coordinates).
Unit restriction      : all outputs in torso_length_ratio; absolute units are a bug.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BiomechRecord:
    """Single biomechanical proxy metric result.

    Parameters
    ----------
    metric_id     : unique identifier (e.g. 'biomech.com.trajectory_range_x')
    exercise_id   : exercise identifier
    rep_id        : rep number (None = sequence-level)
    value         : metric value
    unit          : must be torso_length_ratio or degree
    source_fields : exercise definition fields that drove this metric (provenance)
    note          : optional interpretation note
    """
    metric_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str] = field(default_factory=list)
    note: str | None = None

    def __post_init__(self) -> None:
        if self.unit not in ("torso_length_ratio", "degree", "dimensionless"):
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': absolute units (N, kg, m) are not allowed. "
                f"unit='{self.unit}'. Use torso_length_ratio or degree."
            )
        if not self.source_fields:
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': source_fields is empty. "
                "Provenance fields from the exercise definition must be specified."
            )


__all__ = ["BiomechRecord"]
