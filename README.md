# Movement Project

[English](README_eng.md) | 한국어

박사학위 논문 연구 — 단일 비전(monocular, 모바일 카메라) 3D 포즈 데이터로부터 신체 동작의
질을 생체역학적으로 정량화하여 해석 가능한 디지털 바이오마커(digital biomarker)로 표현하는
분석 프레임워크.

저장소: <https://github.com/JonnielPark/movement_project>

![Interpretable digital biomarker framework overview](docs/assets/framework_overview.png)

*그림. 단일 비전 기반 동작 품질 분석 프레임워크의 개념도. 그림의 6개 macro-stage는 아래
11단계 파이프라인과 선택 ⑤-1 하위 단계를 요약한 것이며, 우측의 점수와 라벨은 실제 검증
결과가 아니라 설명용 예시이다.*

---

## 연구 프레이밍 (Research Framing)

본 프로젝트는 단안 3D pose를 보정된 절대 3D 생체역학 계측값으로 보지 않고, 촬영 조건에
의존하는 움직임 관찰 신호로 해석한다. 카메라 각도, landmark 가시성, depth 추정 불확실성은
명시적 availability/confidence metadata로 표현하고, 세부 trace history는 모든 downstream
payload에 강제로 싣지 않고 stage report 또는 선택적 audit export에 둔다.

따라서 목표 biomarker 전략은 view-aware reliability-weighted 분석이다. 선택한 촬영 view에서
잘 관찰되는 feature는 강하게 반영하고, depth 의존도가 높거나 관찰 품질이 낮은 feature는
낮은 가중치로 반영하거나 low confidence 또는 not assessed로 보고한다. 이 관점에서 촬영 각도는
분석 설계 변수다. 정면 view는 frontal alignment, 측면 view는 sagittal depth와 ROM, 사선 view는
두 계열의 균형 관찰을 강조한다. 향후 더 나은 단안 pose/depth 모델, 다중 카메라, 또는 추가
센서를 사용하면 feature 신뢰도와 분석 세부도를 높일 수 있으며, 현재 단안 biomarker 논리를
부정하지 않고 확장하는 구조가 된다.

---

## 파이프라인 (Pipeline)

```text
Pose CSV  +  annotation CSV  +  exercise YAML 산출물
            ↓
①  Validation          구조적 무결성 점검
②  Annotation          프레임 단위 구간 메타데이터 (phase 칼럼 예약)
③  Exercise Definition 생체역학적 특성 객체 로딩
④  Preprocessing       단안 데이터 품질 보정
⑤  Normalization       신체 상대 좌표 정규화
    ⑤-1 Canonicalization normalization 하위 선택 analysis-evidence filter
⑥  Segmentation        관절 움직임 추적 기반 rep/phase 반자동 분할
⑦  Feature Extraction  side-role context + 공간/시간/제어 피처
⑧  Biomech Proxy       CoM · 모멘트 암(moment arms) · load-shift 추세
⑨  Biomarker Derivation 해석 가능한 디지털 바이오마커 + 해석 규칙
⑩  Visualization       단계별 시각화 및 보고               [부분]
⑪  Simulation          강건성 조건 주입(injection)         [부분]
```

단계 활성화는 `configs/pipeline_default.yaml`의 `enabled` 플래그로 제어된다.

---

## 구현 상태 (2026-07-14)

### 완료

