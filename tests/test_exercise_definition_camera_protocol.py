from pathlib import Path

import pandas as pd
import pytest
import yaml

from movement.exercise_definition import load_exercise_definition
from movement.pipeline import (
    ExerciseDefinitionConfig,
    NormalizationConfig,
    PipelineConfig,
    ValidationConfig,
    run_pipeline,
)


DEFINITIONS_DIR = Path("data/definitions/exercises")


def _write_modified_squat(tmp_path: Path, **camera_updates: object) -> None:
    raw = yaml.safe_load((DEFINITIONS_DIR / "squat.yaml").read_text(encoding="utf-8"))
    raw["exercise_id"] = "bad"
    raw["camera_protocol"].update(camera_updates)
    (tmp_path / "bad.yaml").write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )


def test_squat_loads_camera_protocol():
    definition = load_exercise_definition("squat", DEFINITIONS_DIR)

    protocol = definition.camera_protocol

    assert protocol is not None
    assert protocol.recommended_zones == ["Z2", "Z8"]
    assert protocol.recommended_height == "H2"
    assert protocol.anchor == "reference_mat"
    assert protocol.distance_cm == [200, 250]
    assert "knee_valgus" in protocol.primary_observation_purpose
    assert protocol.out_of_zone_policy == "warn_and_continue"
    assert protocol.coordinate_correction == "none"


def test_generic_definition_keeps_camera_protocol_optional():
    definition = load_exercise_definition("generic", DEFINITIONS_DIR)

    assert definition.camera_protocol is None


def test_unknown_recommended_camera_zone_is_rejected(tmp_path):
    _write_modified_squat(tmp_path, recommended_zones=["Z2", "Z99"])

    with pytest.raises(ValueError, match="recommended_zones"):
        load_exercise_definition("bad", tmp_path)


def test_unknown_recommended_camera_height_is_rejected(tmp_path):
    _write_modified_squat(tmp_path, recommended_height="H99")

    with pytest.raises(ValueError, match="recommended_height"):
        load_exercise_definition("bad", tmp_path)


def test_out_of_zone_policy_must_warn_and_continue(tmp_path):
    _write_modified_squat(tmp_path, out_of_zone_policy="reject")

    with pytest.raises(ValueError, match="out_of_zone_policy"):
        load_exercise_definition("bad", tmp_path)


def test_pipeline_reports_camera_zone_mismatch_without_exclusion():
    df = pd.DataFrame(
        {
            "frame": [0, 1],
            "camera_zone": ["Z3", "Z3"],
            "camera_height_level": ["H2", "H2"],
        }
    )
    config = PipelineConfig(
        validation=ValidationConfig(enabled=False),
        normalization=NormalizationConfig(enabled=False),
        exercise_definition=ExerciseDefinitionConfig(
            enabled=True,
            exercise_id="squat",
        ),
    )

    with pytest.warns(UserWarning, match="camera_zone outside recommended_zones"):
        _, report = run_pipeline(df, config)

    filming = report["exercise_definition"]["filming_condition"]
    assert filming["recommended_zones"] == ["Z2", "Z8"]
    assert filming["observed_zones"] == ["Z3"]
    assert filming["zone_match"] is False
    assert filming["height_match"] is True
    assert filming["forced_exclusion"] is False
    assert filming["coordinate_correction"] == "none"
    assert filming["warnings"]
