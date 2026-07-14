# 03. 운동 정의 (Exercise Definition)

**문서 버전:** 1.7.1
**최종 갱신:** 2026-07-14
**영문 동기화:** `docs_eng/pipeline/03_exercise_definition.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ③은 `exercise_id`로 exercise YAML artifact를 로드하고 `ExerciseContext`를
조립한 뒤, 후속 단계 ④-⑨이 사용하는 하위 호환 `ExerciseDefinition` 객체를 반환한다.

운동 정의는 동작이 무엇을 의미하는가를 기술한다. Annotation은 녹화 안에서 그 동작이 어디서
발생했는가를 기술한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV + annotation + exercise YAML artifacts
→ ① Validation
→ ② Annotation                    exercise_id, execution_pattern, recording metadata
→ ③ Exercise Definition           ← 본 단계
→ ④ Preprocessing                 laterality, landmarks, quality_rules
→ ⑤ Normalization
→ ⑤-1 Optional Canonicalization    coordinate-analysis priors
→ ⑥ Segmentation                  rep/phase settings
→ ⑦ Feature Extraction            feature_domains, joint_actions, laterality, side_sequence
→ ⑧ Biomech Proxy                 biomechanical_focus
→ ⑨ Biomarker Derivation          compensation_patterns
```

운동별 동작은 가능한 한 Python 분기가 아니라 YAML 데이터로 표현한다.

---

## 2. Split YAML 책임 경계 (Split YAML Ownership)

운동 정의 체계는 운동 수준 YAML artifact와 선택적 세션 조합 artifact를 사용한다.

```text
data/definitions/exercises/<exercise_id>.yaml
    운동 정체성: classification, support, phase model, tags, notes.

data/definitions/analysis_profiles/<exercise_id>.yaml
    분석 동작: landmarks, angle definitions, segmentation settings,
    feature domains, biomechanical focus, compensation patterns, quality rules.

data/definitions/analysis_profiles/<profile_file_id>.yaml
    긴 session을 위한 선택 indexed analysis-profile file. 파일 맨 앞에는 `index`를 두고,
    section exercise YAML은 `analysis_profile_ref`로 profile entry를 가리킨다.

data/definitions/analysis_presets.yaml
    segmentation, landmark/angle set, quality rule을 재사용하기 위한 분석 block.
    Preset은 반복 YAML을 줄이지만 운동 정체성을 숨기면 안 된다.

data/definitions/exercise_sessions/<exercise_session_id>.yaml
    하나 이상의 기존 운동 정의를 순서대로 조합하는 선택 artifact.
    block 순서, 반복 횟수, 세션 수준의 단일 휴식 정책을 지정한다.

data/protocols/performance/<exercise_id>.yaml
    수행 프로토콜: planned sets/counts, count unit, side sequence,
    completion policy, cues, analysis-disrupting performance patterns.

data/protocols/camera/<exercise_id>.yaml
    촬영 프로토콜: recommended zones/heights, view-metric reliability.

data/protocols/camera/<shared_protocol_id>.yaml
    session처럼 연속 촬영되는 경우의 선택 shared camera protocol. Section exercise YAML은
    `camera_protocol_ref`로 이를 가리킨다.
```

Exercise loader는 운동 수준 artifact를 runtime `ExerciseDefinition` 형태로 병합한다.
Session loader는 참조된 각 운동 정의의 의미를 바꾸지 않고 `ExerciseSessionDefinition`
artifact를 읽는다. Legacy combined YAML은 하위 호환 목적으로만 허용하며, 새 작업은 split
artifact를 사용한다.

Analysis profile은 재사용 preset block을 선택할 수 있다.

```yaml
exercise_id: squat
version: 0.5.2
presets:
  segmentation: resistance_vertical_hip
  landmark_set: lower_body_hip_knee_ankle
  quality_rules: lower_body_standard

biomechanical_focus: ...
compensation_patterns: ...
feature_domains: ...
```

Preset expansion은 validation 전에 일어난다. 운동별 profile에 명시된 field는 선택한 preset
field를 override한다. Dict는 재귀적으로 merge하고, list와 scalar 값은 preset 값을 대체한다.
Preset은 반복되는 분석 mechanics에만 허용한다. 긴 session 예시는 여러 section profile을 하나의
indexed profile file에 둘 수 있다. Top-level `index`는 profile 순서와 section label을 기록하고,
각 `profiles` entry는 여전히 참조 section `exercise_id`로 선택된다. 이는 파일 구성 방식이지 새
movement-definition layer가 아니다. `classification`, `support`, `phase_model`, performance
protocol, camera protocol, scoring policy는 각자의 artifact에 남겨야 하며, 그래야 향후 운동이
hidden Python branch 없이 달라질 수 있다.

