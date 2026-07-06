from __future__ import annotations

import json
from pathlib import Path

import pytest

from movement.biomech import BiomechRecord
from movement.biomarker.scoring import (
    derive_biomarkers,
    normalize_depth_dependency_score_weights,
    normalize_domain_feature_family_weights,
    normalize_domain_weights,
    normalize_feature_score_direction_overrides,
    normalize_feature_score_weight_overrides,
    normalize_low_confidence_score_weights,
    normalize_scoring_focus_weights,
    normalize_score_bounds,
)
from movement.exercise_definition import load_exercise_definition
from movement.features import FeatureRecord
from movement.pipeline import load_pipeline_config

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFINITIONS_DIR = _PROJECT_ROOT / "data" / "definitions" / "exercises"


def _write_baseline(path: Path) -> None:
    baseline = {
        "squat": {
            "spatial.range_of_motion.xy.left_knee": {"mean": 100.0, "std": 1.0},
            "temporal.tempo.rep_duration": {"mean": 100.0, "std": 1.0},
            "control.stability.hip_center_x_std": {"mean": 100.0, "std": 1.0},
            "biomech.com.range_x": {"mean": 100.0, "std": 1.0},
        }
    }
    path.write_text(json.dumps(baseline), encoding="utf-8")


def _records():
    feat_records = [
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.left_knee",
            exercise_id="squat",
            rep_id=1,
            value=90.0,
            unit="degree",
            source_fields=["feature_domains.spatial"],
            depth_dependency="none",
        ),
        FeatureRecord(
            feature_id="temporal.tempo.rep_duration",
            exercise_id="squat",
            rep_id=1,
            value=4.1,
            unit="second",
            source_fields=["feature_domains.temporal"],
            depth_dependency="none",
        ),
        FeatureRecord(
            feature_id="control.stability.hip_center_x_std",
            exercise_id="squat",
            rep_id=1,
            value=70.0,
            unit="torso_length_ratio",
            source_fields=["feature_domains.control"],
            depth_dependency="none",
        ),
    ]
    biomech_records = [
        BiomechRecord(
            metric_id="biomech.com.range_x",
            exercise_id="squat",
            rep_id=1,
            value=60.0,
            unit="torso_length_ratio",
            source_fields=["biomechanical_focus.expected_com_motion"],
        )
    ]
    return feat_records, biomech_records


def test_default_domain_weights_are_equal():
    assert normalize_domain_weights() == {
        "spatial": 0.25,
        "temporal": 0.25,
        "control": 0.25,
        "biomech": 0.25,
    }


def test_default_score_bounds_are_zero_to_hundred():
    assert normalize_score_bounds() == {"min": 0.0, "max": 100.0}


def test_default_low_confidence_score_weights_keep_biomech_low_gravity():
    assert normalize_low_confidence_score_weights() == {
        "spatial": 0.0,
        "temporal": 0.0,
        "control": 0.0,
        "biomech": 0.1,
    }


def test_default_depth_dependency_score_weights_are_recording_view_heavy():
    assert normalize_depth_dependency_score_weights() == {
        "none": 1.0,
        "low": 1.0,
        "moderate": 0.5,
        "high": 0.1,
        "unknown": 0.3,
    }


def test_default_scoring_focus_weights_prioritize_primary_intent():
    assert normalize_scoring_focus_weights() == {
        "primary": 1.0,
        "secondary": 0.45,
        "context_constraint": 0.6,
        "compensation": 0.5,
        "diagnostic": 0.0,
    }


def test_default_feature_score_weight_overrides_are_empty():
    assert normalize_feature_score_weight_overrides() == {}


def test_default_feature_score_direction_overrides_are_empty():
    assert normalize_feature_score_direction_overrides() == {}


def test_default_domain_feature_family_weights_are_empty():
    assert normalize_domain_feature_family_weights() == {}


