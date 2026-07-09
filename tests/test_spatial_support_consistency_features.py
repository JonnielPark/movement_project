from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from movement.features import annotate_feature_availability
from movement.features.spatial import (
    compute_range_of_motion,
    compute_movement_path,
    compute_support_consistency,
)


def test_compute_range_of_motion_emits_xy_and_xyz_variants_with_angle_triplet_provenance():
    exercise = SimpleNamespace(
        exercise_id="example_knee_rom",
        classification={"primary_plane": "sagittal"},
        angle_definitions={
            "left_knee_angle": {
                "proximal": "left_hip",
                "vertex": "left_knee",
                "distal": "left_ankle",
            }
        },
        landmarks=SimpleNamespace(model="mediapipe_pose_33"),
    )
    df = pd.DataFrame(
        {
            "left_hip_norm_x": [0.0, 0.0],
            "left_hip_norm_y": [1.0, 1.0],
            "left_hip_norm_z": [0.0, 0.0],
            "left_knee_norm_x": [0.0, 0.0],
            "left_knee_norm_y": [0.0, 0.0],
            "left_knee_norm_z": [0.0, 0.0],
            "left_ankle_norm_x": [1.0, 0.0],
            "left_ankle_norm_y": [0.0, -1.0],
            "left_ankle_norm_z": [0.0, 1.0],
        }
    )

    records = annotate_feature_availability(
        compute_range_of_motion(df, exercise, rep_id=1), df, exercise
    )
    by_id = {record.feature_id: record for record in records}

    xy = by_id["spatial.range_of_motion.xy.left_knee_angle"]
    xyz = by_id["spatial.range_of_motion.xyz.left_knee_angle"]
    assert xy.value == pytest.approx(90.0)
    assert xyz.value == pytest.approx(45.0)
    assert xy.landmark_ids == ["left_hip", "left_knee", "left_ankle"]
    assert xyz.landmark_ids == ["left_hip", "left_knee", "left_ankle"]
    assert "angle_definitions.left_knee_angle.vertex" in xy.source_fields
    assert xy.depth_dependency == "none"
    assert xy.evidence_axes == "xy"
    assert xy.evaluation_domain == "recording_view_only"
    assert xy.feature_family == "range_of_motion"
    assert xyz.depth_dependency == "moderate"
    assert xyz.evidence_axes == "xyz"
    assert xyz.evaluation_domain == "dual_domain_compare"
    assert xyz.feature_family == "range_of_motion"


def test_compute_movement_path_emits_closed_chain_support_consistency_axis_diagnostics():
    exercise = SimpleNamespace(
        exercise_id="example_closed_chain",
        classification={"kinetic_chain": "closed_chain"},
        support_context={
            "base_of_support": "bilateral_feet",
            "contact_points": ["left_foot"],
            "weight_bearing_regions": ["left_foot"],
        },
        landmarks=SimpleNamespace(primary_joints=["left_ankle"]),
    )
    df = pd.DataFrame(
        {
            "left_ankle_norm_x": [0.0, 1.0, 1.0],
            "left_ankle_norm_y": [0.0, 0.0, 2.0],
            "left_ankle_norm_z": [0.0, 0.0, 3.0],
        }
    )

    records = compute_movement_path(df, exercise, rep_id=1)
    by_id = {record.feature_id: record for record in records}

    assert by_id["spatial.movement_path.arc_length_xy.left_ankle"].value == 3.0
    assert by_id["spatial.movement_path.arc_length_xy.left_ankle"].note is not None
    assert by_id[
        "spatial.movement_path.arc_length_xyz.left_ankle"
    ].value == pytest.approx(4.6056)
    assert by_id["spatial.movement_path.arc_length_xyz.left_ankle"].note is not None
    assert by_id["spatial.support_consistency.axis_path_x.left_ankle"].value == 1.0
    assert by_id["spatial.support_consistency.axis_path_y.left_ankle"].value == 2.0
    assert by_id["spatial.support_consistency.axis_path_z.left_ankle"].value == 3.0
    assert by_id["spatial.support_consistency.axis_path_xy.left_ankle"].value == 3.0
    assert (
        by_id["spatial.support_consistency.axis_path_z.left_ankle"].availability
        == "not_assessed"
    )
    assert (
        by_id["spatial.support_consistency.axis_path_z.left_ankle"].depth_dependency
        == "high"
    )


def test_compute_movement_path_can_skip_support_consistency_axis_diagnostics():
    exercise = SimpleNamespace(
        exercise_id="example_closed_chain",
        classification={"kinetic_chain": "closed_chain"},
        support_context={"contact_points": ["left_foot"]},
        landmarks=SimpleNamespace(primary_joints=["left_ankle"]),
    )
    df = pd.DataFrame(
        {
            "left_ankle_norm_x": [0.0, 1.0],
            "left_ankle_norm_y": [0.0, 0.0],
            "left_ankle_norm_z": [0.0, 0.0],
        }
    )

    records = compute_movement_path(
        df,
        exercise,
        rep_id=1,
        include_support_consistency_axis_diagnostics=False,
        include_axis_diagnostics=False,
    )

    assert [record.feature_id for record in records] == [
        "spatial.movement_path.arc_length_xy.left_ankle",
        "spatial.movement_path.arc_length_xyz.left_ankle",
    ]


