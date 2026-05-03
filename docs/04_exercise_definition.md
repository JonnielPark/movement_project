# 04. 운동 정의 (Exercise Definition)

본 단계는 분석 대상 운동의 **생체역학적 속성(주요 관절, 지지면, 수행 단계, 보상 움직임 후보, 품질 기준 등)**을 데이터(YAML)로 표현한다. 후속 단계(annotation 다음의 모든 단계)는 이 운동 정의 객체를 참조해 운동별 처리 규칙을 적용한다.

> 용어는 [`_terminology.md`](_terminology.md)의 단일 정의를 따른다. 새 어휘를 추가할 때는 그 문서에 먼저 등록한다.

---

## 1. 분석의 단위 재정의

### 1-1. 핵심 변화

연구계획서의 핵심 아이디어는 운동을 **명칭 단위**가 아니라 **생체역학적 속성 단위**로 정의하는 것이다.

```text
이전 관점: 4가지 운동(스쿼트, 런지, 파이크 푸쉬업, 플랭크 숄더탭)
            각각에 대한 분석 코드를 구현한다.

현재 관점: 운동을 생체역학적 속성 객체로 정의하고,
            동일한 분석 단계를 모든 운동에 적용한다.
            4가지 운동은 그 속성 공간 위의 4개 표본일 뿐이다.
```

운동 정의 객체가 명시하는 것:

- 어떤 종류의 동작인가 (자세, 운동 사슬, 좌우 패턴, 주된 평면)
- 어떤 관절·신체 부위가 주된 작용 부위인가
- 어떤 수행 단계가 기대되는가
- 어떤 보상 움직임을 모니터링해야 하는가
- 어떤 특징과 생체역학적 근사 지표가 적용되어야 하는가
- 어떤 카메라 시야와 랜드마크가 필요한가
- 분석 가능 여부를 판정하는 품질 기준

이 설계는 분석 체계를 **이식 가능**하게 만든다. 새 운동 추가는 코드 분기 작성이 아니라 YAML 파일 작성이다.

### 1-2. 의대 자문위원을 위한 해석

자문위원이 “이 시스템은 스쿼트만 분석하는가, 런지만 분석하는가?”라고 물을 경우의 답:

> 본 분석 체계는 운동을 명칭이 아니라 생체역학적 속성 객체로 다룹니다. 4가지 동작은 분석 체계의 일관성과 일반화 가능성을 검증하기 위한 표본이며, 추후 새로운 동작을 추가할 때는 운동 정의 한 장(YAML)을 작성하면 됩니다. 산출되는 디지털 바이오마커가 어떤 생체역학적 근거에서 나왔는지는 항상 운동 정의의 필드로 추적할 수 있습니다.

---

## 2. 왜 속성 기반 정의인가 (배경)

기존의 단일 비전 기반 동작 분석 코드는 운동마다 분기를 갖는 경향이 있다.

```text
전형적 패턴:
- if exercise == "squat":   knee valgus 점검
- elif exercise == "lunge": rear hip extension 점검
- elif exercise == "pushup": elbow flare 점검
- ...
```

각 분기는 어떤 관절이 중요한지·어떤 평면이 주된지·어떤 편차를 보상으로 볼 것인지에 대한 가정을 코드 안에 묻어둔다. 이 가정은 데이터로 표현되지 않으므로 다음 문제를 만든다.

- 가정이 코드에 산재해 일관성을 잃는다.
- 새 운동 추가 시 분기를 늘려야 한다.
- 산출 지표가 어떤 생체역학적 근거에서 나왔는지 추적이 어렵다.

본 단계는 그 가정을 운동 정의 스키마로 추출한다. 후속 단계는 정의를 읽고 공통 규칙을 적용한다.

```text
biomarker = function(definition_property, normalized_pose, annotation)
```

이것이 본 프레임워크의 **해석 가능성** 주장의 근거이다. 모든 바이오마커 값은 정의의 어떤 필드가 산출 근거였는지 가리킬 수 있다.

---

## 3. 분석 단계에서의 위치

운동 정의는 ② Annotation 직후에 적재되어, 이후 모든 단계에 제공된다.

```text
Pose CSV
+ optional annotation file
+ exercise definition (YAML)
→ ① 데이터 검증
→ ② Annotation 적용                  (exercise_type, pattern 적재)
→ ③ 운동 정의 로딩                    (exercise_type에 해당하는 YAML 적재)  ← 본 단계
→ ④ 전처리                            (laterality, landmarks, quality_rules 사용)
→ ⑤ 정규화
→ ⑥ 귀속                              (laterality, primary_joints 사용)
→ ⑦ 특징 추출                          (joint_actions, feature_domains 사용)
→ ⑧ 생체역학적 근사 모델링              (biomechanical_focus 사용)
→ ⑨ 지표화                            (compensation_candidates 사용)
→ ⑩ 시각화 / 보고서
```

운동 정의는 프레임을 표시하지 않는다. annotation이 프레임을 표시한다. 운동 정의는 “표시된 프레임이 무엇을 의미하는지”를 후속 단계에 알려준다.

```text
운동 정의           : 동작이 무엇을 의미하는가
annotation         : 동작이 어디에서 일어났는가
특징 추출           : 어떤 정량 지표를 산출하는가
생체역학적 근사      : 그 지표를 어떻게 해석하는가
```

