# 03. 운동 정의 (Exercise Definition)

**문서 버전:** 1.4.3
**최종 갱신:** 2026-05-08
**영문 동기화:** `docs_eng/pipeline/03_exercise_definition.md`는 동일 버전의 영문 번역본이다.

파이프라인 단계 ③. `data/definitions/exercises/`에 있는 운동 YAML 파일을 로드한다.
모든 후속 단계(④–⑨)가 운동별 로직 적용을 위해 참조하는 `ExerciseDefinition` 객체를 반환한다.

---

## 1. 파이프라인 위치 (Pipeline Position)

```text
Pose CSV + 어노테이션 + 운동 YAML
→ ① Validation
→ ② Annotation                    (exercise_type, pattern 선언)
→ ③ Exercise Definition           ← 본 단계
→ ④ Preprocessing                 (laterality, landmarks, quality_rules 참조)
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution            (laterality, primary_joints 참조)
→ ⑧ Feature Extraction            (feature_domains, joint_actions 참조)
→ ⑨ Biomech Proxy                 (biomechanical_focus 참조)
→ ⑩ Biomarker Derivation          (compensation_candidates 참조)
```

운동 정의는 동작이 *무엇을 의미하는가*를 기술한다.
어노테이션은 동작이 *어디서 발생했는가*를 기술한다.

## 2. 설계 (Design)

운동별 동작은 코드 분기가 아닌 YAML 데이터로 표현된다.
새 운동 추가 = `data/definitions/exercises/`에 YAML 파일 1개 작성.

⑧–⑩에서 산출되는 모든 바이오마커는 그 계산을 유발한 정의 필드를 가리키는 `source_fields`를
반드시 참조해야 한다.

## 3. 사용 가능한 정의 (Available Definitions)

```text
data/definitions/exercises/
    squat.yaml
    lunge.yaml
    pike_pushup.yaml
    plank_shoulder_tap.yaml
    generic.yaml               ← 폴백
```

## 4. 폴백 동작 (Fallback Behavior)

어노테이션에 `exercise_type`이 없거나 해당 YAML을 찾지 못하면 `generic.yaml`이 로드된다.
generic 모드는 운동에 무관한(exercise-agnostic) 피처(ROM, 템포, 안정성)만 활성화한다.
보상 움직임 바이오마커는 산출되지 않는다.

```yaml
# generic.yaml (발췌)
exercise_id: generic
classification:
  laterality: bilateral_symmetric
  primary_plane: sagittal
phase_model:
  type: cyclic
compensation_candidates: []
feature_domains:
  spatial: [rom]
  temporal: [tempo]
  control: [stability]
```

## 5. YAML 스키마 개요 (YAML Schema Overview)

```yaml
exercise_id: string            # snake_case 고유 식별자
display_name: string
description: string
version: string
tags: list[string]

classification:                # 거시 운동 분류
support:                       # 접촉/지지 기저면
phase_model:                   # 1회 반복의 시간 구조
rep_segmentation:              # 반복 경계 검출 설정
phase_segmentation:            # 반복 내부 phase 검출 설정
performance_protocol:          # 실전 수행 카운트, 좌우 순서, 완료 규칙
landmarks:                     # 랜드마크 모델 및 주요/보조 관절
angle_definitions:             # 관절각 트리플렛
joint_actions:                 # 기대되는 관절 동작
biomechanical_focus:           # CoM 운동, 안정성, 부하 영역
compensation_candidates:       # 모니터링할 보상 움직임 목록
feature_domains:               # 활성화할 공간/시간/제어 피처
view_requirements:             # 선호 카메라 뷰
camera_protocol:               # 권장 촬영 zone/height와 경고 정책
quality_rules:                 # 분석 적격성 임계값
notes: string
```

초기 구현에서 모든 필드를 채울 필요는 없다.
재구조화 없이 점진적으로 추가할 수 있도록 설계되었다.

## 6. 필드 레퍼런스 (Field Reference)

### classification

```yaml
classification:
  family: lower_body           # lower_body | upper_body | core | full_body | balance | ...
  equipment: none
  load_type: bodyweight        # bodyweight | external_load | assisted | ...
  posture_type: standing       # standing | plank | inverted_closed_chain | kneeling | ...
  kinetic_chain: closed_chain  # open_chain | closed_chain | mixed_chain | ...
  laterality: bilateral_symmetric
      # bilateral_symmetric | bilateral_asymmetric | alternating
      # unilateral_left | unilateral_right | unilateral_unspecified
  movement_pattern: squat
  primary_plane: sagittal      # sagittal | frontal | transverse | multiplanar | static
  secondary_planes: [frontal, transverse]
  complexity: compound         # single_joint | multi_joint | compound | whole_body
```

