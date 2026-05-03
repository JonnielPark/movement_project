"""
movement_project — Digital Biomarker Framework

단일 비전(모바일 카메라) 3D 포즈 데이터로부터 신체 동작의 질을
생체역학적으로 정량화해 해석 가능한 디지털 바이오마커로 표현하는 분석 프레임워크.

분석 단계 (Pipeline) — docs/00_overview.md / docs/_terminology.md 참조:
  ① validation             데이터 무결성 검증
  ② annotation             분석 구간·이동 맥락 표시
  ③ exercise_definition    이동 정의 (생체역학적 속성 객체) 로딩
  ④ preprocessing          단일 비전 데이터 품질 보정
  ⑤ normalization          신체 기준 좌표 정규화
  ⑥ motion_attribution     반복 단위 활성 측 일관성
  ⑦ features.{spatial, temporal, control}  공간·시간·제어 특징
  ⑧ biomech.{com, moment_arm, anthropometry}  생체역학적 근사 모델
  ⑨ biomarker              해석 가능한 디지털 바이오마커 (provenance 포함)
  ⑩ visualization          단계별 시각화 / 보고서

각 단계의 활성화는 configs/pipeline_default.yaml의 enabled 플래그로 제어한다.
용어 단일 정의는 docs/_terminology.md 참조.
"""
from __future__ import annotations

from movement.io import load_pose_csv  # noqa
from movement.validation import run_basic_validation  # noqa
from movement.annotation import apply_annotation, load_annotation_csv  # noqa
from movement.exercise_definition import (  # noqa
    load_exercise_definition,
    load_all_exercise_definitions,
)
from movement.preprocessing import preprocess_pose_dataframe  # noqa
from movement.normalization import normalize_pose_by_hip_torso  # noqa
from movement.motion_attribution import attribute_motion, AttributionThresholds  # noqa
from movement.visualization import (  # noqa
    create_pose_animation,
    create_pose_comparison_animation,
    plot_reliability_overlay,
    plot_joint_angle_timeseries,
    plot_rep_timeline,
    plot_attribution_chart,
    plot_biomarker_radar,
)
from movement.pipeline import load_pipeline_config, run_pipeline  # noqa
from movement.features import FeatureRecord  # noqa
from movement.biomech import BiomechRecord  # noqa
from movement.biomarker import BiomarkerRecord, from_feature_record, from_biomech_record  # noqa

__all__ = [
    # I/O
    "load_pose_csv",
    # ① 데이터 검증
    "run_basic_validation",
    # ② Annotation
    "apply_annotation",
    "load_annotation_csv",
    # ③ 이동 정의
    "load_exercise_definition",
    "load_all_exercise_definitions",
    # ④ 전처리
    "preprocess_pose_dataframe",
    # ⑤ 정규화
    "normalize_pose_by_hip_torso",
    # ⑥ 귀속
    "attribute_motion",
    "AttributionThresholds",
    # ⑦ 특징 (하위 모듈에서 직접 import 권장)
    "FeatureRecord",
    # ⑧ 생체역학적 근사 (하위 모듈에서 직접 import 권장)
    "BiomechRecord",
    # ⑨ 지표화
    "BiomarkerRecord",
    "from_feature_record",
    "from_biomech_record",
    # ⑩ 시각화
    "create_pose_animation",
    "create_pose_comparison_animation",
    "plot_reliability_overlay",
    "plot_joint_angle_timeseries",
    "plot_rep_timeline",
    "plot_attribution_chart",
    "plot_biomarker_radar",
    # 파이프라인 러너
    "load_pipeline_config",
    "run_pipeline",
]
