from __future__ import annotations

import pandas as pd

from movement.exercise_definition import load_exercise_definition
from movement.motion_attribution import attribute_motion


DEFINITIONS_DIR = "data/definitions/exercises"


def _motion_rows(
    *,
    sequence: list[str],
    exercise_id: str,
    starting_side: str,
    moving_landmark: str,
    protocol_cycle_ids: list[int] | None = None,
    rep_unit: str | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    frame = 0
    left_landmark = f"left_{moving_landmark}"
    right_landmark = f"right_{moving_landmark}"

    for rep_index, moving_side in enumerate(sequence):
        rep_id = rep_index + 1
        for step in range(3):
            row: dict[str, object] = {
                "frame": frame,
                "segment_type": "rep",
                "rep_id": rep_id,
                "exercise_id": exercise_id,
                "execution_pattern": "bilateral",
                "starting_side": starting_side,
                f"{left_landmark}_x": 0.0,
                f"{left_landmark}_y": 0.0,
                f"{left_landmark}_z": 0.0,
                f"{right_landmark}_x": 0.0,
                f"{right_landmark}_y": 0.0,
                f"{right_landmark}_z": 0.0,
            }
            row[f"{moving_side}_{moving_landmark}_x"] = float(step)
            if protocol_cycle_ids is not None:
                row["protocol_cycle_id"] = protocol_cycle_ids[rep_index]
            if rep_unit is not None:
                row["rep_unit"] = rep_unit
            rows.append(row)
            frame += 1

    return pd.DataFrame(rows)


def _per_rep_values(df: pd.DataFrame, column: str) -> list[object]:
    return [
        group[column].dropna().iloc[0] for _, group in df.groupby("rep_id", sort=True)
    ]


def test_lunge_uses_same_side_block_performance_protocol():
    definition = load_exercise_definition("lunge", DEFINITIONS_DIR)
    sequence = ["right"] * 5 + ["left"] * 5
    df = _motion_rows(
        sequence=sequence,
        exercise_id="lunge",
        starting_side="right",
        moving_landmark="knee",
    )

    attributed, report = attribute_motion(df, definition)

    assert _per_rep_values(attributed, "expected_active_limb") == sequence
    assert report.performance_side_sequence == {
        "mode": "same_side_block_then_switch",
        "block_size_counts": 5,
        "first_side_source": "annotation.starting_side",
    }
    assert report.expected_side_source == "performance_protocol.side_sequence"
    assert report.exercise_id == "lunge"
    assert report.execution_pattern == "bilateral"
    assert report.num_consistent == 10


def test_lunge_reports_observed_side_sequence_mismatch_as_warning_only():
    definition = load_exercise_definition("lunge", DEFINITIONS_DIR)
    sequence = ["right"] * 5 + ["left"] * 5
    df = _motion_rows(
        sequence=sequence,
        exercise_id="lunge",
        starting_side="right",
        moving_landmark="knee",
    )
    df.loc[df["rep_id"] == 1, "rep_side_sequence"] = "left"

    _, report = attribute_motion(df, definition)

    assert report.side_sequence_warnings == [
        {
            "rep_id": 1,
            "observed": "left",
            "expected": "right",
            "policy": "warning_only",
        }
    ]
    assert report.num_consistent == 10


def test_plank_shoulder_tap_preserves_protocol_cycles_and_alternates_each_tap():
    definition = load_exercise_definition("plank_shoulder_tap", DEFINITIONS_DIR)
    sequence = ["left", "right", "left", "right"]
    df = _motion_rows(
        sequence=sequence,
        exercise_id="plank_shoulder_tap",
        starting_side="left",
        moving_landmark="wrist",
        protocol_cycle_ids=[1, 1, 2, 2],
        rep_unit="tap",
    )

    attributed, report = attribute_motion(df, definition)

    assert _per_rep_values(attributed, "expected_active_limb") == sequence
    assert _per_rep_values(attributed, "protocol_cycle_id") == [1, 1, 2, 2]
    assert _per_rep_values(attributed, "rep_unit") == ["tap", "tap", "tap", "tap"]
    assert report.performance_side_sequence["mode"] == "alternating_each_rep"
    assert definition.performance_protocol.counting.count_unit == "left_right_pair"
    assert definition.performance_protocol.counting.segmentation_reps_per_count == 2