`laterality`가 제어하는 항목:
- ④ 전처리: 좌·우 스왑 검출 실행 여부
- ⑦ 모션 어트리뷰션: 반복별 활성 측 점검 실행 여부 (`bilateral_symmetric`은 건너뜀)

### support

```yaml
support:
  base_of_support: bilateral_feet   # bilateral_feet | single_foot_left | split_stance | ...
  contact_points: [left_foot, right_foot]
  support_surface: floor
  weight_bearing_regions: [left_foot, right_foot]
```

### phase_model

```yaml
phase_model:
  type: resistance_phase
      # resistance_phase | task_phase | static_hold | cyclic | locomotion_phase | custom
  expected_ratio:             # resistance_phase에 한함; 합 ≈ 1.0
    eccentric: 0.4
    isometric: 0.1
    concentric: 0.5
```

표준 구간 이름:

```text
resistance_phase  : eccentric, isometric, concentric, transition_top, transition_bottom
task_phase        : setup, support_stable, weight_shift, tap, reach, return, reset, hold, ...
static_hold       : setup, hold, fatigue, release
locomotion_phase  : initial_contact, loading_response, mid_stance, terminal_stance, ...
```

### rep_segmentation / phase_segmentation

`rep_segmentation`은 반복의 시작·종료 경계를 확정하고 `rep_id`를 만든다.
`phase_segmentation`은 기존 식별자와 YAML 키를 그대로 유지하며, 확정된 반복 내부에서
기구학적 phase 라벨을 만든다.

```yaml
rep_segmentation:
  reference_landmark: hip_center
  reference_axis: vertical
  boundary_logic: local_maximum      # local_maximum | local_minimum | zero_crossing
  smoothing:
    method: savitzky_golay
    window_frames: 7
    polyorder: 3
  minimum_rep_length_frames: 8
  minimum_boundary_distance_frames: 8
  minimum_reps: 1
  boundary_prominence: null
  include_endpoints: true

phase_segmentation:
  reference_landmark: hip_center
  reference_axis: vertical
  phase_sequence: [Descent, Ascent]
  split_logic: local_minimum
  smoothing:
    method: savitzky_golay
    window_frames: 7
    polyorder: 3
  turnaround_hold:
    enabled: true
    half_window_frames: 3
  minimum_rep_length_frames: 8
  multi_inflection_policy: global_extremum
```

### performance_protocol

`performance_protocol`은 피험자에게 운동을 어떻게 수행하고 몇 회로 세도록 안내했는지를
기록한다. 이 필드는 `rep_segmentation`과 분리한다. `rep_segmentation`은 어떤 움직임 단위에
`rep_id`를 붙일지를 정의하고, `performance_protocol`은 실전 프로토콜에서 그 단위를 어떻게
카운트할지를 정의한다.

이 분리는 플랭크 숄더탭처럼 각 tap은 원자적 움직임으로 분할할 수 있지만, 피험자 안내상
1회는 좌우 한 쌍을 의미하는 운동에서 필요하다.

```yaml
performance_protocol:
  counting:
    target_count: 10
    count_unit: repetition       # repetition | left_right_pair | hold_seconds
    segmentation_reps_per_count: 1
  side_sequence:
    mode: none                   # none | alternating_each_rep | same_side_block_then_switch
    block_size_counts: null      # 예: lunge는 5
    first_side_source: null      # null | annotation.starting_side
  completion:
    allow_partial_completion: false
    recommended_sets: 3
  participant_cues:
    - keep_hands_fixed
    - avoid_arm_swing
  analysis_disrupting_patterns:
    - arm_swing
    - unstable_foot_contact
    - incomplete_depth
```

필드 의미:

```text
target_count                  피험자 안내 기준 목표 횟수
count_unit                    프로토콜상 1회가 의미하는 단위
segmentation_reps_per_count   프로토콜 1회에 대응되는 세그멘테이션 원자 반복 수
side_sequence.mode            프로토콜 수준의 기대 좌우 순서
block_size_counts             블록 기반 전환에서 한쪽을 유지하는 횟수
first_side_source             첫 수행 측을 선언하는 위치
allow_partial_completion      목표 횟수 미만 수행을 메타데이터와 함께 수용할지 여부
recommended_sets              실전 취득 권장 세트 수; 자동 반복 배수는 아님
```

예:

