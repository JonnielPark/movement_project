# 03. Exercise Definition

**Document Version:** 1.7.1
**Last Updated:** 2026-07-14
**Korean Sync:** `docs/pipeline/03_exercise_definition.md` is the same-version Korean source.

Pipeline step ③ loads exercise YAML artifacts by `exercise_id`, assembles an
`ExerciseContext`, and returns the backward-compatible `ExerciseDefinition` object
used by downstream stages ④-⑨.

Exercise definitions describe what the movement means. Annotation describes where
the movement happened in a recording.

---

## 1. Pipeline Position

```text
Pose CSV + annotation + exercise YAML artifacts
→ ① Validation
→ ② Annotation                    exercise_id, execution_pattern, recording metadata
→ ③ Exercise Definition           ← this step
→ ④ Preprocessing                 laterality, landmarks, quality_rules
→ ⑤ Normalization
→ ⑤-1 Optional Canonicalization    coordinate-analysis priors
→ ⑥ Segmentation                  rep/phase settings
→ ⑦ Feature Extraction            feature_domains, joint_actions, laterality, side_sequence
→ ⑧ Biomech Proxy                 biomechanical_focus
→ ⑨ Biomarker Derivation          compensation_patterns
```

Exercise-specific behavior should be represented as YAML data rather than Python
branches whenever possible.

---

## 2. Split YAML Ownership

The exercise-definition system uses exercise-level YAML artifacts plus an
optional session-composition artifact.

```text
data/definitions/exercises/<exercise_id>.yaml
    Movement identity: classification, support, phase model, tags, notes.

data/definitions/analysis_profiles/<exercise_id>.yaml
    Analysis behavior: landmarks, angle definitions, segmentation settings,
    feature domains, biomechanical focus, compensation patterns, quality rules.

data/definitions/analysis_profiles/<profile_file_id>.yaml
    Optional indexed analysis-profile file for long sessions. The file begins
    with an `index`, and section exercise YAMLs point to a profile entry with
    `analysis_profile_ref`.

data/definitions/analysis_presets.yaml
    Reusable analysis blocks for segmentation, landmark/angle sets, and quality
    rules. Presets reduce repeated YAML but must not hide exercise identity.

data/definitions/exercise_sessions/<exercise_session_id>.yaml
    Optional ordered composition of one or more existing exercise definitions.
    It specifies block order, repeat count, and one session-level rest policy.

data/protocols/performance/<exercise_id>.yaml
    Performance protocol: planned sets/counts, count unit, side sequence,
    completion policy, cues, analysis-disrupting performance patterns.

data/protocols/camera/<exercise_id>.yaml
    Recording protocol: recommended zones/heights and view-metric reliability.

data/protocols/camera/<shared_protocol_id>.yaml
    Optional shared camera protocol for session-style recordings. Section
    exercise YAMLs point to it with `camera_protocol_ref`.
```

The exercise loader merges the exercise-level artifacts into the runtime
`ExerciseDefinition` shape. The session loader reads `ExerciseSessionDefinition`
artifacts without changing the meaning of each referenced exercise definition.
Legacy combined YAML remains accepted only for backward compatibility; new work
should use split artifacts.

Analysis profiles may select reusable preset blocks:

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

Preset expansion happens before validation. Explicit fields in the exercise
profile override the selected preset fields; dictionaries merge recursively,
while lists and scalar values replace the preset value. Presets are allowed for
repeated analysis mechanics only. Long session-style examples may keep many
section profiles in one indexed profile file. The top-level `index` documents
the profile order and section labels, while each `profiles` entry is still
selected by the referenced section `exercise_id`; this is file organization, not
a new movement-definition layer. `classification`, `support`, `phase_model`,
performance protocol, camera protocol, and scoring policy must remain in their
own artifacts so future exercises can differ without hidden Python branches.

---

## 3. Current And Future Exercise Coverage

Illustrative canonical exercise ID currently used in examples:

```text
squat
generic                  fallback only
```

Retained canonical development/example artifacts:

```text
lunge
pike_pushup
plank_shoulder_tap
```