`exercise_type`이 annotation에 누락되면 generic fallback 정의가 적재된다 (§"Fallback Behavior").

---

## 4. 설계 원칙

### 4-1. 운동별 정보는 코드가 아니라 데이터로 표현한다

```text
권장:
- 주요 관절을 YAML에 명시한다.
- 기대되는 수행 단계를 YAML에 명시한다.
- 보상 움직임 후보를 YAML에 명시한다.
- 특징 추출과 지표화는 그 명시 사항을 읽는다.

지양:
- if exercise == "squat" 분기를 모든 함수에 두는 것
- 모든 운동을 양측 대칭으로 가정하는 것
- 모든 운동에 eccentric/isometric/concentric 단계가 있다고 가정하는 것
- 스쿼트와 런지에 동일한 좌우 대칭 규칙을 적용하는 것
```

### 4-2. 모든 산출 바이오마커는 정의 필드로 추적 가능해야 한다

본 프레임워크의 출력이 “단지 숫자”가 아니라 “해석 가능한 지표”인 근거이다.

---

## 5. 운동 정의의 속성 공간

운동은 속성 공간 위의 한 객체로 표현된다. 속성 공간이 곧 스키마이며, 4가지 표본 운동은 그 속성 공간 위의 4개 점이다.

```text
속성 공간 (스키마 필드)
─────────────────────────────────
classification.posture_type            ∈ standing | plank | inverted_closed_chain | ...
classification.kinetic_chain           ∈ open | closed | mixed | ...
classification.laterality              ∈ bilateral_symmetric | alternating | ...
classification.primary_plane           ∈ sagittal | frontal | transverse | ...
phase_model.type                       ∈ resistance_phase | task_phase | static_hold | ...
landmarks.primary_joints               ⊆ joint vocabulary
joint_actions                          ⊆ joint action vocabulary
biomechanical_focus.expected_com_motion ∈ vertical | minimal | medial_lateral | ...
compensation_candidates                ⊆ compensation vocabulary
feature_domains                        ⊆ feature vocabulary
view_requirements                      ⊆ view vocabulary
quality_rules                          ⊆ quality rule vocabulary
```

4가지 표본 운동의 위치:

```text
                       posture        kinetic_chain          laterality              primary_plane
─────────────────────  ─────────────  ─────────────────────  ──────────────────────  ─────────────
squat                  standing       closed_chain           bilateral_symmetric     sagittal
lunge                  standing_split closed_chain           alternating             sagittal
pike_pushup            inverted_cc    closed_chain           bilateral_symmetric     sagittal
plank_shoulder_tap     plank          closed_chain_alt       alternating             frontal
```

새 운동을 추가하려면 동일한 축 위에서 값을 선택한다. 어휘 안에 들어가는 한, 새 코드 분기 없이 분석이 동일한 규칙으로 적용된다.

---

## 6. 정의 → 바이오마커 매핑

본 절은 정의 필드가 어떻게 바이오마커 선택을 구동하는지를 설명한다. 산출 공식은 ⑦ 특징 추출과 ⑧ 생체역학적 근사 모델링 단계에 속하며, 본 절의 매핑은 두 단계와 정의 단계 사이의 계약(contract)이다.

### 6-1. 매핑 원칙

```text
원칙 1: 모든 바이오마커는 적어도 하나의 정의 필드가 소유한다.
        (산출 근거 필드가 없는 바이오마커는 산출하지 않는다.)

원칙 2: 정의 필드가 누락되면 의존 바이오마커는 생략된다.
        (조용히 근사값으로 대체하지 않는다.)

원칙 3: 속성 변경 시 바이오마커 집합이 자동으로 갱신된다.
        (예: laterality를 변경하면 좌우 대칭성 바이오마커가 활성/비활성된다.)

원칙 4: 바이오마커 출력은 provenance를 동반한다.
        (어떤 정의 필드가 산출했는지, 어떤 annotation 반복에 속하는지)
```

### 6-2. 표 1. 속성 필드 → 특징 영역

다음 표는 정의 속성이 어떤 특징 영역을 활성화하는지 요약한다.

```text
정의 필드                              값                              활성화되는 특징 영역
─────────────────────────────────────  ─────────────────────────────  ──────────────────────────────────────────
classification.laterality              bilateral_symmetric            spatial.symmetry, control.lateral_shift
classification.laterality              alternating                    temporal.left_right_timing_variability,
                                                                      control.balance_control
classification.laterality              unilateral_*                   per-side spatial.rom, control.stability

classification.primary_plane           sagittal                       spatial.rom (sagittal angles),
                                                                      shape (sagittal trajectory)
classification.primary_plane           frontal                        spatial.alignment (frontal),
                                                                      control.lateral_shift
classification.primary_plane           transverse                     control.rotation_control

classification.posture_type            standing                       biomechanical_proxy.com_displacement (vertical)
classification.posture_type            plank | inverted_closed_chain  control.trunk_stability,
                                                                      biomechanical_proxy.support_moment_proxy
classification.posture_type            single_leg_standing            control.balance_control

phase_model.type                       resistance_phase               temporal.eccentric_duration,
                                                                      temporal.isometric_duration,
                                                                      temporal.concentric_duration,
                                                                      temporal.timing_ratio
phase_model.type                       task_phase                     temporal.phase_duration,
                                                                      temporal.rhythm_consistency
phase_model.type                       static_hold                    control.com_stability (over hold window),
                                                                      temporal.pause_duration

biomechanical_focus.expected_com_motion vertical                      biomechanical_proxy.com_displacement (z),
                                                                      biomechanical_proxy.com_velocity_proxy
biomechanical_focus.expected_com_motion minimal                       control.com_stability,
                                                                      compensation: excessive_com_lateral_shift
```

