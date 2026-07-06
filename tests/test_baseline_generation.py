from __future__ import annotations

import json
from pathlib import Path

from movement.biomech import BiomechRecord
from movement.biomarker.scoring import (
    build_baseline_from_records,
    build_baseline_qc,
)
from movement.core.io import load_pose_csv
from movement.exercise_definition import load_exercise_definition
from movement.features import FeatureRecord
from movement.pipeline import run_pipeline
from movement.stage_context import build_stage_check_pipeline_config
from scripts.generate_baseline import generate_baseline

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFINITIONS_DIR = _PROJECT_ROOT / "data" / "definitions" / "exercises"


def _exercise():
    return load_exercise_definition("squat", _DEFINITIONS_DIR)


def test_baseline_qc_tracks_included_and_withheld_records():
    exercise = _exercise()
    feat_records = [
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.left_knee",
            exercise_id="squat",
            rep_id=1,
            value=90.0,
            unit="degree",
            source_fields=["feature_domains.spatial"],
            availability="assessed",
        ),
        FeatureRecord(
            feature_id="spatial.role_alignment.left_right.range_of_motion_xy.knee",
            exercise_id="squat",
            rep_id=1,
            value=0.3,
            unit="dimensionless",
            source_fields=["feature_domains.spatial"],
            availability="low_confidence",
            availability_reasons=["view_metric_low"],
            depth_dependency="high",
            model_depth_reliability="low",
        ),
    ]
    biomech_records = [
        BiomechRecord(
            metric_id="biomech.com.range_x",
            exercise_id="squat",
            rep_id=1,
            value=0.1,
            unit="torso_length_ratio",
            source_fields=["biomechanical_focus.expected_com_motion"],
        )
    ]

    baseline = build_baseline_from_records(feat_records, biomech_records)
    qc = build_baseline_qc(
        feat_records,
        biomech_records,
        exercise_definition=exercise,
        baseline_metrics=baseline,
        baseline_status="provisional",
        source_type="synthetic",
        pose_backend="mediapipe",
        source_files=["synthetic.csv"],
        annotation_files=["synthetic_annotation.csv"],
    )

    assert sorted(baseline) == [
        "biomech.com.range_x",
        "spatial.range_of_motion.xy.left_knee",
    ]
    assert qc["baseline_status"] == "provisional"
    assert qc["definition_version"] == exercise.version
    assert qc["recording_count"] == 1
    assert qc["rep_count"] == 1
    assert qc["included_metric_count"] == 2
    assert qc["withheld_metric_count"] == 1
    assert qc["availability_counts"] == {"assessed": 1, "low_confidence": 2}
    assert qc["low_confidence_score_weights"]["biomech"] == 0.1
    assert qc["depth_dependency_score_weights"]["high"] == 0.1
    assert qc["scoring_focus_weights"]["primary"] == 1.0
    assert qc["scoring_focus_weights"]["diagnostic"] == 0.0
    assert qc["feature_score_weight_overrides"] == {}
    assert qc["feature_score_direction_overrides"] == {}
    assert qc["withheld_reason_counts"]["view_metric_low"] == 1
    assert "monocular_biomech_proxy_low_confidence" not in qc["withheld_reason_counts"]


