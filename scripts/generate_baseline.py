"""
Generate baseline metric statistics for biomarker scoring.

The script runs the same code-backed ①-⑨ path used by stage-check notebooks,
builds per-metric mean/std entries, and writes a baseline bundle for review.

The metric-statistics output remains backward compatible:
    { exercise_id: { metric_id: {"mean": float, "std": float} } }

Usage:
    python scripts/generate_baseline.py
    python scripts/generate_baseline.py --exercise squat \
        --baseline-status provisional
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow running directly from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from movement.biomech import extract_rep_biomech
from movement.biomarker.scoring import (
    BASELINE_STATUSES,
    DEFAULT_DEPTH_DEPENDENCY_SCORE_WEIGHTS,
    DEFAULT_FEATURE_SCORE_WEIGHT_OVERRIDES,
    DEFAULT_SCORING_FOCUS_WEIGHTS,
    build_baseline_from_records,
    build_baseline_qc,
    save_baseline,
    save_baseline_qc,
)
from movement.core.io import load_pose_csv
from movement.exercise_definition import load_exercise_definition
from movement.features import extract_rep_features, summarize_phase_to_rep
from movement.pipeline import load_pipeline_config, run_pipeline
from movement.stage_context import (
    build_stage_check_pipeline_config,
    recording_id_from_pose_csv,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_INPUT = _PROJECT_ROOT / "data/pose/sample/mediapipe_squat_synthetic.csv"
_DEFAULT_ANN = (
    _PROJECT_ROOT / "data/pose/sample/mediapipe_squat_synthetic_annotation.csv"
)
_DEFAULT_DEFS = _PROJECT_ROOT / "data/definitions/exercises"
_DEFAULT_OUTPUT = _PROJECT_ROOT / "data/reference/baseline_zscore.json"
_DEFAULT_BASELINES_DIR = _PROJECT_ROOT / "data/reference/baselines"


def _read_existing_baseline(path: Path) -> dict[str, dict[str, dict[str, float]]]:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as fp:
            data = json.load(fp)
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _default_qc_output_path(output_path: Path, exercise_id: str) -> Path:
    return output_path.parent / "baseline_qc" / f"{exercise_id}_baseline_qc.json"


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_PROJECT_ROOT))
    except ValueError:
        return str(path)


def _baseline_id(
    *,
    exercise_id: str,
    definition_version: str,
    baseline_status: str,
    created_at: datetime,
) -> str:
    date_token = created_at.strftime("%Y%m%d")
    version_token = str(definition_version).replace(".", "_")
    return f"{exercise_id}_{version_token}_{baseline_status}_{date_token}"


def _write_baseline_bundle(
    *,
    baseline_root: Path,
    baseline_id: str,
    exercise_def: Any,
    baseline_status: str,
    source_type: str,
    source_mode: str,
    pose_backend: str,
    coordinate_mode: str,
    metrics: dict[str, dict[str, float]],
    qc_payload: dict[str, Any],
    created_at: datetime,
) -> dict[str, Path]:
    baseline_root.mkdir(parents=True, exist_ok=True)
    metrics_path = baseline_root / "metrics.json"
    qc_path = baseline_root / "qc.json"
    metadata_path = baseline_root / "baseline.yaml"

    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    qc_path.write_text(
        json.dumps(qc_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    metadata = {
        "baseline_id": baseline_id,
        "exercise_id": exercise_def.exercise_id,
        "exercise_definition_version": exercise_def.version,
        "baseline_status": baseline_status,
        "source_type": source_type,
        "source_mode": source_mode,
        "pose_backend": pose_backend,
        "coordinate_mode": coordinate_mode,
        "created_at": created_at.isoformat(),
        "metrics_path": "metrics.json",
        "qc_path": "qc.json",
        "active_for_scoring": False,
    }

    def _yaml_scalar(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    metadata_lines = [
        f"{key}: {_yaml_scalar(value)}" for key, value in metadata.items()
    ]
    metadata_path.write_text("\n".join(metadata_lines) + "\n", encoding="utf-8")

    return {
        "baseline_dir": baseline_root,
        "metadata_path": metadata_path,
        "metrics_path": metrics_path,
        "qc_path": qc_path,
    }


def generate_baseline(
    *,
    csv_path: Path,
    ann_path: Path | None,
    exercise_id: str,
    definitions_dir: Path,
    output_path: Path,
    qc_output_path: Path | None = None,
    baseline_output_dir: Path | None = None,
    mirror_active_metrics: bool = False,
    baseline_status: str = "provisional",
    source_type: str = "synthetic",
    source_mode: str = "single_file",
    pose_backend: str = "mediapipe",
    coordinate_mode: str = "norm",
    manifest_path: Path | None = None,
    low_confidence_biomech_weight: float = 0.1,
    domain_feature_family_weights: dict[str, dict[str, float]] | None = None,
    depth_dependency_score_weights: dict[str, float] | None = None,
    scoring_focus_weights: dict[str, float] | None = None,
    feature_score_weight_overrides: dict[str, float] | None = None,
    feature_score_direction_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Generate a reviewable baseline bundle for one exercise."""

    if baseline_status not in BASELINE_STATUSES:
        valid = ", ".join(BASELINE_STATUSES)
        raise ValueError(
            f"baseline_status must be one of {valid}; got {baseline_status!r}."
        )
    if low_confidence_biomech_weight < 0.0 or low_confidence_biomech_weight > 1.0:
        raise ValueError("low_confidence_biomech_weight must be between 0 and 1.")

    csv_path = csv_path.resolve()
    definitions_dir = definitions_dir.resolve()
    output_path = output_path.resolve()
    resolved_ann = ann_path.resolve() if ann_path and ann_path.exists() else None
    resolved_manifest = manifest_path.resolve() if manifest_path else None
    resolved_qc_output = (
        qc_output_path.resolve()
        if qc_output_path is not None
        else _default_qc_output_path(output_path, exercise_id).resolve()
    )

    print(f"[baseline] Loading pose CSV: {_display_path(csv_path)}")
    raw_df = load_pose_csv(csv_path)

    if resolved_ann is not None:
        print(f"[baseline] Applying annotation: {_display_path(resolved_ann)}")
    else:
        print("[baseline] No annotation found: sequence-level fallback may be used.")

    exercise_def = load_exercise_definition(exercise_id, definitions_dir)
    print(
        "[baseline] Exercise definition loaded: "
        f"{exercise_def.exercise_id} v{exercise_def.version}"
    )
    created_at = datetime.now(timezone.utc)
    baseline_id = _baseline_id(
        exercise_id=exercise_def.exercise_id,
        definition_version=exercise_def.version,
        baseline_status=baseline_status,
        created_at=created_at,
    )
    baseline_dir = (
        baseline_output_dir.resolve()
        if baseline_output_dir is not None
        else (_DEFAULT_BASELINES_DIR / baseline_id).resolve()
    )
    default_pipeline = load_pipeline_config(
        _PROJECT_ROOT / "configs/pipeline_default.yaml"
    )
    default_biomarker = default_pipeline.biomarker

    cfg = build_stage_check_pipeline_config(
        exercise_id=exercise_id,
        definitions_dir=definitions_dir,
        annotation_csv=resolved_ann,
        enable_validation=True,
        enable_annotation=resolved_ann is not None,
        enable_preprocessing=True,
        enable_normalization=True,
        enable_canonicalization=True,
        enable_rep_segmentation=True,
        enable_phase_segmentation=True,
        enable_features=True,
        enable_role_context=True,
        enable_biomech=True,
        enable_biomarker=False,
    )

    print("[baseline] Running pipeline stages ①-⑨.")
    df, report = run_pipeline(raw_df, cfg)

    print("[baseline] Rebuilding feature records for baseline statistics.")
    feat_records = extract_rep_features(df, exercise_def)
    phase_summary_records = summarize_phase_to_rep(feat_records, exercise_def)
    feat_records = feat_records + phase_summary_records
    print(f"  {len(feat_records)} FeatureRecord(s)")

    print("[baseline] Rebuilding biomech records for baseline statistics.")
    biomech_records = extract_rep_biomech(
        df,
        exercise_def,
        use_confidence_weight=True,
    )
    print(f"  {len(biomech_records)} BiomechRecord(s)")

    low_confidence_score_weights = {
        "spatial": 0.0,
        "temporal": 0.0,
        "control": 0.0,
        "biomech": low_confidence_biomech_weight,
    }
    depth_dependency_score_weights = (
        dict(
            default_biomarker.depth_dependency_score_weights
            or DEFAULT_DEPTH_DEPENDENCY_SCORE_WEIGHTS
        )
        if depth_dependency_score_weights is None
        else dict(depth_dependency_score_weights)
    )
    scoring_focus_weights = (
        dict(default_biomarker.scoring_focus_weights or DEFAULT_SCORING_FOCUS_WEIGHTS)
        if scoring_focus_weights is None
        else dict(scoring_focus_weights)
    )
    feature_score_weight_overrides = (
        dict(
            default_biomarker.feature_score_weight_overrides
            or DEFAULT_FEATURE_SCORE_WEIGHT_OVERRIDES
        )
        if feature_score_weight_overrides is None
        else dict(feature_score_weight_overrides)
    )
    feature_score_direction_overrides = (
        dict(default_biomarker.feature_score_direction_overrides or {})
        if feature_score_direction_overrides is None
        else dict(feature_score_direction_overrides)
    )
    domain_feature_family_weights = (
        dict(default_biomarker.domain_feature_family_weights or {})
        if domain_feature_family_weights is None
        else dict(domain_feature_family_weights)
    )

    new_metrics = build_baseline_from_records(
        feat_records,
        biomech_records,
        domain_feature_family_weights=domain_feature_family_weights,
        low_confidence_score_weights=low_confidence_score_weights,
        depth_dependency_score_weights=depth_dependency_score_weights,
        scoring_focus_weights=scoring_focus_weights,
        feature_score_weight_overrides=feature_score_weight_overrides,
        feature_score_direction_overrides=feature_score_direction_overrides,
    )
    print(f"[baseline] Built baseline statistics: {len(new_metrics)} metrics")

    qc_payload = build_baseline_qc(
        feat_records,
        biomech_records,
        exercise_definition=exercise_def,
        baseline_metrics=new_metrics,
        baseline_status=baseline_status,
        source_type=source_type,
        pose_backend=pose_backend,
        coordinate_mode=coordinate_mode,
        recording_count=1,
        source_files=[_display_path(csv_path)],
        annotation_files=[_display_path(resolved_ann)] if resolved_ann else [],
        manifest_path=_display_path(resolved_manifest) if resolved_manifest else None,
        domain_feature_family_weights=domain_feature_family_weights,
        low_confidence_score_weights=low_confidence_score_weights,
        depth_dependency_score_weights=depth_dependency_score_weights,
        scoring_focus_weights=scoring_focus_weights,
        feature_score_weight_overrides=feature_score_weight_overrides,
        feature_score_direction_overrides=feature_score_direction_overrides,
    )
    qc_payload["recording_id"] = recording_id_from_pose_csv(csv_path)
    qc_payload["pipeline_report_keys"] = sorted(report.keys())
    qc_payload["baseline_id"] = baseline_id
    qc_payload["created_at"] = created_at.isoformat()
    qc_payload["source_mode"] = source_mode
    qc_payload["used_for_current_scoring"] = False

    baseline_paths = _write_baseline_bundle(
        baseline_root=baseline_dir,
        baseline_id=baseline_id,
        exercise_def=exercise_def,
        baseline_status=baseline_status,
        source_type=source_type,
        source_mode=source_mode,
        pose_backend=pose_backend,
        coordinate_mode=coordinate_mode,
        metrics=new_metrics,
        qc_payload=qc_payload,
        created_at=created_at,
    )
    print(
        "[baseline] Saved baseline bundle: "
        f"{_display_path(baseline_paths['baseline_dir'])}"
    )

    if mirror_active_metrics:
        existing = _read_existing_baseline(output_path)
        existing[exercise_id] = new_metrics
        save_baseline(existing, output_path)
        print(f"[baseline] Saved metric statistics: {_display_path(output_path)}")

    save_baseline_qc(qc_payload, resolved_qc_output)
    print(f"[baseline] Saved QC metadata: {_display_path(resolved_qc_output)}")

    for i, (metric_id, stats) in enumerate(sorted(new_metrics.items())):
        print(
            f"  {metric_id:60s}  mean={stats['mean']:8.4f}  " f"std={stats['std']:8.4f}"
        )
        if i >= 19:
            print(f"  ... ({len(new_metrics) - 20} more)")
            break

    return {
        "baseline_id": baseline_id,
        "baseline_dir": baseline_paths["baseline_dir"],
        "metadata_path": baseline_paths["metadata_path"],
        "metrics_path": baseline_paths["metrics_path"],
        "bundle_qc_path": baseline_paths["qc_path"],
        "baseline_path": output_path,
        "qc_path": resolved_qc_output,
        "metrics": new_metrics,
        "qc": qc_payload,
    }


