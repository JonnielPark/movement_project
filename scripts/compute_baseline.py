"""
Compute synthetic-normal baseline for biomarker scoring.

Runs the full pipeline (features + biomech) on the normal synthetic sample,
collects all FeatureRecord and BiomechRecord values, and saves per-metric
(mean, std) statistics to data/reference/baseline_zscore.json.

Regenerate whenever the feature set or synthetic data changes.

Usage:
    python scripts/compute_baseline.py
    python scripts/compute_baseline.py --exercise squat --output data/reference/baseline_zscore.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running directly from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd

from movement.biomech import extract_rep_biomech
from movement.biomarker.scoring import build_baseline_from_records, load_baseline, save_baseline
from movement.exercise_definition import load_exercise_definition
from movement.features import extract_rep_features
from movement.io import load_pose_csv
from movement.normalization import normalize_pose_by_hip_torso
from movement.annotation import apply_annotation
from movement.config import LANDMARKS


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_INPUT = _PROJECT_ROOT / "data/pose/sample/mediapipe_squat_synthetic.csv"
_DEFAULT_ANN = _PROJECT_ROOT / "data/pose/sample/mediapipe_squat_synthetic_annotation.csv"
_DEFAULT_DEFS = _PROJECT_ROOT / "data/definitions/exercises"
_DEFAULT_OUTPUT = _PROJECT_ROOT / "data/reference/baseline_zscore.json"


def compute_baseline(
    csv_path: Path,
    ann_path: Path | None,
    exercise_id: str,
    definitions_dir: Path,
    output_path: Path,
) -> None:
    print(f"[baseline] Loading pose CSV: {csv_path}")
    df = load_pose_csv(str(csv_path))

    if ann_path and ann_path.exists():
        print(f"[baseline] Applying annotation: {ann_path}")
        ann_df = pd.read_csv(ann_path)
        df, _ = apply_annotation(df, ann_df)
    else:
        print("[baseline] No annotation found — sequence-level features only.")

    print(f"[baseline] Normalizing coordinates.")
    df, _ = normalize_pose_by_hip_torso(df, landmarks=LANDMARKS)

    ex_def = load_exercise_definition(exercise_id, definitions_dir)
    print(f"[baseline] Exercise definition loaded: {ex_def.exercise_id} v{ex_def.version}")

    print("[baseline] Extracting features...")
    feat_records = extract_rep_features(df, ex_def)
    print(f"  {len(feat_records)} FeatureRecord(s)")

    print("[baseline] Extracting biomech metrics...")
    biomech_records = extract_rep_biomech(df, ex_def, use_visibility_weight=True)
    print(f"  {len(biomech_records)} BiomechRecord(s)")

    new_metrics = build_baseline_from_records(feat_records, biomech_records)
    print(f"[baseline] Built baseline: {len(new_metrics)} metrics")

    # Merge with existing baseline (preserves other exercises)
    existing: dict = {}
    if output_path.exists():
        import json
        with open(output_path, encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = {}

    existing[exercise_id] = new_metrics
    save_baseline(existing, output_path)
    print(f"[baseline] Saved to {output_path}")

    # Preview
    for i, (mid, stats) in enumerate(sorted(new_metrics.items())):
        print(f"  {mid:60s}  mean={stats['mean']:8.4f}  std={stats['std']:8.4f}")
        if i >= 19:
            print(f"  ... ({len(new_metrics) - 20} more)")
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute synthetic-normal baseline.")
    parser.add_argument("--input",    default=str(_DEFAULT_INPUT),  help="Pose CSV path")
    parser.add_argument("--ann",      default=str(_DEFAULT_ANN),    help="Annotation CSV path")
    parser.add_argument("--exercise", default="squat",              help="Exercise ID")
    parser.add_argument("--defs",     default=str(_DEFAULT_DEFS),   help="Exercise definitions dir")
    parser.add_argument("--output",   default=str(_DEFAULT_OUTPUT), help="Output JSON path")
    args = parser.parse_args()

    compute_baseline(
        csv_path=Path(args.input),
        ann_path=Path(args.ann) if args.ann else None,
        exercise_id=args.exercise,
        definitions_dir=Path(args.defs),
        output_path=Path(args.output),
    )


if __name__ == "__main__":
    main()
