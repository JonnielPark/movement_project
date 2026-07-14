import pytest

from movement.exercise_definition import load_exercise_session_definition


SESSIONS_DIR = "data/definitions/exercise_sessions"


def test_example_sequence_loads_uniform_rest_policy():
    session = load_exercise_session_definition("example_sequence", SESSIONS_DIR)

    assert session.exercise_session_id == "example_sequence"
    assert session.rest_policy.rest_between_blocks_s == 120
    assert session.rest_policy.per_block_override_allowed is False
    assert [block.exercise_id for block in session.blocks] == ["squat", "lunge"]
    assert [block.repeat_count for block in session.blocks] == [1, 1]


def test_session_definition_rejects_per_block_rest_override(tmp_path):
    yaml_path = tmp_path / "bad_session.yaml"
    yaml_path.write_text(
        """
exercise_session_id: bad_session
version: 0.1.0
rest_policy:
  rest_between_blocks_s: 120
  per_block_override_allowed: false
blocks:
  - block_id: squat_example
    exercise_id: squat
    repeat_count: 1
    rest_after_block_s: 30
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="per-block rest overrides"):
        load_exercise_session_definition("bad_session", tmp_path)


def test_session_definition_rejects_enabled_per_block_rest_policy(tmp_path):
    yaml_path = tmp_path / "bad_session.yaml"
    yaml_path.write_text(
        """
exercise_session_id: bad_session
version: 0.1.0
rest_policy:
  rest_between_blocks_s: 120
  per_block_override_allowed: true
blocks:
  - block_id: squat_example
    exercise_id: squat
    repeat_count: 1
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must remain false"):
        load_exercise_session_definition("bad_session", tmp_path)


def test_session_definition_rejects_invalid_rest_seconds(tmp_path):
    yaml_path = tmp_path / "bad_session.yaml"
    yaml_path.write_text(
        """
exercise_session_id: bad_session
version: 0.1.0
rest_policy:
  rest_between_blocks_s: -1
  per_block_override_allowed: false
blocks:
  - block_id: squat_example
    exercise_id: squat
    repeat_count: 1
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-negative integer"):
        load_exercise_session_definition("bad_session", tmp_path)


def test_session_definition_rejects_duplicate_block_id(tmp_path):
    yaml_path = tmp_path / "bad_session.yaml"
    yaml_path.write_text(
        """
exercise_session_id: bad_session
version: 0.1.0
rest_policy:
  rest_between_blocks_s: 120
  per_block_override_allowed: false
blocks:
  - block_id: repeated
    exercise_id: squat
    repeat_count: 1
  - block_id: repeated
    exercise_id: lunge
    repeat_count: 1
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicated"):
        load_exercise_session_definition("bad_session", tmp_path)


def test_session_definition_rejects_empty_blocks(tmp_path):
    yaml_path = tmp_path / "bad_session.yaml"
    yaml_path.write_text(
        """
exercise_session_id: bad_session
version: 0.1.0
rest_policy:
  rest_between_blocks_s: 120
  per_block_override_allowed: false
blocks: []
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-empty list"):
        load_exercise_session_definition("bad_session", tmp_path)
