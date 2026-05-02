# Exercise Definition

## Purpose

The exercise definition layer describes the semantic and biomechanical structure of an exercise as data, before annotation, motion attribution, feature extraction, biomechanical proxy modeling, and scoring are applied.

Earlier framework drafts treated four target exercises (squat, lunge, pike push-up, plank shoulder tap) as fixed analysis targets. The exercise definition layer reframes that scope.

```text
old framing: implement analysis logic for four exercises
new framing: define exercises as biomechanical property objects,
             then derive interpretable biomarkers from those properties
```

The four target exercises remain the validation set used for the initial development. They are no longer the unit of analysis.

The unit of analysis is the exercise definition object, which specifies:

```text
- what type of movement it is
- which joints and body regions are important
- which phases are expected
- which compensation patterns should be monitored
- which features and biomechanical proxies are relevant
- which camera views and landmarks are required
- which quality rules apply
```

This makes the framework portable. Adding a new exercise becomes a YAML authoring task, not a feature engineering task.

## Background — Why a Property-Based Definition

Movement quality assessment from monocular pose data has a recurring problem: feature extraction code tends to grow exercise-specific branches that are hard to interpret and hard to reuse.

```text
typical drift:
- if exercise == "squat":      check knee valgus
- elif exercise == "lunge":    check rear hip extension
- elif exercise == "pushup":   check elbow flare
- ...
```

Each branch encodes implicit assumptions about which joints matter, which planes are dominant, and which deviations should count as compensation. Those assumptions are buried inside code rather than expressed as data.

The exercise definition layer extracts those assumptions into a structured schema. Downstream modules read the definition and apply a common rule set, so each biomarker is traceable back to a declared property of the exercise.

```text
biomarker = function(definition_property, normalized_pose, annotation)
```

This is the basis for the framework's interpretability claim. A biomarker value can be explained by pointing at the definition fields that justified its computation.

## Pipeline Role

The exercise definition is loaded together with annotation, immediately after validation, and is made available to all subsequent modules.

```text
Pose CSV
+ optional annotation file
+ exercise definition (YAML)
-> Validation
-> Annotation Mask Application      (loads exercise_type and pattern)
-> Exercise Definition Loading      (loads YAML for that exercise_type)
-> Preprocessing                    (uses laterality, landmarks, quality_rules)
-> Normalization
-> Motion Attribution               (uses laterality, primary_joints)
-> Feature Extraction               (uses joint_actions, feature_domains)
-> Biomechanical Proxy Modeling     (uses biomechanical_focus)
-> Scoring                          (uses compensation_candidates)
-> Visualization / Report
```

The exercise definition does not mark frames. Annotation marks frames. The exercise definition tells downstream modules how the frames should be interpreted.

```text
exercise definition  -> what the movement means
annotation           -> where the movement occurs
features             -> what indicators are computed
biomechanics         -> how the indicators are interpreted
```

