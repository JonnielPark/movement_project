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
    assert symmetry.depth_dependency == "high"
    assert symmetry.model_depth_reliability == "low"

    rom = annotated[1]
    assert rom.view_reliability == "high"
    assert rom.availability == "assessed"
    assert rom.depth_dependency == "moderate"


def test_z8_squat_withholds_high_depth_dependency_symmetry_for_mediapipe():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z8", "Z8"]})
    records = [
        FeatureRecord(
            feature_id="spatial.symmetry.knee",
            exercise_id="squat",
            rep_id=1,
            value=0.25,
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
        FeatureRecord(
            feature_id="temporal.tempo.rep_1",
            exercise_id="squat",
            rep_id=1,
            value=2.1,
            unit="second",
            source_fields=["feature_domains.temporal"],
        ),
        FeatureRecord(
            feature_id="control.compensation.knee_valgus.left",
            exercise_id="squat",
            rep_id=1,
            value=0.04,
            unit="torso_length_ratio",
            source_fields=["compensation_candidates.knee_valgus"],
        ),
    ]

    annotated = annotate_feature_availability(records, df, exercise)

    symmetry, rom, tempo, valgus = annotated
    assert symmetry.view_reliability == "moderate"
    assert symmetry.depth_dependency == "high"
    assert symmetry.model_depth_reliability == "low"
    assert symmetry.availability == "low_confidence"
    assert "model_depth_reliability_low" in symmetry.availability_reasons

    assert rom.view_reliability == "moderate"
    assert rom.depth_dependency == "moderate"
    assert rom.availability == "assessed"

    assert tempo.view_reliability == "high"
    assert tempo.depth_dependency == "none"
    assert tempo.availability == "assessed"

    assert valgus.view_reliability == "high"
    assert valgus.depth_dependency == "low"
    assert valgus.availability == "assessed"


def test_z8_high_depth_dependency_feature_can_be_assessed_with_stronger_depth_model():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z8"]})
    df.attrs["pose_estimator_reliability"] = {"model_depth_reliability": "high"}
    records = [
        FeatureRecord(
            feature_id="spatial.symmetry.knee",
            exercise_id="squat",
            rep_id=1,
            value=0.25,
            unit="dimensionless_cv",
            source_fields=["angle_definitions", "feature_domains.spatial"],
        )
    ]

    annotated = annotate_feature_availability(records, df, exercise)

    assert annotated[0].view_reliability == "moderate"
    assert annotated[0].depth_dependency == "high"
    assert annotated[0].model_depth_reliability == "high"
    assert annotated[0].availability == "assessed"
    assert "model_depth_reliability_low" not in annotated[0].availability_reasons


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
        depth_dependency="high",
        model_depth_reliability="low",
        landmark_quality="low",
    )

    df = features_to_dataframe([record])

    assert df.loc[0, "view_reliability"] == "low"
    assert df.loc[0, "availability"] == "low_confidence"
    assert df.loc[0, "availability_reasons"] == "view_metric_low"
    assert df.loc[0, "camera_zone"] == "Z3"
    assert df.loc[0, "role_context"] == {"near_side": "left"}
    assert df.loc[0, "depth_dependency"] == "high"
    assert df.loc[0, "model_depth_reliability"] == "low"
    assert df.loc[0, "landmark_quality"] == "low"