The examples use squat as a single-block repeated-exercise case. Lunge, pike push-up,
and plank shoulder tap remain in the repository as prior development/example
artifacts. None of these exercises defines the framework's scope.

Korean National Gymnastics is introduced as a draft multi-block sequence example
through `data/definitions/exercise_sessions/korean_national_gymnastics.yaml`.
The current session is an acquisition-and-analysis definition that starts from
the repeated pass of the routine. The initial pass through breathing-to-jumping
is not acquired or analyzed, so those sections are not performed twice for this
project session. The session composes section-level draft exercise definitions
in the order below. It is still review-required runtime YAML: section/event
models, count units, performance protocol, feature-availability policy, and
scoring eligibility should be reviewed section by section before canonical
promotion. The current draft sections use a frontal camera zone (`Z1`) at
waist-height level (`H2`) as the recommended recording setup; view-metric
reliability and section-specific observation purposes still require
section-level review.

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

The sequence should be represented by composing reviewed section/event blocks
rather than by creating a separate "mixed exercise" category.

For this session, the section exercise YAML files share:

```text
analysis_profile_ref.profile_file_id = korean_national_gymnastics
camera_protocol_ref.protocol_id    = korean_national_gymnastics
```

This keeps the file count readable for a long sequence while preserving
section-level analysis-profile entries inside the indexed profile file.

The schema must remain extensible beyond the current example artifacts.
New exercises may introduce different laterality, posture, support, phase or
section models, count units, camera zones, or feature availability, but they
should not require new hardcoded pipeline branches unless a new analytical
capability is genuinely needed.

Future exercises should start as draft split YAML generated through the
notebook-first authoring flow, then be reviewed and promoted to canonical YAML.
See [exercise_authoring_notebook.md](../practical_protocols/exercise_authoring_notebook.md).

Before promotion, a local authoring draft bundle may be tested by pointing
`definitions_dir` to the generated bundle path:

```text
data/processed/authoring_drafts/<exercise_id>/data/definitions/exercises
```

The stage-check notebook may also resolve a selected test `exercise_id` from the
canonical directory, the local authoring draft directory, or the git-tracked
authoring example directory. This lets a newly generated local draft override
the example bundle during review. The canonical definition directory remains the
pipeline default because it contains the project-wide registry and `generic`
fallback definition.

Authoring draft promotion follows a stricter contract than local review:

```text
draft artifact id       draft_<exercise_name> or another review-only id
canonical artifact id   stable public exercise_id such as squat
runtime directories     data/definitions/* and data/protocols/*
status/requires_review  removed from official top-level YAML
authoring provenance    retained under authoring_provenance
baseline status         invalid until regenerated for the promoted definition
```

Promotion is not a blind file rename. The promoted artifacts must use the
canonical `exercise_id` in all split YAML files, keep the authoring selections as
provenance, resolve or explicitly defer review-required fields, and then replace
the runtime canonical artifacts. Stage-check notebooks should then return to the
canonical `exercise_id` rather than reading a draft bundle.

Existing score baselines must not be silently reused after promotion. A baseline
entry is valid only for the exercise definition and feature schema that generated
it. When a promoted authoring artifact replaces an older canonical definition,
the old `baseline_zscore.json` entry for that `exercise_id` should be removed or
version-guarded until a new reference distribution is generated through the
current pipeline.

If `exercise_id` is missing or no matching YAML exists, `generic.yaml` is loaded.
Generic mode activates only exercise-agnostic features such as ROM, tempo, and
stability. Compensation biomarkers are not produced.

---

## 4. Runtime Schema Contract

The merged runtime shape consumed by `ExerciseDefinition` is:

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

Not every field must be equally rich for every exercise. Missing or unavailable
capabilities should be reported as unavailable or low confidence rather than
silently treated as normal.

### ExerciseSessionDefinition composition layer

An `ExerciseDefinition` remains one analyzable movement block. A single-exercise
example is represented as one block; a longer sequence is represented by an
`ExerciseSessionDefinition` that orders several existing blocks. This avoids a
separate general/mixed exercise split and keeps the framework exercise-agnostic:
the pipeline analyzes whatever block definitions are provided.

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
exercise_session_id          Stable ID for the composed exercise session definition.
                              It is distinct from recording metadata `session_id`.
