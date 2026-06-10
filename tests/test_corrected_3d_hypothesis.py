import pandas as pd

from movement.stages.corrected_3d_hypothesis import (
    SupportWidthStabilityConfig,
    build_corrected_3d_hypothesis_candidates,
    build_support_width_stability_sensitivity_report,
)


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
    assert bool(row["used_for_score"]) is False
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
    assert bool(row["used_for_score"]) is False


def test_corrected_3d_hypothesis_result_keeps_coordinates_report_only():
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
    assert result.readiness_provenance["used_for_features_or_scores"] is False
    assert result.readiness_provenance["downstream_coordinate_mode"] == "norm"
    assert (
        result.norm_vs_corrected_sensitivity_report.loc[0, "feature_id"]
        == "candidate.support_width_stability"
    )