읽기 안내: “정의가 이 필드에 이 값을 선언했다면, 이 특징 영역 항목들이 후보가 된다”라는 의미이다. 후보는 랜드마크 가용성과 품질 기준에 의해 다시 걸러진다.

### 6-3. 표 2. 보상 움직임 후보 → 바이오마커 스케치

각 보상 움직임 후보는 하나의 바이오마커를 선택한다. 아래 공식은 산출 정의의 윤곽이며, 실제 구현은 ⑦ 특징 추출과 ⑧ 생체역학적 근사 모델링이 책임진다.

```text
보상 움직임 후보                          바이오마커 명                              스케치 (해석용)
──────────────────────────────────────  ──────────────────────────────────────  ──────────────────────────────────────────────
knee_valgus                             knee_valgus_index                       전두면(frontal) 무릎이 hip–ankle 선에서 벗어난 정도,
                                                                                몸통 길이 정규화
asymmetric_depth                        depth_asymmetry_ratio                   |left_depth − right_depth| / max(left_depth, right_depth)
excessive_trunk_flexion                 trunk_flexion_excess                    peak trunk_angle 에서 운동별 기대 범위까지의 초과량
lateral_pelvic_shift                    pelvis_shift_index                      반복 동안 골반 수평 이동 최대값, 몸통 길이 정규화
heel_lift                               heel_lift_ratio                         heel landmark 높이가 임계값을 넘은 프레임 / 반복 길이
elbow_flare                             elbow_flare_angle                       press 단계의 humerus–trunk 전두면 각도
shoulder_asymmetry                      shoulder_height_asymmetry               |left_shoulder.y − right_shoulder.y| / shoulder width
hip_pike                                hip_pike_index                          plank 자세 hold 동안 hip_angle의 중립 이탈 정도
tempo_instability                       tempo_cv                                반복별 rep_duration의 변동계수
left_right_timing_variability           lr_phase_offset_cv                      반복별 |left_phase_end − right_phase_end|의 변동계수
phase_timing_asymmetry                  phase_ratio_drift                       관측 phase 비율과 phase_model.expected_ratio의 거리
```

정의에 명시되지 않은 보상 움직임 후보는 산출되지 않는다. 이는 의도된 설계이며, 운동마다 어떤 지표가 “해석 가능한지”를 명확히 하기 위함이다.

### 6-4. Provenance 규약

⑦ 특징 추출이 산출하는 모든 바이오마커는 다음 형식의 provenance 레코드를 포함한다. ⑨ 지표화와 ⑩ 시각화가 이를 사용한다.

```text
biomarker_id        : knee_valgus_index
exercise_id         : squat
definition_version  : 0.1.0
source_fields       : [compensation_candidates.knee_valgus,
                       classification.primary_plane,
                       landmarks.primary_joints]
rep_id              : 2
value               : 0.13
unit                : torso_length_ratio
```

⑨ 지표화는 `source_fields` 항목이 없는 바이오마커를 산출하지 않는다. 이는 분석 결과의 감사 가능성(auditability)을 보장한다.

---

## 7. 스키마 개요 (Minimal Example)

```yaml
exercise_id: squat
display_name: Bodyweight Squat

classification:
  family: lower_body
  equipment: none
  load_type: bodyweight
  posture_type: standing
  kinetic_chain: closed_chain
  laterality: bilateral_symmetric
  primary_plane: sagittal

phase_model:
  type: resistance_phase
  expected_ratio:
    eccentric: 0.4
    isometric: 0.1
    concentric: 0.5

landmarks:
  model: mediapipe_pose_33
  primary_joints: [left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle]

compensation_candidates:
  - knee_valgus
  - excessive_trunk_flexion
  - lateral_pelvic_shift

feature_domains:
  spatial: [rom, symmetry, shape]
  temporal: [tempo, variability]
  control: [stability, compensation]
```

권장 최상위 필드 (전체):

```yaml
exercise_id: string
display_name: string
description: string
version: string
tags: list[string]

classification: object
support: object
phase_model: object
landmarks: object
angle_definitions: object
joint_actions: object
biomechanical_focus: object
compensation_candidates: list[string]
feature_domains: object
view_requirements: object
quality_rules: object
notes: string
```

초기 구현은 모든 필드를 채울 필요가 없다. 스키마는 후속 추가가 구조 재설계를 요구하지 않도록 설계되었다.

---

# 필드 사전 (Field Dictionary)

본 절은 운동 정의 YAML의 각 필드와 허용 어휘를 정의한다. 본 사전은 ⑦ 특징 추출 / ⑧ 생체역학적 근사 모델링 / ⑨ 지표화가 공통으로 참조하는 어휘이며, 자유 텍스트 입력은 허용하지 않는다 (어휘 외 값은 산출 비활성을 야기하므로).