def test_compute_movement_path_emits_non_support_trajectory_axis_diagnostics():
    exercise = SimpleNamespace(
        exercise_id="example_closed_chain",
        classification={"kinetic_chain": "closed_chain"},
        support_context={"contact_points": ["left_foot"]},
        landmarks=SimpleNamespace(primary_joints=["left_knee"]),
    )
    df = pd.DataFrame(
        {
            "left_knee_norm_x": [0.0, 1.0, 1.0],
            "left_knee_norm_y": [0.0, 0.0, 2.0],
            "left_knee_norm_z": [0.0, 0.0, 3.0],
        }
    )

    records = compute_movement_path(df, exercise, rep_id=1)
    by_id = {record.feature_id: record for record in records}

    assert by_id["spatial.movement_path.arc_length_xy.left_knee"].value == 3.0
    assert by_id[
        "spatial.movement_path.arc_length_xyz.left_knee"
    ].value == pytest.approx(4.6056)
    assert by_id["spatial.movement_path.axis_path_x.left_knee"].value == 1.0
    assert by_id["spatial.movement_path.axis_path_y.left_knee"].value == 2.0
    assert by_id["spatial.movement_path.axis_path_z.left_knee"].value == 3.0
    assert (
        by_id["spatial.movement_path.arc_length_xy.left_knee"].availability
        == "assessed"
    )
    assert (
        by_id["spatial.movement_path.arc_length_xy.left_knee"].depth_dependency
        == "none"
    )
    assert (
        by_id["spatial.movement_path.arc_length_xyz.left_knee"].availability
        == "assessed"
    )
    assert (
        by_id["spatial.movement_path.arc_length_xyz.left_knee"].depth_dependency
        == "high"
    )
    assert (
        by_id["spatial.movement_path.axis_path_z.left_knee"].depth_dependency == "high"
    )


def test_compute_movement_path_accepts_xy_only_without_depth_records():
    exercise = SimpleNamespace(
        exercise_id="example_xy_only",
        classification={"kinetic_chain": "open_chain"},
        support_context={},
        landmarks=SimpleNamespace(primary_joints=["left_knee"]),
    )
    df = pd.DataFrame(
        {
            "left_knee_norm_x": [0.0, 1.0, 1.0],
            "left_knee_norm_y": [0.0, 0.0, 2.0],
        }
    )

    records = compute_movement_path(df, exercise, rep_id=1)
    by_id = {record.feature_id: record for record in records}

    assert by_id["spatial.movement_path.arc_length_xy.left_knee"].value == 3.0
    assert by_id["spatial.movement_path.arc_length_xy.left_knee"].depth_dependency == (
        "none"
    )
    assert "spatial.movement_path.axis_path_x.left_knee" in by_id
    assert "spatial.movement_path.axis_path_y.left_knee" in by_id
    assert "spatial.movement_path.arc_length_xyz.left_knee" not in by_id
    assert "spatial.movement_path.axis_path_z.left_knee" not in by_id


def test_compute_movement_path_emits_xy_and_xyz_trajectory_variants():
    exercise = SimpleNamespace(
        exercise_id="example_knee_focus",
        classification={"kinetic_chain": "closed_chain"},
        support_context={"contact_points": ["left_foot"]},
        biomechanical_focus=SimpleNamespace(main_load_regions=["knee"]),
        joint_actions={"primary": ["knee_flexion_extension"], "secondary": []},
        landmarks=SimpleNamespace(primary_joints=["left_knee"]),
    )
    df = pd.DataFrame(
        {
            "left_knee_norm_x": [0.0, 1.0, 1.0],
            "left_knee_norm_y": [0.0, 0.0, 2.0],
            "left_knee_norm_z": [0.0, 0.0, 3.0],
        }
    )

    records = compute_movement_path(df, exercise, rep_id=1)
    by_id = {record.feature_id: record for record in records}
    xy_record = by_id["spatial.movement_path.arc_length_xy.left_knee"]
    xyz_record = by_id["spatial.movement_path.arc_length_xyz.left_knee"]
    z_record = by_id["spatial.movement_path.axis_path_z.left_knee"]

    assert xy_record.value == 3.0
    assert xy_record.availability == "assessed"
    assert xy_record.availability_reasons == []
    assert xy_record.depth_dependency == "none"
    assert "spatial.movement_path.recording_view_xy_scoring" in xy_record.source_fields
    assert xyz_record.value == pytest.approx(4.6056)
    assert xyz_record.availability == "assessed"
    assert xyz_record.depth_dependency == "high"
    assert "spatial.movement_path.depth_sensitive_xyz" in xyz_record.source_fields
    assert z_record.availability == "not_assessed"
    assert z_record.depth_dependency == "high"