def main(*, default_mirror_active_metrics: bool = False) -> None:
    parser = argparse.ArgumentParser(description="Generate biomarker baseline.")
    parser.add_argument("--input", default=str(_DEFAULT_INPUT), help="Pose CSV path")
    parser.add_argument("--ann", default=str(_DEFAULT_ANN), help="Annotation CSV path")
    parser.add_argument("--exercise", default="squat", help="Exercise ID")
    parser.add_argument("--defs", default=str(_DEFAULT_DEFS), help="Definitions dir")
    parser.add_argument(
        "--output",
        default=str(_DEFAULT_OUTPUT),
        help="Output baseline JSON path",
    )
    parser.add_argument(
        "--qc-output",
        default=None,
        help=(
            "Output QC JSON path; defaults to "
            "data/reference/baseline_qc/<exercise>_baseline_qc.json"
        ),
    )
    parser.add_argument(
        "--baseline-output-dir",
        default=None,
        help=(
            "Baseline bundle directory; defaults to "
            "data/reference/baselines/<baseline_id>"
        ),
    )
    mirror_group = parser.add_mutually_exclusive_group()
    mirror_group.add_argument(
        "--mirror-active-metrics",
        dest="mirror_active_metrics",
        action="store_true",
        default=default_mirror_active_metrics,
        help="Also mirror generated metrics into data/reference/baseline_zscore.json",
    )
    mirror_group.add_argument(
        "--no-mirror-active-metrics",
        dest="mirror_active_metrics",
        action="store_false",
        help="Do not mirror generated metrics into data/reference/baseline_zscore.json",
    )
    parser.add_argument(
        "--baseline-status",
        default="provisional",
        choices=BASELINE_STATUSES,
        help="Baseline tier label",
    )
    parser.add_argument(
        "--source-type",
        default="synthetic",
        help="Baseline source type, e.g. synthetic or reviewed_recordings",
    )
    parser.add_argument(
        "--source-mode",
        default="single_file",
        help="Baseline source mode, e.g. single_file, current_run, or manifest",
    )
    parser.add_argument(
        "--pose-backend",
        default="mediapipe",
        help="Pose backend used to generate the source CSV",
    )
    parser.add_argument(
        "--coordinate-mode",
        default="norm",
        help="Coordinate mode used for baseline metric computation",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help=(
            "Optional manifest path recorded as provenance; "
            "single-file mode still reads --input"
        ),
    )
    parser.add_argument(
        "--low-confidence-biomech-weight",
        type=float,
        default=0.1,
        help=(
            "Scoring gravity used when including low-confidence biomech records "
            "in provisional baseline stats"
        ),
    )
    args = parser.parse_args()

    generate_baseline(
        csv_path=Path(args.input),
        ann_path=Path(args.ann) if args.ann else None,
        exercise_id=args.exercise,
        definitions_dir=Path(args.defs),
        output_path=Path(args.output),
        qc_output_path=Path(args.qc_output) if args.qc_output else None,
        baseline_output_dir=(
            Path(args.baseline_output_dir) if args.baseline_output_dir else None
        ),
        mirror_active_metrics=args.mirror_active_metrics,
        baseline_status=args.baseline_status,
        source_type=args.source_type,
        source_mode=args.source_mode,
        pose_backend=args.pose_backend,
        coordinate_mode=args.coordinate_mode,
        manifest_path=Path(args.manifest) if args.manifest else None,
        low_confidence_biomech_weight=args.low_confidence_biomech_weight,
    )


if __name__ == "__main__":
    main()
