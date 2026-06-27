from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from movement.exercise_definition import load_exercise_definition
from movement.features import (
    FeatureContext,
    FeatureRecord,
    apply_feature_context,
    extract_rep_features,
    resolve_feature_context,
)


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFINITIONS_DIR = _PROJECT_ROOT / "data" / "definitions" / "exercises"


def test_bilateral_squat_resolves_symmetry_context_without_active_side():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    df = pd.DataFrame({"segment_type": ["rep"], "rep_id": [1]})

    context = resolve_feature_context(df, exercise)

    assert isinstance(context, FeatureContext)
    assert context.laterality == "bilateral_symmetric"
    assert context.role_mode == "bilateral_symmetry"
    assert context.role_context == {"symmetry_context": "bilateral_symmetric"}
    assert context.attribution_confidence == "not_assessed"
    assert "active_side_attribution_not_applicable" in context.context_reasons
    assert "classification.laterality" in context.source_fields


def test_lunge_resolves_active_side_context_when_attribution_report_is_present():
    exercise = load_exercise_definition("lunge", _DEFINITIONS_DIR)
    df = pd.DataFrame(
        {
            "segment_type": ["rep"],
            "rep_id": [1],
            "detected_active_limb": ["right"],
            "expected_active_limb": ["right"],
            "attribution_consistent": [True],
            "attribution_confidence": [0.95],
        }
    )

    context = resolve_feature_context(
        df,
        exercise,
        attribution_report={"skipped": False, "mode": "conservative"},
    )

    assert context.laterality == "alternating"
    assert context.role_mode == "active_side"
    assert context.role_context == {"side_role": "active_side"}
    assert context.attribution_confidence == "assessed"
    assert "motion_attribution_context_available" in context.context_reasons
    assert "performance_protocol.side_sequence" in context.source_fields
    assert "motion_attribution" in context.source_fields


def test_lunge_without_attribution_context_is_low_confidence():
    exercise = load_exercise_definition("lunge", _DEFINITIONS_DIR)
    df = pd.DataFrame({"segment_type": ["rep"], "rep_id": [1]})

    context = resolve_feature_context(df, exercise)

    assert context.role_mode == "active_side"
    assert context.attribution_confidence == "low_confidence"
    assert "motion_attribution_context_missing" in context.context_reasons


def test_apply_feature_context_attaches_bilateral_context_without_value_change():
    context = FeatureContext(
        laterality="bilateral_symmetric",
        role_mode="bilateral_symmetry",
        role_context={"symmetry_context": "bilateral_symmetric"},
        source_fields=["classification.laterality"],
    )
    record = FeatureRecord(
        feature_id="spatial.symmetry.knee",
        exercise_id="squat",
        rep_id=1,
        value=0.25,
        unit="dimensionless_cv",
        source_fields=["angle_definitions", "feature_domains.spatial"],
        availability="low_confidence",
        availability_reasons=["model_depth_reliability_low"],
    )

    [updated] = apply_feature_context([record], context)

    assert updated.value == 0.25
    assert updated.availability == "low_confidence"
    assert updated.role_context == {"symmetry_context": "bilateral_symmetric"}
    assert "classification.laterality" in updated.source_fields
    assert "feature_context.role_mode" in updated.source_fields
    assert "feature_context.role_context" in updated.source_fields


def test_extract_rep_features_attaches_context_to_symmetry_records():
    exercise = SimpleNamespace(
        exercise_id="bilateral_fixture",
        classification={"laterality": "bilateral_symmetric"},
        angle_definitions={
            "left_knee_angle": {
                "proximal": "left_hip",
                "vertex": "left_knee",
                "distal": "left_ankle",
            },
            "right_knee_angle": {
                "proximal": "right_hip",
                "vertex": "right_knee",
                "distal": "right_ankle",
            },
        },
        landmarks=SimpleNamespace(primary_joints=[]),
        compensation_candidates=[],
    )
    df = pd.DataFrame(
        {
            "left_hip_norm_x": [0.0, 0.0],
            "left_hip_norm_y": [1.0, 1.0],
            "left_hip_norm_z": [0.0, 0.0],
            "left_knee_norm_x": [0.0, 0.0],
            "left_knee_norm_y": [0.0, 0.0],
            "left_knee_norm_z": [0.0, 0.0],
            "left_ankle_norm_x": [1.0, 1.0],
            "left_ankle_norm_y": [0.0, 0.0],
            "left_ankle_norm_z": [0.0, 0.0],
            "right_hip_norm_x": [0.2, 0.2],
            "right_hip_norm_y": [1.0, 1.0],
            "right_hip_norm_z": [0.0, 0.0],
            "right_knee_norm_x": [0.2, 0.2],
            "right_knee_norm_y": [0.0, 0.0],
            "right_knee_norm_z": [0.0, 0.0],
            "right_ankle_norm_x": [1.2, 1.2],
            "right_ankle_norm_y": [0.0, 0.0],
            "right_ankle_norm_z": [0.0, 0.0],
        }
    )

    records = extract_rep_features(df, exercise)
    symmetry_records = [
        record
        for record in records
        if record.feature_id.startswith("spatial.symmetry.")
    ]

    assert symmetry_records
    for record in symmetry_records:
        assert record.role_context == {"symmetry_context": "bilateral_symmetric"}
        assert "classification.laterality" in record.source_fields
        assert "feature_context.role_context" in record.source_fields