## 8. 기본 메타데이터

### `exercise_id`

영문 lowercase snake_case의 고유 식별자.

```text
squat
lunge
pike_pushup
plank_shoulder_tap
single_leg_squat
pushup
side_plank
```

### `display_name`

사람이 읽기 위한 운동 명.

```text
Bodyweight Squat
Forward Lunge
Pike Push-up
Plank Shoulder Tap
```

### `description`

짧은 운동 설명. 의대 자문위원이 읽었을 때도 의미가 명확해야 한다.

```yaml
description: 양측 하지 폐쇄 사슬 동작으로 hip·knee·ankle 협응을 평가한다.
```

### `version`

운동 정의 버전(semantic).

### `tags`

검색·그룹핑용 태그. 어휘:

```text
bodyweight   lower_body   upper_body   core
closed_chain bilateral    unilateral   asymmetric
stability    mobility     strength     rehab
sports       screening
```

---

## 9. classification

운동의 거시적 분류.

```yaml
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
```

각 필드의 어휘는 §부록 A에 정리한다.

---

## 10. support

신체가 지면·지지면과 어떻게 접촉하는지를 정의한다.

```yaml
support:
  base_of_support: bilateral_feet
  contact_points: [left_foot, right_foot]
  support_surface: floor
  weight_bearing_regions: [left_foot, right_foot]
```

어휘는 §부록 A 참조.

---

## 11. phase_model

운동의 시간적 구조.

```yaml
phase_model:
  type: resistance_phase
  expected_ratio:
    eccentric: 0.4
    isometric: 0.1
    concentric: 0.5
```

`expected_ratio` 합은 약 1.0 (허용 0.98 ~ 1.02).

`type` 어휘:

```text
resistance_phase   eccentric / isometric / concentric 구조
task_phase         과제형: setup / shift / tap / return 등
static_hold        정적 자세 유지
cyclic             반복적 순환 동작 (저항 단계 구분 없음)
locomotion_phase   보행 / step 기반
balance_phase      시간 경과에 따른 균형 도전
transition_phase
custom
```

상세 어휘(저항성 / 과제형 / 정적 / 보행)는 §부록 A.

---

## 12. landmarks

### 12-1. 모델

초기 모델은 MediaPipe Pose 33 (`mediapipe_pose_33`).

```yaml
landmarks:
  model: mediapipe_pose_33
```

MediaPipe Pose 33 인덱스는 §부록 B 참조.

### 12-2. 권장 관절·영역 명

본 프레임워크 내 코드·논문에서 사용하는 표준 명명:

```text
left_shoulder   right_shoulder   left_elbow   right_elbow
left_wrist      right_wrist      left_hip     right_hip
left_knee       right_knee       left_ankle   right_ankle
left_foot       right_foot       trunk        pelvis        head
```

### 12-3. `primary_joints`

운동의 주된 작용 관절.

```yaml
primary_joints:
  - left_hip
  - right_hip
  - left_knee
  - right_knee
  - left_ankle
  - right_ankle
```

### 12-4. `secondary_joints`

주된 작용은 아니지만 안정성·정렬·보상에 관여하는 관절.

```yaml
secondary_joints:
  - left_shoulder
  - right_shoulder
  - trunk
  - pelvis
```

### 12-5. `critical_landmarks`, `optional_landmarks`

```yaml
critical_landmarks: [23, 24, 25, 26, 27, 28]
optional_landmarks: [11, 12, 29, 30, 31, 32]
```

`critical_landmarks` 누락은 분석 가능성을 직접 위협한다. `optional_landmarks`는 보조 지표 산출에 도움이 된다.

---

## 13. angle_definitions

관절 각도 산출 규약.

```yaml
angle_definitions:
  left_knee_angle:
    points: [23, 25, 27]
    vertex: 25
  right_knee_angle:
    points: [24, 26, 28]
    vertex: 26
```

표준 각도 명·MediaPipe triplet은 §부록 B 참조. 단일 비전 기반 angle은 모두 “proxy”로 해석한다.

---

## 14. joint_actions

각 관절에서 기대되는 작용. `_proxy` 접미사는 단일 비전에서 간접적으로 추정함을 의미한다.

```yaml
joint_actions:
  primary:
    - hip_flexion_extension
    - knee_flexion_extension
    - ankle_dorsiflexion_plantarflexion
  secondary:
    - trunk_flexion_control
    - pelvis_frontal_plane_control
```

전체 어휘는 §부록 A.

---

## 15. biomechanical_focus

운동을 어떻게 역학적으로 해석할지 명시한다. ⑧ 생체역학적 근사 모델링 단계가 직접 참조한다.

```yaml
biomechanical_focus:
  expected_com_motion: vertical
  stability_requirement: medium
  main_load_regions: [hip, knee, ankle]
  primary_constraints: [maintain_foot_contact, maintain_trunk_alignment]
```

`expected_com_motion` 어휘:

```text
minimal                          vertical
anterior_posterior               medial_lateral
vertical_and_anterior_posterior  vertical_and_medial_lateral
rotational                       multidirectional
```

`stability_requirement`: `low | medium | high | very_high`.

`main_load_regions`, `primary_constraints` 어휘는 §부록 A.

