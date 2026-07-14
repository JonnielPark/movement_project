from pathlib import Path

import yaml

from movement.exercise_definition import (
    load_exercise_context,
    load_exercise_session_definition,
)


DEFINITIONS_DIR = "data/definitions/exercises"
SESSIONS_DIR = "data/definitions/exercise_sessions"
ANALYSIS_PROFILE_PATH = Path(
    "data/definitions/analysis_profiles/korean_national_gymnastics.yaml"
)

EXPECTED_KNG_BLOCKS = [
    ("01_breathing_start", "korean_national_gymnastics_breathing_start", "숨쉬기", 1),
    ("02_leg", "korean_national_gymnastics_leg", "다리운동", 2),
    ("03_arm", "korean_national_gymnastics_arm", "팔운동", 3),
    ("04_neck", "korean_national_gymnastics_neck", "목운동", 4),
    ("05_chest", "korean_national_gymnastics_chest", "가슴운동", 5),
    ("06_side", "korean_national_gymnastics_side", "옆구리운동", 6),
    ("07_back_abdomen", "korean_national_gymnastics_back_abdomen", "등배운동", 7),
    ("08_trunk", "korean_national_gymnastics_trunk", "몸통운동", 8),
    ("09_whole_body", "korean_national_gymnastics_whole_body", "온몸운동", 9),
    ("10_jumping", "korean_national_gymnastics_jumping", "뜀뛰기", 10),
    ("11_limbs", "korean_national_gymnastics_limbs", "팔다리운동", 11),
    (
        "12_breathing_cooldown",
        "korean_national_gymnastics_breathing_cooldown",
        "숨고르기",
        12,
    ),
]


def test_korean_national_gymnastics_session_uses_repeat_pass_analysis_order():
    session = load_exercise_session_definition(
        "korean_national_gymnastics",
        SESSIONS_DIR,
    )

    assert session.exercise_session_id == "korean_national_gymnastics"
    assert session.rest_policy.rest_between_blocks_s == 0
    assert session.rest_policy.per_block_override_allowed is False
    scope = session.raw["acquisition_and_analysis_scope"]
    assert scope["starts_from"] == "repeated_sequence"
    assert scope["initial_pass_policy"] == "not_acquired"
    assert [
        (block.block_id, block.exercise_id, block.raw["section_name_ko"])
        for block in session.blocks
    ] == [
        (block_id, exercise_id, section_name_ko)
        for block_id, exercise_id, section_name_ko, _ in EXPECTED_KNG_BLOCKS
    ]


def test_korean_national_gymnastics_section_definitions_are_loadable_drafts():
    for _, exercise_id, section_name_ko, conventional_order in EXPECTED_KNG_BLOCKS:
        context = load_exercise_context(exercise_id, DEFINITIONS_DIR)
        definition = context.exercise_definition

        assert context.is_split_source is True
        assert context.exercise_identity["status"] == "draft"
        assert context.exercise_identity["section_order"] == conventional_order
        assert context.exercise_identity["section_name_ko"] == section_name_ko
        assert context.exercise_identity["analysis_profile_ref"] == {
            "profile_file_id": "korean_national_gymnastics",
            "profile_id": exercise_id,
        }
        assert (
            context.source_paths["analysis_profile"].as_posix()
            == "data/definitions/analysis_profiles/korean_national_gymnastics.yaml"
        )
        assert context.analysis_profile["exercise_id"] == exercise_id
        assert definition.exercise_id == exercise_id
        assert definition.is_generic_fallback is False
        assert definition.landmarks.model == "mediapipe_pose_33"


def test_korean_national_gymnastics_analysis_profile_file_uses_index():
    profile_file = yaml.safe_load(ANALYSIS_PROFILE_PATH.read_text(encoding="utf-8"))
    expected_index = [
        {
            "profile_id": exercise_id,
            "section_order": conventional_order,
            "section_name_ko": section_name_ko,
        }
        for _, exercise_id, section_name_ko, conventional_order in EXPECTED_KNG_BLOCKS
    ]

    assert profile_file["analysis_profile_id"] == "korean_national_gymnastics"
    assert profile_file["index"] == expected_index
    assert set(profile_file["profiles"]) == {
        item["profile_id"] for item in expected_index
    }


def test_korean_national_gymnastics_sections_use_frontal_waist_camera_protocol():
    for _, exercise_id, _, _ in EXPECTED_KNG_BLOCKS:
        context = load_exercise_context(exercise_id, DEFINITIONS_DIR)
        camera_protocol = context.camera_protocol["camera_protocol"]
        definition = context.exercise_definition

        assert "camera_protocol" not in context.exercise_identity["requires_review"]
        assert (
            context.source_paths["camera_protocol"].as_posix()
            == "data/protocols/camera/korean_national_gymnastics.yaml"
        )
        assert (
            context.camera_protocol["camera_protocol_id"]
            == "korean_national_gymnastics"
        )
        assert camera_protocol["recommended_zones"] == ["Z1"]
        assert camera_protocol["recommended_height"] == "H2"
        assert definition.camera_protocol is not None
        assert definition.camera_protocol.recommended_zones == ["Z1"]
        assert definition.camera_protocol.recommended_height == "H2"
