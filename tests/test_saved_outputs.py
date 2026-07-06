import json

import pandas as pd

from movement.biomech import BIOMECH_REQUIRED_COLUMNS, save_biomech_outputs
from movement.biomarker import (
    BIOMARKER_REQUIRED_COLUMNS,
    BIOMARKER_SCORE_ITEM_REQUIRED_COLUMNS,
    BIOMARKER_SCORE_REQUIRED_COLUMNS,
    BiomarkerRecord,
    save_biomarker_outputs,
    score_records_to_item_dataframe,
)
from movement.biomarker.scoring import BiomarkerScoreRecord
from movement.features import FEATURE_REQUIRED_COLUMNS, save_feature_outputs


class _Serializable:
    def as_dict(self):
        return {"mode": "test"}


def _feature_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "feature_id": "spatial.role_alignment.left_right.range_of_motion_xy.knee",
                "exercise_id": "draft_squat",
                "rep_id": 1,
                "phase": None,
                "value": 0.1,
                "unit": "dimensionless",
                "source_fields": ["left_knee_norm_x", "right_knee_norm_x"],
                "availability": "assessed",
                "availability_reasons": [],
                "view_reliability": "recording_view",
                "depth_dependency": "none",
                "model_depth_reliability": "low",
                "landmark_quality": "usable",
                "focus_tier": "context_constraint",
                "camera_zone": "front_or_back",
                "role_context": {"left": "primary"},
            }
        ]
    )


def _biomech_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "metric_id": "biomech.com.range_x",
                "metric_family": "biomech.com",
                "exercise_id": "draft_squat",
                "rep_id": 1,
                "value": 0.2,
                "unit": "torso_length_ratio",
                "source_fields": ["hip_center_norm_x"],
                "note": "low-confidence proxy",
                "visibility_weight_applied": True,
                "n_frames_used": 12,
                "n_frames_excluded_low_visibility": 1,
                "availability": "low_confidence",
                "availability_reasons": ["monocular_biomech_proxy_low_confidence"],
                "depth_dependency": "high",
                "model_depth_reliability": "low",
                "landmark_quality": "usable",
                "focus_tier": "primary",
            }
        ]
    )


def _biomarker_records() -> list[BiomarkerRecord]:
    return [
        BiomarkerRecord(
            biomarker_id="spatial.role_alignment.left_right.range_of_motion_xy.knee",
            exercise_id="draft_squat",
            definition_version="0.1.0",
            source_fields=["left_knee_norm_x", "right_knee_norm_x"],
            rep_id=1,
            value=0.1,
            unit="dimensionless",
            availability="assessed",
            availability_reasons=[],
            focus_tier="context_constraint",
        )
    ]


def _score_records() -> list[BiomarkerScoreRecord]:
    return [
        BiomarkerScoreRecord(
            score_id="rep_quality_score",
            exercise_id="draft_squat",
            definition_version="0.1.0",
            rep_id=1,
            domain_scores={
                "spatial": 95.0,
                "temporal": 98.0,
                "control": 100.0,
                "biomech": 100.0,
            },
            floor_applied={
                "spatial": False,
                "temporal": False,
                "control": False,
                "biomech": False,
            },
            final_score=98.25,
            deductions=[
                {
                    "domain": "spatial",
                    "feature_id": "spatial.range_of_motion.xy.left_knee_angle",
                    "value": 85.4,
                    "deduction": 1.5,
                    "landmark_ids": ["left_hip", "left_knee", "left_ankle"],
                    "evaluation_domain": "recording_view_only",
                    "evidence_axes": "xy",
                }
            ],
            withheld_features=[
                {
                    "domain": "biomech",
                    "feature_id": "biomech.com.range_x",
                    "availability": "low_confidence",
                }
            ],
            source_fields=["analysis.scoring"],
        )
    ]


def test_save_feature_outputs_writes_csv_context_and_qc(tmp_path):
    summary = save_feature_outputs(
        feature_df=_feature_df(),
        recording_id="p01_squat_set1",
        exercise_id="draft_squat",
        output_dir=tmp_path,
        feature_context=_Serializable(),
        feature_role_context_report={"skipped": True},
        project_root=tmp_path,
    )

    assert set(summary["artifact"]) == {
        "features_csv",
        "feature_context_json",
        "feature_qc_json",
    }
    saved = pd.read_csv(tmp_path / "p01_squat_set1_features.csv")
    assert len(saved) == 1
    for column in FEATURE_REQUIRED_COLUMNS:
        assert column in saved.columns

    context = json.loads((tmp_path / "p01_squat_set1_feature_context.json").read_text())
    assert context["feature_context"] == {"mode": "test"}
    qc = json.loads((tmp_path / "p01_squat_set1_feature_qc.json").read_text())
    assert qc["missing_source_fields"] == 0


