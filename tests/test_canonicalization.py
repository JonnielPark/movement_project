import math
from pathlib import Path

import numpy as np
import pandas as pd

from movement.canonicalization import (
    CanonicalizationConfig,
    MovementPlaneAlignmentConfig,
    ProtocolHeightLateralWidthAlignmentConfig,
    apply_canonicalization,
)
from movement.config import CONNECTIONS
from movement.core.utils import get_coord_columns
from movement.floor_reference import FloorReferenceConfig
from movement.pipeline import (
    ExerciseDefinitionConfig,
    NormalizationConfig,
    PipelineConfig,
    ValidationConfig,
    load_pipeline_config,
    run_pipeline,
)
from movement.visualization import create_pose_animation


LANDMARKS = [
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]

MOVEMENT_LANDMARKS = [
    "left_hip",
    "left_knee",
    "left_ankle",
    "right_hip",
    "right_knee",
    "right_ankle",
]

PROTOCOL_HEIGHT_LANDMARKS = [
    "left_hip",
    "right_hip",
    "left_wrist",
    "right_wrist",
]


def _sample_norm_df() -> pd.DataFrame:
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


def _sample_movement_plane_df() -> pd.DataFrame:
    rows = []
    base = {
        "left_hip": (-0.12, 0.9, 0.0),
        "right_hip": (0.12, 0.9, 0.0),
        "left_knee": (-0.11, 0.45, 0.18),
        "right_knee": (0.11, 0.45, 0.18),
        "left_ankle": (-0.10, 0.0, 0.34),
        "right_ankle": (0.10, 0.0, 0.34),
    }
    for frame, step in enumerate(np.linspace(-0.5, 0.5, 9)):
        row = {"frame": frame, "timestamp": frame / 30.0}
        for landmark, (base_x, base_y, base_z) in base.items():
            lower_limb_motion = 0.0 if landmark.endswith("hip") else step
            row[f"{landmark}_norm_x"] = base_x + 0.20 * lower_limb_motion
            row[f"{landmark}_norm_y"] = base_y - 0.10 * abs(step)
            row[f"{landmark}_norm_z"] = base_z + 0.40 * lower_limb_motion
            row[f"{landmark}_visibility"] = 0.99
        rows.append(row)
    return pd.DataFrame(rows)


def _sample_protocol_height_df() -> pd.DataFrame:
    rows = []
    base = {
        "left_hip": (-0.20, 0.90, 0.0),
        "right_hip": (0.20, 0.90, 0.0),
        "left_wrist": (-1.00, 0.90, -0.40),
        "right_wrist": (0.60, 0.90, 0.40),
    }
    for frame in range(3):
        row = {
            "frame": frame,
            "timestamp": frame / 30.0,
            "camera_height_level": "H2",
        }
        for landmark, (x, y, z) in base.items():
            row[f"{landmark}_norm_x"] = x
            row[f"{landmark}_norm_y"] = y
            row[f"{landmark}_norm_z"] = z
            row[f"{landmark}_visibility"] = 0.99
        rows.append(row)
    return pd.DataFrame(rows)


def test_disabled_canonicalization_preserves_dataframe_without_canon_columns():
    df = _sample_norm_df()

    out, report = apply_canonicalization(
        df,
        landmarks=LANDMARKS,
        config=CanonicalizationConfig(enabled=False),
    )

    assert report["status"] == "disabled"
    assert report["candidate_available"] is False
    assert report["candidate_confidence"] == "not_available"
    assert report["burden_level"] == "none"
    assert "score_gravity" not in report
    assert "score_contribution_enabled" not in report
    assert out is not df
    assert list(out.columns) == list(df.columns)
    assert "left_heel_canon_y" not in out.columns


