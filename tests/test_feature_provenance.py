import pytest

from movement.biomarker import BiomarkerRecord
from movement.features import FeatureRecord


def test_feature_record_requires_source_fields():
    with pytest.raises(ValueError, match="source_fields is empty"):
        FeatureRecord(
            feature_id="spatial.rom.left_knee",
            exercise_id="squat",
            rep_id=1,
            value=42.0,
            unit="degree",
            source_fields=[],
        )


def test_biomarker_record_requires_source_fields():
    with pytest.raises(ValueError, match="source_fields is empty"):
        BiomarkerRecord(
            biomarker_id="spatial.rom.left_knee",
            exercise_id="squat",
            definition_version="0.5.2",
            source_fields=[],
            rep_id=1,
            value=42.0,
            unit="degree",
        )
