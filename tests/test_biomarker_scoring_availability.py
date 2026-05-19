from __future__ import annotations

import json
from pathlib import Path

from movement.biomarker.scoring import derive_biomarkers
from movement.exercise_definition import load_exercise_definition
from movement.features import FeatureRecord

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFINITIONS_DIR = _PROJECT_ROOT / "data" / "definitions" / "exercises"


def _write_baseline(path: Path) -> None:
    baseline = {
        "squat": {
            "spatial.rom.left_knee": {"mean": 100.0, "std": 1.0},
            "spatial.symmetry.knee": {"mean": 0.0, "std": 0.1},
        }
    }
    path.write_text(json.dumps(baseline), encoding="utf-8")


def test_low_confidence_feature_is_passed_through_but_not_scored(tmp_path: Path):
    baseline_path = tmp_path / "baseline.json"
    _write_baseline(baseline_path)
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    feat_records = [
        FeatureRecord(
            feature_id="spatial.rom.left_knee",
            exercise_id="squat",
            rep_id=1,
            value=100.0,
            unit="degree",
            source_fields=["feature_domains.spatial"],
            availability="assessed",
            view_reliability="high",
        ),
        FeatureRecord(
            feature_id="spatial.symmetry.knee",
            exercise_id="squat",
            rep_id=1,
            value=1.0,
            unit="dimensionless_cv",
            source_fields=["feature_domains.spatial"],
            availability="low_confidence",
            view_reliability="low",
            availability_reasons=["view_metric_low"],
            camera_zone="Z3",
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
        if record.biomarker_id == "spatial.symmetry.knee"
    )
    assert withheld_biomarker.availability == "low_confidence"
    assert withheld_biomarker.view_reliability == "low"

    score = score_records[0]
    assert score.final_score == 100.0
    assert [item["feature_id"] for item in score.deductions] == [
        "spatial.rom.left_knee"
    ]
    assert score.withheld_features == [
        {
            "domain": "spatial",
            "feature_id": "spatial.symmetry.knee",
            "value": 1.0,
            "availability": "low_confidence",
            "view_reliability": "low",
            "camera_zone": "Z3",
            "reasons": ["view_metric_low"],
        }
    ]
