"""
tests/test_fms_mapping.py

Unit tests for the FMS-like clinical crosswalk:
    - YAML coverage for four exercises
    - traffic-light conversion from BiomarkerScoreRecord-like inputs
    - forbidden clinical-assertion vocabulary guard
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pytest

from movement.clinical import load_fms_mapping, traffic_light_for_score


_MAPPING_PATH = Path(__file__).resolve().parent.parent / "data" / "clinical" / "fms_mapping.yaml"
_EXERCISES = ("squat", "lunge", "pike_pushup", "plank_shoulder_tap")


@dataclass
class _Score:
    exercise_id: str
    final_score: float


def test_load_fms_mapping_covers_four_exercises():
    mapping = load_fms_mapping(_MAPPING_PATH)
    assert set(_EXERCISES).issubset(mapping.keys())


def test_each_exercise_has_minimum_criteria_and_references():
    mapping = load_fms_mapping(_MAPPING_PATH)
    for exercise_id in _EXERCISES:
        item = mapping[exercise_id]
        assert len(item.linked_criteria) >= 3
        assert item.references
        assert {"green", "yellow", "red"} == set(item.traffic_light_mapping.keys())
        for criterion in item.linked_criteria:
            assert criterion.id
            assert criterion.domain in {"spatial", "temporal", "control", "biomech"}
            assert criterion.feature_id_prefix
            assert criterion.rationale


@pytest.mark.parametrize(
    ("score", "expected"),
    [(92.0, "green"), (77.0, "yellow"), (60.0, "red")],
)
def test_traffic_light_for_numeric_score(score, expected):
    label = traffic_light_for_score(score, "squat", mapping_path=_MAPPING_PATH)
    assert label.label == expected
    assert label.exercise_id == "squat"
    assert any("fms_mapping.yaml" in sf for sf in label.source_fields)


def test_traffic_light_accepts_score_record_like_object():
    label = traffic_light_for_score(
        _Score(exercise_id="plank_shoulder_tap", final_score=84.5),
        mapping_path=_MAPPING_PATH,
    )
    assert label.label == "yellow"
    assert label.meaning == "mild_alignment_or_control_issue"


def test_score_is_clipped_to_project_range():
    label = traffic_light_for_score(130.0, "lunge", mapping_path=_MAPPING_PATH)
    assert label.label == "green"
    assert label.score == 100.0


def test_missing_exercise_raises_key_error():
    with pytest.raises(KeyError):
        traffic_light_for_score(90.0, "unknown_exercise", mapping_path=_MAPPING_PATH)


def test_mapping_avoids_forbidden_assertion_vocabulary():
    text = _MAPPING_PATH.read_text(encoding="utf-8")
    forbidden = re.compile(
        r"clinically significant|clinically meaningful|diagnos(?:is|tic|e)|patient classification",
        re.IGNORECASE,
    )
    assert forbidden.search(text) is None
