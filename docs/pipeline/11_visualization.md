# 11. 시각화 (Visualization)

**문서 버전:** 1.0.1
**최종 갱신:** 2026-05-06  
**영문 동기화:** `docs_eng/pipeline/11_visualization.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ⑪. ①–⑩ 러너 외부에서 독립적으로 호출된다. 진단 검사 및 임상의 대상
보고를 위해 포즈 데이터와 분석 결과를 렌더링하는 함수들의 모음.

본 설계의 골자는 **provenance 중심**이다: 검토자는 그림 1개를 읽고 각 감점을 기여 피처,
반복(rep), 구간(phase), 원천 랜드마크, 생체역학적 추론까지 역추적할 수 있어야 한다.
CDSS(Clinical Decision Support System) 관점에서, 시각적 밀도보다 해석 가능성과 직관성이 우선한다.

모든 함수는 데이터프레임 / 레코드 목록을 입력으로 받고 figure 객체를 반환한다;
입력 데이터를 수정하지 않는다. 학위논문 §7.5에 해당.

---

## 1. 역할 (Role)

```text
진단 용도         개발 및 디버깅 중 원시 데이터, 전처리, 정규화 효과 검사

결과 보고         바이오마커 점수, 피처 분포, 동작 품질 지표를
                  임상의 검토와 학위논문 그림에 적합한 검토 가능 레이아웃으로 제시
```

## 2. 파이프라인 단계 대응 (Correspondence to Pipeline Steps)

```text
① Validation 후              → 프레임 커버리지 / 결측값 히트맵
② Annotation 후              → 반복 경계 + 구간 라벨 타임라인
③ Exercise Definition 후     → (좌표 출력 없음; 시각화 없음)
④ Preprocessing 후           → 신뢰도 마스크 오버레이, 보정 전·후
⑤ Normalization 후           → 원시 vs. 정규화 골격 비교
⑥ Segmentation 후     → 평활화된 기준 궤적 + 구간 밴드
⑦ Motion Attribution 후      → 반복별 활성 측 할당 차트
⑧ Feature Extraction 후      → 관절각 시계열, ROM 막대, 대칭
⑨ Biomech Proxy 후           → CoM 궤적, 모멘트 암 오버레이
⑩ Biomarker Derivation 후    → 바이오마커 레이더, attribution 히트맵
⑫ Simulation 후              → 강건성 민감도 곡선
```

## 3. Provenance 공개 규약 (Provenance Disclosure Convention)

모든 시각화 함수는 입력 레코드의 `source_fields`를 소비하여, 호버 툴팁(인터랙티브 Plotly)
또는 캡션(정적 matplotlib)을 통해 표면화한다.

`plot_attribution_heatmap()`은 셀당 다음을 노출한다:

```text
feature_id    : control.compensation.knee_valgus.left
rep_id        : 2
phase         : Descent
value         : 0.13 (torso_length_ratio)
z_score       : 1.8
deduction     : 5.4 pts
source_fields : compensation_candidates.knee_valgus,
                landmarks.primary_joints
reasoning     : "Frontal-plane knee deviation; possible hip abductor weakness."
```

이를 통해 사용자는 그림을 떠나지 않고 `score → deduction → feature → landmark → YAML field`
사슬을 역추적할 수 있다.

## 4. 구현된 함수 (Implemented Functions)

### 4-1. create_pose_animation

Play/Pause 버튼과 frame slider를 가진 Plotly 인터랙티브 3D 포즈 애니메이션.

```python
from movement.visualization import create_pose_animation
from movement.config import LANDMARKS, CONNECTIONS

fig = create_pose_animation(
    df,
    landmarks=LANDMARKS,
    connections=CONNECTIONS,
    coord_mode="raw",        # "raw" 또는 "norm"
    frame_duration=100,      # 프레임당 ms
    height=750,
    width=1000,
    show_text=True,
)
fig.show()
```

`coord_mode`:
```text
"raw"   <landmark>_x/y/z 칼럼
"norm"  <landmark>_norm_x/y/z 칼럼 (⑤ Normalization 필요)
```

### 4-2. create_pose_comparison_animation

두 좌표 모드를 한 애니메이션에 오버레이한다 (파랑 = raw, 빨강 = normalized).
⑤ 정규화 디버깅에 사용된다.

```python
from movement.visualization import create_pose_comparison_animation

