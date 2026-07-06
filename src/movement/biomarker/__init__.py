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

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from movement.record_metadata import COMMON_RECORD_METADATA_FIELDS


@dataclass
class BiomarkerRecord:
    """Single digital biomarker.

    Parameters
    ----------
    biomarker_id      : unique identifier (e.g. 'biomarker.range_of_motion.left_knee')
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
    depth_dependency  : optional monocular-depth dependency inherited from FeatureRecord
    model_depth_reliability : optional pose-estimator depth reliability
    landmark_quality  : optional feature-level landmark evidence summary
    focus_tier        : optional scoring-intent tier inherited from FeatureRecord
    landmark_ids      : optional canonical landmark references
    support_role      : optional support/proxy role metadata
    coordinate_reference : optional coordinate-family metadata
    evaluation_domain : optional scoring/evaluation evidence domain
    evidence_axes     : optional coordinate-axis metadata
    feature_family    : optional broad feature family metadata
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
    depth_dependency: str | None = None
    model_depth_reliability: str | None = None
    landmark_quality: str | None = None
    focus_tier: str | None = None
    landmark_ids: list[str] = field(default_factory=list)
    support_role: str | None = None
    coordinate_reference: str | None = None
    evaluation_domain: str | None = None
    evidence_axes: str | None = None
    feature_family: str | None = None

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
            "depth_dependency": self.depth_dependency,
            "model_depth_reliability": self.model_depth_reliability,
            "landmark_quality": self.landmark_quality,
            "focus_tier": self.focus_tier,
            "landmark_ids": self.landmark_ids,
            "support_role": self.support_role,
            "coordinate_reference": self.coordinate_reference,
            "evaluation_domain": self.evaluation_domain,
            "evidence_axes": self.evidence_axes,
            "feature_family": self.feature_family,
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
        depth_dependency=getattr(feature, "depth_dependency", None),
        model_depth_reliability=getattr(feature, "model_depth_reliability", None),
        landmark_quality=getattr(feature, "landmark_quality", None),
        focus_tier=getattr(feature, "focus_tier", None),
        landmark_ids=list(getattr(feature, "landmark_ids", []) or []),
        support_role=getattr(feature, "support_role", None),
        coordinate_reference=getattr(feature, "coordinate_reference", None),
        evaluation_domain=getattr(feature, "evaluation_domain", None),
        evidence_axes=getattr(feature, "evidence_axes", None),
        feature_family=getattr(feature, "feature_family", None),
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
        availability=getattr(biomech, "availability", None),
        availability_reasons=list(getattr(biomech, "availability_reasons", []) or []),
        depth_dependency=getattr(biomech, "depth_dependency", None),
        model_depth_reliability=getattr(biomech, "model_depth_reliability", None),
        landmark_quality=getattr(biomech, "landmark_quality", None),
        focus_tier=getattr(biomech, "focus_tier", None),
        landmark_ids=list(getattr(biomech, "landmark_ids", []) or []),
        support_role=getattr(biomech, "support_role", None),
        coordinate_reference=getattr(biomech, "coordinate_reference", None),
        evaluation_domain=getattr(biomech, "evaluation_domain", None),
        evidence_axes=getattr(biomech, "evidence_axes", None),
        feature_family=getattr(biomech, "feature_family", None),
    )


def derive_biomarkers(
    feat_records,
    biomech_records,
    exercise_definition,
    definition_version: str,
    *,
    baseline_path=None,
    domain_weights=None,
    domain_feature_family_weights=None,
    low_confidence_score_weights=None,
    depth_dependency_score_weights=None,
    feature_score_weight_overrides=None,
    feature_score_direction_overrides=None,
    scoring_focus_weights=None,
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
        domain_feature_family_weights=domain_feature_family_weights,
        low_confidence_score_weights=low_confidence_score_weights,
        depth_dependency_score_weights=depth_dependency_score_weights,
        feature_score_weight_overrides=feature_score_weight_overrides,
        feature_score_direction_overrides=feature_score_direction_overrides,
        scoring_focus_weights=scoring_focus_weights,
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


BIOMARKER_REQUIRED_COLUMNS = [
    "biomarker_id",
    "exercise_id",
    "definition_version",
    "source_fields",
    "rep_id",
    "value",
    "unit",
    "note",
    "view_reliability",
    "availability",
    "availability_reasons",
    "camera_zone",
    "depth_dependency",
    "model_depth_reliability",
    "landmark_quality",
    "focus_tier",
    *COMMON_RECORD_METADATA_FIELDS,
]

BIOMARKER_SCORE_REQUIRED_COLUMNS = [
    "score_id",
    "exercise_id",
    "definition_version",
    "rep_id",
    "domain_scores",
    "floor_applied",
    "final_score",
    "deductions",
    "withheld_features",
    "source_fields",
    "domain_weights",
    "domain_feature_family_weights",
    "low_confidence_score_weights",
    "depth_dependency_score_weights",
    "feature_score_weight_overrides",
    "feature_score_direction_overrides",
    "scoring_focus_weights",
    "score_bounds",
]

BIOMARKER_SCORE_ITEM_REQUIRED_COLUMNS = [
    "score_id",
    "exercise_id",
    "definition_version",
    "rep_id",
    "domain",
    "feature_id",
    "item_score",
    "deduction",
    "value",
    "scoring_mode",
    "availability",
    "availability_weight",
    "depth_dependency",
    "depth_dependency_weight",
    "focus_tier",
    "focus_weight",
    "feature_weight",
    "feature_family",
    "feature_family_weight",
    "confidence_weight",
    "baseline_mean",
    "baseline_std",
    "score_direction",
    "z_raw",
    "z",
    "w",
    *COMMON_RECORD_METADATA_FIELDS,
]


def _serialize_output_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    try:
        import pandas as pd

        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return value


def _relative_output_path(path: Path, project_root: Path | None) -> str:
    if project_root is None:
        return str(path)
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _records_to_dataframe(records: list[Any], required_columns: list[str]):
    import pandas as pd

    rows = [
        record.as_dict() if hasattr(record, "as_dict") else dict(record)
        for record in records
    ]
    dataframe = pd.DataFrame(rows)
    for column in required_columns:
        if column not in dataframe.columns:
            dataframe[column] = pd.Series(dtype="object")
    return dataframe[
        required_columns + [c for c in dataframe.columns if c not in required_columns]
    ]


def _write_csv_with_json_columns(
    dataframe, path: Path, json_columns: tuple[str, ...]
) -> None:
    csv_df = dataframe.copy()
    for column in json_columns:
        if column in csv_df.columns:
            csv_df[column] = csv_df[column].map(_serialize_output_value)
    csv_df.to_csv(path, index=False, encoding="utf-8")


def score_records_to_item_dataframe(score_records: list[Any]) -> "Any":
    """Flatten BiomarkerScoreRecord deductions into item-level score rows.

    Item rows are a reporting view of the already-computed deduction audit. They
    do not introduce new movement-quality logic.
    """

    import pandas as pd

    rows: list[dict[str, Any]] = []
    for record in score_records:
        score_bounds = getattr(record, "score_bounds", None) or {}
        score_min = float(score_bounds.get("min", 0.0))
        score_max = float(score_bounds.get("max", 100.0))
        for item in getattr(record, "deductions", []) or []:
            deduction = float(item.get("deduction", 0.0))
            item_score = max(score_min, min(score_max, score_max - deduction))
            row = {
                "score_id": getattr(record, "score_id", None),
                "exercise_id": getattr(record, "exercise_id", None),
                "definition_version": getattr(record, "definition_version", None),
                "rep_id": getattr(record, "rep_id", None),
            }
            row.update(dict(item))
            row["item_score"] = round(item_score, 2)
            row["deduction"] = round(deduction, 4)
            rows.append(row)

    dataframe = pd.DataFrame(rows)
    for column in BIOMARKER_SCORE_ITEM_REQUIRED_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = pd.Series(dtype="object")
    return dataframe[
        BIOMARKER_SCORE_ITEM_REQUIRED_COLUMNS
        + [
            c
            for c in dataframe.columns
            if c not in BIOMARKER_SCORE_ITEM_REQUIRED_COLUMNS
        ]
    ]


def save_biomarker_outputs(
    *,
    biomarker_records: list[Any],
    score_records: list[Any],
    recording_id: str,
    exercise_id: str,
    output_dir: str | Path,
    project_root: str | Path | None = None,
) -> "Any":
    """Save ⑩ biomarker/score tables and compact QC for follow-along checks."""

    import pandas as pd

    output_path = Path(output_dir)
    root = Path(project_root) if project_root is not None else None
    output_path.mkdir(parents=True, exist_ok=True)
    biomarker_csv = output_path / f"{recording_id}_biomarkers.csv"
    score_csv = output_path / f"{recording_id}_biomarker_scores.csv"
    score_item_csv = output_path / f"{recording_id}_biomarker_score_items.csv"
    qc_path = output_path / f"{recording_id}_biomarker_qc.json"

    biomarker_df = _records_to_dataframe(biomarker_records, BIOMARKER_REQUIRED_COLUMNS)
    score_df = _records_to_dataframe(score_records, BIOMARKER_SCORE_REQUIRED_COLUMNS)
    score_item_df = score_records_to_item_dataframe(score_records)

    _write_csv_with_json_columns(
        biomarker_df,
        biomarker_csv,
        ("source_fields", "availability_reasons", "landmark_ids"),
    )
    _write_csv_with_json_columns(
        score_df,
        score_csv,
        (
            "domain_scores",
            "floor_applied",
            "deductions",
            "withheld_features",
            "source_fields",
            "domain_weights",
            "domain_feature_family_weights",
            "low_confidence_score_weights",
            "depth_dependency_score_weights",
            "feature_score_weight_overrides",
            "feature_score_direction_overrides",
            "scoring_focus_weights",
            "score_bounds",
        ),
    )
    _write_csv_with_json_columns(
        score_item_df,
        score_item_csv,
        ("landmark_ids",),
    )

    reloaded_biomarkers = pd.read_csv(biomarker_csv)
    reloaded_scores = pd.read_csv(score_csv)
    reloaded_score_items = pd.read_csv(score_item_csv)
    if len(reloaded_biomarkers) != len(biomarker_df):
        raise AssertionError("Saved biomarker row count mismatch.")
    if len(reloaded_scores) != len(score_df):
        raise AssertionError("Saved biomarker score row count mismatch.")
    if len(reloaded_score_items) != len(score_item_df):
        raise AssertionError("Saved biomarker score item row count mismatch.")
    for column in BIOMARKER_REQUIRED_COLUMNS:
        if column not in reloaded_biomarkers.columns:
            raise AssertionError(f"Saved biomarker CSV missing column: {column}")
    for column in BIOMARKER_SCORE_REQUIRED_COLUMNS:
        if column not in reloaded_scores.columns:
            raise AssertionError(f"Saved biomarker score CSV missing column: {column}")
    for column in BIOMARKER_SCORE_ITEM_REQUIRED_COLUMNS:
        if column not in reloaded_score_items.columns:
            raise AssertionError(
                f"Saved biomarker score item CSV missing column: {column}"
            )

    final_scores = [
        float(record.final_score)
        for record in score_records
        if getattr(record, "final_score", None) is not None
    ]
    withheld_count = sum(
        len(getattr(record, "withheld_features", []) or []) for record in score_records
    )
    qc_payload = {
        "recording_id": recording_id,
        "exercise_id": exercise_id,
        "biomarker_rows": int(len(biomarker_df)),
        "score_rows": int(len(score_df)),
        "score_item_rows": int(len(score_item_df)),
        "score_available": bool(score_records),
        "final_score_min": min(final_scores) if final_scores else None,
        "final_score_max": max(final_scores) if final_scores else None,
        "withheld_feature_count": int(withheld_count),
        "artifacts": {
            "biomarkers_csv": _relative_output_path(biomarker_csv, root),
            "biomarker_scores_csv": _relative_output_path(score_csv, root),
            "biomarker_score_items_csv": _relative_output_path(score_item_csv, root),
            "biomarker_qc_json": _relative_output_path(qc_path, root),
        },
    }
    qc_path.write_text(
        json.dumps(qc_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return pd.DataFrame(
        [
            {
                "artifact": "biomarkers_csv",
                "path": _relative_output_path(biomarker_csv, root),
                "rows": len(reloaded_biomarkers),
            },
            {
                "artifact": "biomarker_scores_csv",
                "path": _relative_output_path(score_csv, root),
                "rows": len(reloaded_scores),
            },
            {
                "artifact": "biomarker_score_items_csv",
                "path": _relative_output_path(score_item_csv, root),
                "rows": len(reloaded_score_items),
            },
            {
                "artifact": "biomarker_qc_json",
                "path": _relative_output_path(qc_path, root),
                "rows": 1,
            },
        ]
    )


__all__ = [
    "BIOMARKER_REQUIRED_COLUMNS",
    "BIOMARKER_SCORE_REQUIRED_COLUMNS",
    "BIOMARKER_SCORE_ITEM_REQUIRED_COLUMNS",
    "BiomarkerRecord",
    "from_feature_record",
    "from_biomech_record",
    "derive_biomarkers",
    "derive_interpretations",
    "save_biomarker_outputs",
    "score_records_to_item_dataframe",
]
