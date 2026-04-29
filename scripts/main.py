"""
Movement Project — Pipeline Runner

Usage
-----
    python scripts/main.py
    python scripts/main.py --config configs/pipeline_default.yaml
    python scripts/main.py --input data/sample/mediapipe_forward_bend_sample.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make `movement` importable without package install
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from movement.config import LANDMARKS
from movement.io import load_pose_csv
from movement.pipeline import load_pipeline_config, run_pipeline


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the movement analysis pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=_ROOT / "configs" / "pipeline_default.yaml",
        metavar="PATH",
        help="Pipeline config YAML",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        metavar="PATH",
        help="Override input CSV path from config",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if not args.config.exists():
        print(f"[ERROR] config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    config = load_pipeline_config(args.config)
    input_path = args.input if args.input is not None else (_ROOT / config.input.path)

    print(f"[INFO] config : {args.config}")
    print(f"[INFO] input  : {input_path}")

    df = load_pose_csv(input_path)
    print(f"[INFO] loaded : {len(df)} frames, {df.shape[1]} columns")

    df, report = run_pipeline(df, config, LANDMARKS)

    print("\n[REPORT]")
    print(json.dumps(report, indent=2, default=str))

    if config.output.save_processed:
        out_path = _ROOT / config.output.processed_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
        print(f"\n[INFO] saved processed → {out_path}")

    if config.output.save_report:
        rep_path = _ROOT / config.output.report_path
        rep_path.parent.mkdir(parents=True, exist_ok=True)
        with open(rep_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[INFO] saved report    → {rep_path}")


if __name__ == "__main__":
    main()
