from __future__ import annotations

from movement.record_metadata import (
    classify_feature_family,
    infer_common_record_metadata,
    load_joint_profiles,
    load_landmark_metadata,
    resolve_landmark_metadata,
)


def test_landmark_metadata_registry_exposes_stable_joint_fields():
    metadata = load_landmark_metadata()

    left_knee = metadata["left_knee"]
    assert left_knee["body_region"] == "knee"
    assert left_knee["side"] == "left"
    assert left_knee["paired_with"] == "right_knee"
    assert left_knee["proximal_landmarks"] == ["left_hip"]
    assert left_knee["distal_landmarks"] == ["left_ankle"]
    assert left_knee["default_joint_actions"] == ["knee.flexion_extension"]
    assert left_knee["joint_profile"] == "knee"
    assert left_knee["support_capable"] is False

    left_ankle = metadata["left_ankle"]
    assert left_ankle["body_region"] == "ankle"
    assert left_ankle["proximal_landmarks"] == ["left_knee"]
    assert left_ankle["distal_landmarks"] == ["left_heel", "left_foot_index"]
    assert left_ankle["default_joint_actions"] == ["ankle.dorsiflexion_plantarflexion"]
    assert left_ankle["joint_profile"] == "ankle"
    assert left_ankle["support_capable"] is True
    assert left_ankle["default_depth_sensitivity"] == "high"

    left_hip = metadata["left_hip"]
    assert left_hip["default_joint_actions"] == ["hip.flexion_extension"]
    assert left_hip["joint_profile"] == "hip"

    left_shoulder = metadata["left_shoulder"]
    assert left_shoulder["default_joint_actions"] == ["shoulder.flexion_extension"]
    assert left_shoulder["joint_profile"] == "shoulder"

    deprecated_fields = {
        "weight_bearing_capable",
        "pose_role",
        "proximal_landmark",
        "distal_landmark",
        "depth_sensitivity",
    }
    for row in metadata.values():
        assert deprecated_fields.isdisjoint(row)


def test_joint_profiles_keep_local_action_names_private_to_profile():
    profiles = load_joint_profiles()

    ankle = profiles["ankle"]
    assert ankle["joint_model"] == "primary_axis_flexion_extension"
    assert ankle["anatomical_actions"]["primary"] == ["dorsiflexion_plantarflexion"]
    assert "foot_heading_proxy" in ankle["anatomical_actions"]["secondary"]
    assert "foot_progression_proxy" not in ankle["anatomical_actions"]["secondary"]
    assert all(
        not action.startswith("ankle_")
        for actions in ankle["anatomical_actions"].values()
        for action in actions
    )

    hip = profiles["hip"]
    assert hip["joint_model"] == "primary_axis_flexion_extension"
    assert hip["anatomical_actions"]["primary"] == ["flexion_extension"]
    assert hip["anatomical_actions"]["secondary"] == []
    assert "abduction_adduction" not in hip["anatomical_actions"]["secondary"]
    assert "rotation_proxy" not in hip["anatomical_actions"]["secondary"]
    assert hip["feature_templates"]["range_of_motion"] == [
        "spatial.range_of_motion.xy.{side}_hip_angle",
        "spatial.range_of_motion.xyz.{side}_hip_angle",
    ]
    assert hip["feature_templates"]["role_alignment"] == [
        "spatial.role_alignment.left_right.range_of_motion_xy.hip"
    ]

    knee = profiles["knee"]
    assert knee["anatomical_actions"]["primary"] == ["flexion_extension"]
    assert knee["anatomical_actions"]["secondary"] == ["varus_valgus_proxy"]
    assert "rotation_proxy" not in knee["anatomical_actions"]["secondary"]
    assert knee["typical_motion_planes"]["secondary"] == ["frontal"]
    assert knee["feature_templates"]["range_of_motion"] == [
        "spatial.range_of_motion.xy.{side}_knee_angle",
        "spatial.range_of_motion.xyz.{side}_knee_angle",
    ]
    assert knee["feature_templates"]["movement_path"] == [
        "spatial.movement_path.arc_length_xy.{side}_knee",
        "spatial.movement_path.arc_length_xyz.{side}_knee",
    ]
    assert knee["feature_templates"]["role_alignment"] == [
        "spatial.role_alignment.left_right.range_of_motion_xy.knee"
    ]
    assert knee["feature_templates"]["compensation_links"] == [
        "control.compensation.knee_valgus.xy.{side}",
        "control.compensation.knee_varus.xy.{side}",
    ]

    shoulder = profiles["shoulder"]
    assert shoulder["anatomical_actions"]["primary"] == ["flexion_extension"]
    assert shoulder["anatomical_actions"]["secondary"] == ["scapular_stability_proxy"]
    assert "abduction_adduction" not in shoulder["anatomical_actions"]["primary"]
    assert "rotation_proxy" not in shoulder["anatomical_actions"]["secondary"]
    assert shoulder["feature_templates"]["range_of_motion"] == [
        "spatial.range_of_motion.xy.{side}_shoulder_angle",
        "spatial.range_of_motion.xyz.{side}_shoulder_angle",
    ]

    elbow = profiles["elbow"]
    assert elbow["anatomical_actions"]["primary"] == ["flexion_extension"]
    assert elbow["anatomical_actions"]["secondary"] == []
    assert "pronation_supination_proxy" not in elbow["anatomical_actions"]["secondary"]
    assert "elbow_flare" in elbow["feature_templates"]["planned_compensation_patterns"]

    wrist = profiles["wrist"]
    assert wrist["joint_model"] == "endpoint_support_proxy"
    assert wrist["anatomical_actions"]["secondary"] == []
    assert (
        "radial_ulnar_deviation_proxy" not in wrist["anatomical_actions"]["secondary"]
    )
    assert wrist["feature_templates"]["movement_path"] == [
        "spatial.movement_path.arc_length_xy.{side}_wrist",
        "spatial.movement_path.arc_length_xyz.{side}_wrist",
    ]


