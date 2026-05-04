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


def extract_rep_features(
    df: "pd.DataFrame",
    exercise_definition: "Any",
) -> "list[FeatureRecord]":
    """Extract spatial, temporal, and control features per rep and for the full sequence.

    Rep boundaries are read from annotation columns (segment_type, rep_id).
    When annotation columns are absent, all features are computed sequence-level.

    Per-rep features (one record per rep_id):
        spatial  : ROM, symmetry, trajectory shape
        control  : CoM stability, compensation arc length

    Sequence-level features (rep_id = None):
        temporal : tempo per rep, inter-rep variability (requires ≥ 2 reps)
        spatial  : symmetry, shape over the full sequence (when no reps found)

    Parameters
    ----------
    df : pd.DataFrame
        Normalized pose dataframe. Must contain <landmark>_norm_x/y/z columns.
    exercise_definition : ExerciseDefinition

    Returns
    -------
    list[FeatureRecord]
    """
    from movement.features.control import compute_compensation, compute_stability
    from movement.features.spatial import compute_rom, compute_shape, compute_symmetry
    from movement.features.temporal import compute_tempo, compute_variability

    records: list[FeatureRecord] = []

    has_annotation = "segment_type" in df.columns and "rep_id" in df.columns
    rep_ids: list = []
    if has_annotation:
        rep_mask = df["segment_type"] == "rep"
        rep_ids = sorted(df.loc[rep_mask, "rep_id"].dropna().unique())

    if rep_ids:
        for rep_id in rep_ids:
            mask = (df["segment_type"] == "rep") & (df["rep_id"] == rep_id)
            df_rep = df.loc[mask]
            rid = int(rep_id)
            records += compute_rom(df_rep, exercise_definition, rep_id=rid)
            records += compute_symmetry(df_rep, exercise_definition, rep_id=rid)
            records += compute_shape(df_rep, exercise_definition, rep_id=rid)
            records += compute_stability(df_rep, exercise_definition, rep_id=rid)
            records += compute_compensation(df_rep, exercise_definition, rep_id=rid)

        # Temporal features span multiple reps — computed on the full df
        records += compute_tempo(df, exercise_definition)
        records += compute_variability(df, exercise_definition)
    else:
        # No rep annotation: sequence-level fallback
        records += compute_rom(df, exercise_definition)
        records += compute_symmetry(df, exercise_definition)
        records += compute_shape(df, exercise_definition)
        records += compute_stability(df, exercise_definition)
        records += compute_compensation(df, exercise_definition)

    return records


def features_to_dataframe(records: list[FeatureRecord]) -> "pd.DataFrame":
    """Convert a list of FeatureRecord objects to a tidy DataFrame.

    Columns: feature_id, exercise_id, rep_id, value, unit, source_fields, note.
    source_fields is serialized as a pipe-joined string for tabular compatibility.
    Returns an empty DataFrame (with schema columns) when records is empty.
    """
    import pandas as pd

    if not records:
        return pd.DataFrame(columns=[
            "feature_id", "exercise_id", "rep_id",
            "value", "unit", "source_fields", "note",
        ])

    rows = [
        {
            "feature_id":   r.feature_id,
            "exercise_id":  r.exercise_id,
            "rep_id":       r.rep_id,
            "value":        r.value,
            "unit":         r.unit,
            "source_fields": "|".join(r.source_fields),
            "note":         r.note,
        }
        for r in records
    ]
    return pd.DataFrame(rows)


__all__ = ["FeatureRecord", "extract_rep_features", "features_to_dataframe"]
