from __future__ import annotations

import json
from pathlib import Path

import pytest

from movement.biomech import BiomechRecord
from movement.biomarker.scoring import (
    derive_biomarkers,
    normalize_domain_weights,
    normalize_score_bounds,
)
from movement.exercise_definition import load_exercise_definition
from movement.features import FeatureRecord
from movement.pipeline import load_pipeline_config


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFINITIONS_DIR = (
    _PROJECT_ROOT / "data" / "definitions" / "exercises"
)


def _write_baseline(path: Path) -> None:
    baseline = {
        "squat": {
            "spatial.rom.left_knee": {"mean": 100.0, "std": 1.0},
            "temporal.tempo.rep_1": {"mean": 100.0, "std": 1.0},
            "control.stability.hip_center_x_std": {"mean": 100.0, "std": 1.0},
            "biomech.com.range_x": {"mean": 100.0, "std": 1.0},
        }
    }
    path.write_text(json.dumps(baseline), encoding="utf-8")


def _records():
    feat_records = [
        FeatureRecord(
            feature_id="spatial.rom.left_knee",
            exercise_id="squat",
            rep_id=1,
            value=90.0,
            unit="degree",
            source_fields=["feature_domains.spatial"],
        ),
        FeatureRecord(
            feature_id="temporal.tempo.rep_1",
            exercise_id="squat",
            rep_id=1,
            value=80.0,
            unit="second",
            source_fields=["feature_domains.temporal"],
        ),
        FeatureRecord(
            feature_id="control.stability.hip_center_x_std",
            exercise_id="squat",
            rep_id=1,
            value=70.0,
            unit="torso_length_ratio",
            source_fields=["feature_domains.control"],
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
        "biomech": 96.0,
    }
    assert score.domain_weights == {
        "spatial": 0.25,
        "temporal": 0.25,
        "control": 0.25,
        "biomech": 0.25,
    }
    assert score.final_score == 97.5
    assert score.as_dict()["domain_weights"] == score.domain_weights
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
        "biomech": 9.6,
    }
    assert score.final_score == 9.75


def test_negative_domain_weight_raises():
    with pytest.raises(ValueError, match="must be >= 0"):
        normalize_domain_weights({"control": -1.0})


def test_invalid_score_bounds_raise():
    with pytest.raises(ValueError, match="greater than lower bound"):
        normalize_score_bounds({"min": 10.0, "max": 10.0})

    with pytest.raises(ValueError, match="lower bound must be >= 0"):
        normalize_score_bounds({"min": -1.0, "max": 100.0})
