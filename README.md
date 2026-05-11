# Movement Project

[English](README_eng.md) | 한국어

박사학위 논문 연구 — 단일 비전(monocular, 모바일 카메라) 3D 포즈 데이터로부터 신체 동작의
질을 생체역학적으로 정량화하여 해석 가능한 디지털 바이오마커(digital biomarker)로 표현하는
분석 프레임워크.

저장소: <https://github.com/JonnielPark/movement_project>

![Interpretable digital biomarker framework overview](docs/assets/framework_overview.png)

*그림. 단일 비전 기반 동작 품질 분석 프레임워크의 개념도. 그림의 6개 macro-stage는 아래
12단계 파이프라인을 요약한 것이며, 우측의 점수와 라벨은 실제 검증 결과가 아니라 설명용 예시이다.*

---

## 파이프라인 (Pipeline)

```text
Pose CSV  +  annotation CSV  +  운동 정의 (exercise definition) YAML
            ↓
①  Validation          구조적 무결성 점검
②  Annotation          프레임 단위 구간 메타데이터 (phase 칼럼 예약)
③  Exercise Definition 생체역학적 특성 객체 로딩
④  Preprocessing       단안 데이터 품질 보정
⑤  Normalization       신체 상대 좌표 정규화
⑥  Segmentation        관절 움직임 추적 기반 rep/phase 반자동 분할
⑦  Motion Attribution  반복별 활성 측(active-side) 일관성
⑧  Feature Extraction  공간/시간/제어 피처 (반복 + 구간 단위)
⑨  Biomech Proxy       CoM · 모멘트 암(moment arms) · load-shift 추세
⑩  Biomarker Derivation 해석 가능한 디지털 바이오마커 + 해석 규칙
⑪  Visualization       단계별 시각화 및 보고               [부분]
⑫  Simulation          강건성 조건 주입(injection)         [부분]
```

단계 활성화는 `configs/pipeline_default.yaml`의 `enabled` 플래그로 제어된다.

---

## 구현 상태 (2026-05-11)

### 완료

| 영역 | 모듈 / 파일 | 비고 |
|---|---|---|
| Pose I/O 및 설정 | `io.py`, `config.py` | CSV 로딩, 랜드마크/연결 정의 |
| ① Validation | `validation.py` | 구조적 무결성 리포트 |
| ② Annotation | `annotation.py` | 프레임 단위 메타데이터 병합; 촬영/수행 provenance와 관찰 protocol metadata 보존; performance/failure provenance를 annotation report로 요약 |
| ③ Exercise Definition | `exercise_definition.py` | YAML 로더 + 검증기 + generic 폴백; `rep_segmentation`, `phase_segmentation`, `performance_protocol`, `CameraProtocolSpec`, `allowed_side_sequence_modes` |
| ④ Preprocessing | `preprocessing.py` | 가시성 게이팅, 분절 일관성, 각도 한계, 속도 이상값, 좌·우 swap, 보간, 평활화 |
| ⑤ Normalization | `normalization.py` | 골반 중심 평행이동 + 몸통 길이 중앙값 척도 |
| ⑥ Segmentation | `segmentation.py` | `rep_segmentation` 반복 경계 검출 + 기존 `phase_segmentation` phase 라벨; 실패 지점 리포트 |
| ⑦ Motion Attribution | `motion_attribution.py` | 반복별 활성 사지(active-limb) 일관성; `performance_protocol.side_sequence` 참조; conservative / auto-correct 모드 |
| ⑧ Feature Extraction | `features/` | ROM · 대칭(symmetry) · 형태(shape) · 템포 · 변동성 · CoM 안정성 · 보상 규칙 (`knee_valgus`, `lateral_pelvic_shift`, `excessive_trunk_flexion`, `heel_lift`, `pelvic_rotation`); 반복 단위 + **구간 단위** 방출; registry coverage, compensation availability, analysis-disrupting detectability audit; `summarize_phase_to_rep()` |
| ⑨ Biomech Proxy | `biomech/` | CoM range/path · 무릎/엉덩이 모멘트 암(가시성 가중) · **load-shift OLS slope** (`biomech/load_shift.py`, §6.5) |
| ⑩ Biomarker Derivation | `biomarker/` | Z-score 감점 · 동적 하한(dynamic floor) · 조정 가능 점수 범위/도메인 가중치 · **YAML 기반 해석 규칙** (`biomarker/interpretation.py`, §7.3) |
| 임상 매핑 | 임상 매핑 문서, `data/definitions/clinical/`, `clinical.py` | §5.5/§5.6 운동별 피처 × 생체역학적 의미 표 + 기본 FMS-like traffic-light mapping |
| 해석 규칙 | `data/definitions/interpretation_rules/` | §7.3 규칙 엔진; 4개 운동 × 5–7개 규칙; 금지 어휘 검증 완료 |
| 파이프라인 러너 | `pipeline.py` | 단계 ①–⑩ 결선 |
| 프로토콜 메타데이터 스키마 | `exercise_definition.py`, `annotation.py`, `motion_attribution.py`, `pipeline.py`, 운동 YAML | CameraProtocol parser/validation, camera-zone warning provenance, protocol count/side-sequence metadata, MediaPipe-style input 명확화 |
| Task A 검증 pass | `segmentation.py`, `features/`, reporting records, `tests/` | 현재 4대 운동 범위에서 A1-A6 완료: phase segmentation, feature registry coverage, compensation availability, analysis-disrupting detectability, source-field 정책, performance/failure provenance |
| 단위 테스트 | `tests/` | 프로토콜 메타데이터 스키마 대상 테스트 17개 통과. Task A6 compensation-availability audit 이후 최근 full run 99개 전체 통과 |