def test_derived_profiles_keep_reference_proxy_scope_explicit():
    profiles = load_joint_profiles()

    pelvis = profiles["pelvis_reference"]
    assert pelvis["joint_model"] == "derived_reference_proxy"
    assert pelvis["anatomical_actions"]["primary"] == ["control_proxy"]
    assert pelvis["anatomical_actions"]["secondary"] == [
        "lateral_tilt_proxy",
        "anterior_posterior_tilt_proxy",
        "rotation_proxy",
        "weight_shift_control",
    ]
    assert pelvis["feature_templates"]["stability"] == [
        "control.stability.hip_center_x_std",
        "control.stability.hip_center_z_std",
        "control.stability.hip_center_support_center_xy_drift",
    ]
    assert (
        "control.compensation.lateral_pelvic_shift.xy"
        in pelvis["feature_templates"]["compensation_links"]
    )

    trunk = profiles["trunk_reference"]
    assert trunk["anatomical_actions"]["secondary"] == [
        "flexion_extension_proxy",
        "lateral_flexion_proxy",
        "rotation_proxy",
    ]
    assert trunk["feature_templates"]["compensation_links"] == [
        "control.compensation.excessive_trunk_flexion.xy",
        "control.compensation.excessive_trunk_flexion.xyz",
    ]

    support = profiles["support_base"]
    assert support["feature_templates"]["support_consistency"] == [
        "spatial.support_consistency.center_drift_xy",
        "spatial.support_consistency.width_variation_xy",
    ]

    whole_body_com = profiles["whole_body_com"]
    assert whole_body_com["feature_templates"]["biomechanical_proxy"] == [
        "biomech.com.range_x",
        "biomech.com.range_z",
        "biomech.com.path_length",
    ]


def test_record_metadata_keeps_landmark_ids_and_dynamic_context_only():
    metadata = infer_common_record_metadata(
        "spatial.movement_path.arc_length_xy.left_knee",
        source_fields=["spatial.movement_path.recording_view_xy_scoring"],
        unit="torso_length_ratio",
        depth_dependency="none",
    )

    assert metadata["landmark_ids"] == ["left_knee"]
    assert "body_region" not in metadata
    assert "side" not in metadata
    assert "joint_action" not in metadata
    assert metadata["support_role"] == "moving_landmark"
    assert metadata["coordinate_reference"] == "norm_recording_view_xy"
    assert metadata["evaluation_domain"] == "recording_view_only"
    assert metadata["evidence_axes"] == "xy"
    assert metadata["feature_family"] == "movement_path"


def test_classify_feature_family_accepts_domain_local_phase_profiles():
    assert (
        classify_feature_family(
            "spatial.phase_profile.range_of_motion_ratio.descent_ascent"
        )
        == "phase_profile"
    )
    assert (
        classify_feature_family("temporal.phase_profile.duration_ratio.descent_ascent")
        == "phase_profile"
    )
    assert (
        classify_feature_family("biomech.phase_profile.load_shift_ratio.descent_ascent")
        == "phase_profile"
    )


