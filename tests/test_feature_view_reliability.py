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
            feature_id="spatial.role_alignment.left_right.range_of_motion_xy.knee",
            exercise_id="squat",
            rep_id=1,
            value=0.4,
            unit="dimensionless_cv",
            source_fields=["angle_definitions", "feature_domains.spatial"],
        ),
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.left_knee_angle",
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
    assert rom.depth_dependency == "none"


def test_z8_squat_withholds_high_depth_dependency_symmetry_for_mediapipe():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z8", "Z8"]})
    records = [
        FeatureRecord(
            feature_id="spatial.role_alignment.left_right.range_of_motion_xy.knee",
            exercise_id="squat",
            rep_id=1,
            value=0.25,
            unit="dimensionless_cv",
            source_fields=["angle_definitions", "feature_domains.spatial"],
        ),
        FeatureRecord(
            feature_id="spatial.range_of_motion.xyz.left_knee_angle",
            exercise_id="squat",
            rep_id=1,
            value=95.0,
            unit="degree",
            source_fields=["angle_definitions", "feature_domains.spatial"],
        ),
        FeatureRecord(
            feature_id="temporal.tempo.rep_duration",
            exercise_id="squat",
            rep_id=1,
            value=2.1,
            unit="second",
            source_fields=["feature_domains.temporal"],
        ),
        FeatureRecord(
            feature_id="control.compensation.knee_valgus.xy.left",
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
    assert valgus.depth_dependency == "none"
    assert valgus.availability == "assessed"


def test_control_self_reference_features_are_diagnostic_not_assessed():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z3"]})
    records = [
        FeatureRecord(
            feature_id="control.stability.hip_center_x_std",
            exercise_id="squat",
            rep_id=1,
            value=0.0,
            unit="torso_length_ratio",
            source_fields=["feature_domains.control.stability"],
        ),
        FeatureRecord(
            feature_id="control.compensation.lateral_pelvic_shift.xy",
            exercise_id="squat",
            rep_id=1,
            value=0.0,
            unit="torso_length_ratio",
            source_fields=["compensation_candidates.lateral_pelvic_shift"],
        ),
    ]

    annotated = annotate_feature_availability(records, df, exercise)

    for record in annotated:
        assert record.availability == "not_assessed"
        assert record.focus_tier == "diagnostic"
        assert "coordinate_reference_self_measurement" in record.availability_reasons


def test_heel_lift_uses_recording_view_support_metadata():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z3"]})
    records = [
        FeatureRecord(
            feature_id="control.compensation.heel_lift.xy.left",
            exercise_id="squat",
            rep_id=1,
            value=0.02,
            unit="torso_length_ratio",
            source_fields=["left_heel"],
        )
    ]

    annotated = annotate_feature_availability(records, df, exercise)

    heel_lift = annotated[0]
    assert heel_lift.availability == "assessed"
    assert heel_lift.depth_dependency == "none"
    assert heel_lift.landmark_ids == ["left_heel"]
    assert heel_lift.support_role == "support_consistency"
    assert heel_lift.coordinate_reference == "norm_recording_view_xy"
    assert heel_lift.evaluation_domain == "recording_view_only"
    assert heel_lift.evidence_axes == "y"


def test_trunk_flexion_xy_and_xyz_keep_separate_control_metadata():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z3"]})
    records = [
        FeatureRecord(
            feature_id="control.compensation.excessive_trunk_flexion.xy",
            exercise_id="squat",
            rep_id=1,
            value=25.0,
            unit="degree",
            source_fields=["left_shoulder", "right_shoulder", "left_hip", "right_hip"],
        ),
        FeatureRecord(
            feature_id="control.compensation.excessive_trunk_flexion.xyz",
            exercise_id="squat",
            rep_id=1,
            value=45.0,
            unit="degree",
            source_fields=["left_shoulder", "right_shoulder", "left_hip", "right_hip"],
        ),
    ]

    trunk_xy, trunk_xyz = annotate_feature_availability(records, df, exercise)

    assert trunk_xy.depth_dependency == "none"
    assert trunk_xy.coordinate_reference == "norm_recording_view_xy"
    assert trunk_xy.evaluation_domain == "recording_view_only"
    assert trunk_xy.evidence_axes == "xy"

    assert trunk_xyz.depth_dependency == "moderate"
    assert trunk_xyz.coordinate_reference == "norm_model_depth"
    assert trunk_xyz.evaluation_domain == "dual_domain_compare"
    assert trunk_xyz.evidence_axes == "xyz"


def test_z8_high_depth_dependency_feature_can_be_assessed_with_stronger_depth_model():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z8"]})
    df.attrs["pose_estimator_reliability"] = {"model_depth_reliability": "high"}
    records = [
        FeatureRecord(
            feature_id="spatial.role_alignment.left_right.range_of_motion_xy.knee",
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


def test_support_consistency_role_alignment_uses_recording_view_support_reliability():
    exercise = load_exercise_definition("squat", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z3", "Z3"]})
    records = [
        FeatureRecord(
            feature_id=(
                "spatial.role_alignment.left_right.support_consistency_xy_drift.left_ankle_right_ankle"
            ),
            exercise_id="squat",
            rep_id=1,
            value=0.1,
            unit="dimensionless_cv",
            source_fields=[
                "support",
                "feature_domains.spatial",
                "support_consistency.recording_view_xy",
            ],
            depth_dependency="none",
        )
    ]

    annotated = annotate_feature_availability(records, df, exercise)

    assert annotated[0].view_reliability == "high"
    assert annotated[0].availability == "assessed"
    assert annotated[0].depth_dependency == "none"
    assert (
        "view_metric_reliability.zones.Z3.centerline_stability"
        in annotated[0].source_fields
    )


def test_lunge_side_view_preserves_role_sagittal_metric_and_flags_frontal_metric():
    exercise = load_exercise_definition("lunge", _DEFINITIONS_DIR)
    df = pd.DataFrame({"camera_zone": ["Z3"]})
    records = [
        FeatureRecord(
            feature_id="spatial.range_of_motion.xy.left_knee_angle",
            exercise_id="lunge",
            rep_id=1,
            value=80.0,
            unit="degree",
            source_fields=["angle_definitions", "feature_domains.spatial"],
        ),
        FeatureRecord(
            feature_id="control.compensation.knee_valgus.xy.left",
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
        feature_id="spatial.role_alignment.left_right.range_of_motion_xy.knee",
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
        landmark_ids=["left_knee", "right_knee"],
        support_role="moving_landmark",
        coordinate_reference="norm_model_depth",
        evaluation_domain="dual_domain_compare",
        evidence_axes="xyz",
        feature_family="role_alignment",
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
    assert df.loc[0, "landmark_ids"] == ["left_knee", "right_knee"]
    assert df.loc[0, "support_role"] == "moving_landmark"
    assert df.loc[0, "coordinate_reference"] == "norm_model_depth"
    assert df.loc[0, "evaluation_domain"] == "dual_domain_compare"
    assert df.loc[0, "evidence_axes"] == "xyz"
    assert df.loc[0, "feature_family"] == "role_alignment"