> 본 단계의 산출 지표는 모두 “상대적 부하 분포의 경향성”이며, 절대 토크가 아니다 ([`_terminology.md`](_terminology.md) §4, §8).

---

## 16. compensation_candidates

해당 운동에서 모니터링할 보상 움직임 후보. 본 리스트에 명시된 후보만 ⑨ 지표화에서 바이오마커로 산출된다.

```yaml
compensation_candidates:
  - knee_valgus
  - excessive_trunk_flexion
  - lateral_pelvic_shift
```

전체 어휘 (하지 / 체간·골반 / 상지 / 제어·타이밍 4 그룹)는 §부록 A.

---

## 17. feature_domains

활성화되는 특징 영역.

```yaml
feature_domains:
  spatial:
    - rom
    - symmetry
    - shape
  temporal:
    - tempo
    - variability
  control:
    - stability
    - compensation
  biomechanical_proxy:
    - com_displacement
    - moment_arm_proxy
```

각 하위 어휘는 §부록 A.

---

## 18. view_requirements

카메라 시야와 가려짐 위험을 명시한다. 단일 비전 환경에서 시야 선택은 산출 신뢰도에 직결된다.

```yaml
view_requirements:
  preferred_views: [frontal, sagittal_left, sagittal_right]
  acceptable_views: [front_oblique, side_oblique]
  critical_landmarks: [23, 24, 25, 26, 27, 28]
  occlusion_risk: medium
```

어휘는 §부록 A.

---

## 19. quality_rules

분석 가능성을 판정하는 임계값 집합.

```yaml
quality_rules:
  minimum_visible_landmark_ratio: 0.8
  minimum_critical_landmark_ratio: 0.9
  max_missing_gap_frames: 10
  max_interpolation_gap_frames: 3
  exclude_rep_if_critical_landmark_missing: true
  exclude_rep_if_phase_missing: false
  allow_partial_feature_output: true
```

본 필드는 ④ 전처리와 ⑦ 특징 추출이 직접 읽는다.

---

## 20. annotation과의 관계

annotation은 “이 프레임이 한 반복(rep)이다”를 표시한다. 운동 정의는 “그 반복이 무엇을 의미하는가”를 표시한다.

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern
rep,1,1,100,180,true,squat,bilateral
rep,1,2,190,270,true,squat,bilateral
```

`squat` 운동 정의가 명시하는 것:

```text
- 주요 관절: hip, knee, ankle
- 주된 평면: sagittal
- 좌우 패턴: bilateral_symmetric
- 보상 움직임 후보: knee_valgus, lateral_pelvic_shift, ...
- 기대 phase 비율: eccentric 0.4 / isometric 0.1 / concentric 0.5
- 기대 CoM 이동: vertical
```

이 둘이 결합되어 후속 단계는 어떤 특징을 산출하고, 어떤 바이오마커를 도출하며, 각 반복을 어떻게 해석할지를 결정한다.

## 21. Fallback Behavior

`exercise_type`이 annotation에 누락되었거나, 해당 YAML 파일을 찾지 못하면 generic 정의가 적재된다.

```yaml
exercise_id: generic
display_name: Generic Movement
classification:
  family: full_body
  laterality: bilateral_symmetric
  primary_plane: sagittal
phase_model:
  type: cyclic
landmarks:
  model: mediapipe_pose_33
  primary_joints: []
compensation_candidates: []
feature_domains:
  spatial: [rom]
  temporal: [tempo]
  control: [stability]
quality_rules:
  minimum_visible_landmark_ratio: 0.8
```

generic 모드에서도 분석 단계는 실행되며, 산출 지표는 운동 무관 spatial / temporal / 안정성 특징으로 제한된다. 보상 움직임 바이오마커는 산출되지 않는다.

---

## 22. 운동 정의 작성 워크플로 (노트북 → annotation 해석 파일)

운동 정의는 YAML로 직접 작성하거나, 본 프로젝트의 노트북(드롭다운/체크박스/숫자 입력)을 통해 대화식으로 작성할 수 있다.

### 목표

```text
1. 비개발자(예: 임상 자문위원, 운동 처방자)도 운동 정의를 작성할 수 있게 한다.
2. 작성 시점에 어휘 검증을 수행한다.
3. 다음 두 산출물을 생성한다:
   - 운동 정의 YAML
   - 시각화·보고서가 사용할 annotation 해석 파일
```

### 노트북 셀 배치 (예정)

```text
Cell 1.  exercise_id, display_name 선택
Cell 2.  classification           (드롭다운: family, posture_type, ...)
Cell 3.  support                  (드롭다운: base_of_support, support_surface)
Cell 4.  phase_model              (type 드롭다운, expected_ratio 숫자 입력)
Cell 5.  landmarks                (다중 선택: primary_joints, secondary_joints)
Cell 6.  joint_actions            (다중 선택: primary, secondary)
Cell 7.  biomechanical_focus      (드롭다운 + 다중 선택)
Cell 8.  compensation_candidates  (다중 선택)
Cell 9.  feature_domains          (영역별 다중 선택)
Cell 10. view_requirements        (다중 선택 + 드롭다운)
Cell 11. quality_rules            (숫자/불리언)
Cell 12. 검증 / 미리보기           (스키마·어휘·비율 합 점검)
Cell 13. 내보내기                  (YAML + annotation 해석 파일)
```

각 드롭다운은 어휘 외 값을 거부해 향후 산출 비활성을 만드는 오타를 사전에 막는다.

### Annotation 해석 파일

운동 정의를 내보낼 때 함께 작성되는 보조 파일.

```text
exercise_definitions/<exercise_id>.yaml             # 정의
annotation_hints/<exercise_id>_interpretation.yaml  # 해석 힌트
```

내용 예:

```yaml
exercise_id: squat
display_name: Bodyweight Squat
definition_version: 0.1.0