---

## 3. 현재 및 향후 운동 범위 (Current And Future Exercise Coverage)

현재 예시에서 사용하는 illustrative canonical exercise ID:

```text
squat
generic                  fallback only
```

보존하는 선행 개발/예시 canonical artifact:

```text
lunge
pike_pushup
plank_shoulder_tap
```

예시는 스쿼트를 single-block 반복 운동 사례로 사용한다. Lunge, pike push-up, plank shoulder tap은
선행 개발/예시 artifact로 repository에 남긴다. 이 운동들이 framework의 범위를 정의하지는 않는다.

국민체조는 `data/definitions/exercise_sessions/korean_national_gymnastics.yaml`을 통해 draft
multi-block sequence 예시로 도입한다. 현재 session은 routine의 되풀이 구간부터 시작하는 취득 및
분석용 session definition이다. 숨쉬기부터 뜀뛰기까지의 첫 진행은 취득하지도 분석하지도 않으므로,
이 프로젝트 session에서는 해당 구간을 두 번 수행하지 않는다. 이 session은 아래 순서의
section-level draft exercise definition을 조합한다. 다만 아직 review-required runtime YAML이며,
canonical 승격 전에는 section/event model, count unit, performance protocol,
feature-availability policy, scoring eligibility를 section별로 검토해야 한다. 현재 draft section의
권장 촬영 조건은 정면 camera zone(`Z1`)과 허리높이 level(`H2`)로 지정한다. View-metric
reliability와 section별 관찰 목적은 계속 section 단위 검토 대상으로 남긴다.

```text
01 breathing_start       숨쉬기
02 leg                   다리운동
03 arm                   팔운동
04 neck                  목운동
05 chest                 가슴운동
06 side                  옆구리운동
07 back_abdomen          등배운동
08 trunk                 몸통운동
09 whole_body            온몸운동
10 jumping               뜀뛰기
11 limbs                 팔다리운동
12 breathing_cooldown    숨고르기
```

이 sequence는 별도 "혼합형 운동" category를 만들기보다 검토된 section/event block을 조합하는
방식으로 표현한다.

이 session의 section exercise YAML은 다음 공유 참조를 사용한다:

```text
analysis_profile_ref.profile_file_id = korean_national_gymnastics
camera_protocol_ref.protocol_id    = korean_national_gymnastics
```

이렇게 하면 긴 sequence의 파일 수를 읽기 쉽게 줄이면서도 indexed profile file 안에서 section별
analysis-profile entry는 유지할 수 있다.

스키마는 현재 예시 artifact 밖으로도 확장 가능해야 한다. 새 운동은 다른 laterality,
posture, support, phase 또는 section model, count unit, camera zone, feature availability를
도입할 수 있다. 다만 새로운 분석 능력이 정말 필요한 경우가 아니라면 stage-level hardcoded
branch를 추가하지 않는다.

향후 운동은 notebook-first authoring flow에서 draft split YAML로 시작한 뒤, 연구자 검토 후
canonical YAML로 승격한다.
[exercise_authoring_notebook.md](../practical_protocols/exercise_authoring_notebook.md)를 참조한다.

승격 전에는 local authoring draft bundle을 다음 생성 경로로 지정해 테스트할 수 있다.

```text
data/processed/authoring_drafts/<exercise_id>/data/definitions/exercises
```

Stage-check notebook은 선택한 test `exercise_id`를 canonical directory, local authoring draft
directory, git-tracked authoring example directory 순서로 탐색할 수 있다. 이렇게 하면 방금 생성한
local draft가 review 중에는 example bundle보다 우선한다. Pipeline 기본값은 project-wide registry와
`generic` fallback definition을 포함하는 canonical definition directory로 유지한다.

Authoring draft 승격은 local review보다 엄격한 계약을 따른다.

```text
draft artifact id       draft_<exercise_name> 또는 다른 review-only id
canonical artifact id   squat 같은 안정적인 public exercise_id
runtime directories     data/definitions/* 및 data/protocols/*
status/requires_review  official top-level YAML에서 제거
authoring provenance    authoring_provenance에 보존
baseline status         승격된 정의 기준으로 재생성하기 전까지 invalid
```

