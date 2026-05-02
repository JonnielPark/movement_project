# Preprocessing

## Purpose

The preprocessing module identifies low-reliability landmark detections in monocular 3D pose data and corrects short-term noise before normalization and feature extraction.

Validation only reports data integrity problems.

Preprocessing may modify coordinate values when the correction is limited, traceable, and necessary for downstream analysis.

The main purpose is to prepare a stable pose sequence while preserving the original movement pattern.

## Background — Why Preprocessing Looks Different in Monocular Pose Data

Monocular pose estimators (such as MediaPipe Pose) typically return coordinates for every landmark in every frame, even when a landmark is occluded or detected with very low confidence. Truly missing values are rare.

The dominant data quality problem is therefore not missing coordinates, but landmarks that are reported with anatomically implausible positions, low visibility, or unstable jumps between frames.

Preprocessing in this project is structured around that reality.

## Pipeline Role

Preprocessing runs after exercise definition loading and before normalization.

```text
Pose CSV
-> Validation
-> Annotation Mask Application
-> Exercise Definition Loading
-> Preprocessing
-> Normalization
-> Motion Attribution
-> Feature Extraction
```

Annotation runs first so that `exercise_type` and `pattern` are available. Exercise definition loading runs next so that the property object (which exposes `landmarks`, `laterality`, `quality_rules`, etc.) is available to preprocessing without re-reading annotation metadata. This lets preprocessing enable or skip exercise-specific checks.

Normalization runs after preprocessing so that the median torso length used for scale estimation is computed from cleaned reference landmarks (hip and shoulder).

## Design Rule

Preprocessing should correct data quality problems, not movement quality problems.

```text
allowed:
- visibility-based reliability marking
- anatomical constraint checking
- left-right label swap correction (label-only, no coordinate change)
- short-gap interpolation over reliability-masked frames
- small frame-level noise smoothing
- preprocessing report generation

not allowed:
- changing abnormal movement into normal movement
- correcting poor squat depth
- correcting knee valgus pattern
- deleting frames silently
- changing original frame numbers
- modifying coordinates to enforce a specific kinematic skeleton model
```

The preprocessing step should not hide biomechanically or movement-quality meaningful patterns.

## Input

The input is a pose dataframe after validation, annotation, and exercise definition loading.

Required coordinate columns follow the project data format:

```text
<landmark>_x
<landmark>_y
<landmark>_z
```

Visibility columns are used by reliability detection when available:

```text
<landmark>_visibility
```

Annotation context columns may be used to enable exercise-specific logic:

```text
exercise_type
pattern
```

Exercise definition fields read by preprocessing:

```text
landmarks.primary_joints
landmarks.critical_landmarks
classification.laterality
quality_rules.minimum_visible_landmark_ratio
quality_rules.max_interpolation_gap_frames
```

When the loaded definition is the generic fallback, preprocessing applies conservative defaults.

## Output

The preprocessing function should return both a dataframe and a report.

```python
pre_df, pre_report = preprocess_pose_dataframe(df, landmarks, exercise_definition)
```

The output dataframe should preserve:

```text
frame
timestamp
raw coordinate columns
visibility columns, if available
annotation columns
```

In addition, preprocessing adds reliability-related columns:

```text
<landmark>_reliable        : bool, per-landmark per-frame reliability mask
preprocessing_valid        : bool, frame-level summary
preprocessing_note         : str, reason if invalid
swap_corrected             : bool, frame-level label swap flag
```

The initial implementation may either update coordinate columns directly or add separate preprocessed coordinate columns.

For early development, direct coordinate update is acceptable if the report clearly records which operations were applied.

Later versions may add separate columns such as:

```text
left_knee_pre_x
left_knee_pre_y
left_knee_pre_z
```

## Initial Processing Scope

The first preprocessing implementation should support a small and explicit set of operations.

```text
1. visibility-based reliability detection
2. anatomical constraint checking
3. velocity-based outlier detection
4. frame-level left-right swap detection (exercise-aware)
5. short-gap interpolation over reliability-masked frames
6. optional smoothing
7. preprocessing report
```

This keeps the module simple enough for early testing while still making the later feature extraction step more stable.

## Reliability Detection

A reliability mask is produced per landmark per frame. A landmark is marked unreliable when one or more of the following conditions hold.

### Visibility Gating

```text
landmark.visibility < visibility_threshold (default: 0.5)
```

Low-visibility landmarks are flagged but not deleted.

### Segment Length Consistency