annotation_hints:
  rep_meaning: |
    한 반복은 완전한 하강과 상승이다. eccentric / concentric 지속 시간이
    크게 비대칭이면 페이싱 또는 제어 문제를 시사한다.
  expected_pattern: bilateral
  expected_phases: [eccentric, isometric, concentric]
  primary_indicators:
    - knee_valgus_index
    - depth_asymmetry_ratio
    - trunk_flexion_excess
    - tempo_cv
  reading_guide:
    knee_valgus_index: |
      값이 클수록 하강 단계 무릎의 전두면 collapse를 의미한다.
      반대측·세트 내 다른 반복과 함께 비교한다.
    depth_asymmetry_ratio: |
      0.15 이상이면 단측 깊이 편향 가능성. 해석 전 랜드마크 신뢰도를 확인한다.
    trunk_flexion_excess: |
      양수는 기대 범위 초과 trunk flexion. hip mobility 또는 균형 신호일 수 있다.
  view_advice: |
    knee_valgus_index는 frontal 시야가 권장된다.
    trunk_flexion_excess와 depth_asymmetry_ratio는 sagittal 시야가 권장된다.
```

이 파일이 사용되는 곳:

```text
⑩ 시각화        → 바이오마커별 reading guide / 차트 주석
보고서 자동 생성 → 운동별 보고서 섹션
provenance      → 사용자에게 노출되는 source_fields 설명
```

노트북은 바이오마커 값을 계산하지 않는다. 노트북의 단일 책임은 두 YAML 파일 작성이다.

### 작성 시점 검증

노트북은 분석 단계 시작 시 로더가 수행하는 검증과 동일한 검증을 수행한다.

```text
- 필수 필드 존재
- 어휘 값이 허용 집합 안에 있는지
- expected_ratio 합이 1.0 ± 0.02 인지
- primary_joints가 비어있지 않은지
- compensation_candidates가 허용 어휘 안에 있는지
- feature_domains가 허용 어휘 안에 있는지
```

검증 실패 시 YAML 내보내기를 차단하고 노트북에 읽기 쉬운 오류를 표시한다.

---

## 23. 초기 완료 기준

```text
1. 운동 정의 YAML 파일을 적재할 수 있다.
2. 필수 필드가 검증된다.
3. 어휘 값이 검증된다.
4. phase 비율 합이 1.0에 근접하는지 점검된다.
5. primary / secondary 관절이 파싱된다.
6. compensation_candidates 가 파싱된다.
7. feature_domains 가 파싱된다.
8. exercise_type 누락 시 generic fallback이 동작한다.
9. 후속 단계가 운동별 분석 규칙을 정의 객체로부터 조회할 수 있다.
```

초기 구현이 다루지 않는 항목:

```text
- 데이터로부터 운동 정의 자동 생성
- 포즈로부터 운동 종류 자동 판별
- phase 자동 검출
- 생체역학적 근사 직접 산출
- 동작 품질 점수화
- 드롭다운 노트북
```

드롭다운 노트북과 annotation 해석 파일 내보내기는 다음 개발 단계에서 추가된다.

---

## 24. 향후 확장

- 본 사전으로부터 JSON 스키마 자동 생성, 로더와 노트북이 공통 검증 사용
- 정의 diffing 도구: 정의 수정 시 어떤 바이오마커가 활성/비활성되는지 요약
- 큐레이션된 정의 라이브러리(`exercise_definitions/`): 일반 스크리닝·재활 동작 포함
- `compensation_candidates` 자동 제안 (classification + phase_model 기반)
- 동일 운동의 인구 변종(예: 노인, 술후) 정의 — 기본 정의 상속
- 바이오마커 provenance를 ⑨ 지표화에 직접 연결해 점수 설명에서 정의 필드를 인용

---

## 25. 예시: Bodyweight Squat (Full)

```yaml
exercise_id: squat
display_name: Bodyweight Squat
description: 양측 하지 폐쇄 사슬 동작으로 hip·knee·ankle 협응을 평가한다.
version: 0.1.0
tags:
  - bodyweight
  - lower_body
  - closed_chain
  - bilateral
  - strength

classification:
  family: lower_body
  equipment: none
  load_type: bodyweight
  external_load_position: none
  posture_type: standing
  kinetic_chain: closed_chain
  laterality: bilateral_symmetric
  movement_pattern: squat
  primary_plane: sagittal
  secondary_planes:
    - frontal
    - transverse
  complexity: compound

support:
  base_of_support: bilateral_feet
  contact_points:
    - left_foot
    - right_foot
  support_surface: floor
  weight_bearing_regions:
    - left_foot
    - right_foot