def test_save_biomech_outputs_writes_csv_and_qc(tmp_path):
    summary = save_biomech_outputs(
        biomech_df=_biomech_df(),
        recording_id="p01_squat_set1",
        exercise_id="draft_squat",
        output_dir=tmp_path,
        project_root=tmp_path,
    )

    assert set(summary["artifact"]) == {"biomech_csv", "biomech_qc_json"}
    saved = pd.read_csv(tmp_path / "p01_squat_set1_biomech.csv")
    assert len(saved) == 1
    for column in BIOMECH_REQUIRED_COLUMNS:
        assert column in saved.columns

    qc = json.loads((tmp_path / "p01_squat_set1_biomech_qc.json").read_text())
    assert qc["availability_counts"] == {"low_confidence": 1}


def test_save_biomarker_outputs_writes_csv_score_and_qc(tmp_path):
    summary = save_biomarker_outputs(
        biomarker_records=_biomarker_records(),
        score_records=_score_records(),
        recording_id="p01_squat_set1",
        exercise_id="draft_squat",
        output_dir=tmp_path,
        project_root=tmp_path,
    )

    assert set(summary["artifact"]) == {
        "biomarkers_csv",
        "biomarker_scores_csv",
        "biomarker_score_items_csv",
        "biomarker_qc_json",
    }
    saved_biomarkers = pd.read_csv(tmp_path / "p01_squat_set1_biomarkers.csv")
    saved_scores = pd.read_csv(tmp_path / "p01_squat_set1_biomarker_scores.csv")
    saved_score_items = pd.read_csv(
        tmp_path / "p01_squat_set1_biomarker_score_items.csv"
    )
    assert len(saved_biomarkers) == 1
    assert len(saved_scores) == 1
    assert len(saved_score_items) == 1
    for column in BIOMARKER_REQUIRED_COLUMNS:
        assert column in saved_biomarkers.columns
    for column in BIOMARKER_SCORE_REQUIRED_COLUMNS:
        assert column in saved_scores.columns
    for column in BIOMARKER_SCORE_ITEM_REQUIRED_COLUMNS:
        assert column in saved_score_items.columns
    assert saved_score_items.loc[0, "item_score"] == 98.5
    assert saved_score_items.loc[0, "deduction"] == 1.5

    qc = json.loads((tmp_path / "p01_squat_set1_biomarker_qc.json").read_text())
    assert qc["score_available"] is True
    assert qc["score_item_rows"] == 1
    assert qc["withheld_feature_count"] == 1


def test_score_records_to_item_dataframe_expands_deductions():
    item_df = score_records_to_item_dataframe(_score_records())

    assert len(item_df) == 1
    assert item_df.loc[0, "rep_id"] == 1
    assert item_df.loc[0, "domain"] == "spatial"
    assert item_df.loc[0, "feature_id"] == (
        "spatial.range_of_motion.xy.left_knee_angle"
    )
    assert item_df.loc[0, "item_score"] == 98.5
    assert item_df.loc[0, "landmark_ids"] == [
        "left_hip",
        "left_knee",
        "left_ankle",
    ]


def test_save_biomarker_outputs_preserves_empty_score_contract(tmp_path):
    save_biomarker_outputs(
        biomarker_records=_biomarker_records(),
        score_records=[],
        recording_id="p01_squat_set1",
        exercise_id="draft_squat",
        output_dir=tmp_path,
        project_root=tmp_path,
    )

    saved_scores = pd.read_csv(tmp_path / "p01_squat_set1_biomarker_scores.csv")
    saved_score_items = pd.read_csv(
        tmp_path / "p01_squat_set1_biomarker_score_items.csv"
    )
    assert saved_scores.empty
    assert saved_score_items.empty
    for column in BIOMARKER_SCORE_REQUIRED_COLUMNS:
        assert column in saved_scores.columns
    for column in BIOMARKER_SCORE_ITEM_REQUIRED_COLUMNS:
        assert column in saved_score_items.columns

    qc = json.loads((tmp_path / "p01_squat_set1_biomarker_qc.json").read_text())
    assert qc["score_available"] is False
    assert qc["score_rows"] == 0
    assert qc["score_item_rows"] == 0
