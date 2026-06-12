import pandas as pd

from movement.stages.validation import run_basic_validation


def _minimal_pose_df(visibility: list[float]) -> pd.DataFrame:
    n = len(visibility)
    return pd.DataFrame(
        {
            "frame": list(range(n)),
            "timestamp": [i / 30.0 for i in range(n)],
            "nose_x": [0.1] * n,
            "nose_y": [0.2] * n,
            "nose_z": [0.3] * n,
            "nose_visibility": visibility,
        }
    )


def test_low_visibility_is_warning_not_blocking_validation():
    df = _minimal_pose_df([0.1] * 10)

    report = run_basic_validation(
        df=df,
        required_columns=["frame", "timestamp", "nose_x", "nose_y", "nose_z"],
        coordinate_columns=["nose_x", "nose_y", "nose_z"],
        visibility_columns=["nose_visibility"],
    )

    assert report["structural_passed"] is True
    assert report["passed"] is True
    assert report["visibility"]["passed"] is False
    assert report["visibility"]["severity"] == "warning"
    assert report["visibility"]["policy"] == "warning_provenance_only"
    assert report["warnings"] == [
        {
            "check": "visibility",
            "severity": "warning",
            "policy": "warning_provenance_only",
            "message": "Low or unavailable visibility is handled by downstream reliability gates.",
        }
    ]


def test_structural_failure_still_blocks_validation():
    df = _minimal_pose_df([0.9] * 10).drop(columns=["nose_z"])

    report = run_basic_validation(
        df=df,
        required_columns=["frame", "timestamp", "nose_x", "nose_y", "nose_z"],
        coordinate_columns=["nose_x", "nose_y"],
        visibility_columns=["nose_visibility"],
    )

    assert report["required_columns"]["passed"] is False
    assert report["structural_passed"] is False
    assert report["passed"] is False
