# 03. 운동 정의 (Exercise Definition)

**문서 버전:** 1.6.1
**최종 갱신:** 2026-06-20
**영문 동기화:** `docs_eng/pipeline/03_exercise_definition.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ③은 `exercise_id`로 exercise YAML artifact를 로드하고 `ExerciseContext`를
조립한 뒤, 후속 단계 ④-⑪이 사용하는 하위 호환 `ExerciseDefinition` 객체를 반환한다.

운동 정의는 동작이 무엇을 의미하는가를 기술한다. Annotation은 녹화 안에서 그 동작이 어디서
발생했는가를 기술한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV + annotation + exercise YAML artifacts
→ ① Validation
→ ② Annotation                    exercise_type, pattern, recording metadata
→ ③ Exercise Definition           ← 본 단계
→ ④ Preprocessing                 laterality, landmarks, quality_rules
→ ⑤ Normalization
→ ⑥ Canonicalization              coordinate-candidate priors
→ ⑦ Segmentation                  rep/phase settings
→ ⑧ Motion Attribution            laterality, side_sequence
→ ⑨ Feature Extraction            feature_domains, joint_actions
→ ⑩ Biomech Proxy                 biomechanical_focus
→ ⑪ Biomarker Derivation          compensation_candidates
```

운동별 동작은 가능한 한 Python 분기가 아니라 YAML 데이터로 표현한다.

---

## 2. Split YAML 책임 경계 (Split YAML Ownership)

현재 대상 운동은 네 종류의 연결된 YAML artifact를 사용한다.

```text
data/definitions/exercises/<exercise_id>.yaml
    운동 정체성: classification, support, phase model, tags, notes.

data/definitions/analysis_profiles/<exercise_id>.yaml
    분석 동작: landmarks, angle definitions, segmentation settings,
    feature domains, biomechanical focus, compensation candidates, quality rules.

data/definitions/analysis_presets.yaml
    segmentation, landmark/angle set, quality rule을 재사용하기 위한 분석 block.
    Preset은 반복 YAML을 줄이지만 운동 정체성을 숨기면 안 된다.

data/protocols/performance/<exercise_id>.yaml
    피험자 안내 프로토콜: planned sets/counts, count unit, side sequence,
    completion policy, cues, analysis-disrupting performance patterns.

data/protocols/camera/<exercise_id>.yaml
    촬영 프로토콜: recommended zones/heights, view-metric reliability.
```

Loader는 이 artifact들을 runtime `ExerciseDefinition` 형태로 병합한다. Legacy combined YAML은
하위 호환 목적으로만 허용하며, 새 작업은 split artifact를 사용한다.

Analysis profile은 재사용 preset block을 선택할 수 있다.

```yaml
exercise_id: squat
version: 0.5.2
presets:
  segmentation: resistance_vertical_hip
  landmark_set: lower_body_hip_knee_ankle
  quality_rules: lower_body_standard

biomechanical_focus: ...
compensation_candidates: ...
feature_domains: ...
```

Preset expansion은 validation 전에 일어난다. 운동별 profile에 명시된 field는 선택한 preset
field를 override한다. Dict는 재귀적으로 merge하고, list와 scalar 값은 preset 값을 대체한다.
Preset은 반복되는 분석 mechanics에만 허용한다. `classification`, `support`, `phase_model`,
피험자 안내 protocol, camera protocol, scoring policy는 각자의 artifact에 남겨야 하며, 그래야
향후 운동이 hidden Python branch 없이 달라질 수 있다.

---

## 3. 현재 및 향후 운동 범위 (Current And Future Exercise Coverage)

현재 canonical exercise ID:

```text
squat
lunge
pike_pushup
plank_shoulder_tap
generic                  fallback only
```

스키마는 이 4개 운동 밖으로도 확장 가능해야 한다. 새 운동은 다른 laterality, posture, support,
phase model, count unit, camera zone, feature availability를 도입할 수 있다. 다만 새로운
분석 능력이 정말 필요한 경우가 아니라면 stage-level hardcoded branch를 추가하지 않는다.