| 영역 | 모듈 / 파일 | 비고 |
|---|---|---|
| Pose I/O 및 설정 | `core/io.py`, `core/config.py` | CSV 로딩, 랜드마크/연결 정의 |
| ① Validation | `stages/validation.py` | 구조적 무결성 리포트 |
| ② Annotation | `stages/annotation.py` | 프레임 단위 메타데이터 병합; 촬영/수행 metadata 보존; performance/failure audit 정보를 annotation report로 요약 |
| ③ Exercise Definition | `definitions/exercise_definition.py` | `ExerciseContext` 로더 + 검증기 + generic 폴백; exercise identity / analysis profile / performance protocol / camera protocol split YAML; 재사용 analysis preset; block 사이 공통 휴식을 가진 exercise-session 조합 YAML; legacy combined YAML 하위 호환 |
| ④ Preprocessing | `stages/preprocessing.py` | 가시성 게이팅, 분절 일관성, 각도 한계, 속도 이상값, 좌·우 swap, 보간, 평활화 |
| ⑤ Normalization | `stages/normalization.py`, `stages/canonicalization.py`, `stages/floor_reference.py`, `stages/corrected_3d_hypothesis.py` | 골반 중심 평행이동 + 몸통 길이 중앙값 척도; 선택 ⑤-1 analysis-evidence filter는 `normalization.canonicalization` 아래에 두며 기본 비활성화 |
| ⑥ Segmentation | `stages/segmentation.py` | `rep_segmentation` 반복 경계 검출 + 기존 `phase_segmentation` phase 라벨; 실패 지점 리포트 |
| ⑦ Feature Extraction | `features/`, `features/side_role_context.py` | Side-role context resolution, ROM · 대칭(symmetry) · 형태(shape) · 템포 · 변동성 · CoM 안정성 · 보상 규칙 (`knee_valgus`, `lateral_pelvic_shift`, `excessive_trunk_flexion`, `heel_lift`, `pelvic_rotation`); 반복 단위 + **구간 단위** 방출; registry coverage, compensation availability, analysis-disrupting detectability audit; `summarize_phase_to_rep()` |
| ⑧ Biomech Proxy | `biomech/` | CoM range/path · 무릎/엉덩이 모멘트 암(가시성 가중) · **load-shift OLS slope** (`biomech/load_shift.py`, §6.5) |
| ⑨ Biomarker Derivation | `biomarker/` | Z-score 감점 · 동적 하한(dynamic floor) · 조정 가능 점수 범위/도메인 가중치 · **YAML 기반 해석 규칙** (`biomarker/interpretation.py`, §7.3); movement quality score와 data confidence 분리 |
| 임상 매핑 | 임상 매핑 문서, `data/definitions/clinical/`, `definitions/clinical.py` | §5.5/§5.6 운동별 피처 × 생체역학적 의미 표 + 기본 FMS-like traffic-light mapping |
| 해석 규칙 | `data/definitions/interpretation_rules/` | §7.3 규칙 엔진; 보존 중인 4개 운동 rule 파일; 금지 어휘 검증 완료; 국민체조 rule은 exercise-definition 검토 후 작성 |
| 파이프라인 러너 | `pipeline.py` | 현재 구현 단계 ①–⑨ 결선; 선택 ⑤-1 `normalization.canonicalization`과 `support_plane_alignment` report 연결; legacy root `canonicalization`과 `floor_relative_correction`은 하위 호환 alias로 유지 |
| 프로토콜 메타데이터 스키마 | `definitions/exercise_definition.py`, `stages/annotation.py`, `features/side_role_context.py`, `pipeline.py`, 운동 YAML | CameraProtocol parser/validation, camera-zone warning audit, protocol count/side-sequence metadata, MediaPipe-style input 명확화 |
| 파이프라인 검증 기준선 | `segmentation.py`, `features/`, reporting records, `tests/` | 보존 중인 운동 정의 예시에서 phase segmentation, feature registry coverage, compensation availability, analysis-disrupting detectability, 선택적 audit-reference 정책, performance/failure report 검증 완료; 스쿼트와 국민체조는 정의 기반 확장성을 보여주기 위한 예시이지 framework 한계가 아님 |
| 단위 테스트 | `tests/` | 최근 full run 153개 전체 통과 |

### 부분 완료

| 영역 | 모듈 | 미완 |
|---|---|---|
| Far-side preprocessing 근거 | `stages/preprocessing.py` | 측면 촬영 반대측 landmark jitter 안정화, feature availability, data-confidence hook (→ Task B) |
| Side-role context 근거 | `features/side_role_context.py` | 구조화된 feature-context log, false-context 지표, ambiguous-repetition report (→ Task C) |
| Robustness simulation 근거 | `simulation/`, `scripts/` | viewpoint variation, compensation injection, 실험 러너, long-format output, robustness summary (→ Task C) |
| ⑩ Visualization | `reporting/visualization.py` | 논문용 정적 figure: phase segmentation, load shift, robustness sensitivity, side-role context heatmap, radar, score breakdown (→ Task D) |

### 계획 (방어 이전)