승격은 단순 파일명 변경이 아니다. 승격된 artifact는 모든 split YAML에서 canonical
`exercise_id`를 사용해야 하고, authoring 선택값은 provenance로 보존해야 하며,
review-required field는 해결하거나 명시적으로 deferred 상태로 남긴 뒤 runtime canonical
artifact를 대체해야 한다. Stage-check notebook은 그 후 draft bundle이 아니라 canonical
`exercise_id`를 다시 사용해야 한다.

기존 score baseline은 승격 후 조용히 재사용하면 안 된다. Baseline entry는 그것을 생성한 운동
정의와 feature schema에 대해서만 유효하다. 승격된 authoring artifact가 이전 canonical definition을
대체하면, 해당 `exercise_id`의 기존 `baseline_zscore.json` entry는 제거하거나 version guard를
둬야 하며, 현재 pipeline으로 새 reference distribution을 만들기 전까지는 사용하지 않는다.

`exercise_id`가 없거나 일치하는 YAML이 없으면 `generic.yaml`을 로드한다. Generic mode는 ROM,
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
compensation_patterns: ...
feature_domains: ...
view_requirements: ...
camera_protocol: ...
view_metric_reliability: ...
quality_rules: ...
notes: string
```

모든 운동이 모든 필드를 같은 깊이로 채울 필요는 없다. 누락되거나 아직 사용할 수 없는 기능은
정상 처리로 조용히 넘기지 말고 unavailable 또는 low confidence로 보고한다.

### ExerciseSessionDefinition 조합 레이어

`ExerciseDefinition`은 하나의 분석 가능한 movement block으로 유지한다. 단일 운동 예시는 block
하나로 표현하고, 더 긴 sequence는 여러 기존 block의 순서를 정하는 `ExerciseSessionDefinition`으로
표현한다. 이렇게 하면 일반형/혼합형 운동을 별도 구분하지 않고도 framework를 운동 종류에
매몰되지 않게 유지할 수 있다. Pipeline은 제공된 block definition을 분석한다.

```yaml
exercise_session_id: example_sequence
version: 0.1.0
description: Example composition of existing exercise definitions.
rest_policy:
  rest_between_blocks_s: 120
  per_block_override_allowed: false
blocks:
  - block_id: squat_example
    exercise_id: squat
    repeat_count: 1
  - block_id: lunge_example
    exercise_id: lunge
    repeat_count: 1
```

Field contract:

```text
exercise_session_id          조합된 exercise session definition의 안정적인 ID.
                              Recording metadata의 `session_id`와 구분한다.
blocks                       분석 가능한 block의 비어 있지 않은 ordered list.
blocks[].block_id            해당 exercise session definition 안에서 고유한 ID.
blocks[].exercise_id         block이 참조하는 기존 exercise definition.
blocks[].repeat_count        참조 exercise block의 양의 정수 반복 횟수.
rest_policy.rest_between_blocks_s
                              연속 block 사이의 계획 휴식 시간(초). 계획 휴식이 없으면 null.
rest_policy.per_block_override_allowed
                              현재는 반드시 false. Block별 개별 휴식 override는 아직 지원하지 않는다.
```

Session definition은 조합과 scheduling layer이지 새로운 movement definition layer가 아니다.
Block별 analysis setting, segmentation, feature availability, camera protocol, performance
protocol, scoring policy는 참조된 exercise artifact가 소유한다. 향후 점수 추적은 block-level
output을 `exercise_session_id` 아래에서 집계할 수 있지만, 현재 schema에는 block별 score rule이나
block별 휴식 override를 넣지 않는다.

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
  body_geometry: neutral_upright | neutral_prone_line | high_hip_inverted_v | ...
  kinetic_chain: open_chain | closed_chain | mixed_chain | ...
  laterality: bilateral_symmetric | bilateral_asymmetric | alternating |
              unilateral_left | unilateral_right | unilateral_unspecified
  movement_template_id: bilateral_lower_body_closed_chain | ...
  movement_pattern: movement_template_id의 deprecated alias
  movement_pattern_source: derived_from_joint_actions_and_context | manual
  primary_plane: sagittal | frontal | transverse | multiplanar | static
  secondary_planes: list[string]
  complexity: single_joint | multi_joint | compound | whole_body
```

