# 운동 작성 노트북 (Exercise Authoring Notebook)

**문서 버전:** 0.1.1
**최종 갱신:** 2026-05-16
**영문 동기화:** [docs_eng/practical_protocols/exercise_authoring_notebook.md](../../docs_eng/practical_protocols/exercise_authoring_notebook.md)는 동일 내용의 영문 번역본이다.

본 문서는 새 운동을 만들 때 사용할 임시 UI 개발 방식을 정의한다. 현재 단계에서는 별도 웹앱보다
Jupyter notebook 기반 authoring UI를 먼저 만든다. 목적은 드롭다운, 체크박스, 짧은 입력값으로
운동 초안을 만들고, 이를 여러 YAML 산출물로 나누어 생성하는 흐름을 검증하는 것이다.

이 문서는 실제 운동 수행 지침이나 촬영 지침이 아니다. 수행 지침은
[exercise_performance_protocol.md](exercise_performance_protocol.md), 촬영 지침은
[camera_protocol.md](camera_protocol.md)를 따른다.

---

## 1. 현재 결정

현재 개발 단계에서는 notebook UI를 우선한다.

이유:

1. 기존 검증 흐름이 notebook 중심이므로 새 웹 프레임워크를 도입하지 않아도 된다.
2. 사용자가 선택한 값과 생성될 YAML preview를 한 화면에서 확인하기 쉽다.
3. 4대 대상 운동의 기존 YAML을 분리하기 전에 authoring schema를 빠르게 검증할 수 있다.
4. 나중에 웹 UI를 만들더라도 같은 authoring spec과 generator를 재사용할 수 있다.

초기 버전은 별도 의존성 없이 셀 변수, 표 형태 preview, YAML text preview로 시작한다.
`ipywidgets` 같은 위젯 의존성이 필요하다고 판단되면, 새 패키지 추가 전에 별도로 결정한다.
Streamlit, Dash, React 기반 대시보드는 현재 우선 구현 범위가 아니다.

현재 구현 파일:

```text
src/movement/definitions/exercise_authoring.py
    ExerciseAuthoringSpec, registry loader, deterministic artifact generator,
    draft writer, overwrite protection

data/registries/
    exercise_authoring_schema.yaml
    movement_patterns.yaml
    support_templates.yaml
    phase_templates.yaml
    landmark_sets.yaml
    analysis_templates.yaml
    performance_templates.yaml
    camera_templates.yaml

notebook/16_exercise_authoring_test.ipynb
    생성 draft YAML을 preview하는 notebook prototype
```

---

## 2. 설계 원칙

notebook은 최종 데이터 구조를 직접 손으로 편집하는 장소가 아니다. 사용자는 하나의 작은
`exercise_authoring_spec`을 작성하고, generator가 필요한 YAML들을 자동 생성한다.

```text
Notebook selections
→ exercise_authoring_spec
→ deterministic generator
→ draft YAML preview
→ researcher review
→ canonical YAML files
```

핵심 원칙:

- 사용자가 UI에서 다루는 입력은 운동 정체성과 큰 분석 선택지만 포함한다.
- generator는 동일 입력에서 항상 같은 YAML을 만든다.
- 초안은 먼저 `data/processed/authoring_drafts/<exercise_id>/` 아래에 생성한다.
- 기존 canonical YAML은 명시적 승인 전 덮어쓰지 않는다.
- 자동 생성 가능 항목과 연구자 검토 필요 항목을 분리해 표시한다.
- 임상적 단정 표현, 질환 진단 표현, 절대 토크/힘 단위는 생성하지 않는다.

---

## 3. Authoring Spec

notebook UI가 만드는 1차 입력은 다음처럼 작게 유지한다.

```yaml
exercise_id: squat
display_name: Bodyweight Squat
movement_pattern: squat
posture_type: standing
laterality: bilateral_symmetric
support_template: bilateral_feet
primary_body_regions: [hip, knee, ankle]
primary_plane: sagittal
secondary_planes: [frontal, transverse]
phase_template: descent_ascent
counting_template: repeated_repetition
camera_template: front_oblique_lower_body
analysis_template: bilateral_lower_body_closed_chain
```

이 파일은 연구자가 직접 검토하기 쉬운 초안이며, 파이프라인이 직접 소비하는 실행 기준 파일은
아니다.

---

## 4. 생성 산출물

generator는 하나의 authoring spec에서 다음 산출물을 만든다.

```text
data/definitions/exercises/<exercise_id>.yaml
    운동 정체성만 담는 exercise definition

data/definitions/analysis_profiles/<exercise_id>.yaml
    segmentation, landmarks, angle_definitions, feature_domains, quality override,
    compensation candidate 초안

data/protocols/performance/<exercise_id>.yaml
    target sets/reps, count unit, side sequence, participant cues,
    analysis-disrupting performance patterns

data/protocols/camera/<exercise_id>.yaml
    recommended zones, height, observation purpose, view-metric reliability
```

기존 `data/definitions/interpretation_rules/<exercise_id>.yaml`과
`data/definitions/clinical/feature_meanings.yaml`은 별도 해석/표시 레이어로 유지한다.

현재 loader는 split YAML 산출물과 legacy combined exercise YAML을 모두 읽을 수 있다. Split
산출물의 경우 파이프라인은 `exercise_id`로 위 파일들을 묶은 `ExerciseContext`를 로드하고,
기존 단계에는 하위 호환 `ExerciseDefinition`을 제공한다.

---

## 5. 자동 생성과 검토 항목

자동 생성 가능:

- `exercise_id`, `display_name`, 기본 `classification`
- `support`와 contact point 초안
- 기본 `phase_model`
- landmark set과 angle triplet 초안
- 기본 `rep_segmentation` / `phase_segmentation` template
- 기본 performance count template
- camera zone / height 추천 초안

연구자 검토 필요:

- compensation candidate와 실제 구현 가능성
- view-metric reliability
- quality threshold와 scoring eligibility
- clinical meaning 문장
- 운동별 예외 규칙
- 기존 4대 운동과의 명칭/단계 일관성

검토 전 산출물에는 다음 metadata를 포함한다.

```yaml
status: draft
generated_by: exercise_authoring_notebook
requires_review:
  - compensation_candidates
  - view_metric_reliability
  - quality_rules
  - clinical_meaning
```

---

## 6. Notebook 목표

초기 notebook은 `notebook/16_exercise_authoring_test.ipynb`로 둔다.

필수 셀 흐름:

1. 표준 autoreload 셀
2. registry 로드
3. authoring spec 입력 또는 선택
4. exercise identity preview
5. analysis profile preview
6. performance protocol preview
7. camera protocol preview
8. review checklist 표시
9. draft YAML 저장

노트북은 generator를 검증하는 UI prototype이다. 핵심 생성 로직은 이미
`src/movement/definitions/exercise_authoring.py`에 있으므로, 노트북 셀은 YAML 조립을 직접
다시 구현하지 말고 이 모듈을 호출한다.

---

## 7. 향후 웹 UI와의 연결

나중에 웹 UI를 만들 경우, 웹 UI는 YAML 파일을 직접 조립하지 않는다. notebook에서 검증한
`exercise_authoring_spec` schema와 generator를 호출한다.

```text
Web UI dropdowns
→ same exercise_authoring_spec
→ same generator
→ same YAML review workflow
```

따라서 이번 단계의 핵심 산출물은 예쁜 UI가 아니라 다음 세 가지다.

1. 작고 명확한 authoring spec
2. 재사용 가능한 generator
3. 사람이 검토할 수 있는 YAML preview와 review checklist