def test_domain_feature_family_weights_are_normalized():
    weights = normalize_domain_feature_family_weights(
        {"spatial": {"range_of_motion": 2.0, "movement_path": 1.0}}
    )
    assert weights["spatial"]["range_of_motion"] == pytest.approx(2.0 / 3.0)
    assert weights["spatial"]["movement_path"] == pytest.approx(1.0 / 3.0)


def test_pipeline_default_config_exposes_scoring_parameters():
    config = load_pipeline_config(_PROJECT_ROOT / "configs" / "pipeline_default.yaml")
    assert config.biomarker.score_bounds == {
        "min": 0.0,
        "max": 100.0,
    }
    assert config.biomarker.domain_weights == {
        "spatial": 1.0,
        "temporal": 1.0,
        "control": 1.0,
        "biomech": 1.0,
    }
    assert config.biomarker.domain_feature_family_weights == {
        "spatial": {
            "range_of_motion": 0.60,
            "movement_path": 0.15,
            "support_consistency": 0.05,
            "role_alignment": 0.15,
            "phase_profile": 0.05,
        },
        "temporal": {
            "tempo": 0.25,
            "variability": 0.50,
            "phase_profile": 0.25,
        },
    }
    assert config.biomarker.scoring_focus_weights == {
        "primary": 1.0,
        "secondary": 0.45,
        "context_constraint": 0.6,
        "compensation": 0.5,
        "diagnostic": 0.0,
    }
    assert config.biomarker.low_confidence_score_weights == {
        "spatial": 0.0,
        "temporal": 0.0,
        "control": 0.0,
        "biomech": 0.1,
    }
    assert config.biomarker.depth_dependency_score_weights == {
        "none": 1.0,
        "low": 1.0,
        "moderate": 0.5,
        "high": 0.1,
        "unknown": 0.3,
    }
    assert config.biomarker.feature_score_weight_overrides == {
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
    assert config.biomarker.feature_score_direction_overrides == {
        "spatial.support_consistency.*": "upper_bound_only",
        "spatial.role_alignment.left_right.support_consistency_xy_drift.*": "upper_bound_only",
        "spatial.movement_path.arc_length_xy.left_hip.turnaround_hold": "upper_bound_only",
        "spatial.movement_path.arc_length_xy.right_hip.turnaround_hold": "upper_bound_only",
        "spatial.movement_path.arc_length_xy.left_knee.turnaround_hold": "upper_bound_only",
        "spatial.movement_path.arc_length_xy.right_knee.turnaround_hold": "upper_bound_only",
    }


def test_equal_default_weights_drive_final_score(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    _write_baseline(baseline_path)
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records, biomech_records = _records()

    _, score_records = derive_biomarkers(
        feat_records,
        biomech_records,
        exercise,
        exercise.version,
        baseline_path=baseline_path,
    )

    score = score_records[0]
    assert score.domain_scores == {
        "spatial": 99.0,
        "temporal": 98.0,
        "control": 97.0,
        "biomech": 99.96,
    }
    assert score.domain_weights == {
        "spatial": 0.25,
        "temporal": 0.25,
        "control": 0.25,
        "biomech": 0.25,
    }
    assert score.final_score == 98.49
    assert score.as_dict()["domain_weights"] == score.domain_weights
    assert (
        score.as_dict()["domain_feature_family_weights"]
        == score.domain_feature_family_weights
    )
    assert (
        score.as_dict()["low_confidence_score_weights"]
        == score.low_confidence_score_weights
    )
    assert (
        score.as_dict()["depth_dependency_score_weights"]
        == score.depth_dependency_score_weights
    )
    assert score.as_dict()["scoring_focus_weights"] == score.scoring_focus_weights
    assert (
        score.as_dict()["feature_score_weight_overrides"]
        == score.feature_score_weight_overrides
    )
    assert (
        score.as_dict()["feature_score_direction_overrides"]
        == score.feature_score_direction_overrides
    )
    assert score.score_bounds == {"min": 0.0, "max": 100.0}
    assert score.as_dict()["score_bounds"] == score.score_bounds


def test_custom_relative_weights_are_normalized(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    _write_baseline(baseline_path)
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records, biomech_records = _records()

    _, score_records = derive_biomarkers(
        feat_records,
        biomech_records,
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        domain_weights={
            "spatial": 1.0,
            "temporal": 1.0,
            "control": 2.0,
            "biomech": 0.0,
        },
    )

    score = score_records[0]
    assert score.domain_weights == {
        "spatial": 0.25,
        "temporal": 0.25,
        "control": 0.5,
        "biomech": 0.0,
    }
    assert score.final_score == 97.75


def test_custom_score_bounds_scale_domain_and_final_scores(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    _write_baseline(baseline_path)
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records, biomech_records = _records()

    _, score_records = derive_biomarkers(
        feat_records,
        biomech_records,
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        score_bounds={"min": 0.0, "max": 10.0},
    )

    score = score_records[0]
    assert score.score_bounds == {"min": 0.0, "max": 10.0}
    assert score.domain_scores == {
        "spatial": 9.9,
        "temporal": 9.8,
        "control": 9.7,
        "biomech": 10.0,
    }
    assert score.final_score == 9.85


def test_negative_domain_weight_raises():
    with pytest.raises(ValueError, match="must be >= 0"):
        normalize_domain_weights({"control": -1.0})


def test_invalid_low_confidence_score_weight_raises():
    with pytest.raises(ValueError, match="between 0 and 1"):
        normalize_low_confidence_score_weights({"biomech": 1.5})


def test_invalid_depth_dependency_score_weight_raises():
    with pytest.raises(ValueError, match="between 0 and 1"):
        normalize_depth_dependency_score_weights({"high": 1.5})


def test_invalid_scoring_focus_weight_raises():
    with pytest.raises(ValueError, match="between 0 and 1"):
        normalize_scoring_focus_weights({"secondary": 1.5})


def test_invalid_feature_score_weight_override_raises():
    with pytest.raises(ValueError, match="between 0 and 1"):
        normalize_feature_score_weight_overrides(
            {"spatial.range_of_motion.xy.left_knee": 1.5}
        )


def test_invalid_feature_score_direction_override_raises():
    with pytest.raises(ValueError, match="must be one of"):
        normalize_feature_score_direction_overrides(
            {"spatial.movement_path.arc_length_xy.left_knee": "sideways"}
        )


def test_invalid_domain_feature_family_weight_raises():
    with pytest.raises(ValueError, match="must be >= 0"):
        normalize_domain_feature_family_weights({"spatial": {"range_of_motion": -1.0}})

    with pytest.raises(ValueError, match="must be positive"):
        normalize_domain_feature_family_weights({"spatial": {"range_of_motion": 0.0}})


def test_invalid_score_bounds_raise():
    with pytest.raises(ValueError, match="greater than lower bound"):
        normalize_score_bounds({"min": 10.0, "max": 10.0})

    with pytest.raises(ValueError, match="lower bound must be >= 0"):
        normalize_score_bounds({"min": -1.0, "max": 100.0})


def test_feature_score_weight_override_attenuates_matching_feature(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    _write_baseline(baseline_path)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["squat"]["spatial.movement_path.arc_length_xyz.left_ankle"] = {
        "mean": 100.0,
        "std": 1.0,
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records, biomech_records = _records()
    feat_records.append(
        FeatureRecord(
            feature_id="spatial.movement_path.arc_length_xyz.left_ankle",
            exercise_id="squat",
            rep_id=1,
            value=50.0,
            unit="torso_length_ratio",
            source_fields=["feature_domains.spatial"],
            depth_dependency="none",
        )
    )

    _, score_records = derive_biomarkers(
        feat_records,
        biomech_records,
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        feature_score_weight_overrides={
            "spatial.movement_path.arc_length_xyz.left_ankle": 0.1,
        },
    )

    score = score_records[0]
    ankle_deduction = next(
        item
        for item in score.deductions
        if item["feature_id"] == "spatial.movement_path.arc_length_xyz.left_ankle"
    )
    assert ankle_deduction["feature_weight"] == 0.1
    assert ankle_deduction["confidence_weight"] == 0.1
    assert score.feature_score_weight_overrides == {
        "spatial.movement_path.arc_length_xyz.left_ankle": 0.1,
    }


def test_secondary_focus_weight_attenuates_matching_feature(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "spatial.range_of_motion.xy.trunk_angle": {
                "mean": 10.0,
                "std": 1.0,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.trunk_angle",
            exercise_id="squat",
            rep_id=1,
            value=0.0,
            unit="degree",
            source_fields=["joint_actions.secondary"],
            depth_dependency="none",
            focus_tier="secondary",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        scoring_focus_weights={"secondary": 0.45},
    )

    deduction = score_records[0].deductions[0]
    assert deduction["focus_tier"] == "secondary"
    assert deduction["focus_weight"] == 0.45
    assert deduction["confidence_weight"] == 0.45
    assert deduction["deduction"] == 4.5


def test_diagnostic_focus_weight_zero_withholds_feature(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "spatial.support_consistency.axis_path_z.left_ankle": {
                "mean": 100.0,
                "std": 1.0,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.support_consistency.axis_path_z.left_ankle",
            exercise_id="squat",
            rep_id=1,
            value=80.0,
            unit="torso_length_ratio",
            source_fields=[
                "feature_domains.spatial",
                "support_consistency.axis_diagnostic",
            ],
            depth_dependency="none",
            focus_tier="diagnostic",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
    )

    score = score_records[0]
    assert score.deductions == []
    assert score.withheld_features[0]["focus_tier"] == "diagnostic"
    assert score.withheld_features[0]["reasons"] == ["scoring_focus_weight_zero"]


def test_feature_score_weight_override_prefix_pattern_matches_phase_suffix(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "spatial.movement_path.arc_length_xyz.left_ankle.descent": {
                "mean": 100.0,
                "std": 1.0,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.movement_path.arc_length_xyz.left_ankle.descent",
            exercise_id="squat",
            rep_id=1,
            value=50.0,
            unit="torso_length_ratio",
            source_fields=["feature_domains.spatial"],
            depth_dependency="none",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        feature_score_weight_overrides={
            "spatial.movement_path.arc_length_xyz.left_ankle.*": 0.1,
        },
    )

    assert score_records[0].deductions[0]["feature_weight"] == 0.1


def test_feature_score_weight_zero_withholds_matching_feature(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "spatial.movement_path.arc_length_xyz.left_ankle.descent": {
                "mean": 100.0,
                "std": 1.0,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.movement_path.arc_length_xyz.left_ankle.descent",
            exercise_id="squat",
            rep_id=1,
            value=50.0,
            unit="torso_length_ratio",
            source_fields=["feature_domains.spatial"],
            depth_dependency="none",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        feature_score_weight_overrides={
            "spatial.movement_path.arc_length_xyz.left_ankle.*": 0.0,
        },
    )

    score = score_records[0]
    assert score.deductions == []
    assert score.withheld_features[0]["feature_id"] == (
        "spatial.movement_path.arc_length_xyz.left_ankle.descent"
    )
    assert score.withheld_features[0]["reasons"] == ["feature_score_weight_zero"]


def test_feature_score_direction_upper_bound_only_ignores_lower_values(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "spatial.movement_path.arc_length_xy.left_knee.turnaround_hold": {
                "mean": 10.0,
                "std": 1.0,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.movement_path.arc_length_xy.left_knee.turnaround_hold",
            exercise_id="squat",
            rep_id=1,
            value=5.0,
            unit="torso_length_ratio",
            source_fields=["feature_domains.spatial"],
            depth_dependency="none",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        feature_score_direction_overrides={
            "spatial.movement_path.arc_length_xy.left_knee.turnaround_hold": (
                "upper_bound_only"
            ),
        },
    )

    score = score_records[0]
    deduction = score.deductions[0]
    assert score.domain_scores["spatial"] == 100.0
    assert deduction["score_direction"] == "upper_bound_only"
    assert deduction["z_raw"] == -5.0
    assert deduction["z"] == 0.0
    assert deduction["deduction"] == 0.0
    assert score.feature_score_direction_overrides == {
        "spatial.movement_path.arc_length_xy.left_knee.turnaround_hold": "upper_bound_only",
    }


def test_feature_score_direction_upper_bound_only_penalizes_higher_values(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "spatial.movement_path.arc_length_xy.left_knee.turnaround_hold": {
                "mean": 10.0,
                "std": 1.0,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.movement_path.arc_length_xy.left_knee.turnaround_hold",
            exercise_id="squat",
            rep_id=1,
            value=15.0,
            unit="torso_length_ratio",
            source_fields=["feature_domains.spatial"],
            depth_dependency="none",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        feature_score_direction_overrides={
            "spatial.movement_path.arc_length_xy.left_knee.*": "upper_bound_only",
        },
    )

    score = score_records[0]
    deduction = score.deductions[0]
    assert score.domain_scores["spatial"] == 95.0
    assert deduction["score_direction"] == "upper_bound_only"
    assert deduction["z_raw"] == 5.0
    assert deduction["z"] == 5.0
    assert deduction["deduction"] == 5.0


def test_temporal_tolerance_band_ignores_acceptable_duration(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "temporal.tempo.rep_duration": {
                "mean": 1.467,
                "std": 0.1467,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="temporal.tempo.rep_duration",
            exercise_id="squat",
            rep_id=1,
            value=2.1,
            unit="second",
            source_fields=["feature_domains.temporal.tempo"],
            depth_dependency="none",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
    )

    score = score_records[0]
    deduction = score.deductions[0]
    assert score.domain_scores["temporal"] == 100.0
    assert deduction["scoring_mode"] == "acceptable_duration_band"
    assert deduction["z_raw"] == 0.0
    assert deduction["deduction"] == 0.0
    assert deduction["target_min_s"] == 1.2
    assert deduction["target_max_s"] == 3.5


def test_temporal_tolerance_band_penalizes_only_excess_duration(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "temporal.tempo.rep_duration": {
                "mean": 1.467,
                "std": 0.1467,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="temporal.tempo.rep_duration",
            exercise_id="squat",
            rep_id=1,
            value=4.1,
            unit="second",
            source_fields=["feature_domains.temporal.tempo"],
            depth_dependency="none",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
    )

    score = score_records[0]
    deduction = score.deductions[0]
    assert score.domain_scores["temporal"] == 98.0
    assert deduction["scoring_mode"] == "acceptable_duration_band"
    assert deduction["z_raw"] == 2.0
    assert deduction["deduction"] == 2.0
    assert deduction["target_tolerance_s"] == 0.3


def test_sequence_level_tempo_cv_is_scored_in_each_rep_audit(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "temporal.variability.tempo_cv": {
                "mean": 0.0,
                "std": 0.01,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="temporal.tempo.rep_duration",
            exercise_id="squat",
            rep_id=1,
            value=2.0,
            unit="second",
            source_fields=["feature_domains.temporal.tempo"],
            depth_dependency="none",
        ),
        FeatureRecord(
            feature_id="temporal.tempo.rep_duration",
            exercise_id="squat",
            rep_id=2,
            value=2.1,
            unit="second",
            source_fields=["feature_domains.temporal.tempo"],
            depth_dependency="none",
        ),
        FeatureRecord(
            feature_id="temporal.variability.tempo_cv",
            exercise_id="squat",
            rep_id=None,
            value=0.04,
            unit="dimensionless_cv",
            source_fields=[
                "feature_domains.temporal.variability",
                "temporal.tempo.rep_duration",
            ],
            depth_dependency="none",
        ),
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        domain_feature_family_weights={
            "temporal": {"tempo": 0.25, "variability": 0.50, "phase_profile": 0.25}
        },
    )

    assert {score.rep_id for score in score_records} == {1, 2}
    for score in score_records:
        assert score.domain_scores["temporal"] == 100.0
        deduction = score.deductions[0]
        assert deduction["feature_id"] == "temporal.variability.tempo_cv"
        assert deduction["scoring_mode"] == "maximum_sufficient_ceiling"
        assert deduction["z"] == 0.0
        assert deduction["target_max_cv"] == 0.05
        assert deduction["feature_family_weight"] == 0.5


def test_temporal_variability_band_penalizes_high_tempo_cv(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "temporal.variability.tempo_cv": {
                "mean": 0.0,
                "std": 0.01,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="temporal.tempo.rep_duration",
            exercise_id="squat",
            rep_id=1,
            value=2.0,
            unit="second",
            source_fields=["feature_domains.temporal.tempo"],
            depth_dependency="none",
        ),
        FeatureRecord(
            feature_id="temporal.variability.tempo_cv",
            exercise_id="squat",
            rep_id=None,
            value=0.10,
            unit="dimensionless_cv",
            source_fields=[
                "feature_domains.temporal.variability",
                "temporal.tempo.rep_duration",
            ],
            depth_dependency="none",
        ),
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        domain_feature_family_weights={
            "temporal": {"tempo": 0.25, "variability": 0.50, "phase_profile": 0.25}
        },
    )

    deduction = score_records[0].deductions[0]
    assert score_records[0].domain_scores["temporal"] == 99.5
    assert deduction["scoring_mode"] == "maximum_sufficient_ceiling"
    assert deduction["z"] == 1.0
    assert deduction["deduction"] == 0.5


def test_temporal_phase_profile_band_ignores_acceptable_ratio(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "temporal.phase_profile.duration_ratio.descent_ascent": {
                "mean": 1.0,
                "std": 0.1,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="temporal.phase_profile.duration_ratio.descent_ascent",
            exercise_id="squat",
            rep_id=1,
            value=1.3,
            unit="dimensionless",
            source_fields=["feature_domains.temporal.phase_profile"],
            depth_dependency="none",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        domain_feature_family_weights={
            "temporal": {"tempo": 0.25, "variability": 0.50, "phase_profile": 0.25}
        },
    )

    deduction = score_records[0].deductions[0]
    assert score_records[0].domain_scores["temporal"] == 100.0
    assert deduction["scoring_mode"] == "acceptable_ratio_band"
    assert deduction["z"] == 0.0
    assert deduction["deduction"] == 0.0
    assert deduction["target_min_ratio"] == 0.5
    assert deduction["target_max_ratio"] == 2.0


def test_temporal_phase_profile_band_penalizes_outside_ratio(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "temporal.phase_profile.duration_ratio.descent_ascent": {
                "mean": 1.0,
                "std": 0.1,
            }
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="temporal.phase_profile.duration_ratio.descent_ascent",
            exercise_id="squat",
            rep_id=1,
            value=2.5,
            unit="dimensionless",
            source_fields=["feature_domains.temporal.phase_profile"],
            depth_dependency="none",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        domain_feature_family_weights={
            "temporal": {"tempo": 0.25, "variability": 0.50, "phase_profile": 0.25}
        },
    )

    deduction = score_records[0].deductions[0]
    assert score_records[0].domain_scores["temporal"] == 99.5
    assert deduction["scoring_mode"] == "acceptable_ratio_band"
    assert deduction["z"] == 2.0
    assert deduction["deduction"] == 0.5
    assert deduction["target_tolerance_ratio"] == 0.25


def test_domain_feature_family_weights_do_not_redistribute_withheld_family(
    tmp_path,
):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "spatial.range_of_motion.xy.left_knee": {"mean": 10.0, "std": 1.0},
            "spatial.movement_path.arc_length_xyz.left_ankle": {
                "mean": 10.0,
                "std": 1.0,
            },
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.left_knee",
            exercise_id="squat",
            rep_id=1,
            value=0.0,
            unit="degree",
            source_fields=["feature_domains.spatial"],
            depth_dependency="none",
        ),
        FeatureRecord(
            feature_id="spatial.movement_path.arc_length_xyz.left_ankle",
            exercise_id="squat",
            rep_id=1,
            value=0.0,
            unit="torso_length_ratio",
            source_fields=["feature_domains.spatial"],
            depth_dependency="none",
        ),
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
        domain_feature_family_weights={
            "spatial": {"range_of_motion": 1.0, "movement_path": 1.0}
        },
        feature_score_weight_overrides={
            "spatial.movement_path.arc_length_xyz.left_ankle": 0.0,
        },
    )

    score = score_records[0]
    assert score.domain_scores["spatial"] == 95.0
    assert score.deductions == [
        {
            "feature_id": "spatial.range_of_motion.xy.left_knee",
            "value": 0.0,
            "scoring_mode": "baseline_zscore",
            "availability": "assessed",
            "availability_weight": 1.0,
            "depth_dependency": "none",
            "depth_dependency_weight": 1.0,
            "focus_tier": "primary",
            "focus_weight": 1.0,
            "feature_weight": 1.0,
            "feature_family": "range_of_motion",
            "feature_family_weight": 0.5,
            "confidence_weight": 1.0,
            "baseline_mean": 10.0,
            "baseline_std": 1.0,
            "score_direction": "two_sided",
            "z_raw": -10.0,
            "z": -10.0,
            "w": 0.5,
            "deduction": 5.0,
            "domain": "spatial",
        }
    ]
    withheld = score.withheld_features[0]
    assert withheld["feature_id"] == "spatial.movement_path.arc_length_xyz.left_ankle"
    assert withheld["reasons"] == ["feature_score_weight_zero"]


def test_range_of_motion_target_band_replaces_baseline_zscore_when_rom_is_sufficient(
    tmp_path,
):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "spatial.range_of_motion.xy.left_knee_angle": {"mean": 60.0, "std": 1.0},
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.left_knee_angle",
            exercise_id="squat",
            rep_id=1,
            value=120.0,
            unit="degree",
            source_fields=["feature_domains.spatial"],
            depth_dependency="none",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
    )

    score = score_records[0]
    deduction = score.deductions[0]
    assert score.domain_scores["spatial"] == 100.0
    assert deduction["scoring_mode"] == "minimum_sufficient_band"
    assert deduction["z"] == 0.0
    assert deduction["deduction"] == 0.0
    assert deduction["target_min"] == 90.0
    assert deduction["target_excessive"] == 160.0


def test_range_of_motion_target_band_penalizes_insufficient_rom_shortfall(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline = {
        "squat": {
            "spatial.range_of_motion.xy.left_knee_angle": {"mean": 60.0, "std": 1.0},
        }
    }
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.left_knee_angle",
            exercise_id="squat",
            rep_id=1,
            value=80.0,
            unit="degree",
            source_fields=["feature_domains.spatial"],
            depth_dependency="none",
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records,
        [],
        exercise,
        exercise.version,
        baseline_path=baseline_path,
    )

    score = score_records[0]
    deduction = score.deductions[0]
    assert score.domain_scores["spatial"] == 99.0
    assert deduction["scoring_mode"] == "minimum_sufficient_band"
    assert deduction["z"] == -1.0
    assert deduction["deduction"] == 1.0
