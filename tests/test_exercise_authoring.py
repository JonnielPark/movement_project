import pytest
import yaml

from movement.exercise_definition import load_exercise_context, load_exercise_definition
from movement.exercise_authoring import (
    ExerciseAuthoringSpec,
    artifact_to_yaml,
    derive_movement_pattern_from_authoring_axes,
    generate_authoring_artifacts,
    load_authoring_registries,
    recommend_analysis_templates_for_authoring_axes,
    recommend_camera_positions_for_authoring_axes,
    recommend_counting_templates_for_authoring_axes,
    recommend_phase_templates_for_authoring_axes,
    suggest_body_regions_from_joint_actions,
    write_authoring_draft_artifacts,
)


DEFINITIONS_DIR = "data/definitions/exercises"
EXAMPLE_AUTHORING_DEFINITIONS_DIR = (
    "data/examples/exercise_authoring/draft_squat/data/definitions/exercises"
)
TARGET_EXERCISES = ("squat", "lunge", "pike_pushup", "plank_shoulder_tap")


def _squat_spec() -> ExerciseAuthoringSpec:
    return ExerciseAuthoringSpec(
        exercise_id="draft_squat",
        display_name="Draft Squat",
        movement_pattern="squat",
        posture_type="standing",
        body_geometry="neutral_upright",
        laterality="bilateral_symmetric",
        support_template="bilateral_feet",
        primary_body_regions=("hip", "knee", "ankle"),
        primary_joint_actions=(
            "hip_flexion_extension",
            "knee_flexion_extension",
            "ankle_dorsiflexion_plantarflexion",
        ),
        secondary_joint_actions=("trunk_flexion_extension",),
        primary_plane="sagittal",
        secondary_planes=("frontal", "transverse"),
        phase_template="descent_ascent_hip_center",
        counting_template="repeated_repetition",
        target_count_per_set=10,
        camera_view_family="front_oblique",
        camera_height_level="H2",
        analysis_template="bilateral_lower_body_closed_chain",
    )


def test_authoring_registries_load_current_template_set():
    registries = load_authoring_registries()

    assert "exercise_id" in registries["schema"]["required_fields"]
    assert "squat" in registries["movement_patterns"]["patterns"]
    assert "supine_body_floor" in registries["support_templates"]["templates"]
    assert (
        registries["phase_templates"]["templates"]["static_hold_center"][
            "implementation_status"
        ]
        == "planned"
    )
    assert (
        registries["performance_templates"]["templates"]["timed_hold_seconds"][
            "implementation_status"
        ]
        == "planned"
    )
    assert (
        "bilateral_lower_body_closed_chain"
        in registries["analysis_templates"]["templates"]
    )
    assert "front_oblique" in registries["camera_zones"]["view_families"]
    assert "H2" in registries["camera_zones"]["height_levels"]


@pytest.mark.parametrize(
    ("axes", "expected"),
    [
        (
            {
                "posture_type": "standing",
                "body_geometry": "neutral_upright",
                "laterality": "bilateral_symmetric",
                "support_template": "bilateral_feet",
                "primary_body_regions": ("hip", "knee", "ankle"),
                "primary_joint_actions": (
                    "hip_flexion_extension",
                    "knee_flexion_extension",
                    "ankle_dorsiflexion_plantarflexion",
                ),
                "secondary_joint_actions": ("trunk_flexion_extension",),
            },
            "squat",
        ),
        (
            {
                "posture_type": "standing",
                "body_geometry": "neutral_upright",
                "laterality": "alternating",
                "support_template": "split_stance",
                "primary_body_regions": ("hip", "knee", "ankle"),
                "primary_joint_actions": (
                    "hip_flexion_extension",
                    "knee_flexion_extension",
                    "ankle_dorsiflexion_plantarflexion",
                ),
                "secondary_joint_actions": ("weight_shift_control",),
            },
            "lunge",
        ),
        (
            {
                "posture_type": "floor_supported_prone",
                "body_geometry": "high_hip_inverted_v",
                "laterality": "bilateral_symmetric",
                "support_template": "hands_and_feet",
                "primary_body_regions": ("shoulder", "elbow", "wrist"),
                "primary_joint_actions": (
                    "shoulder_flexion_extension",
                    "elbow_flexion_extension",
                ),
                "secondary_joint_actions": ("scapular_stability_proxy",),
            },
            "push",
        ),
        (
            {
                "posture_type": "floor_supported_prone",
                "body_geometry": "neutral_prone_line",
                "laterality": "alternating",
                "support_template": "hands_and_feet_with_trunk",
                "primary_body_regions": ("trunk", "pelvis", "shoulder"),
                "primary_joint_actions": (
                    "anti_rotation_control",
                    "weight_shift_control",
                ),
                "secondary_joint_actions": ("shoulder_flexion_extension",),
            },
            "anti_rotation",
        ),
    ],
)
def test_movement_pattern_is_derived_from_authoring_axes(axes, expected):
    assert derive_movement_pattern_from_authoring_axes(**axes) == expected