향후 운동은 notebook-first authoring flow에서 draft split YAML로 시작한 뒤, 연구자 검토 후
canonical YAML로 승격한다.
[exercise_authoring_notebook.md](../practical_protocols/exercise_authoring_notebook.md)를 참조한다.

승격 전에는 local authoring draft bundle을 다음 생성 경로로 지정해 테스트할 수 있다.

```text
data/processed/authoring_drafts/<exercise_id>/data/definitions/exercises
```

Stage-check notebook은 선택한 test `exercise_id`를 canonical directory, git-tracked authoring
example directory, local authoring draft directory 순서로 탐색할 수 있다. Pipeline 기본값은
project-wide registry와 `generic` fallback definition을 포함하는 canonical definition directory로
유지한다.

`exercise_type`이 없거나 일치하는 YAML이 없으면 `generic.yaml`을 로드한다. Generic mode는 ROM,
tempo, stability 같은 exercise-agnostic feature만 활성화한다. Compensation biomarker는 산출하지
않는다.

---

## 4. Runtime Schema 계약

`ExerciseDefinition`이 소비하는 merged runtime shape는 다음과 같다.

```yaml
exercise_id: string
display_name: string
description: string
version: string
tags: list[string]

classification: ...
support: ...
phase_model: ...
rep_segmentation: ...
phase_segmentation: ...
performance_protocol: ...
landmarks: ...
angle_definitions: ...
joint_actions: ...
biomechanical_focus: ...
compensation_candidates: ...
feature_domains: ...
view_requirements: ...
camera_protocol: ...
view_metric_reliability: ...
quality_rules: ...
notes: string
```

모든 운동이 모든 필드를 같은 깊이로 채울 필요는 없다. 누락되거나 아직 사용할 수 없는 기능은
정상 처리로 조용히 넘기지 말고 unavailable 또는 low confidence로 보고한다.

---

## 5. 필드 계약 (Field Contracts)

### classification

거시적 운동 정체성을 정의하고 laterality에 민감한 단계를 제어한다.

```yaml
classification:
  family: lower_body | upper_body | core | full_body | balance | ...
  equipment: none | external_load | assisted | ...
  load_type: bodyweight | external_load | assisted | ...
  posture_type: standing | plank | inverted_closed_chain | kneeling | ...
  kinetic_chain: open_chain | closed_chain | mixed_chain | ...
  laterality: bilateral_symmetric | bilateral_asymmetric | alternating |
              unilateral_left | unilateral_right | unilateral_unspecified
  movement_pattern: squat | lunge | pushup | shoulder_tap | custom
  primary_plane: sagittal | frontal | transverse | multiplanar | static
  secondary_planes: list[string]
  complexity: single_joint | multi_joint | compound | whole_body
```

`laterality`는 L/R swap 처리와 motion-attribution 점검에 영향을 준다. 양측 대칭 운동은 반복별
active-side attribution을 건너뛸 수 있고, 편측/교대 운동은 active-side 또는 role metadata를
보존해야 한다.

### support and phase_model

`support`는 접촉과 체중부하 맥락을 기술한다. standing, plank, kneeling, inverted closed-chain,
향후 운동군까지 표현할 수 있어야 한다.

```yaml
support:
  base_of_support: bilateral_feet | split_stance | single_foot_left | hands_feet | ...
  contact_points: list[string]
  support_surface: floor | mat | bench | wall | ...
  weight_bearing_regions: list[string]
```

`phase_model`은 하나의 반복 또는 task cycle 구조를 기술한다.

```yaml
phase_model:
  type: resistance_phase | task_phase | static_hold | cyclic | locomotion_phase | custom
  expected_ratio: optional mapping
```

가능하면 표준 phase vocabulary를 재사용하되, 기존 family로 표현하기 어려운 운동은 `custom`을
허용한다.

### segmentation