```yaml
# 런지: 한쪽 5회 뒤 반대쪽 5회.
performance_protocol:
  counting:
    target_count: 10
    count_unit: repetition
    segmentation_reps_per_count: 1
  side_sequence:
    mode: same_side_block_then_switch
    block_size_counts: 5
    first_side_source: annotation.starting_side
  completion:
    allow_partial_completion: false
    recommended_sets: 3

# 플랭크 숄더탭: 좌우 한 쌍을 프로토콜 1회로 계산.
performance_protocol:
  counting:
    target_count: 10
    count_unit: left_right_pair
    segmentation_reps_per_count: 2
  side_sequence:
    mode: alternating_each_rep
    block_size_counts: null
    first_side_source: annotation.starting_side
  completion:
    allow_partial_completion: false
    recommended_sets: 3
```

현재 구현은 ③ Exercise Definition에서 이 메타데이터를 파싱하고 검증한다.
⑦ Motion Attribution은 아직 기존 `pattern` / `starting_side` 동작을 사용하며,
블록 기반 좌우 순서 강제는 후속 구현 단계로 둔다.

### landmarks

```yaml
landmarks:
  model: mediapipe_pose_33
  primary_joints: [left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle]
  secondary_joints: [left_shoulder, right_shoulder, trunk, pelvis]
  critical_landmarks: [23, 24, 25, 26, 27, 28]   # MediaPipe 인덱스
  optional_landmarks: [11, 12, 29, 30, 31, 32]
```

표준 관절 이름:

```text
left_shoulder  right_shoulder  left_elbow    right_elbow
left_wrist     right_wrist     left_hip      right_hip
left_knee      right_knee      left_ankle    right_ankle
left_foot      right_foot      trunk         pelvis       head
```

### angle_definitions

```yaml
angle_definitions:
  left_knee_angle:  { points: [23, 25, 27], vertex: 25 }
  right_knee_angle: { points: [24, 26, 28], vertex: 26 }
  left_hip_angle:   { points: [11, 23, 25], vertex: 23 }
  right_hip_angle:  { points: [12, 24, 26], vertex: 24 }
```

표준 트리플렛 (MediaPipe 인덱스):

```text
left_shoulder_angle  : [23, 11, 13]   right_shoulder_angle : [24, 12, 14]
left_elbow_angle     : [11, 13, 15]   right_elbow_angle    : [12, 14, 16]
left_hip_angle       : [11, 23, 25]   right_hip_angle      : [12, 24, 26]
left_knee_angle      : [23, 25, 27]   right_knee_angle     : [24, 26, 28]
left_ankle_angle     : [25, 27, 31]   right_ankle_angle    : [26, 28, 32]
```

### biomechanical_focus

```yaml
biomechanical_focus:
  expected_com_motion: vertical
      # minimal | vertical | anterior_posterior | medial_lateral
      # vertical_and_anterior_posterior | vertical_and_medial_lateral
      # rotational | multidirectional
  stability_requirement: medium   # low | medium | high | very_high
  main_load_regions: [hip, knee, ankle]
      # shoulder | elbow | wrist | trunk | core | hip | knee | ankle | foot | pelvis
  primary_constraints:
    - maintain_foot_contact
    - maintain_trunk_alignment
    - avoid_knee_valgus
```

### compensation_candidates

```yaml
compensation_candidates:
  - knee_valgus
  - excessive_trunk_flexion
  - lateral_pelvic_shift
```

여기에 명시된 보상 움직임만 ⑩에서 바이오마커로 산출된다.

전체 어휘:

```text
# 하체
knee_valgus                    knee_varus
asymmetric_depth               asymmetric_knee_flexion
asymmetric_hip_flexion         limited_ankle_dorsiflexion_proxy
heel_lift                      foot_external_rotation_proxy
foot_collapse_proxy            pelvis_drop
lateral_pelvic_shift           hip_shift
insufficient_rear_hip_extension unstable_step_width

# 체간 / 골반
excessive_trunk_flexion        trunk_extension_compensation
lateral_trunk_lean             trunk_rotation
trunk_sway                     pelvis_rotation
pelvis_anterior_tilt_proxy     pelvis_posterior_tilt_proxy
hip_pike                       hip_drop
loss_of_neutral_spine_proxy

# 상체
shoulder_elevation_compensation shoulder_asymmetry
shoulder_collapse              elbow_flare
elbow_asymmetry                wrist_shift
scapular_instability_proxy     insufficient_head_descent
head_forward_shift

# 제어 / 타이밍
excessive_com_lateral_shift    excessive_com_variability
phase_timing_asymmetry         tempo_instability
left_right_timing_variability  movement_discontinuity
```

### feature_domains

