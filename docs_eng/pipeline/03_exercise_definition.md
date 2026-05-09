# 03. Exercise Definition

**Document Version:** 1.4.5
**Last Updated:** 2026-05-09
**Korean Sync:** `docs/pipeline/03_exercise_definition.md` is the same-version Korean source.

Pipeline step ③. Loads exercise YAML files from `data/definitions/exercises/`.
Returns an `ExerciseDefinition` object that all downstream steps (④–⑨) reference
to apply exercise-specific logic.

---

## 1. Pipeline Position

```text
Pose CSV + annotation + exercise YAML
→ ① Validation
→ ② Annotation                    (exercise_type, pattern declared)
→ ③ Exercise Definition           ← this step
→ ④ Preprocessing                 (reads laterality, landmarks, quality_rules)
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution            (reads laterality, primary_joints)
→ ⑧ Feature Extraction            (reads feature_domains, joint_actions)
→ ⑨ Biomech Proxy                 (reads biomechanical_focus)
→ ⑩ Biomarker Derivation          (reads compensation_candidates)
```

Exercise definitions describe *what* the movement means.
Annotation describes *where* the movement happened.

## 2. Design

Exercise-specific behavior is expressed as YAML data, not code branches.
Adding a new exercise = writing one YAML file in `data/definitions/exercises/`.

Every biomarker produced by ⑧–⑩ must reference `source_fields` pointing to the
definition fields that drove its computation.

## 3. Available Definitions

```text
data/definitions/exercises/
    squat.yaml
    lunge.yaml
    pike_pushup.yaml
    plank_shoulder_tap.yaml
    generic.yaml               ← fallback
```

## 4. Fallback Behavior

If `exercise_type` is absent from annotation, or the corresponding YAML is not found,
`generic.yaml` is loaded. Generic mode activates only exercise-agnostic features
(ROM, tempo, stability). Compensation movement biomarkers are not produced.

```yaml
# generic.yaml (excerpt)
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

## 5. YAML Schema Overview

```yaml
exercise_id: string            # snake_case unique identifier
display_name: string
description: string
version: string
tags: list[string]

classification:                # macro-level exercise classification
support:                       # contact / base of support
phase_model:                   # temporal structure of one rep
rep_segmentation:              # repetition-boundary detection settings
phase_segmentation:            # intra-rep phase detection settings
performance_protocol:          # practical counting, side sequence, and completion rules
landmarks:                     # landmark model and primary/secondary joints
angle_definitions:             # joint angle triplets
joint_actions:                 # expected joint actions
biomechanical_focus:           # CoM motion, stability, load regions
compensation_candidates:       # list of compensation movements to monitor
feature_domains:               # which spatial/temporal/control features to activate
view_requirements:             # preferred camera views
camera_protocol:               # recommended filming zone/height and warning policy
quality_rules:                 # thresholds for analysis eligibility
notes: string
```

Not all fields need to be populated in the initial implementation.
The schema is designed to allow incremental addition without restructuring.

## 6. Field Reference

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

`laterality` controls:
- ④ preprocessing: whether to run L/R swap detection
- ⑦ motion attribution: whether to run per-rep active-side check (`bilateral_symmetric` → skipped)

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
  expected_ratio:             # only for resistance_phase; must sum to ~1.0
    eccentric: 0.4
    isometric: 0.1
    concentric: 0.5
```

Standard phase names:

```text
resistance_phase  : eccentric, isometric, concentric, transition_top, transition_bottom
task_phase        : setup, support_stable, weight_shift, tap, reach, return, reset, hold, ...
static_hold       : setup, hold, fatigue, release
locomotion_phase  : initial_contact, loading_response, mid_stance, terminal_stance, ...
```

### rep_segmentation / phase_segmentation

`rep_segmentation` confirms repetition start/end boundaries and creates `rep_id`.
`phase_segmentation` keeps the existing identifier and YAML key, and creates
kinematic phase labels inside confirmed reps.

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

`performance_protocol` records how the participant is instructed to perform and
count the exercise. It is separate from `rep_segmentation`: segmentation defines
which movement unit receives a `rep_id`, while the performance protocol defines
how the protocol-facing count is interpreted.

This separation is needed for exercises such as plank shoulder tap, where each tap
may be segmented as an atomic movement but one participant-facing protocol count
means a left-right pair.

