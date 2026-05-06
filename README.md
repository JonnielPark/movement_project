# Movement Project

박사학위 논문 연구 — 단일 비전(monocular, 모바일 카메라) 3D 포즈 데이터로부터 신체 동작의
질을 생체역학적으로 정량화하여 해석 가능한 디지털 바이오마커(digital biomarker)로 표현하는
분석 프레임워크.

저장소: <https://github.com/JonnielPark/movement_project>

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
⑥  Phase Segmentation  반복 내 기구학적(kinematic) 구간의 반자동 분할
⑦  Motion Attribution  반복별 활성 측(active-side) 일관성
⑧  Feature Extraction  공간/시간/제어 피처 (반복 + 구간 단위)
⑨  Biomech Proxy       CoM · 모멘트 암(moment arms) · load-shift 추세
⑩  Biomarker Derivation 해석 가능한 디지털 바이오마커 + 해석 규칙
⑪  Visualization       단계별 시각화 및 보고               [부분]
⑫  Simulation          강건성 조건 주입(injection)         [부분]
```

단계 활성화는 `configs/pipeline_default.yaml`의 `enabled` 플래그로 제어된다.

---

## 구현 상태 (2026-05-05)

### 완료

| 영역 | 모듈 / 파일 | 비고 |
|---|---|---|
| Pose I/O 및 설정 | `io.py`, `config.py` | CSV 로딩, 랜드마크/연결 정의 |
| ① Validation | `validation.py` | 구조적 무결성 리포트 |
| ② Annotation | `annotation.py` | 프레임 단위 메타데이터 병합; `phase` 칼럼 예약 |
| ③ Exercise Definition | `exercise_definition.py` | YAML 로더 + 검증기 + generic 폴백; `PhaseSegmentationSpec` |
| ④ Preprocessing | `preprocessing.py` | 가시성 게이팅, 분절 일관성, 각도 한계, 속도 이상값, 좌·우 swap, 보간, 평활화 |
| ⑤ Normalization | `normalization.py` | 골반 중심 평행이동 + 몸통 길이 중앙값 척도 |
| ⑥ Phase Segmentation | `segmentation.py` | SG 평활 변곡 검출; Descent / Ascent / Bottom\_Hold; multi-inflection 정책; 4개 운동 YAML 모두 v0.2.0 |
| ⑦ Motion Attribution | `motion_attribution.py` | 반복별 활성 사지(active-limb) 일관성; conservative / auto-correct 모드 |
| ⑧ Feature Extraction | `features/` | ROM · 대칭(symmetry) · 형태(shape) · 템포 · 변동성 · CoM 안정성 · 보상 규칙 (`knee_valgus`, `lateral_pelvic_shift`, `excessive_trunk_flexion`, `heel_lift`, `pelvic_rotation`); 반복 단위 + **구간 단위** 방출; `summarize_phase_to_rep()` |
| ⑨ Biomech Proxy | `biomech/` | CoM range/path · 무릎/엉덩이 모멘트 암(가시성 가중) · **load-shift OLS slope** (`biomech/load_shift.py`, §6.5) |
| ⑩ Biomarker Derivation | `biomarker/` | Z-score 감점 · 동적 하한(dynamic floor) · 도메인 종합 점수 · **YAML 기반 해석 규칙** (`biomarker/interpretation.py`, §7.3) |
| 임상 매핑 | 임상 매핑 문서, `data/definitions/clinical/` | §5.5/§5.6 운동별 피처 × 생체역학적 의미 표 + 대시보드 툴팁용 YAML 미러 |
| 해석 규칙 | `data/definitions/interpretation_rules/` | §7.3 규칙 엔진; 4개 운동 × 5–7개 규칙; 금지 어휘 검증 완료 |
| 파이프라인 러너 | `pipeline.py` | 단계 ①–⑩ 결선 |
| 단위 테스트 | `tests/` | `test_biomech_load_shift.py` (17건), `test_interpretation.py` (20건) |

### 부분 완료

| 영역 | 모듈 | 미완 |
|---|---|---|
| ⑪ Visualization | `visualization.py` | Biomech overlay · attribution 히트맵 · 레이더 · 강건성 민감도 차트 (→ Task B) |
| ⑫ Simulation | `simulation/` | 실험 러너 + 시점(viewpoint) 변동 왜곡 (→ Task A) |

### 계획 (방어 이전)

| 과업 | 산출물 | 학위논문 § |
|---|---|---|
| E — FMS 연계 | FMS 연계 문서 + `data/definitions/clinical/fms_mapping.yaml` | §7.4 |
| A — 강건성 러너 | `scripts/run_robustness_experiment.py` | §8 |
| B — 시각화 차트 | provenance 중심 차트 함수 6개 | §11 |
| F — CDSS 대시보드 | `dashboard/app.py` (Streamlit + phantom 3D) | §7.5 |

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
│   ├── reference/                   # baseline_zscore.json (합성 정상 베이스라인)
│   └── processed/                   # 파이프라인 단계별 중간·최종 산출물 (.gitignore)
├── docs/
│   ├── terminology.md               # 모든 도메인 용어의 단일 진실원
│   ├── overview.md                  # 프레임워크 개요
│   ├── pipeline/                    # 파이프라인 ① ~ ⑫ 단계 문서
│   │   └── 01_data_format.md ~ 12_insilico_simulation.md
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

README에서는 최상위 문서만 버전 추적한다. `pipeline/` 및 `clinical/` 내부 문서의 목록과 버전은 [docs/overview.md](docs/overview.md)의 문서 인덱스에서 추적한다.

| 버전 | 파일 | 내용 | 영문 동기화 |
|---|---|---|---|
| 1.0.0 | [docs/terminology.md](docs/terminology.md) | 모든 도메인 용어의 단일 진실원 | [docs_eng/terminology.md](docs_eng/terminology.md) |
| 1.0.0 | [docs/overview.md](docs/overview.md) | 프레임워크 개요 및 세부 문서 인덱스 | [docs_eng/overview.md](docs_eng/overview.md) |

영문 문서는 동일한 구조로 `docs_eng/`에 동기화되어 있다.

---

## 데이터 정책 (Data Policy)

본 프로젝트는 영상 자체를 다루지 않고 영상에서 추출된 **관절 포인트 시계열(CSV)** 만 분석 대상으로 한다.

**커밋 가능.**

- `data/pose/sample/` — 코드로 임의 생성한 합성/데모 관절 포인트 CSV
- `data/pose/mediapipe/` — MediaPipe로 추출한 관절 포인트 CSV
- `data/definitions/` — 운동 정의, 해석 규칙, 임상 매핑 YAML
- `data/reference/` — 합성 정상 베이스라인 등 기준 통계

**커밋하지 않음 (`.gitignore`).**

- 파이프라인 산출물 — `data/processed/`

**주의.** 커밋 가능한 CSV에 피험자 이름·생년월일 등 직접 식별자가 포함되어 있다면 익명 ID로 치환한 뒤 커밋한다. 식별 정보 사이드카가 필요해지면 먼저 경로와 `.gitignore` 규칙을 문서화한 뒤 추가한다.

---

## 연구 범위 (Scope)

본 프로젝트는 임상 효능(clinical efficacy)이 아닌 **공학적 실현 가능성과 강건성 검증**을 목표로 한다.
모든 지표는 상대값(torso\_length\_ratio, degree, dimensionless\_cv)이다.
절대 힘 단위(N, N·m, kg)는 계산되지 않으며 소스 코드에 등장해서는 안 된다.

---

## 라이선스 (License)

TBD.
