from __future__ import annotations

import json
from pathlib import Path

from movement.biomech import BiomechRecord
from movement.biomarker.scoring import derive_biomarkers
from movement.exercise_definition import load_exercise_definition
from movement.features import FeatureRecord

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFINITIONS_DIR = _PROJECT_ROOT / "data" / "definitions" / "exercises"


def _write_baseline(path: Path) -> None:
    baseline = {
        "squat": {
            "spatial.range_of_motion.xy.left_knee": {"mean": 100.0, "std": 1.0},
            "spatial.role_alignment.left_right.range_of_motion_xy.knee": {
                "mean": 0.0,
                "std": 0.1,
            },
            "biomech.com.range_x": {"mean": 0.0, "std": 0.1},
        }
    }
    path.write_text(json.dumps(baseline), encoding="utf-8")


def test_low_confidence_feature_is_passed_through_but_not_scored(tmp_path: Path):
    baseline_path = tmp_path / "baseline.json"
    _write_baseline(baseline_path)
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.left_knee",
            exercise_id="squat",
            rep_id=1,
            value=100.0,
            unit="degree",
            source_fields=["feature_domains.spatial"],
            availability="assessed",
            view_reliability="high",
        ),
        FeatureRecord(
            feature_id="spatial.role_alignment.left_right.range_of_motion_xy.knee",
            exercise_id="squat",
            rep_id=1,
            value=1.0,
            unit="dimensionless_cv",
            source_fields=["feature_domains.spatial"],
            availability="low_confidence",
            view_reliability="low",
            availability_reasons=["view_metric_low"],
            camera_zone="Z3",
            depth_dependency="high",
            model_depth_reliability="low",
            landmark_quality="low",
        ),
    ]

    biomarker_records, score_records = derive_biomarkers(
        feat_records=feat_records,
        biomech_records=[],
        exercise_definition=exercise,
        definition_version=exercise.version,
        baseline_path=baseline_path,
    )

    assert len(biomarker_records) == 2
    withheld_biomarker = next(
        record
        for record in biomarker_records
        if record.biomarker_id
        == "spatial.role_alignment.left_right.range_of_motion_xy.knee"
    )
    assert withheld_biomarker.availability == "low_confidence"
    assert withheld_biomarker.view_reliability == "low"
    assert withheld_biomarker.depth_dependency == "high"
    assert withheld_biomarker.model_depth_reliability == "low"
    assert withheld_biomarker.landmark_quality == "low"

    score = score_records[0]
    assert score.final_score == 100.0
    assert [item["feature_id"] for item in score.deductions] == [
        "spatial.range_of_motion.xy.left_knee"
    ]
    assert score.withheld_features == [
        {
            "domain": "spatial",
            "feature_id": "spatial.role_alignment.left_right.range_of_motion_xy.knee",
            "value": 1.0,
            "availability": "low_confidence",
            "view_reliability": "low",
            "camera_zone": "Z3",
            "depth_dependency": "high",
            "model_depth_reliability": "low",
            "landmark_quality": "low",
            "focus_tier": "primary",
            "reasons": ["view_metric_low", "availability_score_weight_zero"],
        }
    ]


def test_low_confidence_biomech_is_scored_with_low_gravity(tmp_path: Path):
    baseline_path = tmp_path / "baseline.json"
    _write_baseline(baseline_path)
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.left_knee",
            exercise_id="squat",
            rep_id=1,
            value=100.0,
            unit="degree",
            source_fields=["feature_domains.spatial"],
            availability="assessed",
        )
    ]
    biomech_records = [
        BiomechRecord(
            metric_id="biomech.com.range_x",
            exercise_id="squat",
            rep_id=1,
            value=1.0,
            unit="torso_length_ratio",
            source_fields=["biomechanical_focus.expected_com_motion"],
        )
    ]

    biomarker_records, score_records = derive_biomarkers(
        feat_records=feat_records,
        biomech_records=biomech_records,
        exercise_definition=exercise,
        definition_version=exercise.version,
        baseline_path=baseline_path,
    )

    biomech_biomarker = next(
        record
        for record in biomarker_records
        if record.biomarker_id == "biomech.com.range_x"
    )
    assert biomech_biomarker.availability == "low_confidence"

    score = score_records[0]
    assert score.domain_scores["biomech"] == 99.9
    assert [item["feature_id"] for item in score.deductions] == [
        "spatial.range_of_motion.xy.left_knee",
        "biomech.com.range_x",
    ]
    biomech_deduction = score.deductions[1]
    assert biomech_deduction["availability"] == "low_confidence"
    assert biomech_deduction["availability_weight"] == 0.1
    assert biomech_deduction["depth_dependency"] == "high"
    assert biomech_deduction["depth_dependency_weight"] == 0.1
    assert biomech_deduction["confidence_weight"] == 0.01
    assert biomech_deduction["deduction"] == 0.1
    assert score.withheld_features == []


def test_low_confidence_biomech_can_be_withheld_by_zero_gravity(tmp_path: Path):
    baseline_path = tmp_path / "baseline.json"
    _write_baseline(baseline_path)
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.left_knee",
            exercise_id="squat",
            rep_id=1,
            value=100.0,
            unit="degree",
            source_fields=["feature_domains.spatial"],
            availability="assessed",
        )
    ]
    biomech_records = [
        BiomechRecord(
            metric_id="biomech.com.range_x",
            exercise_id="squat",
            rep_id=1,
            value=1.0,
            unit="torso_length_ratio",
            source_fields=["biomechanical_focus.expected_com_motion"],
        )
    ]

    _, score_records = derive_biomarkers(
        feat_records=feat_records,
        biomech_records=biomech_records,
        exercise_definition=exercise,
        definition_version=exercise.version,
        baseline_path=baseline_path,
        low_confidence_score_weights={"biomech": 0.0},
    )

    score = score_records[0]
    assert score.domain_scores["biomech"] == 100.0
    assert [item["feature_id"] for item in score.deductions] == [
        "spatial.range_of_motion.xy.left_knee"
    ]
    assert score.withheld_features == [
        {
            "domain": "biomech",
            "feature_id": "biomech.com.range_x",
            "value": 1.0,
            "availability": "low_confidence",
            "view_reliability": None,
            "camera_zone": None,
            "depth_dependency": "high",
            "model_depth_reliability": "low",
            "landmark_quality": "unknown",
            "focus_tier": "primary",
            "reasons": [
                "monocular_biomech_proxy_low_confidence",
                "model_depth_reliability_low",
                "availability_score_weight_zero",
            ],
        }
    ]