def test_unknown_authoring_axes_are_not_silently_mapped():
    with pytest.raises(ValueError, match="Could not derive movement_pattern"):
        derive_movement_pattern_from_authoring_axes(
            posture_type="standing",
            body_geometry="neutral_upright",
            laterality="unilateral_left",
            support_template="bilateral_feet",
            primary_body_regions=("wrist",),
            primary_joint_actions=("wrist_flexion_extension",),
        )


@pytest.mark.parametrize(
    ("primary_joint_actions", "secondary_joint_actions", "expected"),
    [
        (
            (
                "hip_flexion_extension",
                "knee_flexion_extension",
                "ankle_dorsiflexion_plantarflexion",
            ),
            ("trunk_flexion_extension",),
            ("hip", "knee", "ankle", "trunk"),
        ),
        (
            ("anti_rotation_control", "weight_shift_control"),
            ("shoulder_flexion_extension",),
            ("pelvis", "trunk", "shoulder"),
        ),
        (
            ("shoulder_flexion_extension", "elbow_flexion_extension"),
            ("scapular_stability_proxy",),
            ("shoulder", "elbow"),
        ),
    ],
)
def test_body_regions_are_suggested_from_joint_actions(
    primary_joint_actions,
    secondary_joint_actions,
    expected,
):
    assert (
        suggest_body_regions_from_joint_actions(
            primary_joint_actions,
            secondary_joint_actions,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("axes", "expected"),
    [
        (
            {
                "posture_type": "standing",
                "body_geometry": "neutral_upright",
                "support_template": "bilateral_feet",
                "primary_joint_actions": (
                    "hip_flexion_extension",
                    "knee_flexion_extension",
                    "ankle_dorsiflexion_plantarflexion",
                ),
                "primary_plane": "sagittal",
            },
            ("descent_ascent_hip_center",),
        ),
        (
            {
                "posture_type": "floor_supported_prone",
                "body_geometry": "high_hip_inverted_v",
                "support_template": "hands_and_feet",
                "primary_joint_actions": (
                    "shoulder_flexion_extension",
                    "elbow_flexion_extension",
                ),
                "primary_plane": "sagittal",
            },
            ("descent_ascent_nose",),
        ),
        (
            {
                "posture_type": "floor_supported_prone",
                "body_geometry": "neutral_prone_line",
                "support_template": "hands_and_feet_with_trunk",
                "primary_joint_actions": ("anti_rotation_control",),
                "secondary_joint_actions": ("weight_shift_control",),
                "primary_plane": "transverse",
            },
            ("lift_tap_return_wrist", "rotate_return_trunk"),
        ),
        (
            {
                "posture_type": "supine",
                "body_geometry": "supine_hooklying",
                "support_template": "supine_body_floor",
                "primary_joint_actions": ("hip_flexion_extension",),
                "primary_plane": "sagittal",
            },
            ("bridge_lift_lower_hip_center",),
        ),
        (
            {
                "posture_type": "seated",
                "body_geometry": "neutral_upright",
                "support_template": "seated_base",
                "primary_joint_actions": ("shoulder_flexion_extension",),
                "primary_plane": "sagittal",
            },
            ("reach_return_wrist",),
        ),
        (
            {
                "posture_type": "standing",
                "body_geometry": "neutral_upright",
                "support_template": "bilateral_feet",
                "primary_joint_actions": (),
                "primary_plane": "static",
            },
            ("static_hold_center",),
        ),
    ],
)
def test_phase_templates_are_recommended_from_authoring_axes(axes, expected):
    assert recommend_phase_templates_for_authoring_axes(**axes) == expected


@pytest.mark.parametrize(
    ("laterality", "phase_template", "expected"),
    [
        (
            "bilateral_symmetric",
            "descent_ascent_hip_center",
            ("repeated_repetition",),
        ),
        (
            "bilateral_asymmetric",
            "descent_ascent_hip_center",
            ("repeated_repetition",),
        ),
        (
            "unilateral_left",
            "descent_ascent_hip_center",
            ("repeated_repetition",),
        ),
        (
            "alternating",
            "lift_tap_return_wrist",
            ("alternating_left_right_pair", "same_side_block_then_switch_5_each"),
        ),
        (
            "alternating",
            "descent_ascent_hip_center",
            ("alternating_left_right_pair", "same_side_block_then_switch_5_each"),
        ),
        (
            "bilateral_symmetric",
            "static_hold_center",
            ("timed_hold_seconds",),
        ),
    ],
)
def test_counting_templates_are_recommended_from_laterality_and_phase(
    laterality,
    phase_template,
    expected,
):
    assert (
        recommend_counting_templates_for_authoring_axes(
            laterality=laterality,
            phase_template=phase_template,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("axes", "expected"),
    [
        (
            {
                "posture_type": "standing",
                "body_geometry": "neutral_upright",
                "laterality": "bilateral_symmetric",
                "support_template": "bilateral_feet",
                "primary_body_regions": ("hip", "knee", "ankle"),
                "primary_joint_actions": (
                    "hip_flexion_extension",
                    "knee_flexion_extension",
                    "ankle_dorsiflexion_plantarflexion",
                ),
            },
            ("bilateral_lower_body_closed_chain",),
        ),
        (
            {
                "posture_type": "standing",
                "body_geometry": "neutral_upright",
                "laterality": "alternating",
                "support_template": "split_stance",
                "primary_body_regions": ("hip", "knee", "ankle"),
                "primary_joint_actions": (
                    "hip_flexion_extension",
                    "knee_flexion_extension",
                    "ankle_dorsiflexion_plantarflexion",
                ),
            },
            ("alternating_lower_body_split_stance",),
        ),
        (
            {
                "posture_type": "floor_supported_prone",
                "body_geometry": "high_hip_inverted_v",
                "laterality": "bilateral_symmetric",
                "support_template": "hands_and_feet",
                "primary_body_regions": ("shoulder", "elbow", "wrist"),
                "primary_joint_actions": (
                    "shoulder_flexion_extension",
                    "elbow_flexion_extension",
                ),
            },
            ("bilateral_upper_body_inverted_closed_chain",),
        ),
        (
            {
                "posture_type": "floor_supported_prone",
                "body_geometry": "neutral_prone_line",
                "laterality": "alternating",
                "support_template": "hands_and_feet_with_trunk",
                "primary_body_regions": ("trunk", "pelvis", "shoulder"),
                "primary_joint_actions": (
                    "anti_rotation_control",
                    "weight_shift_control",
                ),
            },
            ("alternating_core_anti_rotation",),
        ),
    ],
)
def test_analysis_templates_are_recommended_from_authoring_axes(axes, expected):
    assert recommend_analysis_templates_for_authoring_axes(**axes) == expected


@pytest.mark.parametrize(
    ("axes", "expected"),
    [
        (
            {
                "posture_type": "standing",
                "laterality": "bilateral_symmetric",
                "support_template": "bilateral_feet",
                "primary_body_regions": ("hip", "knee", "ankle"),
                "primary_joint_actions": (
                    "hip_flexion_extension",
                    "knee_flexion_extension",
                    "ankle_dorsiflexion_plantarflexion",
                ),
                "primary_plane": "sagittal",
            },
            ("front_oblique/H2",),
        ),
        (
            {
                "posture_type": "standing",
                "laterality": "alternating",
                "support_template": "split_stance",
                "primary_body_regions": ("hip", "knee", "ankle"),
                "primary_joint_actions": (
                    "hip_flexion_extension",
                    "knee_flexion_extension",
                    "ankle_dorsiflexion_plantarflexion",
                ),
                "primary_plane": "sagittal",
            },
            ("side/H2",),
        ),
        (
            {
                "posture_type": "floor_supported_prone",
                "laterality": "bilateral_symmetric",
                "support_template": "hands_and_feet",
                "primary_body_regions": ("shoulder", "elbow", "wrist"),
                "primary_joint_actions": (
                    "shoulder_flexion_extension",
                    "elbow_flexion_extension",
                ),
                "primary_plane": "sagittal",
            },
            ("side/H1",),
        ),
        (
            {
                "posture_type": "floor_supported_prone",
                "laterality": "alternating",
                "support_template": "hands_and_feet_with_trunk",
                "primary_body_regions": ("trunk", "pelvis"),
                "primary_joint_actions": ("anti_rotation_control",),
                "primary_plane": "transverse",
            },
            ("front_oblique/H1",),
        ),
    ],
)
def test_camera_positions_are_recommended_from_authoring_axes(axes, expected):
    assert recommend_camera_positions_for_authoring_axes(**axes) == expected


def test_supine_authoring_axes_require_a_future_template_family():
    with pytest.raises(ValueError, match="posture_type=supine"):
        derive_movement_pattern_from_authoring_axes(
            posture_type="supine",
            body_geometry="supine_tabletop",
            laterality="alternating",
            support_template="hands_and_feet_with_trunk",
            primary_body_regions=("trunk", "pelvis", "hip"),
            primary_joint_actions=("anti_rotation_control",),
        )


@pytest.mark.parametrize(
    ("body_geometry", "posture_type", "primary_joint_actions"),
    [
        (
            "forward_lean_hinge",
            "standing",
            ("hip_flexion_extension", "knee_flexion_extension"),
        ),
        (
            "supine_hollow",
            "supine",
            ("anti_rotation_control", "hip_flexion_extension"),
        ),
        (
            "hanging_tuck",
            "hanging",
            ("hip_flexion_extension", "trunk_flexion_extension"),
        ),
    ],
)
def test_future_body_geometry_options_require_future_template_family(
    body_geometry, posture_type, primary_joint_actions
):
    with pytest.raises(ValueError, match="Could not derive movement_pattern"):
        derive_movement_pattern_from_authoring_axes(
            posture_type=posture_type,
            body_geometry=body_geometry,
            laterality="bilateral_symmetric",
            support_template="bilateral_feet",
            primary_body_regions=("hip", "knee", "trunk"),
            primary_joint_actions=primary_joint_actions,
        )


def test_generate_authoring_artifacts_split_yaml_responsibilities():
    registries = load_authoring_registries()
    artifacts = generate_authoring_artifacts(_squat_spec(), registries)

    exercise = artifacts["exercise_definition"]
    analysis = artifacts["analysis_profile"]
    performance = artifacts["performance_protocol"]
    camera = artifacts["camera_protocol"]

    assert set(artifacts) == {
        "exercise_definition",
        "analysis_profile",
        "performance_protocol",
        "camera_protocol",
    }

    assert exercise["exercise_id"] == "draft_squat"
    assert exercise["status"] == "draft"
    assert exercise["generated_by"] == "exercise_authoring_notebook"
    assert (
        exercise["classification"]["movement_template_id"]
        == "bilateral_lower_body_closed_chain"
    )
    assert exercise["classification"]["movement_pattern"] == "squat"
    assert exercise["classification"]["body_geometry"] == "neutral_upright"
    assert (
        exercise["classification"]["movement_pattern_source"]
        == "derived_from_joint_actions_and_context"
    )
    assert exercise["support"]["base_of_support"] == "bilateral_feet"
    assert exercise["joint_actions"]["primary"] == [
        "hip_flexion_extension",
        "knee_flexion_extension",
        "ankle_dorsiflexion_plantarflexion",
    ]
    assert exercise["joint_actions"]["secondary"] == [
        "trunk_flexion_extension",
        "pelvis_lateral_tilt_proxy",
        "pelvis_rotation_proxy",
    ]
    assert exercise["authoring_inference"]["active_rules"] == [
        "standing_bilateral_feet_sagittal_lower_body_bend_frontal",
        "standing_bilateral_feet_sagittal_lower_body_bend_transverse",
    ]
    assert "rep_segmentation" not in exercise
    assert "feature_domains" not in exercise
    assert "camera_protocol" not in exercise

    assert analysis["rep_segmentation"]["reference_landmark"] == "hip_center"
    assert (
        analysis["rep_segmentation"]["reference_coordinate_family"]
        == "recording_view_raw"
    )
    assert analysis["rep_segmentation"]["reference_axis"] == "image_y"
    assert analysis["phase_segmentation"]["split_logic"] == "local_maximum"
    assert analysis["landmarks"]["model"] == "mediapipe_pose_33"
    assert "compensation_candidates" in analysis["requires_review"]
    assert "context_inferred_joint_actions" in analysis["requires_review"]
    assert "context_inferred_compensation_candidates" in analysis["requires_review"]
    assert "context_inferred_feature_domains" in analysis["requires_review"]
    assert "foot_external_rotation_proxy" in analysis["compensation_candidates"]
    assert "joint_tracking_error" in analysis["feature_domains"]["control"]
    assert (
        "compensation_load_shift_proxy"
        in analysis["feature_domains"]["biomechanical_proxy"]
    )

    assert (
        performance["performance_protocol"]["prescription"]["target_count_per_set"]
        == 10
    )
    assert performance["performance_protocol"]["counting"]["target_count"] == 10
    assert "target_sets" not in performance["performance_protocol"]["prescription"]
    assert "recommended_sets" not in performance["performance_protocol"]["completion"]
    assert (
        "rest_between_sets_s" not in performance["performance_protocol"]["prescription"]
    )
    assert camera["camera_protocol"]["selected_view"] == {
        "view_family": "front_oblique",
        "member_zones": ["Z2", "Z8"],
        "height": "H2",
        "position_id": "front_oblique/H2",
        "recommendation_status": "recommended",
    }
    assert camera["camera_protocol"]["recommended_view_positions"] == [
        {
            "view_family": "front_oblique",
            "member_zones": ["Z2", "Z8"],
            "height": "H2",
        },
    ]
    assert {
        "view_family": "side",
        "member_zones": ["Z3", "Z7"],
        "height": "H2",
    } in camera["camera_protocol"]["non_recommended_view_positions"]
    assert camera["camera_protocol"]["recommended_zones"] == ["Z2", "Z8"]
    assert "view_metric_reliability" in camera["requires_review"]


def test_context_inference_stays_conservative_without_secondary_planes():
    registries = load_authoring_registries()
    spec = ExerciseAuthoringSpec(**{**_squat_spec().__dict__, "secondary_planes": ()})

    artifacts = generate_authoring_artifacts(spec, registries)
    exercise = artifacts["exercise_definition"]
    analysis = artifacts["analysis_profile"]

    assert exercise["joint_actions"]["secondary"] == ["trunk_flexion_extension"]
    assert "authoring_inference" not in exercise
    assert "foot_external_rotation_proxy" not in analysis["compensation_candidates"]
    assert "joint_tracking_error" not in analysis["feature_domains"]["control"]
    assert (
        "compensation_load_shift_proxy"
        not in analysis["feature_domains"]["biomechanical_proxy"]
    )


def test_authoring_yaml_generation_is_deterministic():
    registries = load_authoring_registries()

    first = generate_authoring_artifacts(_squat_spec(), registries)
    second = generate_authoring_artifacts(_squat_spec(), registries)

    assert {key: artifact_to_yaml(value) for key, value in first.items()} == {
        key: artifact_to_yaml(value) for key, value in second.items()
    }


def test_unknown_template_reference_is_rejected():
    registries = load_authoring_registries()
    bad_spec = ExerciseAuthoringSpec(
        **{**_squat_spec().__dict__, "analysis_template": "unknown_analysis"}
    )

    with pytest.raises(ValueError, match="analysis_template=unknown_analysis"):
        generate_authoring_artifacts(bad_spec, registries)


def test_unknown_camera_position_is_rejected():
    registries = load_authoring_registries()
    bad_spec = ExerciseAuthoringSpec(
        **{**_squat_spec().__dict__, "camera_view_family": "unknown_view"}
    )

    with pytest.raises(ValueError, match="Unknown camera_view_family=unknown_view"):
        generate_authoring_artifacts(bad_spec, registries)


def test_performance_authoring_overrides_are_validated():
    registries = load_authoring_registries()
    bad_spec = ExerciseAuthoringSpec(
        **{**_squat_spec().__dict__, "target_count_per_set": 0}
    )

    with pytest.raises(ValueError, match="target_count_per_set"):
        generate_authoring_artifacts(bad_spec, registries)


def test_optional_set_and_rest_metadata_are_only_added_when_explicit():
    registries = load_authoring_registries()
    spec = ExerciseAuthoringSpec(
        **{
            **_squat_spec().__dict__,
            "target_sets": 3,
            "rest_between_sets_s": (120, 180),
        }
    )

    performance = generate_authoring_artifacts(spec, registries)[
        "performance_protocol"
    ]["performance_protocol"]

    assert performance["prescription"]["target_sets"] == 3
    assert performance["completion"]["recommended_sets"] == 3
    assert performance["prescription"]["rest_between_sets_s"] == [120, 180]


def test_incompatible_posture_body_geometry_pair_is_rejected():
    registries = load_authoring_registries()
    bad_spec = ExerciseAuthoringSpec(
        **{**_squat_spec().__dict__, "body_geometry": "supine_tabletop"}
    )

    with pytest.raises(ValueError, match="not compatible"):
        generate_authoring_artifacts(bad_spec, registries)


def test_incompatible_posture_support_pair_is_rejected():
    registries = load_authoring_registries()
    bad_spec = ExerciseAuthoringSpec(
        **{
            **_squat_spec().__dict__,
            "posture_type": "supine",
            "body_geometry": "supine_tabletop",
            "support_template": "bilateral_feet",
        }
    )

    with pytest.raises(ValueError, match="support_template=bilateral_feet"):
        generate_authoring_artifacts(bad_spec, registries)


def test_write_authoring_drafts_uses_mirrored_paths_and_protects_overwrite(tmp_path):
    registries = load_authoring_registries()
    artifacts = generate_authoring_artifacts(_squat_spec(), registries)

    paths = write_authoring_draft_artifacts(artifacts, draft_root=tmp_path)

    exercise_path = (
        tmp_path
        / "draft_squat"
        / "data"
        / "definitions"
        / "exercises"
        / "draft_squat.yaml"
    )
    assert paths["exercise_definition"] == exercise_path
    assert exercise_path.exists()

    loaded = yaml.safe_load(exercise_path.read_text(encoding="utf-8"))
    assert loaded["exercise_id"] == "draft_squat"
    assert loaded["status"] == "draft"

    with pytest.raises(FileExistsError):
        write_authoring_draft_artifacts(artifacts, draft_root=tmp_path)

    write_authoring_draft_artifacts(artifacts, draft_root=tmp_path, overwrite=True)


def test_authoring_draft_bundle_loads_as_canonical_view(tmp_path):
    registries = load_authoring_registries()
    artifacts = generate_authoring_artifacts(_squat_spec(), registries)

    paths = write_authoring_draft_artifacts(
        artifacts,
        draft_root=tmp_path,
    )

    exercise_path = (
        tmp_path
        / "draft_squat"
        / "data"
        / "definitions"
        / "exercises"
        / "draft_squat.yaml"
    )
    assert paths["exercise_definition"] == exercise_path
    assert exercise_path.exists()

    context = load_exercise_context(
        "draft_squat",
        exercise_path.parent,
        authoring_mode="canonical_view",
        canonical_exercise_id="squat",
        canonical_display_name="Bodyweight Squat",
    )
    definition = context.exercise_definition

    assert context.exercise_id == "squat"
    assert definition.exercise_id == "squat"
    assert definition.display_name == "Bodyweight Squat"
    assert context.source_paths["exercise_definition"] == exercise_path
    assert context.exercise_identity["exercise_id"] == "squat"
    assert context.exercise_identity["display_name"] == "Bodyweight Squat"
    assert "status" not in context.exercise_identity
    assert "generated_by" not in context.exercise_identity
    assert "requires_review" not in context.exercise_identity
    assert context.exercise_identity["authoring_spec"]["exercise_id"] == "squat"
    provenance = context.exercise_identity["authoring_provenance"]
    assert provenance["authoring_mode"] == "canonical_view"
    assert provenance["generated_by"] == "exercise_authoring_notebook"
    assert provenance["source_status"] == "draft"
    assert provenance["source_authoring_exercise_id"] == "draft_squat"
    assert provenance["source_artifact_exercise_id"] == "draft_squat"
    assert provenance["canonical_exercise_id"] == "squat"
    assert "biomechanical_identity" in provenance["requires_review"]
    assert context.analysis_profile["exercise_id"] == "squat"
    assert (
        "compensation_candidates"
        in context.analysis_profile["authoring_provenance"]["requires_review"]
    )
    assert context.performance_protocol["exercise_id"] == "squat"
    assert (
        "participant_cues"
        in context.performance_protocol["authoring_provenance"]["requires_review"]
    )
    assert context.camera_protocol["exercise_id"] == "squat"
    assert (
        "view_metric_reliability"
        in context.camera_protocol["authoring_provenance"]["requires_review"]
    )
    assert definition.rep_segmentation.reference_landmark == "hip_center"
    assert definition.performance_protocol is not None
    assert definition.camera_protocol is not None

    with pytest.raises(ValueError, match="canonical_exercise_id is required"):
        load_exercise_context(
            "draft_squat",
            exercise_path.parent,
            authoring_mode="canonical_view",
        )


def test_split_exercise_context_loads_backward_compatible_definition():
    context = load_exercise_context("squat", DEFINITIONS_DIR)
    definition = context.exercise_definition

    assert context.is_split_source is True
    assert set(context.source_paths) == {
        "exercise_definition",
        "analysis_profile",
        "analysis_presets",
        "performance_protocol",
        "camera_protocol",
    }
    assert context.exercise_identity["support"]["base_of_support"] == "bilateral_feet"
    assert "rep_segmentation" not in context.exercise_identity
    assert "feature_domains" not in context.exercise_identity

    assert definition.exercise_id == "squat"
    assert definition.rep_segmentation is not None
    assert (
        definition.rep_segmentation.reference_coordinate_family == "recording_view_raw"
    )
    assert definition.rep_segmentation.reference_axis == "image_y"
    assert definition.phase_segmentation is not None
    assert (
        definition.phase_segmentation.reference_coordinate_family
        == "recording_view_raw"
    )
    assert definition.phase_segmentation.split_logic == "local_maximum"
    assert definition.performance_protocol is not None
    assert definition.camera_protocol is not None
    assert definition.feature_domains.spatial[:2] == ["rom", "symmetry"]
    assert context.analysis_profile["rep_segmentation"]["reference_landmark"] == (
        "hip_center"
    )
    assert (
        context.analysis_profile["quality_rules"]["minimum_visible_landmark_ratio"]
        == 0.8
    )


def test_analysis_profile_presets_expand_before_definition_parse():
    pike = load_exercise_context("pike_pushup", DEFINITIONS_DIR)
    plank = load_exercise_context("plank_shoulder_tap", DEFINITIONS_DIR)

    assert pike.exercise_definition.rep_segmentation is not None
    assert pike.exercise_definition.rep_segmentation.reference_landmark == "nose"
    assert (
        pike.exercise_definition.angle_definitions["left_elbow_angle"]["vertex"] == 13
    )
    assert pike.exercise_definition.quality_rules.minimum_visible_landmark_ratio == 0.75

    assert plank.exercise_definition.phase_segmentation is not None
    assert plank.exercise_definition.phase_segmentation.phase_sequence == [
        "Lift",
        "Tap",
        "Return",
    ]
    assert (
        plank.exercise_definition.quality_rules.minimum_critical_landmark_ratio == 0.85
    )


def test_target_exercise_identity_yaml_keeps_only_identity_fields():
    moved_fields = {
        "rep_segmentation",
        "phase_segmentation",
        "landmarks",
        "angle_definitions",
        "biomechanical_focus",
        "compensation_candidates",
        "feature_domains",
        "quality_rules",
        "performance_protocol",
        "camera_protocol",
        "view_metric_reliability",
    }

    for exercise_id in TARGET_EXERCISES:
        context = load_exercise_context(exercise_id, DEFINITIONS_DIR)
        identity_keys = set(context.exercise_identity)
        assert not moved_fields.intersection(identity_keys)
        assert context.exercise_definition.exercise_id == exercise_id


def test_target_exercise_identity_yaml_preserves_authoring_spec():
    for exercise_id in TARGET_EXERCISES:
        context = load_exercise_context(exercise_id, DEFINITIONS_DIR)
        authoring_spec = context.exercise_identity.get("authoring_spec")

        assert authoring_spec is not None
        assert authoring_spec["exercise_id"] == exercise_id
        assert (
            authoring_spec["movement_pattern_source"]
            == "derived_from_joint_actions_and_context"
        )
        assert authoring_spec["phase_template"]
        assert authoring_spec["counting_template"]
        assert authoring_spec["analysis_template"]
        assert (
            authoring_spec["movement_template_id"]
            == authoring_spec["analysis_template"]
        )


def test_canonical_squat_authoring_order_matches_draft_squat():
    canonical = load_exercise_context("squat", DEFINITIONS_DIR).exercise_definition
    draft = load_exercise_context(
        "draft_squat",
        EXAMPLE_AUTHORING_DEFINITIONS_DIR,
    ).exercise_definition

    assert canonical.compensation_candidates == draft.compensation_candidates
    assert canonical.feature_domains.control == draft.feature_domains.control
    assert canonical.joint_actions == draft.joint_actions


def test_load_exercise_definition_still_returns_definition_for_split_yaml():
    definition = load_exercise_definition("plank_shoulder_tap", DEFINITIONS_DIR)

    assert definition.exercise_id == "plank_shoulder_tap"
    assert definition.performance_protocol is not None
    assert definition.performance_protocol.counting.count_unit == "left_right_pair"


def test_git_tracked_authoring_example_loads_as_split_yaml_bundle():
    context = load_exercise_context(
        "draft_squat",
        EXAMPLE_AUTHORING_DEFINITIONS_DIR,
    )

    definition = context.exercise_definition
    assert context.exercise_id == "draft_squat"
    assert definition.exercise_id == "draft_squat"
    assert definition.rep_segmentation.reference_landmark == "hip_center"
    assert definition.performance_protocol is not None
    assert definition.performance_protocol.counting.count_unit == "repetition"
    assert definition.camera_protocol is not None
    assert definition.camera_protocol.recommended_zones == ["Z2", "Z8"]
