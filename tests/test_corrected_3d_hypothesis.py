import pandas as pd

from movement.stages.corrected_3d_hypothesis import (
    SupportWidthStabilityConfig,
    build_corrected_3d_hypothesis_candidates,
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


def test_support_width_stability_report_compares_norm_and_candidate_family():
    df = _pose_with_review_family()
    burden = pd.DataFrame(
        {
            "candidate_family": ["review"],
            "stage": ["planted_support_temporal_memory"],
            "cap_fraction": [0.20],
        }
    )

    report = build_support_width_stability_sensitivity_report(
        df,
        config=SupportWidthStabilityConfig(candidate_family="review"),
        burden_ledger=burden,
    )

    row = report.iloc[0]
    assert row["feature_id"] == "candidate.support_width_stability"
    assert row["evaluation_domain"] == "corrected_3d_hypothesis"
    assert row["availability"] == "assessed"
    assert row["confidence"] == "very_low"
    assert "score_gravity" not in row
    assert "score_contribution_enabled" not in row
    assert "used_for_score" not in row
    assert round(row["norm_value"], 6) == 0.1
    assert round(row["corrected_candidate_value"], 6) == 0.0
    assert round(row["delta"], 6) == -0.1
    assert row["correction_burden"] == 0.2


def test_support_width_stability_report_marks_missing_candidate_not_assessed():
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
        config=SupportWidthStabilityConfig(candidate_family="review"),
    )

    row = report.iloc[0]
    assert row["availability"] == "not_assessed"
    assert "missing_candidate_columns" in row["availability_reasons"]
    assert "score_gravity" not in row
    assert "score_contribution_enabled" not in row
    assert "used_for_score" not in row


def test_corrected_3d_hypothesis_result_keeps_coordinates_as_candidate_evidence():
    df = _pose_with_review_family()
    result = build_corrected_3d_hypothesis_candidates(
        df,
        landmarks=["left_ankle", "right_ankle"],
        solver_config={"output_family": "review"},
        burden_ledger=pd.DataFrame(
            {"candidate_family": ["review"], "cap_fraction": [0.1]}
        ),
    )

    assert result.corrected_candidate_df.equals(df)
    assert result.readiness_provenance["status"] == "candidate_evidence"
    assert result.readiness_provenance["used_for_features_or_scores"] is False
    assert result.readiness_provenance["downstream_coordinate_mode"] == "norm"
    assert "score_gravity" not in result.readiness_provenance
    assert "feature_depth_gravity" not in result.readiness_provenance
    assert (
        result.norm_vs_corrected_sensitivity_report.loc[0, "feature_id"]
        == "candidate.support_width_stability"
    )

    result_dict = result.as_dict()
    assert result_dict["num_sensitivity_rows"] == 1
    row = result_dict["norm_vs_corrected_sensitivity_report"][0]
    assert "score_gravity" not in row
    assert "score_contribution_enabled" not in row
    assert "used_for_score" not in row


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
    config.motion_attribution.enabled = False
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
    assert row["feature_id"] == "candidate.support_width_stability"
    assert row["availability"] == "low_confidence"
    assert "missing_burden_ledger" in row["availability_reasons"]
    assert "score_gravity" not in row
    assert "score_contribution_enabled" not in row
    assert "used_for_score" not in row
    assert review["readiness_provenance"]["status"] == "candidate_evidence"
    assert review["readiness_provenance"]["used_for_features_or_scores"] is False
    assert report["canonicalization"]["corrected_3d_hypothesis"]["review_status"] == (
        "candidate_evidence"
    )


def test_multi_recording_sensitivity_summary_keeps_candidate_evidence():
    reports = [
        {
            "recording_id": "r1",
            "exercise_definition": {"exercise_id": "squat"},
            "corrected_3d_hypothesis_review": {
                "norm_vs_corrected_sensitivity_report": [
                    {
                        "feature_id": "candidate.support_width_stability",
                        "norm_value": 0.10,
                        "corrected_candidate_value": 0.05,
                        "delta_abs": 0.05,
                        "correction_burden": 0.2,
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
                        "feature_id": "candidate.support_width_stability",
                        "norm_value": 0.30,
                        "corrected_candidate_value": 0.10,
                        "delta_abs": 0.20,
                        "correction_burden": 0.9,
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
    assert item["feature_id"] == "candidate.support_width_stability"
    assert item["exercise_id"] == "squat"
    assert item["n_recordings"] == 2
    assert item["n_assessed"] == 1
    assert item["n_low_confidence"] == 1
    assert item["max_correction_burden"] == 0.9
    assert "max_score_gravity" not in summary.columns
    assert "score_contribution_enabled" not in summary.columns
    assert "used_for_score" not in summary.columns
