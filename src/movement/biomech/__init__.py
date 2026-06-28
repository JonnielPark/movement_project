"""
⑨ Biomechanical Proxy Modeling

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

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd
    from movement.definitions.exercise_definition import ExerciseDefinition


@dataclass
class BiomechRecord:
    """Single biomechanical proxy metric result.

    Parameters
    ----------
    metric_id                        : unique identifier (e.g. 'biomech.com.range_x')
    exercise_id                      : exercise identifier
    rep_id                           : rep number (None = sequence-level)
    value                            : metric value
    unit                             : must be torso_length_ratio or degree
    source_fields                    : exercise definition fields used (provenance)
    note                             : optional biomechanical interpretation note
    visibility_weight_applied        : True if low-visibility frames were excluded
    n_frames_used                    : number of frames included in the computation
    n_frames_excluded_low_visibility : frames excluded due to low visibility
    availability                     : scoring availability gate
    availability_reasons             : machine-readable availability provenance
    depth_dependency                 : dependency on monocular model-depth evidence
    model_depth_reliability          : reliability of pose-estimator depth evidence
    landmark_quality                 : landmark quality summary when available
    """

    metric_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str] = field(default_factory=list)
    note: str | None = None
    visibility_weight_applied: bool = False
    n_frames_used: int = 0
    n_frames_excluded_low_visibility: int = 0
    availability: str = "low_confidence"
    availability_reasons: list[str] = field(default_factory=list)
    depth_dependency: str = "high"
    model_depth_reliability: str = "low"
    landmark_quality: str = "unknown"

    def __post_init__(self) -> None:
        if self.unit not in (
            "torso_length_ratio",
            "torso_length_ratio_per_rep",
            "degree",
            "dimensionless",
        ):
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': absolute units (N, kg, m) are not allowed. "
                f"unit='{self.unit}'. Use torso_length_ratio, torso_length_ratio_per_rep, or degree."
            )
        if not self.source_fields:
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': source_fields is empty. "
                "Provenance fields from the exercise definition must be specified."
            )
        valid_availability = {"assessed", "low_confidence", "not_assessed"}
        if self.availability not in valid_availability:
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': invalid availability "
                f"{self.availability!r}."
            )
        valid_depth_dependency = {"none", "low", "moderate", "high", "unknown"}
        if self.depth_dependency not in valid_depth_dependency:
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': invalid depth_dependency "
                f"{self.depth_dependency!r}."
            )
        valid_model_depth_reliability = {"high", "moderate", "low", "unknown"}
        if self.model_depth_reliability not in valid_model_depth_reliability:
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': invalid model_depth_reliability "
                f"{self.model_depth_reliability!r}."
            )
        if self.availability == "low_confidence" and not self.availability_reasons:
            self.availability_reasons = [
                "monocular_biomech_proxy_low_confidence",
                "model_depth_reliability_low",
            ]


def extract_rep_biomech(
    df: "pd.DataFrame",
    exercise_definition: "ExerciseDefinition",
    *,
    use_visibility_weight: bool = True,
) -> "list[BiomechRecord]":
    """Compute CoM and moment-arm metrics per rep_id.

    Rep boundaries are read from annotation columns (segment_type, rep_id).
    When annotation columns are absent, metrics are computed at sequence level.

    When use_visibility_weight=True, frames whose mean primary-joint visibility
    falls below quality_rules.minimum_visible_landmark_ratio are excluded from
    all computations. This reduces the influence of depth-estimation noise from
    monocular vision on the proxy metrics.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized pose dataframe. Must contain <landmark>_norm_x/y/z columns.
    exercise_definition : ExerciseDefinition
    use_visibility_weight : bool
        True (default) — exclude low-visibility frames.
        False — include all frames (useful for A/B comparison).

    Returns
    -------
    list[BiomechRecord]
    """
    from movement.biomech.com import compute_com_metrics, compute_visibility_weights
    from movement.biomech.moment_arm import compute_moment_arms

    records: list[BiomechRecord] = []

    has_annotation = "segment_type" in df.columns and "rep_id" in df.columns
    rep_ids: list = []
    if has_annotation:
        rep_mask = df["segment_type"] == "rep"
        rep_ids = sorted(df.loc[rep_mask, "rep_id"].dropna().unique())

    primary_joints: list[str] = exercise_definition.landmarks.primary_joints or []
    min_vis_ratio: float = (
        exercise_definition.quality_rules.minimum_visible_landmark_ratio
    )

    def _weights_for(df_slice: "pd.DataFrame"):
        if not use_visibility_weight or not primary_joints:
            return None
        return compute_visibility_weights(df_slice, primary_joints, min_vis_ratio)

    moment_arm_records: list[BiomechRecord] = []

    if rep_ids:
        for rep_id in rep_ids:
            mask = (df["segment_type"] == "rep") & (df["rep_id"] == rep_id)
            df_rep = df.loc[mask]
            rid = int(rep_id)
            w = _weights_for(df_rep)
            records += compute_com_metrics(
                df_rep, exercise_definition, rep_id=rid, weights=w
            )
            ma = compute_moment_arms(df_rep, exercise_definition, rep_id=rid, weights=w)
            records += ma
            moment_arm_records += ma

        # Load-shift trend: requires ≥ 3 reps (slope is unreliable on fewer)
        if len(rep_ids) >= 3:
            from movement.biomech.load_shift import compute_load_shift

            records += compute_load_shift(moment_arm_records)
    else:
        w = _weights_for(df)
        records += compute_com_metrics(df, exercise_definition, weights=w)
        records += compute_moment_arms(df, exercise_definition, weights=w)

    return records


BIOMECH_REQUIRED_COLUMNS = [
    "metric_id",
    "exercise_id",
    "rep_id",
    "value",
    "unit",
    "source_fields",
    "note",
    "visibility_weight_applied",
    "n_frames_used",
    "n_frames_excluded_low_visibility",
    "availability",
    "availability_reasons",
    "depth_dependency",
    "model_depth_reliability",
    "landmark_quality",
]


def _serialize_biomech_output_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    try:
        import pandas as pd

        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return value


def _relative_biomech_output_path(path: Path, project_root: Path | None) -> str:
    if project_root is None:
        return str(path)
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _assert_biomech_output_round_trip(
    *,
    csv_path: Path,
    expected_rows: int,
    required_columns: list[str],
) -> "pd.DataFrame":
    import pandas as pd

    reloaded = pd.read_csv(csv_path)
    if len(reloaded) != expected_rows:
        raise AssertionError(
            f"Saved row count mismatch for {csv_path}: "
            f"expected {expected_rows}, got {len(reloaded)}."
        )
    for column in required_columns:
        if column not in reloaded.columns:
            raise AssertionError(f"Saved biomech CSV missing column: {column}")
    if "source_fields" in reloaded.columns:
        source_lengths = reloaded["source_fields"].astype(str).str.len()
        if not source_lengths.gt(0).all():
            raise AssertionError("Saved biomech CSV contains empty source_fields.")
    return reloaded


def _missing_biomech_source_fields(biomech_df: "pd.DataFrame") -> int:
    if "source_fields" not in biomech_df.columns:
        return len(biomech_df)
    return int(biomech_df["source_fields"].fillna("").astype(str).str.len().eq(0).sum())


def save_biomech_outputs(
    *,
    biomech_df: "pd.DataFrame",
    recording_id: str,
    exercise_id: str,
    output_dir: str | Path,
    project_root: str | Path | None = None,
    required_columns: list[str] | None = None,
) -> "pd.DataFrame":
    """Save ⑨ Biomechanical Proxy table/QC and verify CSV round-trip."""

    import pandas as pd

    required = required_columns or BIOMECH_REQUIRED_COLUMNS
    output_path = Path(output_dir)
    root = Path(project_root) if project_root is not None else None
    output_path.mkdir(parents=True, exist_ok=True)
    csv_path = output_path / f"{recording_id}_biomech.csv"
    qc_path = output_path / f"{recording_id}_biomech_qc.json"

    csv_df = biomech_df.copy()
    for column in ("source_fields", "availability_reasons"):
        if column in csv_df.columns:
            csv_df[column] = csv_df[column].map(_serialize_biomech_output_value)
    csv_df.to_csv(csv_path, index=False, encoding="utf-8")

    qc_payload = {
        "recording_id": recording_id,
        "exercise_id": exercise_id,
        "biomech_rows": int(len(biomech_df)),
        "biomech_columns": list(biomech_df.columns),
        "unit_counts": biomech_df["unit"].value_counts(dropna=False).to_dict(),
        "availability_counts": biomech_df["availability"]
        .value_counts(dropna=False)
        .to_dict(),
        "metric_family_counts": biomech_df["metric_family"]
        .value_counts(dropna=False)
        .to_dict(),
        "missing_source_fields": _missing_biomech_source_fields(biomech_df),
    }
    qc_path.write_text(
        json.dumps(qc_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    reloaded = _assert_biomech_output_round_trip(
        csv_path=csv_path,
        expected_rows=len(biomech_df),
        required_columns=required,
    )
    return pd.DataFrame(
        [
            {
                "artifact": "biomech_csv",
                "path": _relative_biomech_output_path(csv_path, root),
                "rows": len(reloaded),
            },
            {
                "artifact": "biomech_qc_json",
                "path": _relative_biomech_output_path(qc_path, root),
                "rows": 1,
            },
        ]
    )


__all__ = [
    "BIOMECH_REQUIRED_COLUMNS",
    "BiomechRecord",
    "extract_rep_biomech",
    "compute_load_shift",
    "save_biomech_outputs",
]