blocks                       Non-empty ordered list of analyzable blocks.
blocks[].block_id            Unique ID within this exercise session definition.
blocks[].exercise_id         Existing exercise definition referenced by the block.
blocks[].repeat_count        Positive integer repeat count for the referenced block.
rest_policy.rest_between_blocks_s
                              Uniform planned rest in seconds between consecutive
                              blocks. Use null when no planned rest is specified.
rest_policy.per_block_override_allowed
                              Must remain false for now. Per-block rest overrides
                              are intentionally not supported yet.
```

The session definition is a composition and scheduling layer, not a new movement
definition layer. Block-level analysis settings, segmentation, feature
availability, camera protocol, performance protocol, and scoring policy remain
owned by the referenced exercise artifacts. Future score tracking can aggregate
block-level outputs under `exercise_session_id`, but the current schema should
not embed per-block score rules or per-block rest overrides.

---

## 5. Field Contracts

### classification

Defines broad movement identity and controls laterality-sensitive stages.

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
  movement_pattern: deprecated alias for movement_template_id
  movement_pattern_source: derived_from_joint_actions_and_context | manual
  primary_plane: sagittal | frontal | transverse | multiplanar | static
  secondary_planes: list[string]
  complexity: single_joint | multi_joint | compound | whole_body
```

`laterality` informs L/R swap handling and side-role context inside Feature
Extraction. Bilateral symmetric tasks may skip per-rep active-side context;
unilateral or alternating tasks should preserve active-side or role metadata.

`movement_template_id` is derived from selected authoring axes such as posture,
support pattern, laterality, primary regions, joint actions, and planes.
It names the analysis template/family, not the public exercise name. During
migration, existing YAML may still expose `movement_pattern`; loaders mirror it
as `movement_template_id` when the new field is absent.

### authoring_spec and authoring_inference

Canonical exercise YAML files may retain the authoring selections that produced
or reconstructed the definition. This provenance is not a scoring feature and
does not replace explicit `classification`, `support`, `phase_model`, or
`joint_actions` fields.

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

If the authoring generator inferred narrow additions from the selected axes,
the YAML may also retain `authoring_inference`. Inference records must be
explainable from posture, support, laterality, joint actions, and planes; they
must not be inferred from the exercise name alone.

### support and phase_model

`support` describes contact and weight-bearing context. It should remain general
enough for standing, plank, kneeling, inverted closed-chain, and future exercise
families.

```yaml
support:
  base_of_support: bilateral_feet | split_stance | single_foot_left | hands_feet | ...
  contact_points: list[string]
  support_surface: floor | mat | bench | wall | ...
  weight_bearing_regions: list[string]
```

The runtime `ExerciseDefinition` preserves this block as `support_context`.
Downstream feature stages may use it for provenance and report-only support
diagnostics, such as closed-chain support-landmark path checks. This must not
become an `exercise_id` branch or a hidden coordinate correction.

`phase_model` describes one repetition or task cycle.

```yaml
phase_model:
  type: resistance_phase | task_phase | static_hold | cyclic | locomotion_phase | custom
  expected_ratio: optional mapping
```

Standard phase vocabularies should be reused when possible, but `custom` is
allowed for future exercises when the phase structure cannot be represented by the
existing families.

### segmentation

`rep_segmentation` creates or confirms repetition boundaries. `phase_segmentation`
assigns phase labels inside confirmed reps.

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

`reference_coordinate_family` is the coordinate source used only for boundary
detection. The default `norm` family reads body-relative columns from ⑤
Normalization. If the reference landmark is also the normalization anchor, such
as `hip_center` after hip-centered normalization, the movement signal may be
removed. In that case the exercise definition should use `recording_view_raw`
with a recording-plane axis such as `image_y` so segmentation follows the
visible movement trace without changing the normalized feature/scoring
coordinates.

If automatic segmentation is uncertain, downstream analysis should use confirmed
manual labels rather than silently accepting poor boundaries.

