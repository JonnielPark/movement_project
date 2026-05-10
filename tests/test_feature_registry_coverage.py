from pathlib import Path

import numpy as np
import pandas as pd

from movement.exercise_definition import load_exercise_definition
from movement.features import audit_feature_registry
from movement.pipeline import PipelineConfig, run_pipeline


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFINITIONS_DIR = _PROJECT_ROOT / "data" / "definitions" / "exercises"


def _minimal_pose_df():
    return pd.DataFrame(
        {
            "frame": [0, 1, 2],
            "timestamp": np.arange(3) / 30.0,
            "use_for_analysis": True,
        }
    )


def test_feature_registry_audit_reports_connected_and_unsupported_yaml_entries():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)

    report = audit_feature_registry(exercise)

    assert report.connected_feature_domain_entries["spatial"] == [
        "rom",
        "symmetry",
        "shape",
    ]
    assert "rep_duration" in report.connected_feature_domain_entries["temporal"]
    assert "com_stability" in report.connected_feature_domain_entries["control"]
    assert {
        "domain": "spatial",
        "entry": "depth_proxy",
        "reason": "no_extractor_registered",
    } in report.unsupported_feature_domain_entries
    assert {
        "domain": "control",
        "entry": "joint_tracking_error",
        "reason": "no_extractor_registered",
    } in report.unsupported_feature_domain_entries


def test_feature_registry_audit_routes_biomechanical_proxy_entries_to_step_09():
    exercise = load_exercise_definition("plank_shoulder_tap", _DEFINITIONS_DIR)

    report = audit_feature_registry(exercise)

    assert {
        "domain": "biomechanical_proxy",
        "entry": "support_moment_proxy",
        "target_step": "09_biomechanical_proxy",
    } in report.external_step_feature_domain_entries
    assert not any(
        item["domain"] == "biomechanical_proxy"
        for item in report.unsupported_feature_domain_entries
    )


def test_feature_registry_audit_reports_compensation_candidate_coverage():
    exercise = load_exercise_definition("pike_pushup", _DEFINITIONS_DIR)

    report = audit_feature_registry(exercise)

    assert "tempo_instability" not in report.implemented_compensation_candidates
    assert {
        "candidate": "tempo_instability",
        "reason": "declared_unimplemented",
    } in report.unimplemented_compensation_candidates
    assert {
        "candidate": "elbow_flare",
        "reason": "no_rule_registered",
    } in report.unimplemented_compensation_candidates


def test_pipeline_reports_feature_registry_coverage_when_features_run():
    config = PipelineConfig()
    config.validation.enabled = False
    config.annotation.enabled = False
    config.exercise_definition.enabled = True
    config.exercise_definition.exercise_id = "squat"
    config.preprocessing.enabled = False
    config.normalization.enabled = False
    config.rep_segmentation.enabled = False
    config.phase_segmentation.enabled = False
    config.features.enabled = True
    config.biomech.enabled = False
    config.biomarker.enabled = False

    _, report = run_pipeline(_minimal_pose_df(), config)

    coverage = report["feature_registry_coverage"]
    assert coverage["exercise_id"] == "squat"
    assert "knee_valgus" in coverage["implemented_compensation_candidates"]
    assert {
        "candidate": "asymmetric_depth",
        "reason": "declared_unimplemented",
    } in coverage["unimplemented_compensation_candidates"]
