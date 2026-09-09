import pandas as pd

from movement.stages.corrected_3d_hypothesis import (
    Corrected3DCoordinateSolverConfig,
    CorrectionPriorConfig,
    RadialXYRelaxationConfig,
    SupportWidthStabilityConfig,
    build_corrected_3d_coordinate_hypothesis,
    build_corrected_3d_hypothesis_evidence,
    build_support_width_stability_sensitivity_report,
    collect_corrected_3d_sensitivity_rows,
    summarize_corrected_3d_sensitivity_reports,
)
from movement.pipeline import PipelineConfig, run_pipeline


def _pose_with_review_family() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "left_ankle_norm_x": [0.0, 0.0, 0.0, 0.0],
            "left_ankle_norm_y": [0.0, 0.0, 0.0, 0.0],
            "right_ankle_norm_x": [1.0, 1.0, 1.1, 1.1],
            "right_ankle_norm_y": [0.0, 0.0, 0.0, 0.0],
            "left_ankle_review_x": [0.0, 0.0, 0.0, 0.0],
            "left_ankle_review_y": [0.0, 0.0, 0.0, 0.0],
            "left_ankle_review_z": [0.0, 0.0, 0.0, 0.0],
            "right_ankle_review_x": [1.0, 1.0, 1.0, 1.0],
            "right_ankle_review_y": [0.0, 0.0, 0.0, 0.0],
            "right_ankle_review_z": [0.0, 0.0, 0.0, 0.0],
        }
    )


def _pipeline_pose_with_review_family() -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "left_hip_x": [-0.5, -0.5, -0.5, -0.5],
            "left_hip_y": [0.0, 0.0, 0.0, 0.0],
            "left_hip_z": [0.0, 0.0, 0.0, 0.0],
            "right_hip_x": [0.5, 0.5, 0.5, 0.5],
            "right_hip_y": [0.0, 0.0, 0.0, 0.0],
            "right_hip_z": [0.0, 0.0, 0.0, 0.0],
            "left_shoulder_x": [-0.5, -0.5, -0.5, -0.5],
            "left_shoulder_y": [1.0, 1.0, 1.0, 1.0],
            "left_shoulder_z": [0.0, 0.0, 0.0, 0.0],
            "right_shoulder_x": [0.5, 0.5, 0.5, 0.5],
            "right_shoulder_y": [1.0, 1.0, 1.0, 1.0],
            "right_shoulder_z": [0.0, 0.0, 0.0, 0.0],
            "left_ankle_x": [-0.5, -0.5, -0.5, -0.5],
            "left_ankle_y": [-1.0, -1.0, -1.0, -1.0],
            "left_ankle_z": [0.0, 0.0, 0.0, 0.0],
            "right_ankle_x": [0.5, 0.5, 0.6, 0.6],
            "right_ankle_y": [-1.0, -1.0, -1.0, -1.0],
            "right_ankle_z": [0.0, 0.0, 0.0, 0.0],
        }
    )
    review_cols = _pose_with_review_family().filter(like="_review_")
    return pd.concat([df, review_cols], axis=1)


def test_support_width_stability_report_compares_norm_and_coordinate_family():
    df = _pose_with_review_family()
    burden = pd.DataFrame(
        {
            "coordinate_family": ["review"],
            "stage": ["planted_support_temporal_memory"],
            "cap_fraction": [0.20],
        }
    )

    report = build_support_width_stability_sensitivity_report(
        df,
        config=SupportWidthStabilityConfig(coordinate_family="review"),
        burden_ledger=burden,
    )

    row = report.iloc[0]
    assert row["feature_id"] == "analysis.support_width_stability"
    assert row["evaluation_domain"] == "corrected_3d_hypothesis"
    assert row["availability"] == "assessed"
    assert row["confidence"] == "very_low"
    assert row["quality_gravity"] > 0.0
    assert "score_gravity" not in row
    assert "score_contribution_enabled" not in row
    assert "used_for_score" not in row
    assert round(row["norm_value"], 6) == 0.1
    assert round(row["corrected_value"], 6) == 0.0
    assert round(row["delta"], 6) == -0.1
    assert row["correction_burden"] == 0.2


def test_support_width_stability_report_marks_missing_analysis_not_assessed():
    df = _pose_with_review_family().drop(
        columns=[
            "left_ankle_review_x",
            "left_ankle_review_y",
            "left_ankle_review_z",
            "right_ankle_review_x",
            "right_ankle_review_y",
            "right_ankle_review_z",
        ]
    )

    report = build_support_width_stability_sensitivity_report(
        df,
        config=SupportWidthStabilityConfig(coordinate_family="review"),
    )

    row = report.iloc[0]
    assert row["availability"] == "not_assessed"
    assert row["quality_gravity"] == 0.0
    assert "missing_corrected_columns" in row["availability_reasons"]
    assert "score_gravity" not in row
    assert "score_contribution_enabled" not in row
    assert "used_for_score" not in row


