from pathlib import Path

import pytest

from movement.io import load_participant_profile_yaml


def test_load_p01_participant_profile_yaml():
    profile = load_participant_profile_yaml(
        Path("data/participants/no_consent/p01.yaml")
    )

    assert profile["participant_id"] == "p01"
    assert profile["anthropometry"]["sex"] == "male"
    assert profile["anthropometry"]["height_bin"] == "171-175cm"
    assert profile["common_subject_skeleton"]["profile_id"] == "male_175cm"
    assert profile["policy"]["used_for_scoring"] is False
    assert profile["policy"]["coordinate_rescale_from_height"] is False


def test_participant_profile_rejects_direct_identifier_policy(tmp_path: Path):
    profile_path = tmp_path / "participant.yaml"
    profile_path.write_text(
        "\n".join(
            [
                "participant_profile:",
                '  schema_version: "0.1.0"',
                "  participant_id: p_test",
                "  policy:",
                "    contains_direct_identifiers: true",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="direct identifiers"):
        load_participant_profile_yaml(profile_path)
