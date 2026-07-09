from pathlib import Path

import numpy as np
import pandas as pd

from movement.exercise_definition import (
    load_all_exercise_definitions,
    load_exercise_definition,
)
from movement.features import audit_analysis_disrupting_patterns
from movement.pipeline import PipelineConfig, run_pipeline


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFINITIONS_DIR = _PROJECT_ROOT / "data" / "definitions" / "exercises"
_TARGET_EXERCISES = {
    "squat",
    "lunge",
    "pike_pushup",
    "plank_shoulder_tap",
}


def _minimal_pose_df():
    return pd.DataFrame(
        {
            "frame": [0, 1, 2],
            "timestamp": np.arange(3) / 30.0,
            "use_for_analysis": True,
        }
    )


def _by_pattern(report):
    return {item["pattern"]: item for item in report.all_patterns}


def test_squat_analysis_disrupting_patterns_are_classified_by_detectability():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)

    report = audit_analysis_disrupting_patterns(exercise)
    by_pattern = _by_pattern(report)

    assert by_pattern["heel_lift"]["classification"] == (
        "pose_detectable_score_feature"
    )
    assert by_pattern["heel_lift"]["linked_compensation_patterns"] == ["heel_lift"]
    assert by_pattern["heel_lift"]["declared_linked_compensation_patterns"] == [
        "heel_lift"
    ]
    assert by_pattern["arm_swing"]["classification"] == "acquisition_control_factor"
    assert by_pattern["excessive_knee_deviation"]["linked_compensation_patterns"] == [
        "knee_valgus",
        "knee_varus",
    ]


def test_lunge_camera_side_change_remains_interpretation_limitation():
    exercise = load_exercise_definition("lunge", _DEFINITIONS_DIR)

    report = audit_analysis_disrupting_patterns(exercise)
    camera_side_change = _by_pattern(report)["camera_side_change"]

    assert camera_side_change["classification"] == "interpretation_limitation_factor"
    assert camera_side_change["annotation_fallback"] == (
        "recording_metadata.camera_zone or annotation.note"
    )
    assert camera_side_change in report.interpretation_limitation_factors


def test_all_current_target_analysis_disrupting_patterns_are_classified():
    definitions = load_all_exercise_definitions(_DEFINITIONS_DIR)

    for exercise_id in _TARGET_EXERCISES:
        report = audit_analysis_disrupting_patterns(definitions[exercise_id])
        assert report.all_patterns
        assert report.unknown_patterns == []


def test_pipeline_reports_analysis_disrupting_pattern_detectability_when_features_run():
    config = PipelineConfig()
    config.validation.enabled = False
    config.annotation.enabled = False
    config.exercise_definition.enabled = True
    config.exercise_definition.exercise_id = "plank_shoulder_tap"
    config.preprocessing.enabled = False
    config.normalization.enabled = False
    config.rep_segmentation.enabled = False
    config.phase_segmentation.enabled = False
    config.features.enabled = True
    config.biomech.enabled = False
    config.biomarker.enabled = False

    _, report = run_pipeline(_minimal_pose_df(), config)

    detectability = report["analysis_disrupting_pattern_detectability"]
    assert detectability["exercise_id"] == "plank_shoulder_tap"
    assert any(
        item["pattern"] == "side_order_error"
        and item["classification"] == "acquisition_control_factor"
        for item in detectability["acquisition_control_factors"]
    )
    assert any(
        item["pattern"] == "missed_shoulder_tap"
        and item["classification"] == "interpretation_limitation_factor"
        for item in detectability["interpretation_limitation_factors"]
    )
