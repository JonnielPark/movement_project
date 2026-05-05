# Movement Project

**문서 버전:** 1.0.0  
**최종 갱신:** 2026-05-06  
**버전 규칙:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)  
**영문 동기화:** `README_eng.md`는 동일 버전의 영문 번역본이다.

박사학위 논문 연구: 단일 비전(monocular, 모바일 카메라) 3D 포즈 데이터로부터 신체 동작의
질을 생체역학적으로 정량화하여 해석 가능한 디지털 바이오마커(digital biomarker)로 표현하는
분석 프레임워크.

저장소: <https://github.com/JonnielPark/movement_project>

---

## 문서 버전 관리

모든 문서는 2026-05-06부터 `1.0.0`으로 버전 표기를 시작한다. 버전 규칙은
Semantic Versioning 2.0.0의 `MAJOR.MINOR.PATCH` 형식을 따른다.

```text
MAJOR  문서 구조, 파이프라인 단계 정의, 공개 API 의미가 호환되지 않게 바뀐 경우
MINOR  새 기능/새 섹션/새 산출물 설명이 추가되었으나 기존 의미와 호환되는 경우
PATCH  오탈자, 번역, 링크, 표현 명확화처럼 의미 변화가 없는 경우
```

`docs/`는 한글 기준 문서이고, `docs_eng/`는 같은 버전과 같은 내용을 가진 영문 번역본이다.
`README_eng.md`도 본 문서의 영문 번역본일 뿐이며 별도 내용을 갖지 않는다.
`docs/code_revision_plan.md`와 `docs_eng/code_revision_plan.md`는 로컬 실행 계획 문서로 유지하며
git 업로드 대상에서 제외한다.

---

## 파이프라인

```text
Pose CSV  +  annotation CSV  +  운동 정의 YAML
            ↓
①  Validation           구조적 무결성 점검
②  Annotation           프레임 단위 구간 메타데이터
③  Exercise Definition  생체역학적 특성 객체 로딩
④  Preprocessing        단안 데이터 품질 보정
⑤  Normalization        신체 상대 좌표 정규화
⑥  Phase Segmentation   반복 내 기구학적 구간의 반자동 분할
⑦  Motion Attribution   반복별 활성 측 일관성
⑧  Feature Extraction   공간/시간/제어 피처, 반복 및 구간 단위
⑨  Biomech Proxy        CoM, 모멘트 암, load-shift 추세
⑩  Biomarker Derivation 해석 가능한 디지털 바이오마커와 해석 규칙
⑪  Visualization        단계별 시각화 및 보고                [부분]
⑫  Simulation           강건성 조건 주입                     [부분]
```

단계 활성화는 `configs/pipeline_default.yaml`의 `enabled` 플래그로 제어된다.

---

## 구현 상태

기준일: 2026-05-06

| 영역 | 모듈 / 파일 | 상태 |
|---|---|---|
| Pose I/O 및 설정 | `io.py`, `config.py` | CSV 로딩, 랜드마크/연결 정의 |
| ① Validation | `validation.py` | 구조적 무결성 리포트 |
| ② Annotation | `annotation.py` | 프레임 단위 메타데이터 병합, `phase` 칼럼 예약 |
| ③ Exercise Definition | `exercise_definition.py` | YAML 로더, 검증기, generic 폴백, `PhaseSegmentationSpec` |
| ④ Preprocessing | `preprocessing.py` | 가시성, 분절 일관성, 각도 한계, 속도 이상값, 좌우 swap, 보간, 평활화 |
| ⑤ Normalization | `normalization.py` | 골반 중심 평행이동과 몸통 길이 중앙값 척도 |
| ⑥ Phase Segmentation | `segmentation.py` | SG 평활 변곡 검출, Descent / Ascent / Bottom_Hold |
| ⑦ Motion Attribution | `motion_attribution.py` | 반복별 활성 사지 일관성, conservative / auto-correct 모드 |
| ⑧ Feature Extraction | `features/` | ROM, 대칭, 형태, 템포, 변동성, CoM 안정성, 보상 규칙 |
| ⑨ Biomech Proxy | `biomech/` | CoM range/path, 모멘트 암, load-shift OLS slope |
| ⑩ Biomarker Derivation | `biomarker/` | Z-score 감점, 동적 하한, 도메인 종합 점수, YAML 해석 규칙 |
| 임상 매핑 | `src/movement/clinical.py`, `data/clinical/` | feature 의미 매핑, FMS식 traffic-light 보조 라벨 |
| 파이프라인 러너 | `pipeline.py` | 단계 ①-⑩ 결선 |
| 단위 테스트 | `tests/` | 46건 통과 |

부분 완료:

| 영역 | 모듈 | 남은 작업 |
|---|---|---|
| ⑪ Visualization | `visualization.py` | provenance 중심 reporting chart, robustness sensitivity chart |
| ⑫ Simulation | `simulation/` | robustness experiment runner, viewpoint variation 평가 |

---

## 프로젝트 구조

```text
movement_project/
├── configs/
│   └── pipeline_default.yaml
├── data/
│   ├── exercise_definitions/
│   ├── clinical/
│   │   ├── feature_meanings.yaml
│   │   └── fms_mapping.yaml
│   ├── interpretation_rules/
│   ├── reference/
│   └── sample/
├── docs/
│   ├── _terminology.md
│   ├── 00_overview.md ~ 12_insilico_simulation.md
│   └── clinical/
├── docs_eng/
│   ├── _terminology.md
│   ├── 00_overview.md ~ 12_insilico_simulation.md
│   └── clinical/
├── notebook/
├── scripts/
├── tests/
└── src/movement/
    ├── annotation.py
    ├── biomech/
    ├── biomarker/
    ├── clinical.py
    ├── exercise_definition.py
    ├── features/
    ├── pipeline.py
    ├── segmentation.py
    └── visualization.py
```