### performance_protocol

`performance_protocol` describes performance instructions and planned
acquisition. It is separate from segmentation because one protocol count may map
to one or more segmented atomic movements.

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

Examples:

```text
lunge
    Can use same_side_block_then_switch with block_size_counts: 5.

plank_shoulder_tap
    Can segment each tap as an atomic movement while counting one left-right pair
    as one performance protocol count.

static hold future exercise
    Can use count_unit: hold_seconds and a static_hold phase model.

Korean National Gymnastics future draft
    Should define reviewed section/event blocks before promotion. Do not reuse
    squat repetition segmentation or score eligibility by assumption.
```

Planned protocol values belong here. What actually happened during recording,
such as `set_index`, `actual_rep_count`, `failure_point_frame`, or
`failure_reason`, belongs to ② Annotation or recording metadata. Partial
completion should lower interpretation confidence or mark partial completion; it
must not be converted directly into a movement-quality penalty.

`rest_between_sets_s` belongs only to repeated sets inside one referenced
exercise block. Planned rest between different blocks in a composed sequence
belongs to `ExerciseSessionDefinition.rest_policy.rest_between_blocks_s`, and is
currently one uniform session-level value.

### landmarks and angle_definitions

The current landmark model is `mediapipe_pose_33`. Exercise definitions should
declare primary, secondary, critical, and optional landmarks according to the
movement, not according to a single squat template.

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

For future pose models, add an adapter or mapping layer before changing exercise
YAML semantics.

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

Only implemented and detectable compensation patterns should produce biomarkers.
Declared-but-unimplemented patterns must be reported by availability/audit logic
instead of silently ignored. Absolute force, torque, or clinical-diagnosis claims
do not belong in these fields.

### camera_protocol and view_metric_reliability

`camera_protocol` is acquisition guidance and provenance. It is not a coordinate
correction rule and should not force exclusion by default.

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

`view_metric_reliability` records which camera zones support which metric
families. It should stay flexible for bilateral symmetric, unilateral,
alternating, static, and future task structures.

```yaml
view_metric_reliability:
  structure: bilateral_symmetric | unilateral_or_alternating | static_hold | custom
  role_labels: optional list[string]
  zones:
    Z1:
      frontal_alignment: high | moderate | low | not_assessed
      sagittal_rom: high | moderate | low | not_assessed
```

For unilateral or alternating tasks, prefer role labels such as `forward_leg`,
`trailing_leg`, `active_side`, and `support_side` over raw anatomical left/right
when the camera view affects interpretation.

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

The confidence and gap thresholds are consumed by ④ Preprocessing and ⑦ Feature
Extraction. `range_of_motion_targets` is consumed by ⑨ Biomarker Scoring. It defines
exercise-specific functional ROM bands: for example, squat knee ROM should be
penalized primarily when it is insufficient, not simply because it is larger than
the synthetic baseline mean. These targets are provisional until reviewed-good
examples or literature-informed values are available, and they should remain
exercise-specific rather than global.

---

## 6. Extending To A New Exercise

Use this checklist for the remaining current exercises and future undefined
exercises.

```text
1. Create draft split YAML artifacts through the authoring notebook.
2. Choose the closest schema family, but do not force the exercise into squat-like
   assumptions if posture, laterality, phase model, or count unit differ.
3. Define primary landmarks, critical landmarks, and feature domains from the
   movement's observable mechanics.
4. Define performance protocol separately from segmentation units.
5. Define camera protocol and view-metric reliability before interpreting
   low-confidence view-dependent features.
6. Keep unsupported metrics as unavailable/not_assessed until implemented and tested.
7. Add or update tests when a new field affects loader behavior or downstream logic.
8. Promote draft YAML to canonical files only after researcher review.
```

Adding a new exercise should usually require YAML and tests, not new stage-level
code. If code changes are required, document the new concept in `docs_eng/` first
and then sync `docs/`.

---

## 7. Provenance Convention

Every biomarker produced by ⑨ must include `source_fields` pointing to the
definition fields that drove the computation.

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

Biomarkers without `source_fields` should not be produced.

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
