"""
강건성 시뮬레이션 (Robustness Simulation)

정상 합성 포즈 데이터에 인위적 조건을 부여해 분석 프레임워크의
공학적 강건성을 검증한다.

본 패키지는 분석 단계(① ~ ⑨) 바깥에서 호출된다.
run_pipeline()에 포함되지 않는다.

하위 모듈:
  simulation.synthetic → 합성 데이터 생성 / 조건 부여 함수

지원 시뮬레이션 조건:
  - ROM 제한  : 관절 가동범위를 인위적으로 축소
  - 좌표 잡음 : 가우시안 잡음 (torso_length_ratio 단위 σ)
  - 가려짐    : 지정 랜드마크의 가시도를 0으로 설정, 좌표를 NaN으로 대체
  - 속도 이상 : 특정 프레임에 위치 점프 삽입

모든 출력은 동일한 컬럼 형식의 포즈 데이터프레임 +
simulation_log dict로 반환된다.

단위 규약: 거리/변위는 torso_length_ratio. 각도는 degree.
절대 단위(N, kg, m) 사용 금지.
"""
from __future__ import annotations

from movement.simulation.synthetic import (  # noqa
    add_gaussian_noise,
    add_occlusion,
    add_velocity_spike,
    restrict_rom,
)

__all__ = [
    "add_gaussian_noise",
    "add_occlusion",
    "add_velocity_spike",
    "restrict_rom",
]
