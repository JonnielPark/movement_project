"""
⑧ Feature Extraction

Computes spatial, temporal, and control domain features from normalized pose data.
Each feature is returned as a FeatureRecord with (value, unit, source_fields)
so that downstream biomarker derivation (⑩) can trace provenance.

When the `phase` column is populated by ⑥ Phase Segmentation, features are
emitted at both rep-level (phase=None) and phase-level (phase='Descent', etc.),
enabling the hierarchical analysis structure described in dissertation §5.5.

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
                    Phase-level records append a phase suffix:
                    'spatial.rom.left_knee.descent'
    exercise_id   : exercise identifier
    rep_id        : rep number (None = sequence-level feature)
    value         : feature value
    unit          : torso_length_ratio | degree | second | dimensionless_cv
    source_fields : exercise definition fields that drove this feature (provenance).
                    Phase-level records must include 'phase_segmentation.*' entries.
    note          : optional interpretation note
    phase         : kinematic phase label (None = rep-level; 'Descent' etc. = phase-level)
    """
    feature_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str] = field(default_factory=list)
    note: str | None = None
    phase: str | None = None

    def __post_init__(self) -> None:
        if not self.source_fields:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': source_fields is empty. "
                "Provenance fields from the exercise definition must be specified."
            )


# ── Phase-aware feature families ─────────────────────────────────────────────
# These feature families are computed per (rep_id, phase) when the phase column
# is populated.  control.compensation is rep-level only because compensation
# candidates span the full rep trajectory (crossing phase boundaries).

PHASE_AWARE_FEATURE_FAMILIES: frozenset[str] = frozenset({
    "spatial.rom",
    "spatial.shape",
    "temporal.tempo",
    "control.stability",
})


def _phase_source_fields(exercise_definition: Any) -> list[str]:
    """Return source_fields provenance entries for phase segmentation."""
    ps = getattr(exercise_definition, "phase_segmentation", None)
    if ps is None:
        return []
    return [
        "phase_segmentation.reference_landmark",
        "phase_segmentation.reference_axis",
        "phase_segmentation.split_logic",
    ]


def _emit_rep_level(
    df_rep: "pd.DataFrame",
    exercise_definition: Any,
    rep_id: int,
) -> "list[FeatureRecord]":
    """Compute all rep-level features (phase=None)."""
    from movement.features.control import compute_compensation, compute_stability
    from movement.features.spatial import compute_rom, compute_shape, compute_symmetry
    from movement.features.temporal import compute_tempo, compute_variability

    records: list[FeatureRecord] = []
    records += compute_rom(df_rep, exercise_definition, rep_id=rep_id)
    records += compute_symmetry(df_rep, exercise_definition, rep_id=rep_id)
    records += compute_shape(df_rep, exercise_definition, rep_id=rep_id)
    records += compute_stability(df_rep, exercise_definition, rep_id=rep_id)
    # Compensation is always rep-level (candidates span phase boundaries)
    records += compute_compensation(df_rep, exercise_definition, rep_id=rep_id)
    return records


def _emit_phase_level(
    df_phase: "pd.DataFrame",
    exercise_definition: Any,
    rep_id: int,
    phase_label: str,
) -> "list[FeatureRecord]":
    """
    Compute phase-level features for one (rep_id, phase) segment.

    Only PHASE_AWARE_FEATURE_FAMILIES are computed at phase level; others stay
    rep-level only.  Each feature_id gets a lowercased phase suffix so that
    rep-level and phase-level IDs remain distinct in the baseline namespace.
    """
    from movement.features.spatial import compute_rom, compute_shape
    from movement.features.control import compute_stability

    if len(df_phase) == 0:
        return []

    phase_suffix = "." + phase_label.lower()
    ps_fields = _phase_source_fields(exercise_definition)

    records: list[FeatureRecord] = []

    for rec in compute_rom(df_phase, exercise_definition, rep_id=rep_id):
        records.append(FeatureRecord(
            feature_id=rec.feature_id + phase_suffix,
            exercise_id=rec.exercise_id,
            rep_id=rep_id,
            value=rec.value,
            unit=rec.unit,
            source_fields=rec.source_fields + ps_fields,
            note=rec.note,
            phase=phase_label,
        ))

    for rec in compute_shape(df_phase, exercise_definition, rep_id=rep_id):
        records.append(FeatureRecord(
            feature_id=rec.feature_id + phase_suffix,
            exercise_id=rec.exercise_id,
            rep_id=rep_id,
            value=rec.value,
            unit=rec.unit,
            source_fields=rec.source_fields + ps_fields,
            note=rec.note,
            phase=phase_label,
        ))

    for rec in compute_stability(df_phase, exercise_definition, rep_id=rep_id):
        records.append(FeatureRecord(
            feature_id=rec.feature_id + phase_suffix,
            exercise_id=rec.exercise_id,
            rep_id=rep_id,
            value=rec.value,
            unit=rec.unit,
            source_fields=rec.source_fields + ps_fields,
            note=rec.note,
            phase=phase_label,
        ))

    return records