`laterality`는 L/R swap 처리와 Feature Extraction 내부의 side-role context에 영향을 준다.
양측 대칭 운동은 반복별 active-side context를 건너뛸 수 있고, 편측/교대 운동은 active-side 또는
role metadata를 보존해야 한다.

`movement_template_id`는 posture, support pattern, laterality, primary
regions, joint actions, planes 같은 authoring axis 조합에서 도출한다. 이는 공개 운동명이 아니라
분석 템플릿/family 이름이다. 마이그레이션 동안 기존 YAML은 `movement_pattern`을 계속 노출할 수
있으며, loader는 새 field가 없으면 이를 `movement_template_id`로 mirror한다.

### authoring_spec and authoring_inference

Canonical exercise YAML file도 해당 정의를 만들거나 재구성한 authoring 선택값을 보존할 수 있다.
이 provenance는 scoring feature가 아니며, 명시적인 `classification`, `support`, `phase_model`,
`joint_actions` field를 대체하지 않는다.

```yaml
authoring_spec:
  exercise_id: squat
  display_name: Bodyweight Squat
  movement_template_id: bilateral_lower_body_closed_chain
  movement_pattern: squat
  movement_pattern_source: derived_from_joint_actions_and_context
  posture_type: standing
  body_geometry: neutral_upright
  laterality: bilateral_symmetric
  support_template: bilateral_feet
  primary_body_regions: [hip, knee, ankle]
  primary_joint_actions: [...]
  secondary_joint_actions: [...]
  phase_template: descent_ascent_hip_center
  counting_template: repeated_repetition
  camera_view_family: front_oblique
  camera_height_level: H2
  analysis_template: bilateral_lower_body_closed_chain
```

Authoring generator가 선택된 axis에서 좁고 설명 가능한 항목을 추론했다면 YAML에
`authoring_inference`도 보존할 수 있다. Inference record는 posture, support, laterality,
joint actions, planes에서 설명되어야 하며 운동 이름만으로 추론하면 안 된다.

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

Runtime `ExerciseDefinition`은 이 block을 `support_context`로 보존한다. 후속 feature 단계는 이를
closed-chain support-landmark path check 같은 provenance 및 report-only support diagnostic에 사용할
수 있다. 이는 `exercise_id` branch나 hidden coordinate correction이 되면 안 된다.

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
  reference_coordinate_family: norm | recording_view_raw | custom
  reference_axis: vertical | anterior_posterior | medial_lateral | image_x | image_y | model_depth | custom
  boundary_logic: local_maximum | local_minimum | zero_crossing | threshold | custom
  smoothing: optional mapping
  minimum_rep_length_frames: int

phase_segmentation:
  reference_landmark: string
  reference_coordinate_family: norm | recording_view_raw | custom
  reference_axis: string
  phase_sequence: list[string]
  split_logic: local_minimum | local_maximum | multi_inflection | custom
  minimum_rep_length_frames: int
```

`reference_coordinate_family`는 boundary detection에만 사용하는 좌표 source다. 기본값 `norm`은
⑤ Normalization의 body-relative column을 읽는다. `hip_center`처럼 reference landmark가
normalization anchor이기도 하면 hip-centered normalization 뒤 움직임 신호가 제거될 수 있다.
이 경우 운동 정의는 normalized feature/scoring 좌표를 바꾸지 않고 `recording_view_raw`와
`image_y` 같은 recording-plane axis를 사용해 눈에 보이는 움직임 trace를 따라 segmentation해야 한다.

자동 segmentation이 불확실하면, 후속 분석은 불량 경계를 조용히 받아들이지 말고 확인된 수동
label을 사용한다.

### performance_protocol

`performance_protocol`은 수행 지시와 계획 취득 조건을 기술한다. 하나의 protocol count가 하나
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
    각 tap을 atomic movement로 segment하면서, 좌우 한 쌍을 수행 protocol 기준 1회로 셀 수 있다.

향후 static hold 운동
    count_unit: hold_seconds와 static_hold phase model을 사용할 수 있다.

향후 국민체조 draft
    승격 전 검토된 section/event block을 정의해야 한다. Squat repetition segmentation 또는
    score eligibility를 가정으로 재사용하지 않는다.
```

