"""
⑧ 생체역학적 근사 모델링 (Biomechanical Proxy Modeling)

단일 비전 환경에서 단순화된 생체역학 규칙을 적용해 근사 지표를 산출한다.

  - 절대값 힘(N, N·m, kg) 측정이 아니라 분절 길이 정규화 비율이 출력 단위.
  - 개인별 절대값이 아닌 상대적 정규화 지표 산출이 목적.

하위 모듈:
  biomech.anthropometry → 통계적 인체 계측 비율 (Winter 1990 기준)
  biomech.com           → CoM 추정 (분절 질량 비율 × 분절 위치)
  biomech.moment_arm    → 관절 모멘트 암 (2D 근사, torso_length_ratio)

Coordinate convention: (T, J, 3) = (frame, joint_index, xyz).
Column convention     : <landmark>_norm_x/y/z 정규화 좌표 사용.
Unit restriction      : 모든 출력 단위는 torso_length_ratio. 절대 단위 사용 금지.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BiomechRecord:
    """단일 생체역학적 근사 지표 결과.

    Parameters
    ----------
    metric_id     : 고유 식별자 (예: 'biomech.com.trajectory_range_x')
    exercise_id   : 운동 ID
    rep_id        : 반복 번호 (None = 시퀀스 단위)
    value         : 지표값
    unit          : 단위 (반드시 torso_length_ratio)
    source_fields : 이 지표를 도출한 운동 정의 필드 (provenance)
    note          : 선택적 보조 설명
    """
    metric_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str] = field(default_factory=list)
    note: str | None = None

    def __post_init__(self) -> None:
        if self.unit not in ("torso_length_ratio", "degree", "dimensionless"):
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': 절대 단위(N, kg, m 등) 사용 금지. "
                f"unit='{self.unit}'. torso_length_ratio 또는 degree를 사용하세요."
            )
        if not self.source_fields:
            raise ValueError(
                f"BiomechRecord '{self.metric_id}': source_fields가 비어 있음. "
                "운동 정의의 출처 필드를 반드시 명시해야 합니다."
            )


__all__ = ["BiomechRecord"]
