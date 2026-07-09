import pandas as pd

from movement.stages.validation import harmonize_pose_schema, run_basic_validation


def _minimal_pose_df(confidence: list[float]) -> pd.DataFrame:
    n = len(confidence)
    return pd.DataFrame(
        {
            "frame": list(range(n)),
            "timestamp": [i / 30.0 for i in range(n)],
            "nose_x": [0.1] * n,
            "nose_y": [0.2] * n,
            "nose_z": [0.3] * n,
            "nose_confidence": confidence,
        }
    )


def test_low_confidence_is_warning_not_blocking_validation():
    df = _minimal_pose_df([0.1] * 10)

    report = run_basic_validation(
        df=df,
        required_columns=["frame", "timestamp", "nose_x", "nose_y", "nose_z"],
        coordinate_columns=["nose_x", "nose_y", "nose_z"],
        confidence_columns=["nose_confidence"],
    )

    assert report["structural_passed"] is True
    assert report["passed"] is True
    assert report["confidence"]["passed"] is False
    assert report["confidence"]["severity"] == "warning"
    assert report["confidence"]["policy"] == "warning_provenance_only"
    assert report["warnings"] == [
        {
            "check": "confidence",
            "severity": "warning",
            "policy": "warning_provenance_only",
            "message": "Low or unavailable landmark confidence is handled by downstream reliability gates.",
        }
    ]


def test_structural_failure_still_blocks_validation():
    df = _minimal_pose_df([0.9] * 10).drop(columns=["nose_z"])

    report = run_basic_validation(
        df=df,
        required_columns=["frame", "timestamp", "nose_x", "nose_y", "nose_z"],
        coordinate_columns=["nose_x", "nose_y"],
        confidence_columns=["nose_confidence"],
    )

    assert report["required_columns"]["passed"] is False
    assert report["structural_passed"] is False
    assert report["passed"] is False


def test_harmonize_pose_schema_adds_nan_z_placeholders_for_xy_input():
    df = pd.DataFrame(
        {
            "frame": [0, 1],
            "timestamp": [0.0, 1.0 / 30.0],
            "left_hip_x": [0.0, 0.1],
            "left_hip_y": [0.0, 0.1],
            "right_hip_x": [1.0, 1.1],
            "right_hip_y": [0.0, 0.1],
        }
    )

    out, report = harmonize_pose_schema(
        df,
        landmarks=["left_hip", "right_hip"],
        coordinate_axes="auto",
    )

    assert report["coordinate_shape"] == ["x", "y", "z"]
    assert report["observed_axes"] == ["x", "y"]
    assert report["validation_axes"] == ["x", "y"]
    assert report["z_source"] == "absent"
    assert report["z_fill_policy"] == "nan_placeholder"
    assert report["z_evaluable"] is False
    assert report["added_z_columns"] == ["left_hip_z", "right_hip_z"]
    assert out.attrs["coordinate_shape"]["raw"] == ["x", "y", "z"]
    assert out.attrs["observed_coordinate_axes"]["raw"] == ["x", "y"]
    assert out["left_hip_z"].isna().all()
    assert out["right_hip_z"].isna().all()


def test_harmonize_pose_schema_maps_backend_confidence_alias_to_confidence():
    df = pd.DataFrame(
        {
            "frame": [0, 1],
            "timestamp": [0.0, 1.0 / 30.0],
            "nose_x": [0.1, 0.2],
            "nose_y": [0.2, 0.3],
            "nose_z": [0.3, 0.4],
            "nose_visibility": [0.9, 0.8],
        }
    )

    out, report = harmonize_pose_schema(df, landmarks=["nose"])

    assert "nose_confidence" in out.columns
    assert "nose_visibility" not in out.columns
    assert out["nose_confidence"].to_list() == [0.9, 0.8]
    assert report["confidence_schema"]["mapped_backend_alias_columns"] == [
        {
            "backend_alias": "nose_visibility",
            "canonical_column": "nose_confidence",
        }
    ]
    assert report["confidence_schema"]["dropped_backend_alias_columns"] == [
        "nose_visibility"
    ]