### 부분 완료

| 영역 | 모듈 | 미완 |
|---|---|---|
| Motion attribution 근거 | `motion_attribution.py` | 구조화된 correction log, false-correction 지표, ambiguous-repetition report (→ Task B) |
| Robustness simulation 근거 | `simulation/`, `scripts/` | viewpoint variation, compensation injection, 실험 러너, long-format output, robustness summary (→ Task C) |
| ⑪ Visualization | `visualization.py` | 논문용 정적 figure: phase segmentation, load shift, robustness sensitivity, attribution heatmap, radar, score breakdown (→ Task D) |

### 계획 (방어 이전)

| 과업 | 산출물 | 학위논문 § |
|---|---|---|
| B — Structured motion-attribution correction log | Correction log, false-correction 지표, ambiguous-repetition report | §8 |
| C — Robustness simulation and experiment runner | viewpoint/compensation simulation injector, `scripts/run_robustness_experiment.py`, long-format output, robustness summary | §8 |
| D — 논문용 reporting visualization | 정적 figure 함수 6개, `save_figure()`, source-field/caption provenance, `outputs/figures/` export | §11 |
| E — Clinical mapping 통합과 dashboard 결정 게이트 | FMS-like mapping coverage 확인, feature availability 연결, 필요 시 traffic-light/severity reporting 통합, dashboard 결정 게이트 | §7.4 |
| F — 유지보수와 저장소 정리 | 집중 변경 후 targeted test, 인계 전 full `pytest`, cache/build 정리, 안정화된 README 개발 명령 | 개발 위생 |
| G — 선택 확장: visibility-aware scoring fallback | 파일럿 촬영에서 occlusion, left/right swap, landmark jitter가 반복될 경우 feature availability policy와 confidence note 추가 | Task B-D 이후 조건부 |