When `exercise_type` is missing from annotation, the pipeline falls back to a generic, exercise-agnostic definition (described in [Fallback Behavior](#fallback-behavior)).

## Design Principle

Exercise-specific information should be represented as data, not hidden inside code.

```text
do:
- declare primary joints in YAML
- declare expected phases in YAML
- declare compensation candidates in YAML
- let feature extraction read those declarations
- let scoring read those declarations

avoid:
- if exercise == "squat" inside every feature function
- assuming all exercises are bilateral symmetric
- assuming all exercises have eccentric / isometric / concentric phases
- using the same symmetry rule for squats and lunges
```

A second principle is auditability. Every computed biomarker should be traceable to one or more definition fields. This is what makes the output interpretable rather than just numeric.

---

## From Exercise List to Biomechanical Property Schema

Each exercise is represented as an object in a property space. The property space is the schema. The four initial exercises are simply four points in that space.

```text
property space (schema fields)
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

The four target exercises occupy the following positions:

```text
                       posture        kinetic_chain          laterality              primary_plane
─────────────────────  ─────────────  ─────────────────────  ──────────────────────  ─────────────
squat                  standing       closed_chain           bilateral_symmetric     sagittal
lunge                  standing_split closed_chain           alternating             sagittal
pike_pushup            inverted_cc    closed_chain           bilateral_symmetric     sagittal
plank_shoulder_tap     plank          closed_chain_alt       alternating             frontal
```

Adding a new exercise means choosing values along the same axes. No new code path is required for the analysis to remain interpretable, as long as the value falls inside the allowed vocabulary.

---

## Definition → Biomarker Mapping

This section explains how property fields drive biomarker selection. The exact formulas belong to the feature extraction and biomechanical proxy modules. The mapping below is the contract between those modules and the definition layer.

### Mapping Principles

```text
principle 1: every biomarker is owned by at least one definition field
             (no biomarker is computed without a justification field)

principle 2: when a definition field is absent, the dependent biomarkers
             are skipped, not silently approximated

principle 3: when a property changes, the biomarker set updates automatically
             (e.g., changing laterality enables/disables symmetry biomarkers)

principle 4: biomarker output should carry provenance
             (which definition fields produced it, which annotation rep it belongs to)
```

### Table 1. Property Fields → Feature Domains

This table shows how high-level definition properties select which feature domains apply.

```text
definition field                       value                          enabled feature domains
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

Reading guide: a row says "if the definition declares this value for this field, then these feature-domain entries become eligible candidates for the exercise." Eligible candidates are still subject to landmark availability and quality rules.

### Table 2. Compensation Candidates → Biomarker Sketch

Each compensation candidate listed in a definition selects a single biomarker. The formulas below are sketches; the actual implementations are the responsibility of feature extraction and biomechanical proxy modules.

```text
compensation candidate                  biomarker name                          sketch (interpretation only)
──────────────────────────────────────  ──────────────────────────────────────  ──────────────────────────────────────────────
knee_valgus                             knee_valgus_index                       frontal-plane deviation of knee from
                                                                                hip–ankle line, normalized by torso length
asymmetric_depth                        depth_asymmetry_ratio                   |left_depth − right_depth| /
                                                                                max(left_depth, right_depth)
excessive_trunk_flexion                 trunk_flexion_excess                    peak trunk_angle minus expected
                                                                                trunk_angle band (defined per exercise)
lateral_pelvic_shift                    pelvis_shift_index                      max horizontal pelvis displacement
                                                                                during rep, normalized by torso length
heel_lift                               heel_lift_ratio                         frames where heel landmark height
                                                                                exceeds threshold, divided by rep length
elbow_flare                             elbow_flare_angle                       angle between humerus and trunk
                                                                                in frontal plane during press phase
shoulder_asymmetry                      shoulder_height_asymmetry               |left_shoulder.y − right_shoulder.y|
                                                                                normalized by shoulder width
hip_pike                                hip_pike_index                          deviation of hip_angle from neutral
                                                                                during plank-style holds
tempo_instability                       tempo_cv                                coefficient of variation of rep duration
                                                                                across reps in a set
left_right_timing_variability           lr_phase_offset_cv                      CV of |left_phase_end − right_phase_end|
                                                                                across reps
phase_timing_asymmetry                  phase_ratio_drift                       distance between observed phase ratios
                                                                                and expected_ratio in phase_model
```

A definition that does not list a given compensation candidate will not produce the corresponding biomarker. This is intentional and is what makes the biomarker set interpretable per exercise.

### Provenance Convention

Each biomarker emitted by feature extraction should carry the definition fields that produced it. This is the recommended record format used by downstream scoring and visualization modules:

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

Scoring should never compute a biomarker that does not have a `source_fields` entry. This keeps interpretation auditable.

---

## Schema Overview

A minimal definition contains a small number of fields. The full field dictionary follows in the next section.

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

Recommended top-level fields:

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

The initial implementation does not need to populate every field. The schema is designed so that later additions do not require restructuring the document.

---

# Field Dictionary

## 1. Basic Metadata

### `exercise_id`

Unique machine-readable exercise name in lowercase snake_case.

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

Human-readable exercise name.

```text
Bodyweight Squat
Forward Lunge
Pike Push-up
Plank Shoulder Tap
```

### `description`

Short explanation of the exercise.

```yaml
description: Bilateral lower-limb closed-chain movement emphasizing hip, knee, and ankle coordination.
```

### `version`

Schema or exercise definition version, semantic.

```text
0.1.0
0.2.0
1.0.0
```

### `tags`

Optional search or grouping labels.

```text
bodyweight   lower_body   upper_body   core
closed_chain bilateral    unilateral   asymmetric
stability    mobility     strength     rehab
sports       screening
```

---

## 2. Classification

The `classification` field defines the broad movement category.

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

### `family`

```text
lower_body   upper_body   core           full_body
balance      locomotion   mobility       plyometric
rehabilitation
```

### `equipment`

```text
none                  bodyweight_only       barbell
dumbbell              kettlebell            machine
cable                 resistance_band       suspension_trainer
medicine_ball         bench                 box
wall                  chair                 foam_roller
other
```

Use `none` for exercises that do not require equipment. Use `bodyweight_only` when the distinction from unloaded clinical movement is meaningful.

### `load_type`

```text
bodyweight             external_load          assisted
resisted               partner_assisted       machine_guided
partial_weight_bearing non_weight_bearing
```

### `external_load_position`

```text
none           front_rack       back_rack       overhead
goblet         suitcase         bilateral_hands unilateral_hand
vest           ankle_weight     machine_path    other
```

### `posture_type`

```text
standing               standing_split         single_leg_standing
kneeling               half_kneeling          quadruped
prone                  supine                 side_lying
seated                 plank                  side_plank
inverted               inverted_closed_chain  hanging
locomotion             transitioning
```

Examples:

```text
squat              -> standing
lunge              -> standing_split
pike_pushup        -> inverted_closed_chain
plank_shoulder_tap -> plank
```

### `kinetic_chain`

```text
open_chain                closed_chain
mixed_chain               closed_chain_alternating
open_chain_alternating
```

Examples:

```text
squat              -> closed_chain
lunge              -> closed_chain
pike_pushup        -> closed_chain
plank_shoulder_tap -> closed_chain_alternating
```

### `laterality`

```text
bilateral_symmetric    bilateral_asymmetric
unilateral_left        unilateral_right
unilateral_unspecified alternating
anti_rotation          cross_body
```

Interpretation:

```text
bilateral_symmetric  -> left and right are expected to behave similarly
bilateral_asymmetric -> left and right have different roles
unilateral_*         -> one side is the primary working side
alternating          -> sides alternate across reps or phases
anti_rotation        -> movement challenges rotational control
cross_body           -> opposite-side coordination is central
```

### `movement_pattern`

```text
squat       hinge       lunge       step
push        pull        press       row
carry       plank       anti_rotation rotation
locomotion  jump        landing     balance_hold
reach       raise       bridge      crawl
other
```

### `primary_plane`

```text
sagittal   frontal   transverse   multiplanar   static
```

### `secondary_planes`

```text
sagittal   frontal   transverse
```

```text
primary_plane    -> where intended movement mainly occurs
secondary_planes -> where compensation or instability may appear
```

### `complexity`

```text
single_joint   multi_joint   compound   whole_body   skill_based
```

---

## 3. Support and Contact

The `support` field defines how the body contacts the ground or support surface.

```yaml
support:
  base_of_support: bilateral_feet
  contact_points: [left_foot, right_foot]
  support_surface: floor
  weight_bearing_regions: [left_foot, right_foot]
```

### `base_of_support`

```text
bilateral_feet         single_foot_left   single_foot_right
split_stance           hands_and_feet     forearms_and_feet
hands_only             knees              hands_and_knees
side_support           seated_support     external_support
moving_support
```

### `contact_points`

```text
left_foot    right_foot     left_heel    right_heel
left_toe     right_toe      left_hand    right_hand
left_wrist   right_wrist    left_forearm right_forearm
left_knee    right_knee     left_hip     right_hip
pelvis       back           head         external_object
```

### `support_surface`

```text
floor        mat            bench        box
wall         chair          machine      unstable_surface
suspension   other
```

### `weight_bearing_regions`

```text
left_foot     right_foot     left_hand     right_hand
left_forearm  right_forearm  left_knee     right_knee
pelvis        trunk
```

---

## 4. Phase Model

The `phase_model` field defines the expected temporal structure of the movement.

```yaml
phase_model:
  type: resistance_phase
  expected_ratio:
    eccentric: 0.4
    isometric: 0.1
    concentric: 0.5
```

The sum of `expected_ratio` values should be approximately `1.0`.

### `type`

```text
resistance_phase   task_phase     static_hold
cyclic             locomotion_phase balance_phase
transition_phase   custom
```

Recommended use:

```text
resistance_phase -> eccentric / isometric / concentric structure
task_phase       -> task-specific phases such as support, shift, tap, return
static_hold      -> no repeated dynamic phase; stability is the main output
cyclic           -> repeated cyclic movement without clear resistance phase
locomotion_phase -> gait-like or step-based movement
balance_phase    -> stability challenge over time
custom           -> exercise-specific user-defined phase model
```

### Standard `resistance_phase` names

```text
eccentric            isometric           concentric
transition_top       transition_bottom
```

### Standard `task_phase` names

```text
setup        support_stable   weight_shift   tap
reach        return           reset          hold
release      contact          recovery       transition
```

Example:

```yaml
phase_model:
  type: task_phase
  expected_ratio:
    support_stable: 0.25
    weight_shift: 0.25
    tap: 0.25
    return: 0.25
```

### Standard `static_hold` names

```text
setup   hold   fatigue   release
```

### Standard `locomotion_phase` names

```text
initial_contact   loading_response   mid_stance       terminal_stance
pre_swing         initial_swing      mid_swing        terminal_swing
```

### Phase Ratio Rules

```text
0.0 <= phase_ratio <= 1.0
sum(expected_ratio.values()) ~= 1.0    (tolerance 0.98 to 1.02)
```

---

## 5. Landmark Model

The initial landmark convention is `mediapipe_pose_33`. MediaPipe Pose Landmarker outputs 33 body landmarks.

```yaml
landmarks:
  model: mediapipe_pose_33
```

### MediaPipe Pose 33 Landmark Index

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

### Recommended Joint Names

```text
left_shoulder   right_shoulder   left_elbow   right_elbow
left_wrist      right_wrist      left_hip     right_hip
left_knee       right_knee       left_ankle   right_ankle
left_foot       right_foot       trunk        pelvis        head
```

### Recommended Region Names

```text
head            neck_proxy       shoulder_girdle  trunk
thorax_proxy    pelvis           left_upper_arm   right_upper_arm
left_forearm    right_forearm    left_hand        right_hand
left_thigh      right_thigh      left_shank       right_shank
left_foot       right_foot
```

### `primary_joints`

Joints that define the main movement.

```yaml
primary_joints:
  - left_hip
  - right_hip
  - left_knee
  - right_knee
  - left_ankle
  - right_ankle
```

### `secondary_joints`

Joints that are not the main driver but matter for stability, alignment, or compensation.

```yaml
secondary_joints:
  - left_shoulder
  - right_shoulder
  - trunk
  - pelvis
```

### `critical_landmarks`

Landmarks required for reliable analysis.

```yaml
critical_landmarks: [23, 24, 25, 26, 27, 28]
```

### `optional_landmarks`

Helpful but not essential landmarks.

```yaml
optional_landmarks: [11, 12, 29, 30, 31, 32]
```

---

## 6. Angle Definitions

Angle definitions specify how joint angles should be computed.

```yaml
angle_definitions:
  left_knee_angle:
    points: [23, 25, 27]
    vertex: 25
  right_knee_angle:
    points: [24, 26, 28]
    vertex: 26
```

### Common Angle Names

```text
left_shoulder_angle     right_shoulder_angle
left_elbow_angle        right_elbow_angle
left_hip_angle          right_hip_angle
left_knee_angle         right_knee_angle
left_ankle_angle        right_ankle_angle
trunk_angle             pelvis_tilt_angle
shoulder_line_angle     pelvis_line_angle
```

### Common MediaPipe Angle Triplets

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

These triplets are proxy definitions and should be interpreted carefully in monocular data.

---

## 7. Joint Actions

The `joint_actions` field describes expected movement at primary and secondary joints.

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

Use the `_proxy` suffix when the measurement is only indirectly estimated from pose landmarks.

---

## 8. Biomechanical Focus

The `biomechanical_focus` field defines how the exercise should be interpreted mechanically.

```yaml
biomechanical_focus:
  expected_com_motion: vertical
  stability_requirement: medium
  main_load_regions: [hip, knee, ankle]
  primary_constraints: [maintain_foot_contact, maintain_trunk_alignment]
```

### `expected_com_motion`

```text
minimal                          vertical
anterior_posterior               medial_lateral
vertical_and_anterior_posterior  vertical_and_medial_lateral
rotational                       multidirectional
```

### `stability_requirement`

```text
low   medium   high   very_high
```

### `main_load_regions`

```text
shoulder   elbow   wrist   trunk   core
hip        knee    ankle   foot    pelvis
```

### `primary_constraints`

```text
maintain_foot_contact          maintain_hand_contact
maintain_trunk_alignment       maintain_pelvis_level
maintain_neutral_spine_proxy   avoid_excessive_rotation
avoid_excessive_lateral_shift  avoid_knee_valgus
avoid_heel_lift                maintain_head_position
maintain_support_symmetry      maintain_controlled_tempo
```

---

## 9. Compensation Candidates

Compensation candidates declare which deviations should be monitored.

```yaml
compensation_candidates:
  - knee_valgus
  - excessive_trunk_flexion
  - lateral_pelvic_shift
```

```text
# Lower body
knee_valgus                      knee_varus
asymmetric_depth                 asymmetric_knee_flexion
asymmetric_hip_flexion           limited_ankle_dorsiflexion_proxy
heel_lift                        foot_external_rotation_proxy
foot_collapse_proxy              pelvis_drop
lateral_pelvic_shift             hip_shift
insufficient_rear_hip_extension  unstable_step_width

# Trunk and pelvis
excessive_trunk_flexion          trunk_extension_compensation
lateral_trunk_lean               trunk_rotation
trunk_sway                       pelvis_rotation
pelvis_anterior_tilt_proxy       pelvis_posterior_tilt_proxy
hip_pike                         hip_drop
loss_of_neutral_spine_proxy

# Upper body
shoulder_elevation_compensation  shoulder_asymmetry
shoulder_collapse                elbow_flare
elbow_asymmetry                  wrist_shift
scapular_instability_proxy       insufficient_head_descent
head_forward_shift

# Control and timing
excessive_com_lateral_shift      excessive_com_variability
phase_timing_asymmetry           tempo_instability
left_right_timing_variability    movement_discontinuity
```

This list is intentionally broad. Each exercise should select only the compensation candidates that are biomechanically relevant.

---

## 10. Feature Domains

The `feature_domains` field selects which feature groups are relevant.

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

### Spatial Features

```text
rom                            joint_angle_min
joint_angle_max                joint_angle_range
symmetry                       shape
trajectory_similarity          alignment
posture_angle                  depth_proxy
reach_distance                 support_width
base_of_support_width
```

### Temporal Features

```text
tempo                          rep_duration
phase_duration                 eccentric_duration
isometric_duration             concentric_duration
timing_ratio                   variability
rhythm_consistency             left_right_timing_variability
pause_duration
```

### Control Features

```text
stability                      compensation
com_stability                  trunk_stability
pelvis_stability               joint_tracking_error
lateral_shift                  rotation_control
balance_control                movement_smoothness
endpoint_control
```

### Biomechanical Proxy Features

```text
com_displacement               com_velocity_proxy
segment_length_normalized_displacement
moment_arm_proxy               relative_joint_load_proxy
load_distribution_proxy        support_moment_proxy
compensation_load_shift_proxy
```

---

## 11. View Requirements

The `view_requirements` field defines camera-view expectations and occlusion risks.

```yaml
view_requirements:
  preferred_views: [frontal, sagittal_left, sagittal_right]
  acceptable_views: [front_oblique, side_oblique]
  critical_landmarks: [23, 24, 25, 26, 27, 28]
  occlusion_risk: medium
```

### `preferred_views`

```text
frontal           sagittal_left      sagittal_right
front_oblique     rear_oblique       side_oblique
top_down          any
```

### `acceptable_views`

```text
frontal           sagittal_left      sagittal_right
front_oblique     rear_oblique       side_oblique
any
```

### `occlusion_risk`

```text
low   medium   high   very_high
```

### `visibility_sensitive_landmarks`

Landmarks that are especially likely to affect feature reliability.

```yaml
visibility_sensitive_landmarks: [23, 24, 25, 26, 27, 28]
```

---

## 12. Quality Rules

Quality rules define whether a recording, set, rep, or phase is usable for downstream analysis.

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

Recommended fields:

```yaml
quality_rules:
  minimum_visible_landmark_ratio: float
  minimum_critical_landmark_ratio: float
  max_missing_gap_frames: integer
  max_interpolation_gap_frames: integer
  exclude_rep_if_critical_landmark_missing: boolean
  exclude_rep_if_phase_missing: boolean
  allow_partial_feature_output: boolean
```

---

## Relationship with Annotation

The exercise definition does not replace annotation. It makes annotation meaningful.

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern
rep,1,1,100,180,true,squat,bilateral
rep,1,2,190,270,true,squat,bilateral
```

Annotation says: "frames 100–180 are rep 1 of a squat."

The exercise definition for `squat` says:

```text
- hip, knee, and ankle are primary joints
- the primary movement plane is sagittal
- the exercise is bilateral symmetric
- knee valgus and lateral pelvic shift are relevant compensation candidates
- expected eccentric / isometric / concentric ratios are 0.4 / 0.1 / 0.5
- expected COM motion is vertical
```

Together, downstream modules know which features to compute, which biomarkers to derive, and how to interpret each rep.

## Fallback Behavior

If `exercise_type` is missing in annotation, or if the corresponding YAML file is not found, the pipeline loads a generic definition.

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

In generic mode, the pipeline still runs, but biomarker output is restricted to exercise-agnostic spatial, temporal, and stability features. No compensation biomarkers are emitted.

---

## Authoring Workflow (Notebook → Annotation Hints)

Definitions can be authored by hand in YAML, or interactively in a notebook that exposes each schema field as a dropdown / checkbox / numeric input.

### Goals

```text
1. allow non-developers to author exercise definitions
2. validate field values against the controlled vocabulary at authoring time
3. produce two artifacts:
   - the exercise definition YAML
   - an annotation interpretation file consumed by visualization and reporting
```

### Notebook Layout (planned)

```text
Cell 1. Pick exercise_id and display_name
Cell 2. classification           (dropdowns: family, posture_type, ...)
Cell 3. support                  (dropdowns: base_of_support, support_surface)
Cell 4. phase_model              (dropdown: type; numeric inputs: expected_ratio)
Cell 5. landmarks                (multi-select: primary_joints, secondary_joints)
Cell 6. joint_actions            (multi-select: primary, secondary)
Cell 7. biomechanical_focus      (dropdowns + multi-select)
Cell 8. compensation_candidates  (multi-select)
Cell 9. feature_domains          (multi-select per domain)
Cell 10. view_requirements       (multi-select + dropdown)
Cell 11. quality_rules           (numeric inputs + booleans)
Cell 12. Validate and preview    (schema check, vocabulary check, ratio sum check)
Cell 13. Export                  (writes YAML + annotation interpretation file)
```

Each dropdown is restricted to the controlled vocabulary defined in the field dictionary above. This prevents free-text typos that would silently disable downstream biomarkers.

### Annotation Interpretation File

When a definition is exported, the notebook also writes a small companion file. It contains the human-readable interpretation hints that visualization, reporting, and biomarker provenance use.

Suggested filename:

```text
exercise_definitions/<exercise_id>.yaml             # the definition itself
annotation_hints/<exercise_id>_interpretation.yaml  # the hints
```

Suggested content:

```yaml
exercise_id: squat
display_name: Bodyweight Squat
definition_version: 0.1.0

annotation_hints:
  rep_meaning: |
    One rep is one full descent and ascent. Eccentric and concentric
    durations should be roughly balanced; large asymmetry suggests
    pacing or control problems.
  expected_pattern: bilateral
  expected_phases: [eccentric, isometric, concentric]
  primary_indicators:
    - knee_valgus_index
    - depth_asymmetry_ratio
    - trunk_flexion_excess
    - tempo_cv
  reading_guide:
    knee_valgus_index: |
      Higher values indicate frontal-plane knee collapse during descent.
      Compare against the contralateral side and across reps in the set.
    depth_asymmetry_ratio: |
      Values above ~0.15 suggest unilateral depth bias; check landmark
      reliability before interpretation.
    trunk_flexion_excess: |
      Positive values indicate trunk flexion beyond the expected band;
      may be a hip mobility or balance signal.
  view_advice: |
    Frontal view is preferred for knee_valgus_index; sagittal view is
    preferred for trunk_flexion_excess and depth_asymmetry_ratio.
```

This file is consumed by:

```text
visualization  -> per-biomarker reading guide and chart annotations
report         -> auto-generated report sections per exercise
biomarker provenance -> source_fields explanation surfaced to the user
```

The notebook does not need to compute any biomarker values. Its only job is to author and export the two YAML files.

### Validation at Authoring Time

The notebook should run the same validation that the loader runs at pipeline start time.

```text
- required fields are present
- vocabulary values are inside the allowed set
- expected_ratio sums to 1.0 ± 0.02
- primary_joints is non-empty
- compensation_candidates only contains items from the allowed list
- feature_domains only contains items from the allowed lists
```

Failed validation should block export of the YAML and surface a readable error message in the notebook.

---

## Initial Completion Criteria

The first implementation of the exercise definition layer is complete when:

```text
1. exercise YAML files can be loaded
2. required fields are validated
3. vocabulary values are validated
4. phase ratios are checked to sum approximately to 1.0
5. primary and secondary joints are parsed
6. compensation candidates are parsed
7. feature domains are parsed
8. fallback to a generic definition works when exercise_type is missing
9. a downstream module can query exercise-specific analysis rules
```

The first implementation does not need to:

```text
- automatically generate exercise definitions from data
- automatically detect exercise type from pose
- automatically detect phases
- compute biomechanical proxies directly
- score movement quality
- ship the dropdown notebook
```

The dropdown notebook and the annotation interpretation export are planned in the next development step.

---

## Future Extensions

Later versions may include:

- a JSON schema file generated from this dictionary, used by the loader and the notebook for shared validation
- a definition diffing tool that summarizes which biomarkers will appear or disappear when a definition is edited
- a curated definition library (`exercise_definitions/`) covering common screening and rehab movements
- automatic suggestion of `compensation_candidates` based on `classification` and `phase_model`
- per-population variants of the same exercise (e.g., elderly, post-surgical) using inheritance from a base definition
- linking biomarker provenance to the scoring layer so that score explanations cite definition fields directly

---

# Example: Bodyweight Squat

```yaml
exercise_id: squat
display_name: Bodyweight Squat
description: Bilateral lower-body closed-chain movement emphasizing hip, knee, and ankle coordination.
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

notes: Squat is a suitable reference exercise for validating bilateral symmetry, sagittal-plane ROM, COM displacement, and lower-limb compensation indicators.
```
