from movement.biomarker import BiomarkerRecord
from movement.features import FeatureRecord


def test_feature_record_accepts_empty_audit_references():
    record = FeatureRecord(
        feature_id="spatial.range_of_motion.xy.left_knee",
        exercise_id="squat",
        rep_id=1,
        value=42.0,
        unit="degree",
        source_fields=[],
        availability="assessed",
        evidence_axes="xy",
        coordinate_reference="norm_recording_view_xy",
        evaluation_domain="recording_view_only",
        feature_family="range_of_motion",
    )

    assert record.source_fields == []
    assert record.availability == "assessed"
    assert record.evidence_axes == "xy"


def test_biomarker_record_accepts_empty_audit_references():
    record = BiomarkerRecord(
        biomarker_id="spatial.range_of_motion.xy.left_knee",
        exercise_id="squat",
        definition_version="0.5.2",
        source_fields=[],
        rep_id=1,
        value=42.0,
        unit="degree",
        availability="assessed",
        evidence_axes="xy",
        coordinate_reference="norm_recording_view_xy",
        evaluation_domain="recording_view_only",
        feature_family="range_of_motion",
    )

    assert record.source_fields == []
    assert record.availability == "assessed"
    assert record.evidence_axes == "xy"
