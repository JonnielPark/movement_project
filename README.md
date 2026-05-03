# Movement Project

**단일 비전 데이터 기반 신체 동작의 생체역학적 수치화를 통한 해석 가능한 디지털 바이오마커 프레임워크**
*An Interpretable Digital Biomarker Framework via Biomechanical Quantification of Human Movement Based on Monocular Vision Data*

박사학위 논문 연구. 단일 모바일 카메라 기반 3D 포즈 데이터로부터 신체 동작 품질을 생체역학적으로 정량화하고, 이를 해석 가능한 디지털 바이오마커로 표현하는 분석 프레임워크의 설계와 검증을 다룬다.

- **학과 / 전공**: 융합의학과 디지털헬스케어전공
- **지도교수**: 박중현
- **연구 기간**: 2026.03 ~ 2027.05
- **저장소**: <https://github.com/JonnielPark/movement_project>
- **주요 인용**: 연구계획서 참고문헌 [1]–[9] (`docs/_terminology.md` §9 참조)

> 용어는 [`docs/_terminology.md`](docs/_terminology.md)에 단일 정의로 고정되어 있으며, 본 문서는 그 정의를 따른다.

---

## 1. 연구 배경 및 목적

최근 카메라 기반 동작 분석은 대중화되었으나, 대부분의 시스템은 단순 횟수 측정이나 관절 각도 비교에 그쳐 신체 동작의 **질적 특성**(관절 정렬, 신체 중심 안정성, 좌우 대칭성, 관절 간 협응, 보상 움직임)을 평가하는 데 한계가 있다[1][2]. 또한 단일 카메라 환경은 가용성이 높은 반면, 랜드마크 누락·심도 정보 불안정성·촬영 각도 왜곡 등 기술적 제약이 존재해 미세한 정렬 변화나 보상 움직임의 안정적 포착이 어렵다[6][7].

본 연구는 단일 비전 기반 포즈 데이터로부터 **공간적·시간적·제어적 특성**을 추출하고, 단순화된 **biomechanical proxy 모델**을 통해 관절 간 상대적 부하 분포의 경향성과 보상 움직임을 해석 가능한 지표로 표현하는 분석 체계를 제안한다[8][9]. 본 연구는 임상적 효과 입증이 아니라, 신체 동작 품질을 생체역학적으로 정량화하고 디지털 바이오마커로 구성하기 위한 **공학적 타당성·강건성 기반 연구**에 초점을 둔다[4].

## 2. 연구 핵심 아이디어

운동을 개별 동작 명칭 단위가 아니라 **운동의 생체역학적 속성 객체**(주요 관절, 지지면, 수행 단계, 보상 움직임 후보, 품질 기준 등)로 정의하고, 이 운동 정의(exercise definition)를 분석의 단위로 사용한다.

```
old framing : "스쿼트 분석 코드", "런지 분석 코드"를 따로 만든다
new framing : 운동을 생체역학적 속성 객체로 정의하고,
              모든 운동에 동일한 분석 단계(공간·시간·제어 + biomechanical proxy)를 적용한다
```

이 설계는 다음 두 가지 효과를 갖는다.

1. **해석 가능성**: 산출된 지표는 운동 정의의 어떤 속성에서 나왔는지 추적 가능 (`source_fields` provenance).
2. **확장성**: 새 운동을 추가할 때 코드 분기를 만들지 않고 YAML 파일을 작성한다.

## 3. 분석 대상 동작 (Validation Set)

분석 체계의 일관성을 검증하기 위해 다음 4가지 대표 대관절 동작을 사용한다. **분석의 단위는 동작 명칭이 아니라 운동 정의 객체**이며, 아래 4가지는 속성 공간 위의 4개 표본이다.

- 스쿼트 (squat) — 하체 체중 지지·시상면 ROM
- 런지 (lunge) — 좌우 비대칭 보상 움직임
- 파이크 푸쉬업 (pike push-up) — 상체 폐쇄 사슬·역지지 자세
- 플랭크 숄더탭 (plank shoulder tap) — 신체 중심 안정성·좌우 교번

## 4. 연구 범위 경계 (중요)

작성·구현 시 다음 경계를 넘지 않는다. 넘어야 할 경우 먼저 확인한다.

- 임상적 효과 입증이 아니라 **공학적 타당성·강건성 검증**이 목표이다.
- 절대적인 토크(N·m) 측정이 아니라 **관절 간 상대적 부하 분포의 경향성**을 산출한다.
- 임상 데이터셋 분석이 아니라 **합성 데이터 기반 시뮬레이션 검증**을 1차 검증 방법으로 사용한다.
- "임상적으로 유의하다", "질환 진단", "환자 분류" 등의 임상 단정 표현은 사용하지 않는다 (`docs/_terminology.md` §8).

## 5. 분석 단계 (Pipeline)

```text
Pose CSV
+ optional annotation file
+ exercise definition (YAML)

→ ① 데이터 검증 (Validation, 무결성 점검)
→ ② Annotation 적용 (분석 구간·운동 맥락 표시)
→ ③ 운동 정의 로딩 (생체역학적 속성 객체)
→ ④ 전처리 (단일 비전 데이터 품질 보정)
→ ⑤ 정규화 (신체 기준 좌표 변환)
→ ⑥ 귀속 / Motion Attribution (반복별 활성 측 일관성 확인)
→ ⑦ 특징 추출 (공간·시간·제어 3대 영역)
→ ⑧ Biomechanical Proxy Modeling (CoM, 모멘트 암, 인체 계측 모델)
→ ⑨ 지표화 (해석 가능한 디지털 바이오마커 + provenance)
→ ⑩ 시각화 / 보고서
```