def test_corrected_3d_hypothesis_result_keeps_coordinates_as_analysis_evidence():
    df = _pose_with_review_family()
    result = build_corrected_3d_hypothesis_evidence(
        df,
        landmarks=["left_ankle", "right_ankle"],
        solver_config={"output_family": "review"},
        burden_ledger=pd.DataFrame(
            {"coordinate_family": ["review"], "cap_fraction": [0.1]}
        ),
    )

    assert result.analysis_coordinate_df.equals(df)
    assert result.readiness_provenance["status"] == "analysis_evidence"
    assert result.readiness_provenance["used_for_features_or_scores"] is False
    assert result.readiness_provenance["downstream_coordinate_mode"] == "norm"
    assert "score_gravity" not in result.readiness_provenance
    assert "feature_depth_gravity" not in result.readiness_provenance
    assert (
        result.norm_vs_corrected_sensitivity_report.loc[0, "feature_id"]
        == "analysis.support_width_stability"
    )

    result_dict = result.as_dict()
    assert result_dict["num_sensitivity_rows"] == 1
    row = result_dict["norm_vs_corrected_sensitivity_report"][0]
    assert "score_gravity" not in row
    assert "score_contribution_enabled" not in row
    assert "used_for_score" not in row


def test_coordinate_solver_corrects_segment_z_without_changing_xy():
    df = pd.DataFrame(
        {
            "frame": [0, 1],
            "prox_norm_x": [0.0, 0.0],
            "prox_norm_y": [0.0, 0.0],
            "prox_norm_z": [0.0, 0.0],
            "dist_norm_x": [0.6, 0.6],
            "dist_norm_y": [0.0, 0.0],
            "dist_norm_z": [0.0, 0.0],
        }
    )

    corrected, ledger, report = build_corrected_3d_coordinate_hypothesis(
        df,
        landmarks=["prox", "dist"],
        config=Corrected3DCoordinateSolverConfig(
            enabled=True,
            output_family="review",
            segment_pairs=(("prox", "dist"),),
            default_segment_length_torso=1.0,
            max_depth_torso=1.0,
            max_z_correction_torso=1.0,
            correction_priors=(
                CorrectionPriorConfig(
                    name="anthropometric_segment_length",
                    enabled=True,
                    priority="primary",
                ),
            ),
        ),
    )

    assert report["status"] == "applied"
    assert report["applied_priors"] == ["anthropometric_segment_length"]
    assert len(ledger) == 2
    assert corrected["dist_review_x"].tolist() == df["dist_norm_x"].tolist()
    assert corrected["dist_review_y"].tolist() == df["dist_norm_y"].tolist()
    assert round(float(corrected.loc[0, "dist_review_z"]), 6) == 0.8
    assert round(float(ledger.loc[0, "residual_after_torso"]), 6) == 0.0
    assert "score_gravity" not in ledger.columns


def test_coordinate_solver_radial_xy_relaxation_recomputes_z_solution():
    df = pd.DataFrame(
        {
            "prox_norm_x": [-0.51],
            "prox_norm_y": [0.0],
            "prox_norm_z": [0.0],
            "dist_norm_x": [0.51],
            "dist_norm_y": [0.0],
            "dist_norm_z": [0.0],
        }
    )

    corrected, ledger, report = build_corrected_3d_coordinate_hypothesis(
        df,
        landmarks=["prox", "dist"],
        config=Corrected3DCoordinateSolverConfig(
            enabled=True,
            output_family="review",
            segment_pairs=(("prox", "dist"),),
            default_segment_length_torso=1.0,
            max_depth_torso=1.0,
            max_z_correction_torso=1.0,
            correction_priors=(
                CorrectionPriorConfig(
                    name="anthropometric_segment_length",
                    enabled=True,
                    priority="primary",
                ),
                CorrectionPriorConfig(
                    name="radial_xy_relaxation",
                    enabled=True,
                    priority="secondary",
                    weight=0.25,
                ),
            ),
            radial_xy_relaxation=RadialXYRelaxationConfig(
                enabled=True,
                preset="custom",
                direction="pincushion",
                max_xy_shift_torso=0.02,
                radial_strength=1.0,
                max_iterations=1,
            ),
        ),
    )

    assert report["status"] == "applied"
    assert "radial_xy_relaxation" in report["applied_priors"]
    assert ledger.loc[0, "prior"] == "radial_xy_relaxation"
    assert (
        abs(float(corrected.loc[0, "prox_review_x"]) - df.loc[0, "prox_norm_x"])
        <= 0.020001
    )
    assert (
        abs(float(corrected.loc[0, "dist_review_x"]) - df.loc[0, "dist_norm_x"])
        <= 0.020001
    )
    assert float(ledger.loc[0, "residual_after_torso"]) < float(
        ledger.loc[0, "residual_before_torso"]
    )