| 과업 | 산출물 | 학위논문 § |
|---|---|---|
| A — Confidence-aware zone reliability 완성 | 더 넓은 zone/role reliability mapping과 남은 zone-dependent test | §6–§8 |
| B — Structured motion-attribution correction log | Correction log, false-correction 지표, ambiguous-repetition report | §8 |
| C — Robustness simulation and experiment runner | viewpoint/compensation simulation injector, `scripts/run_robustness_experiment.py`, long-format output, robustness summary | §8 |
| D — 논문용 reporting visualization | 정적 figure 함수 6개, `save_figure()`, audit/caption metadata, `outputs/figures/` export | §11 |
| E — Clinical mapping 통합과 dashboard 결정 게이트 | FMS-like mapping coverage 확인, feature availability 연결, 필요 시 traffic-light/severity reporting 통합, dashboard 결정 게이트 | §7.4 |
| F — 유지보수와 저장소 정리 | 집중 변경 후 targeted test, 인계 전 full `python -m pytest`, cache/build 정리, 안정화된 README 개발 명령 | 개발 위생 |
| G — 선택 확장: Confidence-aware scoring fallback | 전처리 이후에도 occlusion, left/right swap, landmark jitter가 반복될 경우 feature availability policy와 confidence note 추가 | motion-attribution, robustness, reporting 이후 조건부 |
| H — 후위 canonicalization scoring-policy 게이트 | multi-recording 근거가 충분하기 전까지 ⑤-1 analysis-space 좌표를 additive/downstream-neutral 상태로 유지 | 조건부 / 후위 |

Dashboard / Phantom 3D 작업은 Task E의 결정 게이트 뒤로 보류하며, 사용자가 학위논문 구현
산출물로 채택하기 전까지는 활성 구현 과업으로 두지 않는다.

---

## 프로젝트 구조 (Project Structure)

```
movement_project/
├── configs/
│   └── pipeline_default.yaml        # 단계 토글 + 모든 런타임 파라미터
├── data/
│   ├── pose/                        # 관절 포인트 시계열 CSV
│   │   ├── sample/                  # 합성/데모 CSV
│   │   └── mediapipe/               # MediaPipe 추출 CSV
│   ├── definitions/                 # YAML 기반 분석 정의
│   │   ├── exercises/               # 운동 정체성 YAML + generic 폴백
│   │   ├── analysis_profiles/       # segmentation, landmarks, features, quality rules
│   │   ├── analysis_presets.yaml    # 재사용 analysis-profile block
│   │   ├── exercise_sessions/       # exercise block 순서 조합 + 공통 휴식 정책
│   │   ├── clinical/                # feature_meanings.yaml, fms_mapping.yaml
│   │   └── interpretation_rules/    # 보존 중인 squat/lunge/pike_pushup/plank_shoulder_tap .yaml
│   ├── protocols/
│   │   ├── performance/             # 수행 기준 count/sequence protocol YAML
│   │   └── camera/                  # 운동별 camera protocol YAML
│   ├── registries/                  # authoring dropdown/template registry
│   ├── camera/                      # camera_zones.yaml 촬영 구역 정의
│   ├── reference/                   # baseline_zscore.json (합성 정상 베이스라인)
│   └── processed/                   # 파이프라인 단계별 중간·최종 산출물 (.gitignore)
├── docs/
│   ├── assets/                       # README 및 문서용 공통 그림
│   ├── terminology.md               # 연구 특화 용어와 임상 표현 원칙
│   ├── overview.md                  # 프레임워크 개요
│   ├── practical_protocols/         # 실전 촬영 및 수행 프로토콜
│   │   ├── camera_protocol.md
│   │   ├── exercise_performance_protocol.md
│   │   └── exercise_authoring_notebook.md
│   ├── pipeline/                    # 파이프라인 ① ~ ⑪ 단계 문서
│   │   └── 00_data_format.md ~ 11_insilico_simulation.md
│   ├── clinical/
│   │   └── per_exercise_mapping.md  # §5.5/§5.6 피처 × 임상적 의미
├── notebook/                        # 역할별 노트북
│   ├── 00_setup/                    # 환경, 데이터 로딩, raw 시각화
│   ├── 10_manual_preparation/       # annotation/운동 정의 작성 및 검토 gate
│   ├── 20_stage_checks/             # 파이프라인 단계별 검증 20-31
│   ├── 30_user_evaluation/          # 사용자 recording 전체 평가
│   └── 90_local_research_review/    # 로컬 p01 연구 리뷰 표면
├── scripts/                         # 일회성 유틸리티 (베이스라인 계산 등)
├── tests/
│   ├── test_biomech_load_shift.py   # ⑧ load-shift slope 부호 + 가드 (17건)
│   └── test_interpretation.py       # ⑨ 규칙 로더 + 3 시나리오 (20건)
└── src/movement/
    ├── biomech/
    │   ├── __init__.py              # BiomechRecord · extract_rep_biomech()
    │   ├── anthropometry.py
    │   ├── com.py
    │   ├── load_shift.py            # §6.5 세트 내 부하 이전 OLS
    │   └── moment_arm.py
    ├── biomarker/
    │   ├── __init__.py
    │   ├── interpretation.py        # §7.3 YAML 규칙 엔진 → InterpretationRecord
    │   └── scoring.py               # BiomarkerScoreRecord · Z-score · 동적 하한
    ├── core/
    │   ├── config.py                # LANDMARKS, CONNECTIONS, column helpers
    │   ├── io.py                    # pose CSV loading
    │   └── utils.py                 # low-level pose/plot utilities
    ├── definitions/
    │   ├── clinical.py              # FMS-like mapping helpers
    │   ├── exercise_authoring.py    # notebook-first 운동 YAML draft generator
    │   └── exercise_definition.py   # ExerciseContext loader + schema dataclasses
    ├── features/
    │   ├── __init__.py              # extract_rep_features() · FeatureRecord
    │   ├── compensation.py          # COMPENSATION_RULES 레지스트리
    │   ├── control.py
    │   ├── spatial.py
    │   └── temporal.py
    ├── pipeline.py
    ├── reporting/
    │   └── visualization.py
    ├── simulation/
    └── stages/
        ├── annotation.py
        ├── canonicalization.py
        ├── floor_reference.py
        ├── side_role_context.py
        ├── normalization.py
        ├── preprocessing.py
        ├── segmentation.py
        └── validation.py
```