연구계획서의 “연구 진행 개요”와 동일한 4단계 일정으로 진행한다.

| 일정 | 단계 | 본 분석 체계의 대응 |
|---|---|---|
| 2026.03 ~ 2026.05 | 연구 환경 구축 및 분석 체계 설계 | ①~③ 구현 + 운동 정의 스키마 |
| 2026.06 ~ 2026.09 | 전처리 및 동작 품질 특성 추출 | ④~⑦ 구현 |
| 2026.10 ~ 2027.01 | 생체역학적 모델링 및 지표화 | ⑧~⑨ + 합성 데이터 생성 |
| 2027.02 ~ 2027.05 | 검증 및 논문 작성 | 강건성 시뮬레이션 + 논문 |

## 6. 현재 구현 상태 (As of 2026-05)

**완료**

- 포즈 CSV 로딩 및 랜드마크 설정
- 데이터 검증 (구조 무결성)
- 3D 포즈 애니메이션 (Plotly, raw / normalized 모드)
- 좌표 정규화 (엉덩이 중심 + 시퀀스 중간값 몸통 길이)
- Annotation 마스크 적용
- 운동 정의 스키마, YAML 로더, 검증기 (generic fallback 포함)
- 전처리: 가시도 게이팅, 분절 길이 일관성, 관절각 한계, 속도 이상치, 운동-인지 좌우 라벨 스왑 검출, 단기 결손 보간, 선택적 평활화
- 분석 단계 러너: 검증→annotation→운동 정의→전처리→정규화 (이후 단계는 미구현)

**예정**

- 귀속(motion attribution): 반복 단위 활성 측 검증
- 특징 추출: 공간(ROM·대칭성·궤적), 시간(tempo·변동성), 제어(안정성·보상). `feature_domains`가 구동
- Biomechanical proxy modeling: CoM, 모멘트 암, 통계적 인체 계측. `biomechanical_focus`가 구동
- 보상 움직임 바이오마커: `compensation_candidates`가 구동
- 동작 품질 지표화: provenance 포함
- 시각화: 신뢰도 마스크 오버레이, 관절각 시계열, 특징/바이오마커 차트
- 강건성 시뮬레이션: ROM 제한, 시각 노이즈, 가려짐, 포즈 추정 불안정성

## 7. 설치

```bash
git clone https://github.com/JonnielPark/movement_project.git
cd movement_project
python -m pip install -e .
```

## 8. 빠른 사용 예

```python
from movement.io import load_pose_csv
from movement.config import (
    LANDMARKS,
    CONNECTIONS,
    make_required_columns,
    make_coordinate_columns,
    make_visibility_columns,
)
from movement.validation import run_basic_validation
from movement.visualization import create_pose_animation

df = load_pose_csv("data/sample/mediapipe_squat_synthetic.csv")

report = run_basic_validation(
    df=df,
    required_columns=make_required_columns(),
    coordinate_columns=make_coordinate_columns(),
    visibility_columns=make_visibility_columns(),
)
print(report["passed"])

fig = create_pose_animation(df, LANDMARKS, CONNECTIONS)
fig.show()
```

## 9. 입력 데이터 형식

iPIXEL EXERCITE 등 단일 카메라 포즈 추정 엔진에서 산출된 3D 좌표를 다음 CSV 형식으로 받는다.

```text
frame
timestamp
<landmark>_x
<landmark>_y
<landmark>_z
<landmark>_visibility   # 권장(필수 아님)
```

자세한 규약은 [`docs/01_data_format.md`](docs/01_data_format.md) 참조.

## 10. 문서 구성

연구계획서를 분석 체계 관점에서 모듈별로 풀어 쓴 문서들. 모든 문서는 [`docs/_terminology.md`](docs/_terminology.md)의 용어 정의를 따른다.

- [용어 정의 (Terminology)](docs/_terminology.md)
- [00. 개요 (Overview)](docs/00_overview.md)
- [01. 데이터 형식 (Data Format)](docs/01_data_format.md)
- [02. 데이터 검증 (Validation)](docs/02_validation.md)
- [03. Annotation 및 분석 구간 (Annotation & Segmentation)](docs/03_annotation_and_segmentation.md)
- [04. 운동 정의 (Exercise Definition)](docs/04_exercise_definition.md)
- [05. 전처리 (Preprocessing)](docs/05_preprocessing.md)
- [06. 정규화 (Normalization)](docs/06_normalization.md)
- [07. 귀속 / Motion Attribution](docs/07_motion_attribution.md)
- [08. 시각화 (Visualization)](docs/08_visualization.md)

## 11. 연구 윤리 / 데이터 관리

- 원본 영상, 사적 녹화물, 임상 데이터, API 키는 커밋하지 않는다.
- 안전하게 공유 가능한 합성·시연 데이터에 한해 `data/sample/`에 둘 수 있다.
- 사적/임상 데이터는 `data/raw/`, `data/private/`, `data/clinical/`에 두고 `.gitignore` 처리한다.

## 12. 라이선스

추후 결정 (TBD).