fig = create_pose_comparison_animation(
    df,
    landmarks=LANDMARKS,
    connections=CONNECTIONS,
    coord_modes=("raw", "norm"),
    names=("Raw", "Normalized"),
)
fig.show()
```

## 5. 계획된 함수 (Planned Functions)

이 함수들은 stub으로 존재한다(`NotImplementedError` 발생); 학위논문 Task B의 잔여
산출물이다 (`code_revision_plan.md` 참조).

### 5-1. plot_reliability_overlay

3D 포즈 애니메이션에 ④ 전처리 신뢰도 마스크를 오버레이한다.
신뢰 불가 랜드마크는 구분되는 색상과 크기로 렌더링된다.

```python
plot_reliability_overlay(
    df, landmarks, connections, reliability_col, coord_mode,
)
```

### 5-2. plot_joint_angle_timeseries

프레임별 관절각 시계열 (단위: degree). 반복 범위는 배경 음영으로 표시되며,
⑧ ROM 피처와 직접 비교 가능하다.

```python
plot_joint_angle_timeseries(
    df, joint_triplets, joint_labels, rep_ranges, coord_mode,
)
```

### 5-3. plot_rep_timeline

② 어노테이션 구간 라벨이 프레임 단위 수평 막대 타임라인으로 렌더링된다.
분석 구간(`use_for_analysis=True`)이 강조된다.

```python
plot_rep_timeline(df, segment_col, rep_col, set_col)
```

### 5-4. plot_attribution_chart

프레임별 ⑦ 모션 어트리뷰션 결과. 검출 vs. 기대 활성 측과 어트리뷰션 신뢰도를 표시한다.

```python
plot_attribution_chart(
    df, attribution_col, confidence_col, expected_col,
)
```

### 5-5. plot_phase_segmentation

평활화된 기준 랜드마크 궤적과 변곡 프레임 마커, phase 색상 밴드(Descent, Ascent,
Turnaround_Hold 등). ⑥ 구간 분할을 시각적으로 검증한다.

```python
plot_phase_segmentation(
    df, reference_landmark, reference_axis, phase_col,
)
```

### 5-6. plot_biomech_overlay

CoM 점과 모멘트 암 라인이 오버레이된 3D 골격(정지 또는 애니메이션).
⑨ 생체역학 프록시 출력을 기하학적 컨텍스트에서 표면화한다.

```python
plot_biomech_overlay(
    df, com_xyz, moment_arm_lines, coord_mode,
)
```

### 5-7. plot_biomarker_radar

도메인 점수 레이더 차트 (spatial / temporal / control / biomech). 시각적 비교를 위해
참조(합성 정상 베이스라인)를 선택적으로 오버레이한다.

```python
plot_biomarker_radar(
    score_records, reference_records=None,
)
```

사용자의 가장 약한 동작 품질 도메인을 한눈에 식별하는 데 유용하다.

### 5-8. plot_biomech_load_shift

세트 내 부하 전이 추세: X축은 반복 번호, Y축은 상대 모멘트 암 프록시.
`biomech.load_shift.*.slope` 지표를 시각화한다
([09_biomechanical_proxy.md](09_biomechanical_proxy.md) §7 참조).

```python
plot_biomech_load_shift(
    biomech_records, joints=("knee", "hip"),
)
```

### 5-9. plot_attribution_heatmap

⑩ 바이오마커 점수화 감점에 대한 provenance 역추적 히트맵.

```text
X축       시간 (frame 또는 phase 경계)
Y축       도메인별로 묶인 feature_id (spatial / temporal / control / biomech)
셀        감점 크기 (색상), 호버로 source_fields 공개
오버레이  ⑥ Segmentation의 phase 경계
```

```python
plot_attribution_heatmap(
    score_records, feat_records, biomech_records,
)
```

### 5-10. plot_robustness_sensitivity

`scripts/run_robustness_experiment.py`가 산출한 long-format CSV
([12_insilico_simulation.md](12_insilico_simulation.md) 참조)를 소비하여,
시뮬레이션 조건 수준에 걸친 지표별 안정성 곡선을 그린다.

```python
plot_robustness_sensitivity(
    robustness_csv_path, conditions=None, metrics=None,
)
```

## 6. 구현 노트 (Implementation Notes)

```text
3D 포즈 애니메이션         Plotly (JupyterLab에서 인터랙티브)
진단 차트                  matplotlib + seaborn
출판 출력                  save_figure(fig, path, fmt='svg')를 통한 svg / pdf
```

§5의 모든 차트에 대해 Plotly와 matplotlib 백엔드 둘 다 지원되어야 한다;
Plotly는 노트북 주도 탐색용, matplotlib은 논문 출력용. 어떤 함수도 입력 데이터프레임을
변경해서는 안 된다.

## 7. 관련 노트북 (Related Notebooks)

```text
notebook/03_raw_visualization_test.ipynb       3D 포즈 애니메이션 (raw)
notebook/04_normalization_test.ipynb           raw vs. normalized 비교
notebook/07_preprocessing_test.ipynb           신뢰도 마스크, 파이프라인 통합
notebook/09_motion_attribution_test.ipynb      반복별 동작 에너지
notebook/10_feature_extraction_test.ipynb      피처 단위 시각화
notebook/15_visualization_demo.ipynb           계획 — Task B 5종 차트 전부
```

## 8. 코드 매핑 (Code Mapping)

```text
src/movement/visualization.py        create_pose_animation,
                                     create_pose_comparison_animation,
                                     plot_reliability_overlay (stub),
                                     plot_joint_angle_timeseries (stub),
                                     plot_rep_timeline (stub),
                                     plot_attribution_chart (stub),
                                     plot_biomarker_radar (stub),
                                     ... (계획된 5-5 ~ 5-10)
src/movement/utils.py                get_frame_data, compute_plot_ranges,
                                     validate_landmark_columns
```

## 9. 향후 확장 (Planned Extensions)

- 논문 출력용 벡터 익스포트를 위한 `save_figure(fig, path, fmt='svg')` 헬퍼
- 세트 내 시각적 반복 간 비교를 위한 반복별 small-multiples 레이아웃
  (반복당 1행, 지표당 1열)
- 신뢰 음영을 가진 baseline-vs-current 레이더 사이드-바이-사이드 오버레이
- `create_pose_animation()` 출력 위에 애니메이션 phase 밴드 오버레이
- 임상의 대상 1페이지 요약을 위한 도메인별 감점 누적 막대 차트
- 임상 시연을 위한 태블릿 친화 반응형 레이아웃
- 런타임 플래그로 구동되는 축 라벨 다국어화 (한국어 / 영어)