Task A는 현재 4대 운동 범위에서 완료됐다. 남은 Task 알파벳은
`docs/code_revision_plan.md`의 현재 우선순위 순서를 따른다. Dashboard / Phantom 3D 작업은
Task E의 결정 게이트 뒤로 보류하며, 사용자가 학위논문 구현 산출물로 채택하기 전까지는 활성
구현 과업으로 두지 않는다.

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
│   │   ├── exercises/               # squat · lunge · pike_pushup · plank_shoulder_tap · generic
│   │   ├── clinical/                # feature_meanings.yaml, fms_mapping.yaml
│   │   └── interpretation_rules/    # squat/lunge/pike_pushup/plank_shoulder_tap .yaml
│   ├── camera/                      # camera_zones.yaml 촬영 구역 정의
│   ├── reference/                   # baseline_zscore.json (합성 정상 베이스라인)
│   └── processed/                   # 파이프라인 단계별 중간·최종 산출물 (.gitignore)
├── docs/
│   ├── assets/                       # README 및 문서용 공통 그림
│   ├── terminology.md               # 연구 특화 용어와 임상 표현 원칙
│   ├── overview.md                  # 프레임워크 개요
│   ├── practical_protocols/         # 실전 촬영 및 수행 프로토콜
│   │   ├── camera_protocol.md
│   │   └── exercise_performance_protocol.md
│   ├── pipeline/                    # 파이프라인 ① ~ ⑫ 단계 문서
│   │   └── 00_data_format.md ~ 12_insilico_simulation.md
│   ├── clinical/
│   │   └── per_exercise_mapping.md  # §5.5/§5.6 피처 × 임상적 의미
│   └── code_revision_plan.md        # 방어 이전 구현 계획 (.gitignore)
├── notebook/                        # 탐색 노트북 (00–13; 14–18 계획)
├── scripts/                         # 일회성 유틸리티 (베이스라인 계산 등)
├── tests/
│   ├── test_biomech_load_shift.py   # ⑨ load-shift slope 부호 + 가드 (17건)
│   └── test_interpretation.py       # ⑩ 규칙 로더 + 3 시나리오 (20건)
└── src/movement/
    ├── annotation.py
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
    ├── config.py
    ├── exercise_definition.py
    ├── features/
    │   ├── __init__.py              # extract_rep_features() · FeatureRecord
    │   ├── compensation.py          # COMPENSATION_RULES 레지스트리
    │   ├── control.py
    │   ├── spatial.py
    │   └── temporal.py
    ├── io.py
    ├── motion_attribution.py
    ├── normalization.py
    ├── pipeline.py
    ├── preprocessing.py
    ├── segmentation.py
    ├── simulation/
    ├── utils.py
    ├── validation.py
    └── visualization.py
```

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
pytest -q
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
<landmark>_visibility  float 0–1  (권장)
```

전체 칼럼 명세와 세부 문서 인덱스는 [docs/overview.md](docs/overview.md)에서 추적한다.

---

## 문서 (Documentation)

README에서는 최상위 문서만 버전 추적한다. `practical_protocols/`, `pipeline/`, `clinical/` 내부 문서의 목록과 버전은 [docs/overview.md](docs/overview.md)의 문서 인덱스에서 추적한다.

| 버전 | 파일 | 내용 |
|---|---|---|
| 1.4.4 | [docs/terminology.md](docs/terminology.md) | 연구 특화 용어와 임상 표현 원칙 |
| 1.4.21 | [docs/overview.md](docs/overview.md) | 프레임워크 개요 및 세부 문서 인덱스 |
| 1.2.3 | [docs/practical_protocols/camera_protocol.md](docs/practical_protocols/camera_protocol.md) | 대상 운동별 촬영 프로토콜 |
| 1.0.8 | [docs/practical_protocols/exercise_performance_protocol.md](docs/practical_protocols/exercise_performance_protocol.md) | 대상 운동별 수행 프로토콜 |
| 1.0.2 | [docs/clinical/exercises/README.md](docs/clinical/exercises/README.md) | 운동별 상세 해석 문서 |

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

현재 대상 운동은 비기구 기반의 제자리 반복 운동(structured in-place bodyweight exercises)으로
한정한다. 기구를 사용하는 운동이나 점프, 달리기, 방향전환처럼 고동적 또는 공간 이동이 큰
운동으로 확장하려면 기구 위치, 외부 부하 metadata, 손-기구 접촉, 지면 접촉 이벤트, 공중
phase, 전역 이동 경로, 더 복잡한 event segmentation과 camera protocol이 추가로 필요하다.

이는 임상적 효능(clinical efficacy)의 직접 증명 이전에, 단안 카메라 환경의 물리적 한계를 우회하여 의료진의 임상적 추론을 일관되게 지원할 수 있는 신뢰성 있는 XAI 구조를 우선적으로 확보하기 위함이다.

---

## 라이선스 (License)

TBD.
