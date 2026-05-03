"""
⑦ 특징 추출 (Feature Extraction)

공간(Spatial) / 시간(Temporal) / 제어(Control) 영역의 특징을 산출한다.
각 특징은 (value, unit, provenance) 형식으로 반환되어 ⑨ 지표화 단계에서 추적 가능하다.

하위 모듈:
  features.spatial   → ROM, 좌우 대칭성, 궤적 형태
  features.temporal  → tempo, 변동성
  features.control   → 안정성(CoM), 보상 움직임

Coordinate convention: (T, J, 3) = (frame, joint_index, xyz).
Column convention     : <landmark>_norm_x/y/z 정규화 좌표 사용.
Unit convention       : torso_length_ratio (무차원, 신체 배율 단위) or degree.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FeatureRecord:
    """단일 특징 계산 결과.

    Parameters
    ----------
    feature_id    : 고유 식별자 (예: 'spatial.rom.left_knee')
    exercise_id   : 운동 ID
    rep_id        : 반복 번호 (None = 시퀀스 단위 특징)
    value         : 특징값
    unit          : 단위 (torso_length_ratio | degree | second | dimensionless_cv)
    source_fields : 이 특징을 도출한 운동 정의 필드 목록 (provenance)
    note          : 선택적 보조 설명
    """
    feature_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str] = field(default_factory=list)
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.source_fields:
            raise ValueError(
                f"FeatureRecord '{self.feature_id}': source_fields가 비어 있음. "
                "운동 정의의 출처 필드를 반드시 명시해야 합니다."
            )


__all__ = ["FeatureRecord"]