phase_model:
  type: resistance_phase
  expected_ratio:
    eccentric: 0.4
    isometric: 0.1
    concentric: 0.5

landmarks:
  model: mediapipe_pose_33
  primary_joints:
    - left_hip
    - right_hip
    - left_knee
    - right_knee
    - left_ankle
    - right_ankle
  secondary_joints:
    - left_shoulder
    - right_shoulder
    - trunk
    - pelvis
    - left_foot
    - right_foot
  critical_landmarks: [23, 24, 25, 26, 27, 28]
  optional_landmarks: [11, 12, 29, 30, 31, 32]

angle_definitions:
  left_hip_angle:   { points: [11, 23, 25], vertex: 23 }
  right_hip_angle:  { points: [12, 24, 26], vertex: 24 }
  left_knee_angle:  { points: [23, 25, 27], vertex: 25 }
  right_knee_angle: { points: [24, 26, 28], vertex: 26 }
  left_ankle_angle: { points: [25, 27, 31], vertex: 27 }
  right_ankle_angle:{ points: [26, 28, 32], vertex: 28 }
  shoulder_line_angle: { points: [11, 12] }
  pelvis_line_angle:   { points: [23, 24] }

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
  main_load_regions:
    - hip
    - knee
    - ankle
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
  spatial:
    - rom
    - symmetry
    - shape
    - depth_proxy
    - alignment
  temporal:
    - tempo
    - rep_duration
    - eccentric_duration
    - isometric_duration
    - concentric_duration
    - timing_ratio
  control:
    - stability
    - compensation
    - com_stability
    - pelvis_stability
    - joint_tracking_error
    - lateral_shift
  biomechanical_proxy:
    - com_displacement
    - segment_length_normalized_displacement
    - moment_arm_proxy
    - relative_joint_load_proxy
    - compensation_load_shift_proxy

