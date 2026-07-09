import pytest

from movement.exercise_definition import load_exercise_definition


DEFINITIONS_DIR = "data/definitions/exercises"


def test_lunge_loads_same_side_block_performance_protocol():
    definition = load_exercise_definition("lunge", DEFINITIONS_DIR)

    protocol = definition.performance_protocol

    assert protocol is not None
    assert protocol.prescription.target_sets == 3
    assert protocol.prescription.target_count_per_set == 10
    assert protocol.prescription.count_unit == "repetition"
    assert protocol.prescription.segmentation_reps_per_count == 1
    assert protocol.prescription.rest_between_sets_s == [120, 180]
    assert protocol.counting.target_count == 10
    assert protocol.counting.count_unit == "repetition"
    assert protocol.counting.segmentation_reps_per_count == 1
    assert protocol.side_sequence.mode == "same_side_block_then_switch"
    assert protocol.side_sequence.block_size_counts == 5
    assert protocol.side_sequence.first_side_source == "annotation.starting_side"
    assert protocol.allowed_side_sequence_modes == [
        "same_side_block_then_switch",
        "alternating_each_rep",
    ]


def test_plank_shoulder_tap_loads_left_right_pair_counting():
    definition = load_exercise_definition("plank_shoulder_tap", DEFINITIONS_DIR)

    protocol = definition.performance_protocol

    assert protocol is not None
    assert protocol.prescription.target_sets == 3
    assert protocol.prescription.target_count_per_set == 10
    assert protocol.prescription.count_unit == "left_right_pair"
    assert protocol.prescription.segmentation_reps_per_count == 2
    assert protocol.counting.target_count == 10
    assert protocol.counting.count_unit == "left_right_pair"
    assert protocol.counting.segmentation_reps_per_count == 2
    assert protocol.side_sequence.mode == "alternating_each_rep"
    assert protocol.allowed_side_sequence_modes == ["alternating_each_rep"]
    assert "excessive_pelvic_rotation" in protocol.analysis_disrupting_patterns


def test_pike_pushup_allows_partial_completion_metadata():
    definition = load_exercise_definition("pike_pushup", DEFINITIONS_DIR)

    protocol = definition.performance_protocol

    assert protocol is not None
    assert protocol.allowed_side_sequence_modes == ["none"]
    assert protocol.prescription.target_sets == 3
    assert protocol.prescription.target_count_per_set == 10
    assert protocol.completion.allow_partial_completion is True
    assert protocol.completion.recommended_sets == 3


def test_target_exercises_recommend_three_validation_sets():
    for exercise_id in ("squat", "lunge", "pike_pushup", "plank_shoulder_tap"):
        definition = load_exercise_definition(exercise_id, DEFINITIONS_DIR)

        assert definition.performance_protocol is not None
        protocol = definition.performance_protocol
        assert protocol.side_sequence.mode in protocol.allowed_side_sequence_modes
        assert protocol.prescription.target_sets == 3
        assert protocol.prescription.target_count_per_set == 10
        assert protocol.completion.recommended_sets == 3


def test_generic_definition_keeps_performance_protocol_optional():
    definition = load_exercise_definition("generic", DEFINITIONS_DIR)

    assert definition.performance_protocol is None


