# 08. 시각화 (Visualization)

본 단계는 분석 단계의 각 결과를 사람이 검토 가능한 형태로 표현한다. 단일 단계가 아니라, 분석 단계 전반에 걸쳐 호출 가능한 함수 집합이다.

> 용어는 [`_terminology.md`](_terminology.md)의 단일 정의를 따른다.

---

## 1. 본 단계의 역할

본 단계는 분석 결과의 두 가지 용도를 지원한다.

```text
1. 진단(diagnostic)
   원본 데이터, 전처리 결과, 정규화 효과 등을 개발·디버깅 시 점검한다.

2. 결과 전달(result communication)
   바이오마커 결과, 특징 분포, 동작 품질 지표를 연구 검토에 적합한 형태로 제시한다.
```

연구 보고서·논문에 그대로 들어갈 그림은 vector(svg/pdf)로 저장한다.

## 2. 분석 단계와의 대응

각 분석 단계 후에 호출 가능한 시각화 함수가 존재한다.

```text
Pose CSV
→ ① 데이터 검증           → 프레임 커버리지 / 결측값 히트맵
→ ② Annotation             → 반복 경계, 구간 라벨 타임라인
→ ③ 운동 정의             → (좌표 출력 없음, 시각화 없음)
→ ④ 전처리                → 신뢰도 마스크 오버레이, before/after 비교
→ ⑤ 정규화                → raw vs normalized skeleton 비교
→ ⑥ 귀속                  → 반복별 활성 측 할당 차트
→ ⑦ 특징 추출             → 관절각 시계열, ROM bar, 좌우 대칭성 차트
→ ⑧ 생체역학적 근사 모델링  → CoM 궤적, 분절 단위 부하 분포 차트
→ ⑨ 지표화                → 바이오마커 radar chart / 요약 차트
```

## 3. 현재 구현된 기능

### 3-1. 3D 포즈 애니메이션

```python
from movement.visualization import create_pose_animation
from movement.config import LANDMARKS, CONNECTIONS

fig = create_pose_animation(
    df,
    landmarks=LANDMARKS,
    connections=CONNECTIONS,
    coord_mode="raw",       # "raw" or "norm"
    frame_duration=100,     # ms per frame
    show_text=True,
)
fig.show()
```

Plotly 기반 인터랙티브 그림. Play / Pause 버튼과 프레임 슬라이더 제공.

매개변수:

```text
coord_mode     "raw"  — 원본 <landmark>_x/y/z 컬럼 사용
               "norm" — 정규화 <landmark>_norm_x/y/z 컬럼 사용
frame_duration 재생 속도 (ms)
show_text      랜드마크 명 라벨 표시
```

### 3-2. Raw vs 정규화 비교

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

두 좌표계를 색상 차이(파랑=raw, 빨강=normalized)로 한 그림에 겹쳐 보여준다. ⑤ 정규화 단계 디버깅용.

## 4. 예정 기능

각 항목은 분석 단계 하나에 대응된다.

### 4-1. 전처리 신뢰도 오버레이

목적: 각 프레임에서 어떤 랜드마크가 unreliable로 표시되었는지 표시.

```text
입력 : <landmark>_reliable 컬럼이 부착된 pre_df
출력 : 2D 히트맵 (frames × landmarks), 신뢰도로 채색
       선택: unreliable 랜드마크가 강조된 3D 포즈 애니메이션
```

가시도 게이팅, 분절 길이, 관절각, 속도 점검의 감사용.

### 4-2. 전처리 Before / After 비교

목적: 보간·평활화 전후의 좌표 궤적 비교.

```text
입력 : 원본 df 와 pre_df
출력 : 랜드마크별 x/y/z 시계열, unreliable 프레임은 음영 처리
```

### 4-3. 관절각 시계열

목적: 단일 시퀀스에 대한 관절각(도) 시계열 표시.

```text
입력 : pre_df 또는 norm_df, 운동 정의의 angle_definitions
출력 : 관절별 line plot, 생리학적 한계 band 음영 표시
```

ROM 점검과 각도 위반 프레임 식별의 1차 도구.

### 4-4. 반복 경계 타임라인

목적: 반복·수행 단계 분할을 타임라인 위에 표시.

```text
입력 : segment_type, set_id, rep_id, phase 컬럼이 부착된 df
출력 : frame index 위 가로 bar chart
```

### 4-5. 귀속 단계 반복별 차트

목적: 반복별 motion energy 비교를 시각화.

```text
입력 : 귀속 보고서 (반복별 활성 측 결정)
출력 : 반복별 left vs right motion energy bar chart
       색: 녹색=기대와 일치, 빨강=불일치
```

### 4-6. 특징 분포 차트

목적: 반복·조건 간 특징값 비교.

```text
영역별 차트 (예정):
  공간(spatial)  : 관절별 ROM 범위 bar, 반복별 좌우 대칭성 지수
  시간(temporal) : tempo line chart, 반복별 변동성(CV) bar chart
  제어(control)  : 안정성 산점도(프레임별 CoM 변위), 보상 움직임 플래그 타임라인
```

### 4-7. 바이오마커 Radar Chart

목적: 모든 바이오마커 차원을 한 그림에 요약.

```text
입력 : 바이오마커 표 (⑨ 지표화 산출)
출력 : radar / spider chart
       각 축 = 한 바이오마커, 기대 범위 band 표시
```

연구 검토용 최종 출력 시각화.

## 5. 좌표 모드 규약

`coord_mode` 매개변수를 받는 모든 시각화 함수는 다음 규약을 따른다.

```text
"raw"  : <landmark>_x, <landmark>_y, <landmark>_z 컬럼
"norm" : <landmark>_norm_x, <landmark>_norm_y, <landmark>_norm_z 컬럼
```

정규화 좌표는 ⑤ 정규화 단계 후에만 사용 가능하다.

## 6. 구현 노트

- 인터랙티브 3D 포즈 애니메이션: Plotly (JupyterLab에서 인터랙티브)
- 진단·결과 차트(예정): matplotlib + seaborn (논문 그림 일관성을 위해)

```text
인터랙티브 포즈 애니메이션  : plotly
진단 / 결과 차트            : matplotlib + seaborn
논문용 출력 형식            : svg / pdf
```

본 단계의 함수는 입력 데이터프레임을 변경하지 않는다. 모든 함수는 데이터프레임을 받아 figure 객체를 반환한다.

## 7. 노트북

각 분석 단계는 시각화 셀을 포함하는 테스트 노트북을 갖는다.

```text
notebook/03_raw_visualization_test.ipynb     → 3D 포즈 애니메이션 (raw)
notebook/04_normalization_test.ipynb         → raw vs normalized 비교
notebook/07_preprocessing_test.ipynb         → 신뢰도 마스크, 분석 단계 통합
notebook/08_motion_attribution_test.ipynb    → 반복별 motion energy
notebook/09_feature_extraction_test.ipynb    → 특징 시각화 (예정)
```

⑦ 특징 추출과 ⑨ 지표화 구현 시 전용 시각화 노트북이 추가된다.