def test_temporal_records_infer_timing_only_public_metadata():
    tempo = infer_common_record_metadata(
        "temporal.tempo.rep_duration",
        source_fields=[
            "feature_domains.temporal.tempo",
            "segmentation.rep_id",
            "timestamp",
        ],
        unit="second",
        depth_dependency="none",
    )

    assert tempo["landmark_ids"] == []
    assert tempo["support_role"] == "unknown"
    assert tempo["coordinate_reference"] == "timestamp"
    assert tempo["evaluation_domain"] == "timing_only"
    assert tempo["evidence_axes"] == "time"
    assert tempo["feature_family"] == "tempo"

    variability = infer_common_record_metadata(
        "temporal.variability.tempo_cv",
        source_fields=[
            "feature_domains.temporal.variability",
            "temporal.tempo.rep_duration",
        ],
        unit="dimensionless_cv",
        depth_dependency="none",
    )

    assert variability["coordinate_reference"] == "timestamp"
    assert variability["evaluation_domain"] == "timing_only"
    assert variability["evidence_axes"] == "time"
    assert variability["feature_family"] == "variability"


def test_control_compensation_records_infer_public_metadata():
    heel_lift = infer_common_record_metadata(
        "control.compensation.heel_lift.xy.left",
        source_fields=["left_heel"],
        unit="torso_length_ratio",
        depth_dependency="none",
    )

    assert heel_lift["landmark_ids"] == ["left_heel"]
    assert heel_lift["support_role"] == "support_consistency"
    assert heel_lift["coordinate_reference"] == "norm_recording_view_xy"
    assert heel_lift["evaluation_domain"] == "recording_view_only"
    assert heel_lift["evidence_axes"] == "y"
    assert heel_lift["feature_family"] == "compensation"

    knee_valgus = infer_common_record_metadata(
        "control.compensation.knee_valgus.xy.right",
        source_fields=["right_hip", "right_knee", "right_ankle"],
        unit="torso_length_ratio",
        depth_dependency="none",
    )

    assert knee_valgus["landmark_ids"] == [
        "right_hip",
        "right_knee",
        "right_ankle",
    ]
    assert knee_valgus["support_role"] == "moving_landmark"
    assert knee_valgus["coordinate_reference"] == "norm_recording_view_xy"
    assert knee_valgus["evaluation_domain"] == "recording_view_only"
    assert knee_valgus["evidence_axes"] == "xy"
    assert knee_valgus["feature_family"] == "compensation"

    pelvis_rotation = infer_common_record_metadata(
        "control.compensation.pelvis_rotation.xyz",
        source_fields=["left_hip", "right_hip"],
        unit="torso_length_ratio",
        depth_dependency="high",
    )

    assert pelvis_rotation["landmark_ids"] == ["left_hip", "right_hip"]
    assert pelvis_rotation["coordinate_reference"] == "norm_model_depth"
    assert pelvis_rotation["evaluation_domain"] == "dual_domain_compare"
    assert pelvis_rotation["evidence_axes"] == "z"

    trunk_xy = infer_common_record_metadata(
        "control.compensation.excessive_trunk_flexion.xy",
        source_fields=["left_shoulder", "right_shoulder", "left_hip", "right_hip"],
        unit="degree",
        depth_dependency="none",
    )
    assert trunk_xy["landmark_ids"] == ["shoulder_center", "hip_center"]
    assert trunk_xy["coordinate_reference"] == "norm_recording_view_xy"
    assert trunk_xy["evaluation_domain"] == "recording_view_only"
    assert trunk_xy["evidence_axes"] == "xy"

    trunk_xyz = infer_common_record_metadata(
        "control.compensation.excessive_trunk_flexion.xyz",
        source_fields=["left_shoulder", "right_shoulder", "left_hip", "right_hip"],
        unit="degree",
        depth_dependency="moderate",
    )
    assert trunk_xyz["landmark_ids"] == ["shoulder_center", "hip_center"]
    assert trunk_xyz["coordinate_reference"] == "norm_model_depth"
    assert trunk_xyz["evaluation_domain"] == "dual_domain_compare"
    assert trunk_xyz["evidence_axes"] == "xyz"


def test_resolve_landmark_metadata_preserves_record_order():
    rows = resolve_landmark_metadata(["right_knee", "left_knee"])

    assert [row["landmark_id"] for row in rows] == ["right_knee", "left_knee"]
    assert [row["side"] for row in rows] == ["right", "left"]