```yaml
feature_domains:
  spatial: [rom, symmetry, shape]
  temporal: [tempo, variability]
  control: [stability, compensation]
  biomechanical_proxy: [com_displacement, moment_arm_proxy]
```

전체 어휘:

```text
spatial:
  rom, joint_angle_min, joint_angle_max, joint_angle_range,
  symmetry, shape, trajectory_similarity, alignment,
  posture_angle, depth_proxy, reach_distance, support_width

temporal:
  tempo, rep_duration, phase_duration, eccentric_duration,
  isometric_duration, concentric_duration, timing_ratio,
  variability, rhythm_consistency, left_right_timing_variability, pause_duration

control:
  stability, compensation, com_stability, trunk_stability,
  pelvis_stability, joint_tracking_error, lateral_shift,
  rotation_control, balance_control, movement_smoothness, endpoint_control

biomechanical_proxy:
  com_displacement, com_velocity_proxy,
  segment_length_normalized_displacement,
  moment_arm_proxy, relative_joint_load_proxy,
  load_distribution_proxy, support_moment_proxy,
  compensation_load_shift_proxy
```

### camera_protocol

`camera_protocol`은 운동별 권장 촬영 조건을 기록하는 메타데이터이다. 이 필드는 데이터 취득
가이드와 결과 경고에 사용하며, 좌표를 직접 보정하거나 데이터를 강제로 제외하는 기준으로
사용하지 않는다.

```yaml
camera_protocol:
  recommended_zones: [Z2, Z8]
  recommended_height: H2
  anchor: reference_mat
  distance_cm: [200, 250]
  primary_observation_purpose:
    - knee_valgus
    - hip_flexion_depth
  out_of_zone_policy: warn_and_continue
  coordinate_correction: none
```

공통 zone/height 정의는 `data/camera/camera_zones.yaml`을 참조한다.
자세한 촬영 원칙은 [camera_protocol.md](../practical_protocols/camera_protocol.md)를 참조한다.
피험자 안내 문구와 분석을 방해하는 수행 패턴은
[exercise_performance_protocol.md](../practical_protocols/exercise_performance_protocol.md)를 참조한다.

### quality_rules

```yaml
quality_rules:
  minimum_visible_landmark_ratio: 0.8
  minimum_critical_landmark_ratio: 0.9
  max_missing_gap_frames: 10
  max_interpolation_gap_frames: 3        # ④ 전처리에서 참조
  exclude_rep_if_critical_landmark_missing: true
  exclude_rep_if_phase_missing: false
  allow_partial_feature_output: true
```

④ 전처리와 ⑧ 피처 추출에서 직접 참조된다.

## 7. Provenance 규약 (Provenance Convention)

⑧–⑩에서 산출되는 모든 바이오마커는 그 계산을 유발한 정의 필드를 가리키는 `source_fields`를
포함한다. `source_fields`가 없는 바이오마커는 산출되지 않는다 (`BiomarkerRecord`에서
`ValueError` 발생).

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

## 8. 전체 예: squat.yaml (Full Example: squat.yaml)