`movement.io`, `movement.validation`, `movement.normalization` 같은 기존 공개 import 경로는
호환 alias로 유지한다. 새 구현 파일을 추가할 때는 위 내부 폴더 구조를 우선 사용한다.

---

## 설치 (Installation)

Python 3.10 이상이 필요하다. 로컬 연구·개발 환경은 Python 3.11 또는 3.12를 권장한다.

```bash
git clone https://github.com/JonnielPark/movement_project.git
cd movement_project
python -m pip install -e .
# 개발 의존성 (pytest)
python -m pip install -e ".[dev]"
```

---

## 빠른 시작 (Quick Start)

```python
from movement.io import load_pose_csv
from movement.pipeline import load_pipeline_config, run_pipeline
import pandas as pd

config = load_pipeline_config("configs/pipeline_default.yaml")
df     = load_pose_csv("data/pose/sample/mediapipe_squat_synthetic.csv")
ann_df = pd.read_csv("data/pose/sample/mediapipe_squat_synthetic_annotation.csv")

df, report = run_pipeline(df, config, ann_df=ann_df)
```

파이프라인 실행 후 해석 라벨을 가져오는 방법:

```python
from movement.biomarker.interpretation import derive_interpretations

# score_records: run_pipeline / derive_biomarkers가 반환한 list[BiomarkerScoreRecord]
for score in score_records:
    for interp in derive_interpretations(score, biomech_records=biomech_records):
        print(f"[rep {score.rep_id}] {interp.rule_id}: {interp.label}")
```

---

## 테스트 (Tests)

```bash
python -m pytest -q
```

---

## 데이터 포맷 (Data Format)

입력 CSV — 필수 칼럼:

```text
frame          정수 프레임 인덱스 (단조 증가)
timestamp      시작 이후 경과 초
<landmark>_x   float
<landmark>_y   float
<landmark>_z   float
<landmark>_confidence  float 0–1  (권장)
```

전체 칼럼 명세와 세부 문서 인덱스는 [docs/overview.md](docs/overview.md)에서 추적한다.

---

## 문서 (Documentation)

README에서는 최상위 문서만 버전 추적한다. `practical_protocols/`, `pipeline/`, `clinical/` 내부 문서의 목록과 버전은 [docs/overview.md](docs/overview.md)의 문서 인덱스에서 추적한다.

