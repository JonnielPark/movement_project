import math

import numpy as np
import pandas as pd

from movement.floor_reference import (
    FloorReferenceConfig,
    apply_floor_relative_correction,
)


LANDMARKS = [
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]


def _sample_floor_df() -> pd.DataFrame:
    rows = []
    x_values = [-0.3, 0.3, -0.2, 0.2]
    z_values = [0.0, 0.0, 0.25, 0.3]
    for frame in range(5):
        row = {"frame": frame, "timestamp": frame / 30.0}
        for idx, landmark in enumerate(LANDMARKS):
            x = x_values[idx]
            z = z_values[idx]
            y = 0.2 + 0.1 * x + 0.2 * z
            row[f"{landmark}_norm_x"] = x
            row[f"{landmark}_norm_y"] = y
            row[f"{landmark}_norm_z"] = z
            row[f"{landmark}_visibility"] = 0.99
        rows.append(row)
    return pd.DataFrame(rows)


def test_disabled_floor_relative_correction_preserves_columns():
    df = _sample_floor_df()

    out, report = apply_floor_relative_correction(
        df=df,
        landmarks=LANDMARKS,
        config=FloorReferenceConfig(enabled=False),
    )

    assert report.status == "disabled"
    assert out is not df
    assert "left_heel_floor_y" not in out.columns
    assert list(out.columns) == list(df.columns)


def test_floor_relative_correction_adds_floor_columns_and_report():
    df = _sample_floor_df()

    out, report = apply_floor_relative_correction(
        df=df,
        landmarks=LANDMARKS,
        config=FloorReferenceConfig(
            enabled=True,
            support_landmarks=LANDMARKS,
            diagnostic_landmarks=["left_heel", "right_heel"],
        ),
    )

    assert report.status == "applied"
    assert report.num_anchor_points > 0
    assert {"b0", "bx", "bz"}.issubset(report.plane_coefficients)
    assert {"b0", "bx", "bz"}.issubset(report.target_plane_coefficients)
    assert report.correction_transform == "rigid_rotation"
    assert report.camera_pitch_deg == 0.0
    assert report.camera_roll_deg == 0.0
    assert "left_heel_floor_y" in out.columns
    assert "left_heel_floor_height" in out.columns
    assert "right_heel_floor_height" in out.columns
    assert "left_heel_norm_y" in out.columns


def test_floor_relative_correction_skips_when_anchors_are_missing():
    df = _sample_floor_df().drop(columns=["left_heel_norm_x", "left_heel_norm_y"])

    out, report = apply_floor_relative_correction(
        df=df,
        landmarks=["right_heel"],
        config=FloorReferenceConfig(
            enabled=True,
            support_landmarks=["left_heel"],
            diagnostic_landmarks=["left_heel"],
        ),
    )

    assert report.status == "skipped"
    assert "right_heel_floor_y" not in out.columns


def test_camera_angle_prior_preserves_matching_target_floor_slope():
    df = _sample_floor_df()

    out, report = apply_floor_relative_correction(
        df=df,
        landmarks=LANDMARKS,
        config=FloorReferenceConfig(
            enabled=True,
            support_landmarks=LANDMARKS,
            diagnostic_landmarks=["left_heel"],
            camera_roll_deg=math.degrees(math.atan(0.1)),
            camera_pitch_deg=math.degrees(math.atan(0.2)),
        ),
    )

    assert report.status == "applied"
    assert abs(report.target_plane_coefficients["bx"] - 0.1) < 1e-12
    assert abs(report.target_plane_coefficients["bz"] - 0.2) < 1e-12
    for landmark in LANDMARKS:
        delta = out[f"{landmark}_floor_y"] - out[f"{landmark}_norm_y"]
        assert float(delta.abs().max()) < 1e-12


def test_vertical_shear_mode_preserves_legacy_y_only_correction():
    df = _sample_floor_df()

    out, report = apply_floor_relative_correction(
        df=df,
        landmarks=LANDMARKS,
        config=FloorReferenceConfig(
            enabled=True,
            support_landmarks=LANDMARKS,
            diagnostic_landmarks=["left_heel"],
            correction_transform="vertical_shear",
        ),
    )

    assert report.status == "applied"
    assert report.correction_transform == "vertical_shear"
    for landmark in LANDMARKS:
        assert out[f"{landmark}_floor_x"].equals(out[f"{landmark}_norm_x"])
        assert out[f"{landmark}_floor_z"].equals(out[f"{landmark}_norm_z"])


def test_rigid_rotation_aligns_floor_normal_and_preserves_segment_length():
    df = _sample_floor_df()

    out, report = apply_floor_relative_correction(
        df=df,
        landmarks=LANDMARKS,
        config=FloorReferenceConfig(
            enabled=True,
            support_landmarks=LANDMARKS,
            diagnostic_landmarks=["left_heel"],
            correction_transform="rigid_rotation",
        ),
    )

    assert report.status == "applied"
    assert report.correction_transform == "rigid_rotation"

    before = df[["left_heel_norm_x", "left_heel_norm_y", "left_heel_norm_z"]].to_numpy()
    before_other = df[
        ["right_heel_norm_x", "right_heel_norm_y", "right_heel_norm_z"]
    ].to_numpy()
    after = out[
        ["left_heel_floor_x", "left_heel_floor_y", "left_heel_floor_z"]
    ].to_numpy()
    after_other = out[
        ["right_heel_floor_x", "right_heel_floor_y", "right_heel_floor_z"]
    ].to_numpy()
    before_distance = np.linalg.norm(before - before_other, axis=1)
    after_distance = np.linalg.norm(after - after_other, axis=1)
    assert np.max(np.abs(before_distance - after_distance)) < 1e-12

    floor_points = []
    for landmark in LANDMARKS:
        floor_points.append(
            out[
                [
                    f"{landmark}_floor_x",
                    f"{landmark}_floor_y",
                    f"{landmark}_floor_z",
                ]
            ].to_numpy()
        )
    floor_points = np.concatenate(floor_points, axis=0)
    design = np.column_stack(
        [np.ones(len(floor_points)), floor_points[:, 0], floor_points[:, 2]]
    )
    coeffs, *_ = np.linalg.lstsq(design, floor_points[:, 1], rcond=None)
    assert abs(float(coeffs[1])) < 1e-12
    assert abs(float(coeffs[2])) < 1e-12
