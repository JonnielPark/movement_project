import json

import pandas as pd

from movement.biomech import BIOMECH_REQUIRED_COLUMNS, save_biomech_outputs
from movement.features import FEATURE_REQUIRED_COLUMNS, save_feature_outputs


class _Serializable:
    def as_dict(self):
        return {"mode": "test"}


def _feature_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "feature_id": "spatial.symmetry.knee",
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
            }
        ]
    )


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