---

## 설치

```bash
git clone https://github.com/JonnielPark/movement_project.git
cd movement_project
python -m pip install -e .
python -m pip install -e ".[dev]"
```

---

## 빠른 시작

```python
import pandas as pd

from movement.io import load_pose_csv
from movement.pipeline import load_pipeline_config, run_pipeline

config = load_pipeline_config("configs/pipeline_default.yaml")
df = load_pose_csv("data/sample/mediapipe_squat_synthetic.csv")
ann_df = pd.read_csv("data/sample/mediapipe_squat_synthetic_annotation.csv")

df, report = run_pipeline(df, config, ann_df=ann_df)
```

해석 규칙과 traffic-light 보조 라벨:

```python
from movement.biomarker.interpretation import derive_interpretations
from movement.clinical import traffic_light_for_score

for score in score_records:
    label = traffic_light_for_score(score)
    print(score.rep_id, label.label, label.meaning)

    for interp in derive_interpretations(score, biomech_records=biomech_records):
        print(interp.rule_id, interp.label)
```

---

## 테스트

```bash
pytest -q
```

현재 기준:

```text
46 passed
```

---

## 문서

| 버전 | 파일 | 내용 | 영문 번역본 |
|---|---|---|---|
| 1.0.0 | [docs/_terminology.md](docs/_terminology.md) | 용어집 | [docs_eng/_terminology.md](docs_eng/_terminology.md) |
| 1.0.0 | [docs/00_overview.md](docs/00_overview.md) | 전체 파이프라인 개요와 문서 인덱스 | [docs_eng/00_overview.md](docs_eng/00_overview.md) |
| 1.0.0 | [docs/01_data_format.md](docs/01_data_format.md) | 입력 CSV 데이터 포맷 | [docs_eng/01_data_format.md](docs_eng/01_data_format.md) |
| 1.0.0 | [docs/02_validation.md](docs/02_validation.md) | ① Validation | [docs_eng/02_validation.md](docs_eng/02_validation.md) |
| 1.0.0 | [docs/03_annotation_and_segmentation.md](docs/03_annotation_and_segmentation.md) | ② Annotation · ⑥ Phase Segmentation | [docs_eng/03_annotation_and_segmentation.md](docs_eng/03_annotation_and_segmentation.md) |
| 1.0.0 | [docs/04_exercise_definition.md](docs/04_exercise_definition.md) | ③ Exercise Definition YAML | [docs_eng/04_exercise_definition.md](docs_eng/04_exercise_definition.md) |
| 1.0.0 | [docs/05_preprocessing.md](docs/05_preprocessing.md) | ④ Preprocessing | [docs_eng/05_preprocessing.md](docs_eng/05_preprocessing.md) |
| 1.0.0 | [docs/06_normalization.md](docs/06_normalization.md) | ⑤ Normalization | [docs_eng/06_normalization.md](docs_eng/06_normalization.md) |
| 1.0.0 | [docs/07_motion_attribution.md](docs/07_motion_attribution.md) | ⑦ Motion Attribution | [docs_eng/07_motion_attribution.md](docs_eng/07_motion_attribution.md) |
| 1.0.0 | [docs/08_feature_extraction.md](docs/08_feature_extraction.md) | ⑧ Feature Extraction | [docs_eng/08_feature_extraction.md](docs_eng/08_feature_extraction.md) |
| 1.0.0 | [docs/09_biomechanical_proxy.md](docs/09_biomechanical_proxy.md) | ⑨ Biomech Proxy | [docs_eng/09_biomechanical_proxy.md](docs_eng/09_biomechanical_proxy.md) |
| 1.0.0 | [docs/10_biomarker_scoring.md](docs/10_biomarker_scoring.md) | ⑩ Biomarker Scoring | [docs_eng/10_biomarker_scoring.md](docs_eng/10_biomarker_scoring.md) |
| 1.0.0 | [docs/11_visualization.md](docs/11_visualization.md) | ⑪ Visualization | [docs_eng/11_visualization.md](docs_eng/11_visualization.md) |
| 1.0.0 | [docs/12_insilico_simulation.md](docs/12_insilico_simulation.md) | ⑫ In-silico Simulation | [docs_eng/12_insilico_simulation.md](docs_eng/12_insilico_simulation.md) |
| 1.0.0 | [docs/clinical/per_exercise_mapping.md](docs/clinical/per_exercise_mapping.md) | 운동별 feature 의미 매핑 | [docs_eng/clinical/per_exercise_mapping.md](docs_eng/clinical/per_exercise_mapping.md) |
| 1.0.0 | [docs/clinical/fms_linkage.md](docs/clinical/fms_linkage.md) | FMS식 traffic-light 매핑 | [docs_eng/clinical/fms_linkage.md](docs_eng/clinical/fms_linkage.md) |

---

## 데이터 정책

- 원본 영상, 개인 녹화본, 임상 데이터, API 키는 커밋하지 않는다.
- 공유 가능한 합성/데모 데이터만 `data/sample/`에 둔다.
- 비공개 및 처리된 데이터는 `data/raw/`, `data/private/`, `data/processed/`에 보관한다.
- 논문용 figure와 실험 결과는 기본적으로 `outputs/`에 저장하며 git 업로드 대상에서 제외한다.

---

## 연구 범위

본 프로젝트는 임상 효능이 아니라 공학적 실현 가능성과 강건성 검증을 목표로 한다.
모든 지표는 상대값(`torso_length_ratio`, `degree`, `dimensionless_cv`)이다.
절대 힘 단위(`N`, `N·m`, `kg`)는 계산하지 않는다.

---

## 라이선스

TBD.