def test_corrected_3d_hypothesis_builder_uses_enabled_coordinate_solver():
    df = pd.DataFrame(
        {
            "prox_norm_x": [0.0, 0.0],
            "prox_norm_y": [0.0, 0.0],
            "prox_norm_z": [0.0, 0.0],
            "dist_norm_x": [0.6, 0.6],
            "dist_norm_y": [0.0, 0.0],
            "dist_norm_z": [0.0, 0.0],
        }
    )

    result = build_corrected_3d_hypothesis_evidence(
        df,
        landmarks=["prox", "dist"],
        solver_config={
            "output_family": "review",
            "support_pair": ["prox", "dist"],
            "coordinate_solver": {
                "enabled": True,
                "segment_pairs": [["prox", "dist"]],
                "default_segment_length_torso": 1.0,
                "max_depth_torso": 1.0,
                "max_z_correction_torso": 2.0,
            },
        },
    )

    assert "dist_review_z" in result.analysis_coordinate_df.columns
    assert result.readiness_provenance["coordinate_solver_status"] == "applied"
    assert result.residual_report["coordinate_solver"]["status"] == "applied"
    assert not result.burden_ledger.empty
    sensitivity = result.norm_vs_corrected_sensitivity_report.iloc[0]
    assert sensitivity["availability"] == "assessed"
    assert sensitivity["quality_gravity"] > 0.0


def test_pipeline_emits_corrected_3d_review_without_scoring_use():
    config = PipelineConfig()
    config.validation.enabled = False
    config.annotation.enabled = False
    config.exercise_definition.enabled = False
    config.preprocessing.enabled = False
    config.normalization.enabled = True
    config.canonicalization.enabled = True
    config.canonicalization.corrected_3d_hypothesis.enabled = True
    config.canonicalization.corrected_3d_hypothesis.output_family = "review"
    config.rep_segmentation.enabled = False
    config.phase_segmentation.enabled = False
    config.features.role_context.enabled = False
    config.features.enabled = False
    config.biomech.enabled = False
    config.biomarker.enabled = False

    _, report = run_pipeline(
        _pipeline_pose_with_review_family(),
        config,
        landmarks=[
            "left_hip",
            "right_hip",
            "left_shoulder",
            "right_shoulder",
            "left_ankle",
            "right_ankle",
        ],
    )

    review = report["corrected_3d_hypothesis_review"]
    row = review["norm_vs_corrected_sensitivity_report"][0]
    assert row["feature_id"] == "analysis.support_width_stability"
    assert row["availability"] == "low_confidence"
    assert row["quality_gravity"] > 0.0
    assert "missing_burden_ledger" in row["availability_reasons"]
    assert "score_gravity" not in row
    assert "score_contribution_enabled" not in row
    assert "used_for_score" not in row
    assert review["readiness_provenance"]["status"] == "analysis_evidence"
    assert review["readiness_provenance"]["used_for_features_or_scores"] is False
    assert report["canonicalization"]["corrected_3d_hypothesis"]["review_status"] == (
        "analysis_evidence"
    )


def test_multi_recording_sensitivity_summary_keeps_analysis_evidence():
    reports = [
        {
            "recording_id": "r1",
            "exercise_definition": {"exercise_id": "squat"},
            "corrected_3d_hypothesis_review": {
                "norm_vs_corrected_sensitivity_report": [
                    {
                        "feature_id": "analysis.support_width_stability",
                        "norm_value": 0.10,
                        "corrected_value": 0.05,
                        "delta_abs": 0.05,
                        "correction_burden": 0.2,
                        "quality_gravity": 0.05,
                        "availability": "assessed",
                    }
                ]
            },
        },
        {
            "recording_id": "r2",
            "exercise_definition": {"exercise_id": "squat"},
            "corrected_3d_hypothesis_review": {
                "norm_vs_corrected_sensitivity_report": [
                    {
                        "feature_id": "analysis.support_width_stability",
                        "norm_value": 0.30,
                        "corrected_value": 0.10,
                        "delta_abs": 0.20,
                        "correction_burden": 0.9,
                        "quality_gravity": 0.1,
                        "availability": "low_confidence",
                    }
                ]
            },
        },
    ]

    rows = collect_corrected_3d_sensitivity_rows(reports)
    summary = summarize_corrected_3d_sensitivity_reports(reports)

    assert len(rows) == 2
    assert "score_gravity" not in rows.columns
    assert "score_contribution_enabled" not in rows.columns
    assert "used_for_score" not in rows.columns
    item = summary.iloc[0]
    assert item["feature_id"] == "analysis.support_width_stability"
    assert item["exercise_id"] == "squat"
    assert item["n_recordings"] == 2
    assert item["n_assessed"] == 1
    assert item["n_low_confidence"] == 1
    assert item["max_correction_burden"] == 0.9
    assert round(item["median_quality_gravity"], 6) == 0.075
    assert "max_score_gravity" not in summary.columns
    assert "score_contribution_enabled" not in summary.columns
    assert "used_for_score" not in summary.columns