def extract_rep_features(
    df: "pd.DataFrame",
    exercise_definition: Any,
) -> "list[FeatureRecord]":
    """
    Extract spatial, temporal, and control features per rep (and optionally per phase).

    Rep boundaries are read from annotation columns (segment_type, rep_id).
    When annotation columns are absent, all features are computed sequence-level.

    When the `phase` column is populated by ⑥ Phase Segmentation, features
    in PHASE_AWARE_FEATURE_FAMILIES are also emitted for each (rep_id, phase)
    segment.  The rep-level records (phase=None) are always emitted regardless.

    Per-rep features (one record per rep_id, phase=None):
        spatial  : ROM, symmetry, trajectory shape
        control  : CoM stability, compensation arc length

    Phase-level features (one record per rep_id × phase, when phase column is set):
        spatial  : ROM, trajectory shape (per Descent/Ascent/etc.)
        control  : CoM stability (per phase)

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
    import pandas as pd
    from movement.features.temporal import compute_tempo, compute_variability

    records: list[FeatureRecord] = []

    has_annotation = "segment_type" in df.columns and "rep_id" in df.columns
    has_phase = (
        has_annotation
        and "phase" in df.columns
        and df.loc[df["segment_type"] == "rep", "phase"].notna().any()
    )

    rep_ids: list = []
    if has_annotation:
        rep_mask = df["segment_type"] == "rep"
        rep_ids = sorted(df.loc[rep_mask, "rep_id"].dropna().unique())

    if rep_ids:
        for rep_id in rep_ids:
            mask = (df["segment_type"] == "rep") & (df["rep_id"] == rep_id)
            df_rep = df.loc[mask]
            rid = int(rep_id)

            # Always emit rep-level features
            records += _emit_rep_level(df_rep, exercise_definition, rid)

            # Emit phase-level features when the phase column is populated for this rep
            if has_phase:
                rep_phases = df_rep["phase"].dropna().unique()
                for phase_label in sorted(rep_phases):
                    df_phase = df_rep.loc[df_rep["phase"] == phase_label]
                    records += _emit_phase_level(
                        df_phase, exercise_definition, rid, str(phase_label)
                    )

        # Temporal features span multiple reps — computed on the full df
        records += compute_tempo(df, exercise_definition)
        records += compute_variability(df, exercise_definition)
    else:
        # No rep annotation: sequence-level fallback
        from movement.features.spatial import compute_rom, compute_shape, compute_symmetry
        from movement.features.control import compute_compensation, compute_stability

        records += compute_rom(df, exercise_definition)
        records += compute_symmetry(df, exercise_definition)
        records += compute_shape(df, exercise_definition)
        records += compute_stability(df, exercise_definition)
        records += compute_compensation(df, exercise_definition)

    return records


def summarize_phase_to_rep(records: "list[FeatureRecord]") -> "list[FeatureRecord]":
    """
    Derive rep-level summary features from phase-level FeatureRecords.

    Dissertation §5.5: hierarchical summary structure.

    Currently computes:
        - Descent/Ascent duration ratio  (requires temporal.tempo phase-level records)
        - Phase ROM asymmetry            (Descent vs Ascent mean ROM difference)

    Parameters
    ----------
    records : list[FeatureRecord]
        Mixed list of rep-level and phase-level records.

    Returns
    -------
    list[FeatureRecord]
        New summary records only (not a copy of the input).
    """
    import pandas as pd

    phase_recs = [r for r in records if r.phase is not None]
    if not phase_recs:
        return []

    summary: list[FeatureRecord] = []

    # Group by (exercise_id, rep_id) for per-rep summaries
    from itertools import groupby

    def _key(r: FeatureRecord) -> tuple:
        return (r.exercise_id, r.rep_id)

    phase_recs_sorted = sorted(phase_recs, key=_key)

    for (ex_id, rep_id), group_iter in groupby(phase_recs_sorted, key=_key):
        group = list(group_iter)

        # Descent vs Ascent mean ROM ratio
        descent_rom = [r.value for r in group if r.phase == "Descent" and "spatial.rom" in r.feature_id]
        ascent_rom = [r.value for r in group if r.phase == "Ascent" and "spatial.rom" in r.feature_id]

        if descent_rom and ascent_rom:
            mean_d = sum(descent_rom) / len(descent_rom)
            mean_a = sum(ascent_rom) / len(ascent_rom)
            ratio = mean_d / mean_a if mean_a > 0 else 1.0
            ps_fields = [r.source_fields for r in group if r.phase in ("Descent", "Ascent")]
            merged_fields = list(dict.fromkeys(
                f for sf in ps_fields for f in sf
            ))
            if not merged_fields:
                merged_fields = ["phase_segmentation.phase_sequence"]
            summary.append(FeatureRecord(
                feature_id="spatial.phase_rom_ratio.descent_ascent",
                exercise_id=ex_id,
                rep_id=rep_id,
                value=round(ratio, 4),
                unit="dimensionless",
                source_fields=merged_fields,
                note=(
                    "Ratio of mean Descent ROM to mean Ascent ROM per rep. "
                    "Values > 1 indicate larger descent range of motion."
                ),
                phase=None,
            ))

    return summary


def features_to_dataframe(records: "list[FeatureRecord]") -> "pd.DataFrame":
    """
    Convert a list of FeatureRecord objects to a tidy DataFrame.

    Columns: feature_id, exercise_id, rep_id, phase, value, unit, source_fields, note.
    source_fields is serialized as a pipe-joined string for tabular compatibility.
    Returns an empty DataFrame (with schema columns) when records is empty.
    """
    import pandas as pd

    if not records:
        return pd.DataFrame(columns=[
            "feature_id", "exercise_id", "rep_id", "phase",
            "value", "unit", "source_fields", "note",
        ])

    rows = [
        {
            "feature_id":    r.feature_id,
            "exercise_id":   r.exercise_id,
            "rep_id":        r.rep_id,
            "phase":         r.phase,
            "value":         r.value,
            "unit":          r.unit,
            "source_fields": "|".join(r.source_fields),
            "note":          r.note,
        }
        for r in records
    ]
    return pd.DataFrame(rows)


__all__ = [
    "FeatureRecord",
    "PHASE_AWARE_FEATURE_FAMILIES",
    "extract_rep_features",
    "summarize_phase_to_rep",
    "features_to_dataframe",
]
