# 운동 작성 노트북 (Exercise Authoring Notebook)

**문서 버전:** 0.2.0
**최종 갱신:** 2026-05-21
**영문 동기화:** [docs_eng/practical_protocols/exercise_authoring_notebook.md](../../docs_eng/practical_protocols/exercise_authoring_notebook.md)는 동일 내용의 영문 번역본이다.

본 문서는 새 운동 추가를 위한 임시 notebook-first workflow를 정의한다.
수행 지침이나 촬영 지침이 아니다. Notebook은 작은 `exercise_authoring_spec`을 만들고,
생성 YAML artifact를 preview한 뒤, canonical file 갱신 전에 연구자 검토용 draft를 작성한다.

---

## 1. 현재 결정 (Current Decision)

별도 web app보다 notebook UI를 먼저 사용한다.

```text
reason 1   현재 검증 흐름이 notebook 중심
reason 2   YAML preview와 연구자 검토를 한 화면에서 수행 가능
reason 3   운동 확장 전에 split-YAML schema를 검증 가능
reason 4   향후 web UI도 같은 spec과 generator를 재사용 가능
```

첫 버전에는 새 UI dependency가 필요하지 않다. 셀 변수, 표, YAML text preview로 충분하다.
widget 또는 web framework dependency는 package 추가 전에 별도로 결정한다.

## 2. 작성 흐름 (Authoring Flow)

```text
Notebook selections
→ exercise_authoring_spec
→ deterministic generator
→ draft YAML preview
→ researcher review
→ canonical YAML files
```

Core rules:

```text
UI input은 작고 연구자 친화적이어야 함
동일 input은 동일 YAML을 생성
draft는 data/processed/authoring_drafts/<exercise_id>/ 아래 작성
canonical YAML은 명시 승인 없이 덮어쓰지 않음
generated fields와 review-required fields를 분리
생성 text는 임상 진단, 임상 효과 주장, 절대 힘/토크 표현을 피함
```

## 3. Authoring Spec

예시:

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

이 spec은 draft input이며 pipeline이 직접 소비하는 실행 기준 문서가 아니다.

## 4. 생성 산출물 (Generated Artifacts)

하나의 spec은 네 artifact family를 생성한다:

```text
data/definitions/exercises/<exercise_id>.yaml
    exercise identity

data/definitions/analysis_profiles/<exercise_id>.yaml
    segmentation, landmarks, angle definitions, feature domains, quality overrides

data/protocols/performance/<exercise_id>.yaml
    target sets/reps, count unit, side sequence, participant cues,
    analysis-disrupting performance patterns

data/protocols/camera/<exercise_id>.yaml
    recommended zones, height, observation purpose, view-metric reliability
```

Interpretation rules와 feature-meaning text는 별도 display layer로 유지한다.
Loader는 split YAML artifact와 legacy combined exercise YAML을 모두 지원한다.

## 5. 검토 경계 (Review Boundary)

자동 생성 가능:

```text
exercise identity and classification
support/contact template
draft phase model
landmark set and draft angle triplets
rep/phase segmentation templates
performance count template
draft camera recommendation
```

연구자 검토 필요:

```text
compensation candidates and implementation feasibility
view-metric reliability
quality thresholds and scoring eligibility
clinical meaning text
exercise-specific exception rules
naming and stage consistency with existing exercises
```

Draft artifact는 다음 metadata를 포함한다:

```yaml
status: draft
generated_by: exercise_authoring_notebook
requires_review:
  - compensation_candidates
  - view_metric_reliability
  - quality_rules
  - clinical_meaning
```

## 6. Notebook 목표 (Notebook Target)

Target notebook:

```text
notebook/16_exercise_authoring_test.ipynb
```

Required cell flow:

```text
1. autoreload
2. registry loading
3. authoring spec input/selection
4. exercise identity preview
5. analysis profile preview
6. performance protocol preview
7. camera protocol preview
8. review checklist
9. draft YAML write
```

Notebook cell은 YAML assembly를 다시 구현하지 말고
`src/movement/definitions/exercise_authoring.py`를 호출해야 한다.

## 7. 코드 매핑 (Code Mapping)

```text
src/movement/definitions/exercise_authoring.py
    ExerciseAuthoringSpec
    load_authoring_registries()
    validate_authoring_spec()
    generate_authoring_artifacts()
    artifact_to_yaml()
    draft_artifact_paths()
    write_authoring_draft_artifacts()

data/registries/
    exercise_authoring_schema.yaml
    movement_patterns.yaml
    support_templates.yaml
    phase_templates.yaml
    landmark_sets.yaml
    analysis_templates.yaml
    performance_templates.yaml
    camera_templates.yaml
```

향후 web UI는 같은 spec과 generator를 호출해야 한다. canonical YAML을 직접 조립하지 않는다.