def test_promoted_knee_xy_trajectory_keeps_primary_focus_after_availability_annotation():
    exercise = SimpleNamespace(
        exercise_id="example_knee_focus",
        classification={"kinetic_chain": "closed_chain"},
        support_context={"contact_points": ["left_foot"]},
        biomechanical_focus=SimpleNamespace(main_load_regions=["knee"]),
        joint_actions={"primary": ["knee_flexion_extension"], "secondary": []},
        landmarks=SimpleNamespace(primary_joints=["left_knee"]),
    )
    df = pd.DataFrame(
        {
            "left_knee_norm_x": [0.0, 1.0, 1.0],
            "left_knee_norm_y": [0.0, 0.0, 2.0],
            "left_knee_norm_z": [0.0, 0.0, 3.0],
        }
    )

    records = annotate_feature_availability(
        compute_movement_path(df, exercise, rep_id=1), df, exercise
    )
    by_id = {record.feature_id: record for record in records}

    assert (
        by_id["spatial.movement_path.arc_length_xy.left_knee"].focus_tier == "primary"
    )
    assert by_id["spatial.movement_path.arc_length_xy.left_knee"].landmark_ids == [
        "left_knee"
    ]
    assert (
        by_id["spatial.movement_path.arc_length_xy.left_knee"].support_role
        == "moving_landmark"
    )
    assert (
        by_id["spatial.movement_path.arc_length_xy.left_knee"].coordinate_reference
        == "norm_recording_view_xy"
    )
    assert (
        by_id["spatial.movement_path.arc_length_xy.left_knee"].evaluation_domain
        == "recording_view_only"
    )
    assert by_id["spatial.movement_path.arc_length_xy.left_knee"].evidence_axes == "xy"
    assert by_id["spatial.movement_path.arc_length_xy.left_knee"].feature_family == (
        "movement_path"
    )
    assert (
        by_id["spatial.movement_path.arc_length_xyz.left_knee"].focus_tier == "primary"
    )
    assert (
        by_id["spatial.movement_path.arc_length_xyz.left_knee"].evidence_axes == "xyz"
    )
    assert by_id[
        "spatial.movement_path.arc_length_xyz.left_knee"
    ].evaluation_domain == ("dual_domain_compare")
    assert (
        by_id["spatial.movement_path.axis_path_x.left_knee"].focus_tier == "diagnostic"
    )
    assert (
        by_id["spatial.movement_path.axis_path_z.left_knee"].focus_tier == "diagnostic"
    )
    assert by_id["spatial.movement_path.axis_path_z.left_knee"].evidence_axes == "z"
    assert by_id["spatial.movement_path.axis_path_z.left_knee"].evaluation_domain == (
        "dual_domain_compare"
    )


def test_compute_support_consistency_emits_recording_view_consistency_features():
    exercise = SimpleNamespace(
        exercise_id="example_closed_chain",
        classification={"kinetic_chain": "closed_chain"},
        support_context={
            "base_of_support": "bilateral_feet",
            "contact_points": ["left_foot", "right_foot"],
            "weight_bearing_regions": ["left_foot", "right_foot"],
        },
        landmarks=SimpleNamespace(primary_joints=["left_ankle", "right_ankle"]),
    )
    df = pd.DataFrame(
        {
            "left_ankle_norm_x": [0.0, 0.1, -0.1],
            "left_ankle_norm_y": [0.0, 0.0, 0.0],
            "left_ankle_norm_z": [0.0, 5.0, -5.0],
            "right_ankle_norm_x": [1.0, 1.1, 0.9],
            "right_ankle_norm_y": [0.0, 0.0, 0.0],
            "right_ankle_norm_z": [0.0, -5.0, 5.0],
        }
    )

    records = compute_support_consistency(df, exercise, rep_id=1)
    by_id = {record.feature_id: record for record in records}

    assert by_id[
        "spatial.support_consistency.point_drift_xy.left_ankle"
    ].value == pytest.approx(0.1)
    assert by_id[
        "spatial.support_consistency.point_drift_xy.right_ankle"
    ].value == pytest.approx(0.1)
    assert by_id["spatial.support_consistency.width_variation_xy"].value == 0.0
    assert by_id["spatial.support_consistency.center_drift_xy"].value == 0.1
    assert (
        by_id[
            "spatial.role_alignment.left_right.support_consistency_xy_drift.left_ankle_right_ankle"
        ].value
        == 0.0
    )
    assert all(record.depth_dependency == "none" for record in records)

    annotated = annotate_feature_availability(records, df, exercise)
    contact = {record.feature_id: record for record in annotated}[
        "spatial.support_consistency.point_drift_xy.left_ankle"
    ]
    assert contact.landmark_ids == ["left_ankle"]
    assert contact.support_role == "support_consistency"
    assert contact.coordinate_reference == "norm_recording_view_xy"
    assert contact.evaluation_domain == "recording_view_only"
    assert contact.evidence_axes == "xy"
    assert contact.feature_family == "support_consistency"