def test_block_side_sequence_requires_block_size(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        """
exercise_id: bad
display_name: Bad
version: 0.0.1
classification:
  family: lower_body
  posture_type: standing
  kinetic_chain: closed_chain
  laterality: alternating
  primary_plane: sagittal
phase_model:
  type: cyclic
landmarks:
  model: mediapipe_pose_33
compensation_patterns: []
feature_domains:
  spatial: []
  temporal: []
  control: []
quality_rules: {}
performance_protocol:
  counting:
    target_count: 10
    count_unit: repetition
    segmentation_reps_per_count: 1
  side_sequence:
    mode: same_side_block_then_switch
    block_size_counts: null
  completion:
    allow_partial_completion: false
    recommended_sets: 1
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="block_size_counts"):
        load_exercise_definition("bad", tmp_path)


def test_performance_prescription_can_drive_backward_compatible_counting(tmp_path):
    yaml_path = tmp_path / "valid.yaml"
    yaml_path.write_text(
        """
exercise_id: valid
display_name: Valid
version: 0.0.1
classification:
  family: lower_body
  posture_type: standing
  kinetic_chain: closed_chain
  laterality: bilateral_symmetric
  primary_plane: sagittal
phase_model:
  type: cyclic
landmarks:
  model: mediapipe_pose_33
compensation_patterns: []
feature_domains:
  spatial: []
  temporal: []
  control: []
quality_rules: {}
performance_protocol:
  prescription:
    target_sets: 2
    target_count_per_set: 8
    count_unit: repetition
    segmentation_reps_per_count: 1
    rest_between_sets_s: [90, 120]
  side_sequence:
    mode: none
    block_size_counts: null
  completion:
    allow_partial_completion: true
""",
        encoding="utf-8",
    )

    definition = load_exercise_definition("valid", tmp_path)
    protocol = definition.performance_protocol

    assert protocol is not None
    assert protocol.prescription.target_sets == 2
    assert protocol.prescription.target_count_per_set == 8
    assert protocol.prescription.rest_between_sets_s == [90, 120]
    assert protocol.counting.target_count == 8
    assert protocol.counting.count_unit == "repetition"
    assert protocol.completion.recommended_sets == 2


def test_performance_prescription_rejects_mismatched_counting_mirror(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        """
exercise_id: bad
display_name: Bad
version: 0.0.1
classification:
  family: lower_body
  posture_type: standing
  kinetic_chain: closed_chain
  laterality: bilateral_symmetric
  primary_plane: sagittal
phase_model:
  type: cyclic
landmarks:
  model: mediapipe_pose_33
compensation_patterns: []
feature_domains:
  spatial: []
  temporal: []
  control: []
quality_rules: {}
performance_protocol:
  prescription:
    target_sets: 3
    target_count_per_set: 10
    count_unit: repetition
    segmentation_reps_per_count: 1
  counting:
    target_count: 8
    count_unit: repetition
    segmentation_reps_per_count: 1
  side_sequence:
    mode: none
    block_size_counts: null
  completion:
    allow_partial_completion: false
    recommended_sets: 3
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="target_count"):
        load_exercise_definition("bad", tmp_path)


def test_performance_prescription_validates_rest_range(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        """
exercise_id: bad
display_name: Bad
version: 0.0.1
classification:
  family: lower_body
  posture_type: standing
  kinetic_chain: closed_chain
  laterality: bilateral_symmetric
  primary_plane: sagittal
phase_model:
  type: cyclic
landmarks:
  model: mediapipe_pose_33
compensation_patterns: []
feature_domains:
  spatial: []
  temporal: []
  control: []
quality_rules: {}
performance_protocol:
  prescription:
    target_sets: 3
    target_count_per_set: 10
    count_unit: repetition
    segmentation_reps_per_count: 1
    rest_between_sets_s: [180, 120]
  side_sequence:
    mode: none
    block_size_counts: null
  completion:
    allow_partial_completion: false
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rest_between_sets_s"):
        load_exercise_definition("bad", tmp_path)


def test_allowed_side_sequence_modes_reject_unknown_mode(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        """
exercise_id: bad
display_name: Bad
version: 0.0.1
classification:
  family: lower_body
  posture_type: standing
  kinetic_chain: closed_chain
  laterality: alternating
  primary_plane: sagittal
phase_model:
  type: cyclic
landmarks:
  model: mediapipe_pose_33
compensation_patterns: []
feature_domains:
  spatial: []
  temporal: []
  control: []
quality_rules: {}
performance_protocol:
  counting:
    target_count: 10
    count_unit: repetition
    segmentation_reps_per_count: 1
  side_sequence:
    mode: alternating_each_rep
    block_size_counts: null
  allowed_side_sequence_modes: [alternating_each_rep, zigzag]
  completion:
    allow_partial_completion: false
    recommended_sets: 1
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="allowed_side_sequence_modes"):
        load_exercise_definition("bad", tmp_path)


def test_selected_side_sequence_mode_must_be_allowed(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        """
exercise_id: bad
display_name: Bad
version: 0.0.1
classification:
  family: lower_body
  posture_type: standing
  kinetic_chain: closed_chain
  laterality: alternating
  primary_plane: sagittal
phase_model:
  type: cyclic
landmarks:
  model: mediapipe_pose_33
compensation_patterns: []
feature_domains:
  spatial: []
  temporal: []
  control: []
quality_rules: {}
performance_protocol:
  counting:
    target_count: 10
    count_unit: repetition
    segmentation_reps_per_count: 1
  side_sequence:
    mode: alternating_each_rep
    block_size_counts: null
  allowed_side_sequence_modes: [none]
  completion:
    allow_partial_completion: false
    recommended_sets: 1
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="side_sequence.mode"):
        load_exercise_definition("bad", tmp_path)