For each predefined skeleton segment (for example, left thigh = `left_hip` to `left_knee`), the per-frame segment length is compared against the sequence-level median.

```text
deviation = |segment_length(t) - median_segment_length| / median_segment_length

if deviation > segment_length_tolerance (default: 0.25):
    mark both endpoint landmarks as unreliable at frame t
```

Bilateral comparison (left vs right segment of the same kind) may also be used as a secondary check.

### Joint Angle Physiological Limits

Computed joint angles are checked against general anatomical ranges (not exercise-specific).

```text
example bounds:
  knee flexion        : -10°  to 160°
  elbow flexion       : -10°  to 160°
  hip flexion         : -30°  to 150°
```

Frames violating these bounds are flagged as unreliable for the corresponding landmarks.

These bounds are intentionally conservative. Exercise-specific normality checks belong to feature extraction, not preprocessing.

### Velocity Outlier Detection

Frame-to-frame displacement is computed for each landmark. Sudden jumps that exceed a velocity threshold are flagged.

```text
v(t) = |p(t) - p(t-1)| / Δt

if v(t) > velocity_threshold:
    mark landmark as unreliable at frame t
```

The threshold may be defined relative to the sequence-level torso length per second to be subject-size invariant.

## Frame-Level Left-Right Swap Detection (Exercise-Aware)

Pose estimators occasionally swap left and right labels of a paired landmark, especially during occlusion, rotation, or in prone postures.

This detection is enabled or disabled based on the loaded exercise definition's `classification.laterality` (cross-checked against `pattern` declared in annotation).

```text
laterality = bilateral_symmetric  -> skip frame-level swap detection
laterality = alternating          -> enable frame-level swap detection
laterality = unilateral_*         -> enable, with single-side priority
```

### Detection Heuristics

Two heuristics are used together.

Temporal consistency check:

```text
swap suspected at frame t if both:
  |p_L(t) - p_R(t-1)|  <  |p_L(t) - p_L(t-1)|
  AND
  |p_R(t) - p_L(t-1)|  <  |p_R(t) - p_R(t-1)|
```

Exercise-specific orientation check (optional, when applicable):

```text
for facing-front exercises:
  expected sign of (left_hip.x - right_hip.x)
  is fixed by the camera convention

if observed sign disagrees for more than orientation_disagree_ratio of
the rep, the rep is flagged as having a possible sequence-level swap
```

### Correction Policy

When a swap is detected with high confidence, the left and right labels of the affected paired landmarks are swapped at the affected frames. This is a label-only operation and does not modify any coordinate value.

```text
swap_corrected column is set to True at swap-affected frames
preprocessing_note records the swap heuristic that triggered the correction
```

When confidence is low, the frames are flagged but labels are not changed. The downstream motion attribution module may flag a higher-level inconsistency at the rep level.

## Mask Gap Handling — Short-Gap Interpolation

Short-gap interpolation is applied over reliability-masked frames, not over coordinates that the source pose estimator left missing.

```text
input  : reliability mask produced by detection steps above
output : coordinates for short masked gaps filled by interpolation,
         long masked gaps left as unreliable
```

Example policy (read from `quality_rules.max_interpolation_gap_frames` in the loaded definition; default 3):

```text
max_interpolation_gap = 3 frames
method                = linear
```

Short masked gaps within the allowed limit are filled. Long masked gaps remain unreliable and are recorded in the report.

```text
short masked gap -> interpolate
long masked gap  -> keep as unreliable, report as unresolved
```

This prevents long unreliable sections from being artificially reconstructed.

## Smoothing

Smoothing may be used to reduce small frame-level jitter on landmarks that are reliable but noisy.

The initial implementation should use a simple and interpretable method.

Recommended initial options:

```text
moving_average
rolling_median
none
```

For pose data, `rolling_median` is preferred because it is robust to remaining outliers.

Default behavior should be conservative.

```text
smoothing.enabled = false
```

If smoothing is enabled, the report should record:

```text
method
window_size
applied_columns
```

The smoothing window should be short enough to avoid removing meaningful movement dynamics.

## Kalman Filter Policy

Kalman filtering is part of the planned final preprocessing pipeline. It is described in the research plan as the target method for compensating frame-level coordinate noise and inter-frame discontinuity.

In the initial implementation, simpler methods are used first to establish a verifiable baseline:

```text
visibility gating
anatomical constraint checking
velocity outlier detection
linear interpolation over masked gaps
rolling median
```

