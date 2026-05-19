from __future__ import annotations

from pathlib import Path

import pandas as pd

from movement.exercise_definition import load_exercise_definition
from movement.features import (
    FeatureRecord,
    annotate_feature_availability,
    features_to_dataframe,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFINITIONS_DIR = _PROJECT_ROOT / "data" / "definitions" / "exercises"


def test_side_view_squat_marks_symmetry_low_confidence():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z3", "Z3"]})
    records = [
        FeatureRecord(
            feature_id="spatial.symmetry.knee",
            exercise_id="squat",
            rep_id=1,
            value=0.4,
            unit="dimensionless_cv",
            source_fields=["angle_definitions", "feature_domains.spatial"],
        ),
        FeatureRecord(
            feature_id="spatial.rom.left_knee_angle",
            exercise_id="squat",
            rep_id=1,
            value=95.0,
            unit="degree",
            source_fields=["angle_definitions", "feature_domains.spatial"],
        ),
    ]

    annotated = annotate_feature_availability(records, df, exercise)

    symmetry = annotated[0]
    assert symmetry.view_reliability == "low"
    assert symmetry.availability == "low_confidence"
    assert symmetry.camera_zone == "Z3"
    assert "view_metric_low" in symmetry.availability_reasons

    rom = annotated[1]
    assert rom.view_reliability == "high"
    assert rom.availability == "assessed"


def test_lunge_side_view_preserves_role_sagittal_metric_and_flags_frontal_metric():
    exercise = load_exercise_definition("lunge", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z3"]})
    records = [
        FeatureRecord(
            feature_id="spatial.rom.left_knee_angle",
            exercise_id="lunge",
            rep_id=1,
            value=80.0,
            unit="degree",
            source_fields=["angle_definitions", "feature_domains.spatial"],
        ),
        FeatureRecord(
            feature_id="control.compensation.knee_valgus.left",
            exercise_id="lunge",
            rep_id=1,
            value=0.08,
            unit="torso_length_ratio",
            source_fields=["compensation_candidates.knee_valgus"],
        ),
    ]

    annotated = annotate_feature_availability(records, df, exercise)

    assert annotated[0].view_reliability == "high"
    assert annotated[0].availability == "assessed"
    assert annotated[1].view_reliability == "low"
    assert annotated[1].availability == "low_confidence"


def test_features_to_dataframe_preserves_availability_metadata():
    record = FeatureRecord(
        feature_id="spatial.symmetry.knee",
        exercise_id="squat",
        rep_id=1,
        value=0.2,
        unit="dimensionless_cv",
        source_fields=["feature_domains.spatial"],
        view_reliability="low",
        availability="low_confidence",
        availability_reasons=["view_metric_low"],
        camera_zone="Z3",
        role_context={"near_side": "left"},
    )

    df = features_to_dataframe([record])

    assert df.loc[0, "view_reliability"] == "low"
    assert df.loc[0, "availability"] == "low_confidence"
    assert df.loc[0, "availability_reasons"] == "view_metric_low"
    assert df.loc[0, "camera_zone"] == "Z3"
    assert df.loc[0, "role_context"] == {"near_side": "left"}
