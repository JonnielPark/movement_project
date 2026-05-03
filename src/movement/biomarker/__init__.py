"""
⑨ 지표화 (Biomarker Derivation)

⑦ 특징 추출과 ⑧ 생체역학적 근사 모델링의 결과를 통합해
해석 가능한 디지털 바이오마커(BiomarkerRecord)를 산출한다.

모든 BiomarkerRecord는 source_fields (provenance) 를 반드시 포함해야 한다.
source_fields가 비어 있으면 ValueError를 발생시킨다.

Unit convention: torso_length_ratio | degree | dimensionless_cv | second.
절대 단위(N, kg, m, N·m) 사용 금지.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BiomarkerRecord:
    """단일 디지털 바이오마커.

    Parameters
    ----------
    biomarker_id      : 고유 식별자 (예: 'biomarker.rom.left_knee')
    exercise_id       : 운동 ID
    definition_version: 참조 운동 정의 버전 (provenance)
    source_fields     : 이 바이오마커를 도출한 운동 정의 필드 목록 (provenance)
    rep_id            : 반복 번호 (None = 시퀀스 단위)
    value             : 바이오마커 값
    unit              : 단위 (torso_length_ratio | degree | dimensionless_cv | second)
    note              : 선택적 임상/생체역학적 해석 보조 설명
    """
    biomarker_id: str
    exercise_id: str
    definition_version: str
    source_fields: list[str]
    rep_id: int | None
    value: float
    unit: str
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.source_fields:
            raise ValueError(
                f"BiomarkerRecord '{self.biomarker_id}': source_fields가 비어 있음. "
                "운동 정의의 출처 필드를 반드시 명시해야 바이오마커가 추적 가능합니다."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "biomarker_id": self.biomarker_id,
            "exercise_id": self.exercise_id,
            "definition_version": self.definition_version,
            "source_fields": self.source_fields,
            "rep_id": self.rep_id,
            "value": self.value,
            "unit": self.unit,
            "note": self.note,
        }


def from_feature_record(
    feature,
    definition_version: str,
    biomarker_id: str | None = None,
    note: str | None = None,
) -> BiomarkerRecord:
    """FeatureRecord를 BiomarkerRecord로 변환한다.

    Parameters
    ----------
    feature          : FeatureRecord
    definition_version : 운동 정의 버전 문자열
    biomarker_id     : 재정의할 바이오마커 ID. None이면 feature.feature_id 사용.
    note             : 선택적 임상/생체역학 해석 메모.
    """
    return BiomarkerRecord(
        biomarker_id=biomarker_id or feature.feature_id,
        exercise_id=feature.exercise_id,
        definition_version=definition_version,
        source_fields=feature.source_fields,
        rep_id=feature.rep_id,
        value=feature.value,
        unit=feature.unit,
        note=note,
    )


def from_biomech_record(
    biomech,
    definition_version: str,
    biomarker_id: str | None = None,
    note: str | None = None,
) -> BiomarkerRecord:
    """BiomechRecord를 BiomarkerRecord로 변환한다."""
    return BiomarkerRecord(
        biomarker_id=biomarker_id or biomech.metric_id,
        exercise_id=biomech.exercise_id,
        definition_version=definition_version,
        source_fields=biomech.source_fields,
        rep_id=biomech.rep_id,
        value=biomech.value,
        unit=biomech.unit,
        note=note or biomech.note,
    )


__all__ = ["BiomarkerRecord", "from_feature_record", "from_biomech_record"]
