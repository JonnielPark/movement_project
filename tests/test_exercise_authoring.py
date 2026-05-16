import pytest
import yaml

from movement.exercise_definition import load_exercise_context, load_exercise_definition
from movement.exercise_authoring import (
    ExerciseAuthoringSpec,
    artifact_to_yaml,
    generate_authoring_artifacts,
    load_authoring_registries,
    write_authoring_draft_artifacts,
)


DEFINITIONS_DIR = "data/definitions/exercises"
TARGET_EXERCISES = ("squat", "lunge", "pike_pushup", "plank_shoulder_tap")


def _squat_spec() -> ExerciseAuthoringSpec:
    return ExerciseAuthoringSpec(
        exercise_id="draft_squat",
        display_name="Draft Squat",
        movement_pattern="squat",
        posture_type="standing",
        laterality="bilateral_symmetric",
        support_template="bilateral_feet",
        primary_body_regions=("hip", "knee", "ankle"),
        primary_plane="sagittal",
        secondary_planes=("frontal", "transverse"),
        phase_template="descent_ascent_hip_center",
        counting_template="repeated_repetition",
        camera_template="front_oblique_lower_body",
        analysis_template="bilateral_lower_body_closed_chain",
    )


def test_authoring_registries_load_current_template_set():
    registries = load_authoring_registries()

    assert "exercise_id" in registries["schema"]["required_fields"]
    assert "squat" in registries["movement_patterns"]["patterns"]
    assert (
        "bilateral_lower_body_closed_chain"
        in registries["analysis_templates"]["templates"]
    )
    assert "front_oblique_lower_body" in registries["camera_templates"]["templates"]


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
    assert exercise["classification"]["movement_pattern"] == "squat"
    assert exercise["support"]["base_of_support"] == "bilateral_feet"
    assert "rep_segmentation" not in exercise
    assert "feature_domains" not in exercise
    assert "camera_protocol" not in exercise

    assert analysis["rep_segmentation"]["reference_landmark"] == "hip_center"
    assert analysis["landmarks"]["model"] == "mediapipe_pose_33"
    assert "compensation_candidates" in analysis["requires_review"]

    assert performance["performance_protocol"]["prescription"]["target_sets"] == 3
    assert camera["camera_protocol"]["recommended_zones"] == ["Z2", "Z8"]
    assert "view_metric_reliability" in camera["requires_review"]


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
        **{**_squat_spec().__dict__, "camera_template": "unknown_camera"}
    )

    with pytest.raises(ValueError, match="camera_template=unknown_camera"):
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


def test_split_exercise_context_loads_backward_compatible_definition():
    context = load_exercise_context("squat", DEFINITIONS_DIR)
    definition = context.exercise_definition

    assert context.is_split_source is True
    assert set(context.source_paths) == {
        "exercise_definition",
        "analysis_profile",
        "performance_protocol",
        "camera_protocol",
    }
    assert context.exercise_identity["support"]["base_of_support"] == "bilateral_feet"
    assert "rep_segmentation" not in context.exercise_identity
    assert "feature_domains" not in context.exercise_identity

    assert definition.exercise_id == "squat"
    assert definition.rep_segmentation is not None
    assert definition.performance_protocol is not None
    assert definition.camera_protocol is not None
    assert definition.feature_domains.spatial[:2] == ["rom", "symmetry"]


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


def test_load_exercise_definition_still_returns_definition_for_split_yaml():
    definition = load_exercise_definition("plank_shoulder_tap", DEFINITIONS_DIR)

    assert definition.exercise_id == "plank_shoulder_tap"
    assert definition.performance_protocol is not None
    assert definition.performance_protocol.counting.count_unit == "left_right_pair"
