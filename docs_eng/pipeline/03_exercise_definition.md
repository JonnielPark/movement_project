# 03. Exercise Definition

**Document Version:** 1.5.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/03_exercise_definition.md` is the same-version Korean source.

Pipeline step ③ loads exercise YAML artifacts by `exercise_id`, assembles an
`ExerciseContext`, and returns the backward-compatible `ExerciseDefinition` object
used by downstream stages ④-⑩.

Exercise definitions describe what the movement means. Annotation describes where
the movement happened in a recording.

---

## 1. Pipeline Position

```text
Pose CSV + annotation + exercise YAML artifacts
→ ① Validation
→ ② Annotation                    exercise_type, pattern, recording metadata
→ ③ Exercise Definition           ← this step
→ ④ Preprocessing                 laterality, landmarks, quality_rules
→ ⑤ Normalization
→ ⑥ Segmentation                  rep/phase settings
→ ⑦ Motion Attribution            laterality, side_sequence
→ ⑧ Feature Extraction            feature_domains, joint_actions
→ ⑨ Biomech Proxy                 biomechanical_focus
→ ⑩ Biomarker Derivation          compensation_candidates
```

Exercise-specific behavior should be represented as YAML data rather than Python
branches whenever possible.

---

## 2. Split YAML Ownership

The current target exercises use four coordinated YAML artifacts.

```text
data/definitions/exercises/<exercise_id>.yaml
    Movement identity: classification, support, phase model, tags, notes.

data/definitions/analysis_profiles/<exercise_id>.yaml
    Analysis behavior: landmarks, angle definitions, segmentation settings,
    feature domains, biomechanical focus, compensation candidates, quality rules.

data/protocols/performance/<exercise_id>.yaml
    Participant-facing protocol: planned sets/counts, count unit, side sequence,
    completion policy, cues, analysis-disrupting performance patterns.

data/protocols/camera/<exercise_id>.yaml
    Recording protocol: recommended zones/heights and view-metric reliability.
```

The loader merges these artifacts into the runtime `ExerciseDefinition` shape.
Legacy combined YAML remains accepted only for backward compatibility; new work
should use split artifacts.

---

## 3. Current And Future Exercise Coverage

Current canonical exercise IDs:

```text
squat
lunge
pike_pushup
plank_shoulder_tap
generic                  fallback only
```

The schema must remain extensible beyond these four exercises. New exercises may
introduce different laterality, posture, support, phase models, count units,
camera zones, or feature availability, but they should not require new hardcoded
pipeline branches unless a new analytical capability is genuinely needed.

Future exercises should start as draft split YAML generated through the
notebook-first authoring flow, then be reviewed and promoted to canonical YAML.
See [exercise_authoring_notebook.md](../practical_protocols/exercise_authoring_notebook.md).

If `exercise_type` is missing or no matching YAML exists, `generic.yaml` is loaded.
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
compensation_candidates: ...
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
  kinetic_chain: open_chain | closed_chain | mixed_chain | ...
  laterality: bilateral_symmetric | bilateral_asymmetric | alternating |
              unilateral_left | unilateral_right | unilateral_unspecified
  movement_pattern: squat | lunge | pushup | shoulder_tap | custom
  primary_plane: sagittal | frontal | transverse | multiplanar | static
  secondary_planes: list[string]
  complexity: single_joint | multi_joint | compound | whole_body
```

`laterality` informs L/R swap handling and motion-attribution checks. Bilateral
symmetric tasks may skip per-rep active-side attribution; unilateral or
alternating tasks should preserve active-side or role metadata.

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

If automatic segmentation is uncertain, downstream analysis should use confirmed
manual labels rather than silently accepting poor boundaries.

### performance_protocol

`performance_protocol` describes participant-facing instructions and planned
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
    as one participant-facing protocol count.

static hold future exercise
    Can use count_unit: hold_seconds and a static_hold phase model.
```

Planned protocol values belong here. What actually happened during recording,
such as `set_index`, `actual_rep_count`, `failure_point_frame`, or
`failure_reason`, belongs to ② Annotation or recording metadata. Partial
completion should lower interpretation confidence or mark partial completion; it
must not be converted directly into a movement-quality penalty.

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

compensation_candidates: list[string]

feature_domains:
  spatial: list[string]
  temporal: list[string]
  control: list[string]
  biomechanical_proxy: list[string]
```

Only implemented and detectable compensation candidates should produce biomarkers.
Declared-but-unimplemented candidates must be reported by availability/audit logic
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
  minimum_visible_landmark_ratio: float
  minimum_critical_landmark_ratio: float
  max_missing_gap_frames: int
  max_interpolation_gap_frames: int
  exclude_rep_if_critical_landmark_missing: bool
  exclude_rep_if_phase_missing: bool
  allow_partial_feature_output: bool
```

These thresholds are consumed by ④ Preprocessing and ⑧ Feature Extraction.

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
4. Define participant-facing protocol separately from segmentation units.
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

Every biomarker produced by ⑧-⑩ must include `source_fields` pointing to the
definition fields that drove the computation.

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

Biomarkers without `source_fields` should not be produced.

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