`rep_segmentation`은 반복 경계를 만들거나 확정한다. `phase_segmentation`은 확정된 반복 내부에
phase label을 붙인다.

```yaml
rep_segmentation:
  reference_landmark: hip_center | wrist_center | shoulder_center | custom
  reference_axis: vertical | horizontal | depth | custom
  boundary_logic: local_maximum | local_minimum | zero_crossing | threshold | custom
  smoothing: optional mapping
  minimum_rep_length_frames: int

phase_segmentation:
  reference_landmark: string
  reference_axis: string
  phase_sequence: list[string]
  split_logic: local_minimum | local_maximum | multi_inflection | custom
  minimum_rep_length_frames: int
```

자동 segmentation이 불확실하면, 후속 분석은 불량 경계를 조용히 받아들이지 말고 확인된 수동
label을 사용한다.

### performance_protocol

`performance_protocol`은 피험자 안내와 계획 취득 조건을 기술한다. 하나의 protocol count가 하나
이상의 segmented atomic movement와 대응될 수 있으므로 segmentation과 분리한다.

```yaml
performance_protocol:
  prescription:
    target_sets: int
    target_count_per_set: int | float
    count_unit: repetition | left_right_pair | hold_seconds | custom
    segmentation_reps_per_count: int | float
    rest_between_sets_s: [min_s, max_s]
  side_sequence:
    mode: none | alternating_each_rep | same_side_block_then_switch | custom
    block_size_counts: int | null
    first_side_source: null | annotation.starting_side
  allowed_side_sequence_modes: list[string]
  completion:
    allow_partial_completion: bool
    recommended_sets: int
  participant_cues: list[string]
  analysis_disrupting_patterns: list[string]
```

예:

```text
lunge
    same_side_block_then_switch와 block_size_counts: 5를 사용할 수 있다.

plank_shoulder_tap
    각 tap을 atomic movement로 segment하면서, 좌우 한 쌍을 피험자 안내 기준 1회로 셀 수 있다.

향후 static hold 운동
    count_unit: hold_seconds와 static_hold phase model을 사용할 수 있다.
```

계획된 protocol 값은 여기에 둔다. 실제 녹화에서 발생한 `set_index`, `actual_rep_count`,
`failure_point_frame`, `failure_reason`은 ② Annotation 또는 recording metadata에 둔다.
Partial completion은 interpretation confidence를 낮추거나 partial completion으로 표시해야 하며,
movement-quality penalty로 직접 변환하지 않는다.

### landmarks and angle_definitions

현재 landmark model은 `mediapipe_pose_33`이다. Exercise definition은 squat template이 아니라
각 운동의 움직임에 맞춰 primary, secondary, critical, optional landmarks를 선언해야 한다.

```yaml
landmarks:
  model: mediapipe_pose_33
  primary_joints: list[string]
  secondary_joints: list[string]
  critical_landmarks: list[int | string]
  optional_landmarks: list[int | string]

angle_definitions:
  left_knee_angle: { points: [23, 25, 27], vertex: 25 }
```

향후 다른 pose model을 쓰려면 exercise YAML 의미를 바꾸기 전에 adapter 또는 mapping layer를
추가한다.

### feature, biomech, and compensation fields

```yaml
joint_actions: mapping

biomechanical_focus:
  expected_com_motion: minimal | vertical | anterior_posterior | medial_lateral |
                       rotational | multidirectional | custom
  stability_requirement: low | medium | high | very_high
  main_load_regions: list[string]
  primary_constraints: list[string]

compensation_candidates: list[string]

feature_domains:
  spatial: list[string]
  temporal: list[string]
  control: list[string]
  biomechanical_proxy: list[string]
```

구현되어 있고 관찰 가능한 compensation candidate만 biomarker를 산출한다. 선언됐지만 아직 구현되지
않은 candidate는 조용히 무시하지 말고 availability/audit logic으로 보고한다. 절대 force, torque,
clinical-diagnosis claim은 이 필드에 넣지 않는다.

### camera_protocol and view_metric_reliability