def test_canonicalization_wraps_support_plane_alignment_as_canon_columns():
    df = _sample_norm_df()

    out, report = apply_canonicalization(
        df,
        landmarks=LANDMARKS,
        config=CanonicalizationConfig(
            enabled=True,
            support_plane_alignment=FloorReferenceConfig(
                enabled=True,
                support_landmarks=LANDMARKS,
                diagnostic_landmarks=["left_heel", "right_heel"],
            ),
        ),
    )

    assert report["status"] == "applied"
    assert report["candidate_available"] is True
    assert report["candidate_confidence"] in {"high", "moderate", "low"}
    assert report["burden_level"] in {"none", "low", "moderate", "high"}
    assert report["applied_priors"] == ["support_plane_alignment"]
    assert report["prior_reports"]["support_plane_alignment"]["status"] == "applied"
    assert report["data_confidence"]["level"] in {"high", "moderate", "low"}
    assert "left_heel_norm_y" in out.columns
    assert "left_heel_canon_y" in out.columns
    assert "left_heel_floor_y" not in out.columns
    assert "left_heel_canon_support_plane_height" in out.columns
    assert out["canonicalization_candidate_available"].all()
    assert "canonicalization_score_gravity" not in out.columns
    assert "canonicalization_score_contribution_enabled" not in out.columns


def test_canonicalization_keeps_canon_equal_to_norm_when_target_prior_matches():
    df = _sample_norm_df()

    out, report = apply_canonicalization(
        df,
        landmarks=LANDMARKS,
        config=CanonicalizationConfig(
            enabled=True,
            support_plane_alignment=FloorReferenceConfig(
                enabled=True,
                support_landmarks=LANDMARKS,
                camera_roll_deg=math.degrees(math.atan(0.1)),
                camera_pitch_deg=math.degrees(math.atan(0.2)),
            ),
        ),
    )

    assert report["status"] == "applied"
    assert report["candidate_available"] is True
    for landmark in LANDMARKS:
        assert out[f"{landmark}_canon_y"].equals(out[f"{landmark}_norm_y"])


def test_movement_plane_alignment_rotates_primary_motion_toward_canon_plane():
    df = _sample_movement_plane_df()

    out, report = apply_canonicalization(
        df,
        landmarks=MOVEMENT_LANDMARKS,
        config=CanonicalizationConfig(
            enabled=True,
            movement_plane_alignment=MovementPlaneAlignmentConfig(
                enabled=True,
                fit_landmarks=MOVEMENT_LANDMARKS,
                correction_strength=1.0,
                max_rotation_deg=45.0,
            ),
        ),
    )

    movement_report = report["prior_reports"]["movement_plane_alignment"]
    assert report["status"] == "applied"
    assert report["candidate_available"] is True
    assert report["applied_priors"] == ["movement_plane_alignment"]
    assert movement_report["status"] == "applied"
    assert movement_report["num_motion_vectors"] > 0
    assert abs(movement_report["applied_rotation_deg"]) > 1.0
    assert (
        movement_report["out_of_plane_residual_ratio_after"]["max"]
        < movement_report["out_of_plane_residual_ratio_before"]["max"]
    )

    before_x_motion = df["left_knee_norm_x"].diff().abs().max()
    after_x_motion = out["left_knee_canon_x"].diff().abs().max()
    assert after_x_motion < before_x_motion
    assert out["canonicalization_valid"].all()


def test_movement_plane_alignment_preserves_segment_length_as_rigid_rotation():
    df = _sample_movement_plane_df()

    out, _ = apply_canonicalization(
        df,
        landmarks=MOVEMENT_LANDMARKS,
        config=CanonicalizationConfig(
            enabled=True,
            movement_plane_alignment=MovementPlaneAlignmentConfig(
                enabled=True,
                fit_landmarks=MOVEMENT_LANDMARKS,
                correction_strength=1.0,
                max_rotation_deg=45.0,
            ),
        ),
    )

    before_left = df[["left_knee_norm_x", "left_knee_norm_y", "left_knee_norm_z"]]
    before_right = df[["right_knee_norm_x", "right_knee_norm_y", "right_knee_norm_z"]]
    after_left = out[["left_knee_canon_x", "left_knee_canon_y", "left_knee_canon_z"]]
    after_right = out[
        ["right_knee_canon_x", "right_knee_canon_y", "right_knee_canon_z"]
    ]
    before_distance = np.linalg.norm(
        before_left.to_numpy() - before_right.to_numpy(),
        axis=1,
    )
    after_distance = np.linalg.norm(
        after_left.to_numpy() - after_right.to_numpy(),
        axis=1,
    )
    assert np.max(np.abs(before_distance - after_distance)) < 1e-12