```yaml
performance_protocol:
  counting:
    target_count: 10
    count_unit: repetition       # repetition | left_right_pair | hold_seconds
    segmentation_reps_per_count: 1
  side_sequence:
    mode: none                   # none | alternating_each_rep | same_side_block_then_switch
    block_size_counts: null      # e.g., lunge: 5
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

Field meanings:

```text
target_count                  participant-facing target count
count_unit                    what one protocol count means
segmentation_reps_per_count   how many segmented atomic reps correspond to one protocol count
side_sequence.mode            expected left/right order at the protocol level
block_size_counts             count size before side switching, if block-based
first_side_source             where the first side is declared
allow_partial_completion      whether fewer than target_count can be accepted with metadata
recommended_sets              practical acquisition recommendation, not an automatic multiplier
```

Examples:

```yaml
# Lunge: 5 repetitions on one side, then 5 on the other side.
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

# Plank shoulder tap: one left-right pair is counted as one protocol cycle.
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

Current implementation parses and validates this metadata in ③ Exercise Definition.
⑦ Motion Attribution still uses the existing `pattern` / `starting_side` behavior;
block-based side-sequence enforcement is a later implementation step.

Acquisition rules that are fixed by the performance protocol, such as count unit,
side sequence, and completion policy, belong in `performance_protocol`. What
actually happened during acquisition (`actual_rep_count`, `failure_point_frame`,
`failure_reason`, and related fields) belongs to ② Annotation or recording metadata,
not to the exercise definition. Compensation candidates are declared in
`compensation_candidates` and `feature_domains.control`; candidates that are not yet
implemented by ⑧–⑩ must be reported rather than silently ignored. Temporary
development mappings and TODOs belong only in the git-ignored
`docs_eng/code_revision_plan.md`, not in the publication-facing acquisition
protocol document.

### landmarks

```yaml
landmarks:
  model: mediapipe_pose_33
  primary_joints: [left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle]
  secondary_joints: [left_shoulder, right_shoulder, trunk, pelvis]
  critical_landmarks: [23, 24, 25, 26, 27, 28]   # MediaPipe indices
  optional_landmarks: [11, 12, 29, 30, 31, 32]
```

Standard joint names:

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

Standard triplets (MediaPipe indices):

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

Only compensation movements listed here are produced as biomarkers by ⑩.

Full vocabulary:

```text
# Lower body
knee_valgus                    knee_varus
asymmetric_depth               asymmetric_knee_flexion
asymmetric_hip_flexion         limited_ankle_dorsiflexion_proxy
heel_lift                      foot_external_rotation_proxy
foot_collapse_proxy            pelvis_drop
lateral_pelvic_shift           hip_shift
insufficient_rear_hip_extension unstable_step_width

# Trunk / pelvis
excessive_trunk_flexion        trunk_extension_compensation
lateral_trunk_lean             trunk_rotation
trunk_sway                     pelvis_rotation
pelvis_anterior_tilt_proxy     pelvis_posterior_tilt_proxy
hip_pike                       hip_drop
loss_of_neutral_spine_proxy

# Upper body
shoulder_elevation_compensation shoulder_asymmetry
shoulder_collapse              elbow_flare
elbow_asymmetry                wrist_shift
scapular_instability_proxy     insufficient_head_descent
head_forward_shift

# Control / timing
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

Full vocabulary:

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

`camera_protocol` records exercise-specific recommended filming conditions. This
field is used for acquisition guidance and result warnings; it is not used to correct
coordinates directly or to force data exclusion.

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

Shared zone/height definitions are stored in `data/camera/camera_zones.yaml`.
For the full filming principle, see
[camera_protocol.md](../practical_protocols/camera_protocol.md). For
participant-facing exercise cues and analysis-disrupting performance patterns, see
[exercise_performance_protocol.md](../practical_protocols/exercise_performance_protocol.md).

### quality_rules

```yaml
quality_rules:
  minimum_visible_landmark_ratio: 0.8
  minimum_critical_landmark_ratio: 0.9
  max_missing_gap_frames: 10
  max_interpolation_gap_frames: 3        # read by ④ preprocessing
  exclude_rep_if_critical_landmark_missing: true
  exclude_rep_if_phase_missing: false
  allow_partial_feature_output: true
```

Read directly by ④ preprocessing and ⑧ feature extraction.

## 7. Provenance Convention

Every biomarker produced by ⑧–⑩ includes `source_fields` pointing to the definition fields
that drove the computation. Biomarkers without `source_fields` are not produced (raises
`ValueError` in `BiomarkerRecord`).

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

## 8. Full Example: squat.yaml

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

## 9. MediaPipe Pose 33 Landmark Index

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

## 10. Loader API

```python
from movement.exercise_definition import load_exercise_definition, load_all_exercise_definitions

definition = load_exercise_definition(
    exercise_id="squat",
    definitions_dir="data/definitions/exercises",
)

all_definitions = load_all_exercise_definitions("data/definitions/exercises")
```