view_requirements:
  preferred_views:
    - frontal
    - sagittal_left
    - sagittal_right
  acceptable_views:
    - front_oblique
    - side_oblique
  critical_landmarks: [23, 24, 25, 26, 27, 28]
  visibility_sensitive_landmarks: [23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
  occlusion_risk: medium

quality_rules:
  minimum_visible_landmark_ratio: 0.8
  minimum_critical_landmark_ratio: 0.9
  max_missing_gap_frames: 10
  max_interpolation_gap_frames: 3
  exclude_rep_if_critical_landmark_missing: true
  exclude_rep_if_phase_missing: false
  allow_partial_feature_output: true

notes: |
  스쿼트는 좌우 대칭, 시상면 ROM, CoM 변위, 하지 보상 움직임을 평가하기 위한
  대표 참조 운동이다.
```

---

# 부록 A. 어휘 표 (Vocabulary Reference)

본 부록은 운동 정의 작성 시 허용되는 어휘를 분야별로 정리한다.

### A-1. classification.family

```text
lower_body   upper_body   core           full_body
balance      locomotion   mobility       plyometric
rehabilitation
```

### A-2. classification.equipment

```text
none                  bodyweight_only       barbell
dumbbell              kettlebell            machine
cable                 resistance_band       suspension_trainer
medicine_ball         bench                 box
wall                  chair                 foam_roller
other
```

### A-3. classification.load_type / external_load_position

```text
load_type:
bodyweight             external_load          assisted
resisted               partner_assisted       machine_guided
partial_weight_bearing non_weight_bearing

external_load_position:
none           front_rack       back_rack       overhead
goblet         suitcase         bilateral_hands unilateral_hand
vest           ankle_weight     machine_path    other
```

### A-4. classification.posture_type

```text
standing               standing_split         single_leg_standing
kneeling               half_kneeling          quadruped
prone                  supine                 side_lying
seated                 plank                  side_plank
inverted               inverted_closed_chain  hanging
locomotion             transitioning
```

### A-5. classification.kinetic_chain / laterality / movement_pattern / planes / complexity

```text
kinetic_chain:
open_chain                closed_chain
mixed_chain               closed_chain_alternating
open_chain_alternating

laterality:
bilateral_symmetric    bilateral_asymmetric
unilateral_left        unilateral_right
unilateral_unspecified alternating
anti_rotation          cross_body

movement_pattern:
squat       hinge       lunge       step
push        pull        press       row
carry       plank       anti_rotation rotation
locomotion  jump        landing     balance_hold
reach       raise       bridge      crawl
other

primary_plane:
sagittal   frontal   transverse   multiplanar   static

secondary_planes:
sagittal   frontal   transverse

complexity:
single_joint   multi_joint   compound   whole_body   skill_based
```

### A-6. support 어휘

```text
base_of_support:
bilateral_feet         single_foot_left   single_foot_right
split_stance           hands_and_feet     forearms_and_feet
hands_only             knees              hands_and_knees
side_support           seated_support     external_support
moving_support

contact_points:
left_foot    right_foot     left_heel    right_heel
left_toe     right_toe      left_hand    right_hand
left_wrist   right_wrist    left_forearm right_forearm
left_knee    right_knee     left_hip     right_hip
pelvis       back           head         external_object

support_surface:
floor        mat            bench        box
wall         chair          machine      unstable_surface
suspension   other

weight_bearing_regions:
left_foot     right_foot     left_hand     right_hand
left_forearm  right_forearm  left_knee     right_knee
pelvis        trunk
```

### A-7. phase_model 표준 단계명

```text
resistance_phase:
eccentric            isometric           concentric
transition_top       transition_bottom

task_phase:
setup        support_stable   weight_shift   tap
reach        return           reset          hold
release      contact          recovery       transition

static_hold:
setup   hold   fatigue   release

locomotion_phase:
initial_contact   loading_response   mid_stance       terminal_stance
pre_swing         initial_swing      mid_swing        terminal_swing
```

### A-8. joint_actions 어휘

```text
shoulder_flexion_extension                  shoulder_abduction_adduction
shoulder_horizontal_abduction_adduction     shoulder_internal_external_rotation_proxy
elbow_flexion_extension                     wrist_extension_flexion_proxy

hip_flexion_extension                       hip_abduction_adduction
hip_internal_external_rotation_proxy        knee_flexion_extension
ankle_dorsiflexion_plantarflexion           foot_pronation_supination_proxy

trunk_flexion_extension                     trunk_lateral_flexion
trunk_rotation_proxy                        pelvis_anterior_posterior_tilt_proxy
pelvis_lateral_tilt_proxy                   pelvis_rotation_proxy
scapular_stability_proxy                    anti_rotation_control
weight_shift_control
```

### A-9. biomechanical_focus 어휘

`expected_com_motion`:

```text
minimal                          vertical
anterior_posterior               medial_lateral
vertical_and_anterior_posterior  vertical_and_medial_lateral
rotational                       multidirectional
```

`stability_requirement`: `low | medium | high | very_high`.

`main_load_regions`:

```text
shoulder   elbow   wrist   trunk   core
hip        knee    ankle   foot    pelvis
```

`primary_constraints`:

```text
maintain_foot_contact          maintain_hand_contact
maintain_trunk_alignment       maintain_pelvis_level
maintain_neutral_spine_proxy   avoid_excessive_rotation
avoid_excessive_lateral_shift  avoid_knee_valgus
avoid_heel_lift                maintain_head_position
maintain_support_symmetry      maintain_controlled_tempo
```

### A-10. compensation_candidates 어휘 (그룹별)

```text
# 하지
knee_valgus                      knee_varus
asymmetric_depth                 asymmetric_knee_flexion
asymmetric_hip_flexion           limited_ankle_dorsiflexion_proxy
heel_lift                        foot_external_rotation_proxy
foot_collapse_proxy              pelvis_drop
lateral_pelvic_shift             hip_shift
insufficient_rear_hip_extension  unstable_step_width

# 체간 / 골반
excessive_trunk_flexion          trunk_extension_compensation
lateral_trunk_lean               trunk_rotation
trunk_sway                       pelvis_rotation
pelvis_anterior_tilt_proxy       pelvis_posterior_tilt_proxy
hip_pike                         hip_drop
loss_of_neutral_spine_proxy

# 상지
shoulder_elevation_compensation  shoulder_asymmetry
shoulder_collapse                elbow_flare
elbow_asymmetry                  wrist_shift
scapular_instability_proxy       insufficient_head_descent
head_forward_shift

# 제어 / 타이밍
excessive_com_lateral_shift      excessive_com_variability
phase_timing_asymmetry           tempo_instability
left_right_timing_variability    movement_discontinuity
```

### A-11. feature_domains 어휘

```text
spatial:
rom                            joint_angle_min
joint_angle_max                joint_angle_range
symmetry                       shape
trajectory_similarity          alignment
posture_angle                  depth_proxy
reach_distance                 support_width
base_of_support_width

temporal:
tempo                          rep_duration
phase_duration                 eccentric_duration
isometric_duration             concentric_duration
timing_ratio                   variability
rhythm_consistency             left_right_timing_variability
pause_duration

control:
stability                      compensation
com_stability                  trunk_stability
pelvis_stability               joint_tracking_error
lateral_shift                  rotation_control
balance_control                movement_smoothness
endpoint_control

biomechanical_proxy:
com_displacement               com_velocity_proxy
segment_length_normalized_displacement
moment_arm_proxy               relative_joint_load_proxy
load_distribution_proxy        support_moment_proxy
compensation_load_shift_proxy
```

### A-12. view_requirements 어휘

```text
preferred_views / acceptable_views:
frontal           sagittal_left      sagittal_right
front_oblique     rear_oblique       side_oblique
top_down          any

occlusion_risk:
low   medium   high   very_high
```

---

# 부록 B. MediaPipe Pose 33 인덱스 / 표준 angle triplet

### B-1. MediaPipe Pose 33 인덱스

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

### B-2. 표준 angle triplet

```yaml
left_shoulder_angle:  [23, 11, 13]
right_shoulder_angle: [24, 12, 14]

left_elbow_angle:     [11, 13, 15]
right_elbow_angle:    [12, 14, 16]

left_hip_angle:       [11, 23, 25]
right_hip_angle:      [12, 24, 26]

left_knee_angle:      [23, 25, 27]
right_knee_angle:     [24, 26, 28]

left_ankle_angle:     [25, 27, 31]
right_ankle_angle:    [26, 28, 32]
```

이 triplet은 단일 비전 환경에서의 proxy 정의이며, 절대 해부학적 각도가 아니다.