def test_protocol_height_lateral_width_alignment_uses_h2_pelvis_anchor():
    df = _sample_protocol_height_df()

    out, report = apply_canonicalization(
        df,
        landmarks=PROTOCOL_HEIGHT_LANDMARKS,
        config=CanonicalizationConfig(
            enabled=True,
            protocol_height_lateral_width_alignment=(
                ProtocolHeightLateralWidthAlignmentConfig(
                    enabled=True,
                    recommended_height_level="H2",
                    correction_strength=0.5,
                    max_scale_change=0.20,
                    max_correction_torso=0.25,
                    min_depth_offset_torso=0.05,
                    visibility_threshold=0.0,
                )
            ),
        ),
    )

    protocol_report = report["prior_reports"]["protocol_height_lateral_width_alignment"]
    assert report["status"] == "applied"
    assert report["candidate_available"] is True
    assert report["candidate_confidence"] in {"high", "moderate", "low"}
    assert report["burden_level"] in {"none", "low", "moderate", "high"}
    assert report["applied_priors"] == ["protocol_height_lateral_width_alignment"]
    assert protocol_report["status"] == "applied"
    assert protocol_report["observed_height_level"] == "H2"
    assert protocol_report["recommended_height_level"] == "H2"
    assert protocol_report["height_match"] is True
    assert protocol_report["anchor_landmarks"] == ["left_hip", "right_hip"]
    assert protocol_report["num_corrected_values"] == len(df)
    assert protocol_report["num_far_side_report_only_values"] == len(df)

    assert (out["left_wrist_canon_x"] > df["left_wrist_norm_x"]).all()
    assert out["right_wrist_canon_x"].equals(df["right_wrist_norm_x"])
    assert out["left_hip_canon_x"].equals(df["left_hip_norm_x"])
    assert "canonicalization_lateral_width_scale_delta_frame" in out.columns


def test_protocol_height_lateral_width_alignment_skips_when_height_mismatches():
    df = _sample_protocol_height_df()

    out, report = apply_canonicalization(
        df,
        landmarks=PROTOCOL_HEIGHT_LANDMARKS,
        config=CanonicalizationConfig(
            enabled=True,
            protocol_height_lateral_width_alignment=(
                ProtocolHeightLateralWidthAlignmentConfig(
                    enabled=True,
                    recommended_height_level="H3",
                    require_height_match=True,
                    visibility_threshold=0.0,
                )
            ),
        ),
    )

    protocol_report = report["prior_reports"]["protocol_height_lateral_width_alignment"]
    assert report["status"] == "rejected"
    assert report["candidate_available"] is False
    assert report["candidate_confidence"] == "not_available"
    assert report["burden_level"] == "none"
    assert report["skipped_priors"] == {
        "protocol_height_lateral_width_alignment": "skipped"
    }
    assert protocol_report["status"] == "skipped"
    assert protocol_report["observed_height_level"] == "H2"
    assert protocol_report["recommended_height_level"] == "H3"
    assert protocol_report["height_match"] is False
    assert out["left_wrist_canon_x"].equals(df["left_wrist_norm_x"])
    assert not out["canonicalization_valid"].any()