계획된 protocol 값은 여기에 둔다. 실제 녹화에서 발생한 `set_index`, `actual_rep_count`,
`failure_point_frame`, `failure_reason`은 ② Annotation 또는 recording metadata에 둔다.
Partial completion은 interpretation confidence를 낮추거나 partial completion으로 표시해야 하며,
movement-quality penalty로 직접 변환하지 않는다.

`rest_between_sets_s`는 하나의 참조 exercise block 안에서 반복되는 set 사이에만 속한다. 조합된
sequence에서 서로 다른 block 사이의 계획 휴식은
`ExerciseSessionDefinition.rest_policy.rest_between_blocks_s`에 두며, 현재는 세션 수준의 단일
공통 값만 허용한다.

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

compensation_patterns: list[string]

feature_domains:
  spatial: list[string]
  temporal: list[string]
  control: list[string]
  biomechanical_proxy: list[string]
```

구현되어 있고 관찰 가능한 compensation pattern만 biomarker를 산출한다. 선언됐지만 아직 구현되지
않은 analysis evidence는 조용히 무시하지 말고 availability/audit logic으로 보고한다. 절대 force, torque,
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
  minimum_confident_landmark_ratio: float
  minimum_critical_landmark_ratio: float
  max_missing_gap_frames: int
  max_interpolation_gap_frames: int
  exclude_rep_if_critical_landmark_missing: bool
  exclude_rep_if_phase_missing: bool
  allow_partial_feature_output: bool
  range_of_motion_targets:
    spatial.range_of_motion.xy.<joint_angle>:
      scoring_mode: minimum_sufficient_band
      minimum_sufficient_deg: float
      excessive_threshold_deg: optional float
      soft_tolerance_deg: float
      excessive_penalty_scale: float
      apply_to_phase_suffixes: [full_rep, descent, ascent]
```

confidence와 gap threshold는 ④ Preprocessing과 ⑦ Feature Extraction에서 소비한다.
`range_of_motion_targets`는 ⑨ Biomarker Scoring에서 소비한다. 운동별 기능적 ROM band를 정의하는 필드이며,
예를 들어 squat knee ROM은 synthetic baseline 평균보다 크다고 감점하기보다 ROM이 부족할 때
주로 감점해야 한다. 이 target은 reviewed-good example이나 문헌 기반 값이 충분해지기 전까지
provisional이며, global rule이 아니라 운동별 rule로 유지한다.

---

## 6. 새 운동으로 확장하기 (Extending To A New Exercise)

나머지 현재 운동과 향후 정의되지 않은 운동에는 이 체크리스트를 사용한다.

```text
1. Authoring notebook으로 draft split YAML artifact를 만든다.
2. 가장 가까운 schema family를 선택하되, posture, laterality, phase model, count unit이 다르면
   squat-like assumption에 억지로 맞추지 않는다.
3. 해당 운동의 관찰 가능한 mechanics를 기준으로 primary landmarks, critical landmarks,
   feature domains를 정의한다.
4. performance protocol과 segmentation unit을 분리해 정의한다.
5. View-dependent feature를 해석하기 전에 camera protocol과 view-metric reliability를 정의한다.
6. 지원되지 않는 metric은 구현과 테스트 전까지 unavailable/not_assessed로 둔다.
7. 새 field가 loader 또는 downstream behavior에 영향을 주면 test를 추가하거나 갱신한다.
8. 연구자 검토 뒤 draft YAML을 canonical file로 승격한다.
```

새 운동 추가는 보통 YAML과 test 추가로 끝나야 하며, stage-level code가 늘어나는 방향은 피한다.
코드 변경이 필요하면 먼저 `docs_eng/`에 새 개념을 기록하고 `docs/`로 동기화한다.

---

## 7. Provenance 규약 (Provenance Convention)

⑨에서 산출되는 모든 biomarker는 계산을 유발한 definition field를 가리키는 `source_fields`를
포함해야 한다.

```text
biomarker_id       : knee_valgus_index
exercise_id        : squat
definition_version : 0.5.0
source_fields      : [compensation_patterns.knee_valgus,
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
    load_exercise_session_definition,
)

definition = load_exercise_definition(
    exercise_id="squat",
    definitions_dir="data/definitions/exercises",
)

all_definitions = load_all_exercise_definitions("data/definitions/exercises")

session = load_exercise_session_definition(
    exercise_session_id="example_sequence",
    sessions_dir="data/definitions/exercise_sessions",
)
```