| 버전 | 파일 | 내용 |
|---|---|---|
| 1.8.5 | [docs/terminology.md](docs/terminology.md) | 연구 특화 용어와 임상 표현 원칙 |
| 1.4.42 | [docs/overview.md](docs/overview.md) | 프레임워크 개요 및 세부 문서 인덱스 |
| 1.4.5 | [docs/practical_protocols/camera_protocol.md](docs/practical_protocols/camera_protocol.md) | 대상 운동별 촬영 프로토콜 |
| 1.1.2 | [docs/practical_protocols/exercise_performance_protocol.md](docs/practical_protocols/exercise_performance_protocol.md) | 대상 운동별 수행 프로토콜 |
| 1.1.2 | [docs/clinical/exercises/README.md](docs/clinical/exercises/README.md) | 운동별 상세 해석 문서 |

---

## 데이터 정책 (Data Policy)

본 프로젝트는 영상 자체를 다루지 않고 영상에서 추출된 **관절 포인트 시계열(CSV)** 만 분석 대상으로 한다.

**커밋 가능.**

- `data/pose/sample/` — 코드로 임의 생성한 합성/데모 관절 포인트 CSV
- `data/pose/mediapipe/` — MediaPipe로 추출한 관절 포인트 CSV
- `data/definitions/` — 운동 정의, 해석 규칙, 임상 매핑 YAML
- `data/camera/` — 촬영 구역과 높이 수준에 대한 공통 YAML
- `data/reference/` — 합성 정상 베이스라인 등 기준 통계

**커밋하지 않음 (`.gitignore`).**

- 파이프라인 산출물 — `data/processed/`

**주의.** 커밋 가능한 CSV에 피험자 이름·생년월일 등 직접 식별자가 포함되어 있다면 익명 ID로 치환한 뒤 커밋한다. 식별 정보 사이드카가 필요해지면 먼저 경로와 `.gitignore` 규칙을 문서화한 뒤 추가한다.

---

## 연구 범위 (Scope)

본 프로젝트는 고가의 생체역학 장비가 요구되는 **'관절 부하의 절대적 정량화(absolute quantification, 예: N, N·m, kg)'를 목적으로 하지 않는다**.

또한 특정 근육의 활성도나 타겟 근육 동원을 직접 판정하지 않는다. 관절 각도, 지지 자세,
외부 부하, 수행 속도, 개인 해부학적 차이에 따라 근육 동원 전략은 달라질 수 있으므로, 본
파이프라인의 활성 측, 상대 부하 전이, moment-arm proxy, 보상 움직임은 특정 근육 활성의
직접 증거가 아니라 관절·분절 수준의 경향성으로 해석한다.

대신, 단일 비전(monocular vision) 기반 원격 모니터링 환경에서도 범용적으로 추적 가능한 **'신체 분절 간의 상대적 부하 전이(relative load shift)'** 및 **'운동 사슬(kinetic chain)의 붕괴 패턴'**을 정량화하여, 시스템의 **공학적 실현 가능성과 강건성(robustness)을 검증**하는 데 집중한다.

따라서 본 파이프라인의 모든 생체역학적 프록시 지표는 절대적 힘·질량·길이 단위가 아니라, 사용자 신체 척도로 정규화한 상대값 또는 각도 기반 지표로 설계 및 산출된다 (예: `torso_length_ratio`, `degree`, `dimensionless_cv`, `dimensionless` 등).

현재 문서 예시는 single-block 반복 운동으로 스쿼트를, multi-block sequence 운동으로 국민체조를
사용한다. 이들은 설명용 예시이지 고정 대상 운동이나 필수 사용 조건이 아니다. 본 framework의 핵심 범위는
정의 기반 확장성이다. 즉 exercise definition, analysis profile, performance protocol,
camera protocol, feature-availability policy, scoring policy가 정의되면 같은 pipeline으로 다른
운동도 분석하고 점수화할 수 있다. 향후 점수 추적은 반복 실행 결과 위에 얹을 수 있으며,
운동에 비종속적인 이 설계를 바꾸지 않는다.

기구를 사용하는 운동이나 점프, 달리기, 방향전환처럼 고동적 또는 공간 이동이 큰 운동으로
확장하려면 기구 위치, 외부 부하 metadata, 손-기구 접촉, 지면 접촉 이벤트, 공중 phase, 전역
이동 경로, 더 복잡한 event segmentation과 camera protocol이 추가로 필요하다.

이는 임상적 효능(clinical efficacy)의 직접 증명 이전에, 단안 카메라 환경의 물리적 한계를 우회하여 의료진의 임상적 추론을 일관되게 지원할 수 있는 신뢰성 있는 XAI 구조를 우선적으로 확보하기 위함이다.

---

## 라이선스 (License)

TBD.