def test_pipeline_uses_exercise_recommended_height_for_protocol_prior():
    df = _sample_protocol_height_df()
    config = PipelineConfig(
        validation=ValidationConfig(enabled=False),
        normalization=NormalizationConfig(enabled=False),
        exercise_definition=ExerciseDefinitionConfig(
            enabled=True,
            exercise_id="squat",
        ),
        canonicalization=CanonicalizationConfig(
            enabled=True,
            protocol_height_lateral_width_alignment=(
                ProtocolHeightLateralWidthAlignmentConfig(
                    enabled=True,
                    observed_height_level="H2",
                    correction_strength=0.5,
                    max_correction_torso=0.25,
                    visibility_threshold=0.0,
                )
            ),
        ),
    )

    out, report = run_pipeline(
        df,
        config,
        landmarks=PROTOCOL_HEIGHT_LANDMARKS,
    )

    protocol_report = report["canonicalization"]["prior_reports"][
        "protocol_height_lateral_width_alignment"
    ]
    assert report["canonicalization"]["candidate_available"] is True
    assert "score_gravity" not in report["canonicalization"]
    assert "score_contribution_enabled" not in report["canonicalization"]
    assert protocol_report["status"] == "applied"
    assert protocol_report["recommended_height_level"] == "H2"
    assert (out["left_wrist_canon_x"] > df["left_wrist_norm_x"]).all()


def test_load_pipeline_config_reads_canonicalization_block():
    cfg_path = Path("tests/_tmp_canonicalization_pipeline.yaml")
    try:
        cfg_path.write_text(
            """
normalization:
  enabled: true
  canonicalization:
    enabled: true
    output_prefix: canon
    report_only: true
    support_plane_alignment:
      enabled: true
      correction_transform: rigid_rotation
      support_landmarks: [left_heel, right_heel]
    movement_plane_alignment:
      enabled: true
      fit_landmarks: [left_hip, left_knee, left_ankle]
      correction_strength: 0.75
      max_rotation_deg: 12.0
    protocol_height_lateral_width_alignment:
      enabled: true
      observed_height_level: H2
      recommended_height_level: H2
      correction_strength: 0.4
      height_anchor_map:
        H2: [left_hip, right_hip]
""",
            encoding="utf-8",
        )

        config = load_pipeline_config(cfg_path)

        assert config.canonicalization.enabled is True
        assert config.canonicalization.output_prefix == "canon"
        assert config.canonicalization.support_plane_alignment.enabled is True
        assert config.canonicalization.support_plane_alignment.support_landmarks == [
            "left_heel",
            "right_heel",
        ]
        assert config.canonicalization.movement_plane_alignment.enabled is True
        assert config.canonicalization.movement_plane_alignment.fit_landmarks == [
            "left_hip",
            "left_knee",
            "left_ankle",
        ]
        assert (
            config.canonicalization.movement_plane_alignment.correction_strength == 0.75
        )
        assert config.canonicalization.movement_plane_alignment.max_rotation_deg == 12.0
        assert (
            config.canonicalization.protocol_height_lateral_width_alignment.enabled
            is True
        )
        assert (
            config.canonicalization.protocol_height_lateral_width_alignment.observed_height_level
            == "H2"
        )
        assert config.canonicalization.protocol_height_lateral_width_alignment.height_anchor_map[
            "H2"
        ] == [
            "left_hip",
            "right_hip",
        ]
    finally:
        cfg_path.unlink(missing_ok=True)


def test_visualization_accepts_canon_coordinate_mode():
    df = _sample_norm_df()
    out, _ = apply_canonicalization(
        df,
        landmarks=LANDMARKS,
        config=CanonicalizationConfig(enabled=True),
    )

    assert get_coord_columns("left_heel", "canon") == [
        "left_heel_canon_x",
        "left_heel_canon_y",
        "left_heel_canon_z",
    ]

    fig = create_pose_animation(
        out,
        landmarks=LANDMARKS,
        connections=[
            conn
            for conn in CONNECTIONS
            if conn[0] in set(LANDMARKS) and conn[1] in set(LANDMARKS)
        ],
        coord_mode="canon",
        show_text=False,
    )
    assert fig.frames