Kalman filtering will be introduced once the simple methods are characterized and a clear need for frame-to-frame state estimation is established.

The YAML option is kept present but disabled until that point.

```yaml
preprocessing:
  enabled: false
  kalman_filter:
    enabled: false
```

This staged approach keeps the early pipeline interpretable while preserving the planned upgrade path.

## Exercise-Specific Branching Summary

Preprocessing reads the loaded exercise definition's `classification.laterality` (and `pattern` from annotation as a cross-check) and applies the following branching.

```text
laterality                       visibility   segment   ROM   velocity   L/R swap   smoothing
─────────────────────────────    ──────────   ───────   ───   ────────   ────────   ─────────
bilateral_symmetric              enabled      enabled   enabled  enabled  skip       optional
alternating                      enabled      enabled   enabled  enabled  enabled    optional
unilateral_*                     enabled      enabled   enabled  enabled  enabled    optional
generic fallback (no definition) enabled      enabled   enabled  enabled  skip       optional
```

When the loaded definition is the generic fallback, preprocessing falls back to the bilateral branch, which is the safer default because it cannot introduce false swap corrections.

## Invalid Frame Marking

Preprocessing should not silently remove frames.

Instead, it adds quality-related metadata columns.

Recommended columns:

```text
preprocessing_valid
preprocessing_note
swap_corrected
```

Suggested meaning:

```text
preprocessing_valid = True   -> frame is usable after preprocessing
preprocessing_valid = False  -> frame still contains unresolved quality problems
swap_corrected      = True   -> left-right labels were swapped at this frame
```

The exact frame exclusion for feature extraction should be handled later by annotation and feature-level rules.

## Configuration Draft

The initial YAML configuration may be expanded as follows.

```yaml
preprocessing:
  enabled: false
  reliability:
    visibility_threshold: 0.5
    segment_length_tolerance: 0.25
    joint_angle_check: true
    velocity_threshold_torso_per_sec: 5.0
  swap_detection:
    enabled: true                # only applied when laterality != bilateral_symmetric
    temporal_consistency: true
    orientation_prior: true
    orientation_disagree_ratio: 0.4
  interpolation:
    enabled: true
    method: linear
    max_gap_frames: 3            # may be overridden per-exercise via quality_rules
  smoothing:
    enabled: false
    method: rolling_median
    window_size: 3
  kalman_filter:
    enabled: false
    process_noise: 0.01
    measurement_noise: 0.1
```

For early development, the default should remain disabled in the full pipeline.

This allows preprocessing to be tested in a notebook before it affects the end-to-end result.

## Preprocessing Report

The preprocessing report should include enough information to inspect what was changed.

Recommended report fields:

```text
method
exercise_type
pattern
laterality
num_frames
num_coordinate_columns

reliability_summary:
  visibility_threshold
  num_low_visibility_frames_per_landmark
  num_segment_length_violations
  num_joint_angle_violations
  num_velocity_outliers
  num_unreliable_landmark_frames

swap_detection_summary:
  enabled
  num_temporal_swap_corrected
  num_orientation_disagree_reps

interpolation_summary:
  enabled
  max_interpolation_gap
  num_short_gaps_interpolated
  num_long_gaps_unresolved

smoothing_summary:
  enabled
  method
  window_size
  applied_columns

num_invalid_frames
applied_columns
```

The report should make the preprocessing step reproducible and auditable.

## Initial Completion Criteria

The first preprocessing implementation is complete when:

```text
1. preprocessing.py exists
2. coordinate columns are selected from the landmark list
3. visibility-based reliability marking works
4. segment length and velocity checks produce a reliability mask
5. exercise-aware frame-level left-right swap detection runs only for
   non-bilateral exercises (driven by the loaded definition)
6. short masked gaps can be interpolated
7. long masked gaps remain unresolved and are reported
8. optional simple smoothing can be applied
9. original frame and timestamp columns are preserved
10. preprocessing report is returned
11. pipeline.py can run preprocessing when enabled
12. notebook/06_preprocessing_test.ipynb verifies the behavior
```

## Future Extensions

Later versions may include:

- visibility-weighted interpolation
- confidence-weighted smoothing
- Hampel filter as a robust outlier-rejecting smoother
- One-Euro Filter for jitter-aware low-latency smoothing
- Kalman filtering as the planned final noise-correction method
- exercise-specific velocity thresholds tuned per movement
- landmark-specific reliability rules (for example, foot landmarks during occluded reps)
- preprocessing visualization before and after correction