```yaml
exercise_id: squat
display_name: Bodyweight Squat
description: Bilateral lower-limb closed-chain movement evaluating hip/knee/ankle coordination.
version: 0.5.2
tags: [bodyweight, lower_body, closed_chain, bilateral, strength]

classification:
  family: lower_body
  equipment: none
  load_type: bodyweight
  posture_type: standing
  kinetic_chain: closed_chain
  laterality: bilateral_symmetric
  movement_pattern: squat
  primary_plane: sagittal
  secondary_planes: [frontal, transverse]
  complexity: compound

support:
  base_of_support: bilateral_feet
  contact_points: [left_foot, right_foot]
  support_surface: floor
  weight_bearing_regions: [left_foot, right_foot]

phase_model:
  type: resistance_phase
  expected_ratio:
    eccentric: 0.4
    isometric: 0.1
    concentric: 0.5

rep_segmentation:
  reference_landmark: hip_center
  reference_axis: vertical
  boundary_logic: local_maximum
  smoothing:
    method: savitzky_golay
    window_frames: 7
    polyorder: 3
  minimum_rep_length_frames: 8
  minimum_boundary_distance_frames: 8
  minimum_reps: 1
  boundary_prominence: null
  include_endpoints: true

phase_segmentation:
  reference_landmark: hip_center
  reference_axis: vertical
  phase_sequence: [Descent, Ascent]
  split_logic: local_minimum
  smoothing:
    method: savitzky_golay
    window_frames: 7
    polyorder: 3
  turnaround_hold:
    enabled: true
    half_window_frames: 3
  minimum_rep_length_frames: 8
  multi_inflection_policy: global_extremum

performance_protocol:
  counting:
    target_count: 10
    count_unit: repetition
    segmentation_reps_per_count: 1
  side_sequence:
    mode: none
    block_size_counts: null
    first_side_source: null
  completion:
    allow_partial_completion: false
    recommended_sets: 3
  participant_cues:
    - keep_hands_fixed
    - avoid_arm_swing
  analysis_disrupting_patterns:
    - arm_swing
    - unstable_foot_contact
    - incomplete_depth

landmarks:
  model: mediapipe_pose_33
  primary_joints:
    - left_hip
    - right_hip
    - left_knee
    - right_knee
    - left_ankle
    - right_ankle
  secondary_joints: [left_shoulder, right_shoulder, trunk, pelvis, left_foot, right_foot]
  critical_landmarks: [23, 24, 25, 26, 27, 28]
  optional_landmarks: [11, 12, 29, 30, 31, 32]

angle_definitions:
  left_hip_angle:    { points: [11, 23, 25], vertex: 23 }
  right_hip_angle:   { points: [12, 24, 26], vertex: 24 }
  left_knee_angle:   { points: [23, 25, 27], vertex: 25 }
  right_knee_angle:  { points: [24, 26, 28], vertex: 26 }
  left_ankle_angle:  { points: [25, 27, 31], vertex: 27 }
  right_ankle_angle: { points: [26, 28, 32], vertex: 28 }

joint_actions:
  primary:
    - hip_flexion_extension
    - knee_flexion_extension
    - ankle_dorsiflexion_plantarflexion
  secondary:
    - trunk_flexion_extension
    - pelvis_lateral_tilt_proxy
    - pelvis_rotation_proxy

biomechanical_focus:
  expected_com_motion: vertical
  stability_requirement: medium
  main_load_regions: [hip, knee, ankle]
  primary_constraints:
    - maintain_foot_contact
    - maintain_trunk_alignment
    - avoid_knee_valgus
    - avoid_heel_lift
    - avoid_excessive_lateral_shift

compensation_candidates:
  - knee_valgus
  - knee_varus
  - asymmetric_depth
  - excessive_trunk_flexion
  - lateral_pelvic_shift
  - heel_lift
  - foot_external_rotation_proxy
  - pelvis_rotation
  - tempo_instability

feature_domains:
  spatial: [rom, symmetry, shape, depth_proxy, alignment]
  temporal: [tempo, rep_duration, eccentric_duration, isometric_duration, concentric_duration, timing_ratio]
  control: [stability, compensation, com_stability, pelvis_stability, lateral_shift]
  biomechanical_proxy: [com_displacement, moment_arm_proxy, relative_joint_load_proxy]

view_requirements:
  preferred_views: [front_oblique]
  acceptable_views: [frontal, sagittal_left, sagittal_right, side_oblique]
  critical_landmarks: [23, 24, 25, 26, 27, 28]
  occlusion_risk: medium

camera_protocol:
  recommended_zones: [Z2, Z8]
  recommended_height: H2
  anchor: reference_mat
  distance_cm: [200, 250]
  primary_observation_purpose:
    - knee_valgus
    - hip_flexion_depth
  out_of_zone_policy: warn_and_continue
  coordinate_correction: none

quality_rules:
  minimum_visible_landmark_ratio: 0.8
  minimum_critical_landmark_ratio: 0.9
  max_missing_gap_frames: 10
  max_interpolation_gap_frames: 3
  exclude_rep_if_critical_landmark_missing: true
  exclude_rep_if_phase_missing: false
  allow_partial_feature_output: true
```

## 9. MediaPipe Pose 33 랜드마크 인덱스

```text
0  nose               1  left_eye_inner    2  left_eye          3  left_eye_outer
4  right_eye_inner    5  right_eye         6  right_eye_outer
7  left_ear           8  right_ear         9  mouth_left        10 mouth_right
11 left_shoulder      12 right_shoulder    13 left_elbow        14 right_elbow
15 left_wrist         16 right_wrist       17 left_pinky        18 right_pinky
19 left_index         20 right_index       21 left_thumb        22 right_thumb
23 left_hip           24 right_hip         25 left_knee         26 right_knee
27 left_ankle         28 right_ankle       29 left_heel         30 right_heel
31 left_foot_index    32 right_foot_index
```

## 10. 로더 API (Loader API)

```python
from movement.exercise_definition import load_exercise_definition, load_all_exercise_definitions

definition = load_exercise_definition(
    exercise_id="squat",
    definitions_dir="data/definitions/exercises",
)

all_definitions = load_all_exercise_definitions("data/definitions/exercises")
```