def test_generate_baseline_writes_provisional_stats_bundle_and_qc(tmp_path):
    baseline_path = tmp_path / "baseline_zscore.json"
    qc_path = tmp_path / "squat_baseline_qc.json"
    baseline_dir = tmp_path / "squat_baseline"

    result = generate_baseline(
        csv_path=_PROJECT_ROOT / "data/pose/sample/mediapipe_squat_synthetic.csv",
        ann_path=(
            _PROJECT_ROOT / "data/pose/sample/mediapipe_squat_synthetic_annotation.csv"
        ),
        exercise_id="squat",
        definitions_dir=_DEFINITIONS_DIR,
        output_path=baseline_path,
        qc_output_path=qc_path,
        baseline_output_dir=baseline_dir,
        mirror_active_metrics=False,
        baseline_status="provisional",
        source_type="synthetic",
        pose_backend="mediapipe",
    )

    qc_payload = json.loads(qc_path.read_text(encoding="utf-8"))
    generated_metrics = json.loads((baseline_dir / "metrics.json").read_text())
    generated_qc = json.loads((baseline_dir / "qc.json").read_text())
    baseline_metadata = (baseline_dir / "baseline.yaml").read_text(encoding="utf-8")

    assert not baseline_path.exists()
    assert generated_metrics
    assert any(key.startswith("biomech.") for key in generated_metrics)
    assert result["metrics"] == generated_metrics
    assert generated_qc["baseline_id"] == result["baseline_id"]
    assert "active_for_scoring: false" in baseline_metadata
    assert "metrics_path: metrics.json" in baseline_metadata
    assert result["baseline_dir"] == baseline_dir.resolve()
    assert qc_payload["exercise_id"] == "squat"
    assert qc_payload["definition_version"] == "0.6.0"
    assert qc_payload["baseline_status"] == "provisional"
    assert qc_payload["source_type"] == "synthetic"
    assert qc_payload["pose_backend"] == "mediapipe"
    assert qc_payload["coordinate_mode"] == "norm"
    assert qc_payload["domain_feature_family_weights"]["spatial"] == {
        "range_of_motion": 0.60,
        "movement_path": 0.15,
        "support_consistency": 0.05,
        "role_alignment": 0.15,
        "phase_profile": 0.05,
    }
    assert qc_payload["domain_feature_family_weights"]["temporal"] == {
        "tempo": 0.25,
        "variability": 0.50,
        "phase_profile": 0.25,
    }
    assert qc_payload["depth_dependency_score_weights"]["moderate"] == 0.5
    assert qc_payload["scoring_focus_weights"] == {
        "primary": 1.0,
        "secondary": 0.45,
        "context_constraint": 0.6,
        "compensation": 0.5,
        "diagnostic": 0.0,
    }
    assert qc_payload["feature_score_weight_overrides"] == {
        "spatial.movement_path.arc_length_xy.left_ankle.*": 0.0,
        "spatial.movement_path.arc_length_xy.right_ankle.*": 0.0,
        "spatial.movement_path.arc_length_xyz.left_ankle.*": 0.0,
        "spatial.movement_path.arc_length_xyz.right_ankle.*": 0.0,
        "spatial.movement_path.arc_length_xyz.left_knee.*": 0.0,
        "spatial.movement_path.arc_length_xyz.right_knee.*": 0.0,
        "spatial.range_of_motion.xyz.*": 0.25,
        "control.compensation.knee_valgus.xy.*": 0.25,
        "control.compensation.knee_varus.xy.*": 0.25,
        "control.compensation.excessive_trunk_flexion.xy": 0.5,
        "control.compensation.excessive_trunk_flexion.xyz": 0.25,
        "spatial.range_of_motion.xy.left_hip_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xy.right_hip_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xy.left_knee_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xy.right_knee_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xy.left_ankle_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xy.right_ankle_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xyz.left_hip_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xyz.right_hip_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xyz.left_knee_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xyz.right_knee_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xyz.left_ankle_angle.turnaround_hold": 0.0,
        "spatial.range_of_motion.xyz.right_ankle_angle.turnaround_hold": 0.0,
    }
    assert qc_payload["feature_score_direction_overrides"] == {
        "spatial.support_consistency.*": "upper_bound_only",
        "spatial.role_alignment.left_right.support_consistency_xy_drift.*": "upper_bound_only",
        "spatial.movement_path.arc_length_xy.left_hip.turnaround_hold": "upper_bound_only",
        "spatial.movement_path.arc_length_xy.right_hip.turnaround_hold": "upper_bound_only",
        "spatial.movement_path.arc_length_xy.left_knee.turnaround_hold": "upper_bound_only",
        "spatial.movement_path.arc_length_xy.right_knee.turnaround_hold": "upper_bound_only",
    }
    assert qc_payload["recording_count"] == 1
    assert qc_payload["rep_count"] >= 1
    assert qc_payload["included_metric_count"] == len(generated_metrics)
    assert qc_payload["withheld_metric_count"] >= 1


def test_pipeline_auto_generates_current_run_baseline_when_missing(tmp_path):
    baseline_path = tmp_path / "baseline_zscore.json"
    baseline_output_dir = tmp_path / "baselines"
    qc_output_dir = tmp_path / "baseline_qc"
    pose_csv = _PROJECT_ROOT / "data/pose/sample/mediapipe_squat_synthetic.csv"
    annotation_csv = (
        _PROJECT_ROOT / "data/pose/sample/mediapipe_squat_synthetic_annotation.csv"
    )
    raw_df = load_pose_csv(pose_csv)
    cfg = build_stage_check_pipeline_config(
        exercise_id="squat",
        definitions_dir=_DEFINITIONS_DIR,
        annotation_csv=annotation_csv,
        enable_validation=True,
        enable_annotation=True,
        enable_preprocessing=True,
        enable_normalization=True,
        enable_canonicalization=True,
        enable_rep_segmentation=True,
        enable_phase_segmentation=True,
        enable_features=True,
        enable_role_context=True,
        enable_biomech=True,
        enable_biomarker=True,
    )
    cfg.input.path = str(pose_csv)
    cfg.biomarker.baseline_generation.active_metrics_path = str(baseline_path)
    cfg.biomarker.baseline_generation.output_dir = str(baseline_output_dir)
    cfg.biomarker.baseline_generation.qc_output_dir = str(qc_output_dir)
    cfg.biomarker.baseline_generation.mirror_active_metrics = False
    cfg.biomarker.baseline_generation.use_generated_for_current_scoring = True

    _, report = run_pipeline(raw_df, cfg)

    generated = report["baseline_generation"]
    assert generated["status"] == "generated"
    assert generated["source_mode"] == "current_run"
    assert generated["used_for_current_scoring"] is True
    assert generated["mirrored_active_metrics"] is False
    assert generated["metric_count"] > 0
    assert not baseline_path.exists()
    assert (Path(generated["metrics_path"])).exists()
    assert (Path(generated["qc_path"])).exists()
    assert report["biomarker_scores"]