`camera_protocol`은 취득 가이드와 provenance다. 좌표 보정 규칙이 아니며 기본적으로 강제 제외를
수행하지 않는다.

```yaml
camera_protocol:
  recommended_zones: list[string]
  recommended_height: H1 | H2 | H3 | custom
  anchor: reference_mat | body_center | custom
  distance_cm: [min_cm, max_cm]
  primary_observation_purpose: list[string]
  out_of_zone_policy: warn_and_continue
  coordinate_correction: none
```

`view_metric_reliability`는 어떤 camera zone이 어떤 metric family를 뒷받침하는지 기록한다.
양측 대칭, 편측, 교대, static, 향후 task 구조까지 표현할 수 있어야 한다.

```yaml
view_metric_reliability:
  structure: bilateral_symmetric | unilateral_or_alternating | static_hold | custom
  role_labels: optional list[string]
  zones:
    Z1:
      frontal_alignment: high | moderate | low | not_assessed
      sagittal_rom: high | moderate | low | not_assessed
```

편측 또는 교대 운동에서는 camera view가 해석에 영향을 줄 수 있으므로, 단순 anatomical
left/right보다 `forward_leg`, `trailing_leg`, `active_side`, `support_side` 같은 role label을
우선한다.

### quality_rules

```yaml
quality_rules:
  minimum_visible_landmark_ratio: float
  minimum_critical_landmark_ratio: float
  max_missing_gap_frames: int
  max_interpolation_gap_frames: int
  exclude_rep_if_critical_landmark_missing: bool
  exclude_rep_if_phase_missing: bool
  allow_partial_feature_output: bool
```

이 threshold는 ④ Preprocessing과 ⑨ Feature Extraction에서 소비한다.

---

## 6. 새 운동으로 확장하기 (Extending To A New Exercise)

나머지 현재 운동과 향후 정의되지 않은 운동에는 이 체크리스트를 사용한다.

```text
1. Authoring notebook으로 draft split YAML artifact를 만든다.
2. 가장 가까운 schema family를 선택하되, posture, laterality, phase model, count unit이 다르면
   squat-like assumption에 억지로 맞추지 않는다.
3. 해당 운동의 관찰 가능한 mechanics를 기준으로 primary landmarks, critical landmarks,
   feature domains를 정의한다.
4. 피험자 안내 protocol과 segmentation unit을 분리해 정의한다.
5. View-dependent feature를 해석하기 전에 camera protocol과 view-metric reliability를 정의한다.
6. 지원되지 않는 metric은 구현과 테스트 전까지 unavailable/not_assessed로 둔다.
7. 새 field가 loader 또는 downstream behavior에 영향을 주면 test를 추가하거나 갱신한다.
8. 연구자 검토 뒤 draft YAML을 canonical file로 승격한다.
```

새 운동 추가는 보통 YAML과 test 추가로 끝나야 하며, stage-level code가 늘어나는 방향은 피한다.
코드 변경이 필요하면 먼저 `docs_eng/`에 새 개념을 기록하고 `docs/`로 동기화한다.

---

## 7. Provenance 규약 (Provenance Convention)

⑧-⑩에서 산출되는 모든 biomarker는 계산을 유발한 definition field를 가리키는 `source_fields`를
포함해야 한다.

```text
biomarker_id       : knee_valgus_index
exercise_id        : squat
definition_version : 0.5.0
source_fields      : [compensation_candidates.knee_valgus,
                      classification.primary_plane,
                      landmarks.primary_joints]
rep_id             : 2
value              : 0.13
unit               : torso_length_ratio
```

`source_fields`가 없는 biomarker는 산출하지 않는다.

---

## 8. Loader API

```python
from movement.exercise_definition import (
    load_all_exercise_definitions,
    load_exercise_definition,
)

definition = load_exercise_definition(
    exercise_id="squat",
    definitions_dir="data/definitions/exercises",
)

all_definitions = load_all_exercise_definitions("data/definitions/exercises")
```
