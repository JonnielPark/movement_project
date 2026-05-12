# 04. Preprocessing

**Document Version:** 1.1.1
**Last Updated:** 2026-05-12
**Korean Sync:** `docs/pipeline/04_preprocessing.md` is the same-version Korean source.

Pipeline step ④. Corrects data quality issues in monocular pose data before normalization.
Returns a corrected copy of the dataframe; does not modify the input.

Corrects data quality issues only — does not alter movement quality patterns
(compensation movements, squat depth, etc.).

Current implementation covers reliability masks, label-only L/R swap correction,
short-gap interpolation, optional smoothing, and optional visibility-aware
far-side stabilization with feature-availability hooks for side-view or
near-side-view recordings.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing          ← this step
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

Runs after ③ so that `exercise_type`, `pattern`, and exercise definition fields
(`laterality`, `quality_rules`) are available to activate exercise-specific checks.

Runs before ⑤ normalization because the scale reference (median torso length) is more
stable after hip/shoulder landmarks have passed reliability gating.

## 2. Design Principle

```text
Allowed:
    Visibility-based reliability marking
    Anatomical constraint checks
    L/R label swap correction (label swap only; coordinates unchanged)
    Short-gap interpolation on reliability-masked segments
    Optional smoothing of small frame-level jitter
    Preprocessing report output

Not allowed:
    Modifying abnormal movement patterns to appear normal
    Correcting insufficient squat depth
    Correcting knee valgus patterns
    Silently deleting frames
    Changing original frame numbers
    Adjusting coordinates to fit a specific kinematic model
```

## 3. Inputs

Required:
```text
<landmark>_x / _y / _z     coordinate columns
```

Optional (used if present):
```text
<landmark>_visibility      reliability gating
exercise_type              exercise-specific logic activation
pattern                    L/R swap detection scope
```

Exercise definition fields read:
```text
landmarks.primary_joints
landmarks.critical_landmarks
classification.laterality
quality_rules.minimum_visible_landmark_ratio
quality_rules.max_interpolation_gap_frames
camera_protocol.recommended_zones
view_metric_reliability
```

## 4. Outputs

```python
pre_df, pre_report = preprocess_pose_dataframe(df, landmarks, exercise_definition)
```

Output columns (added, not replacing originals):

```text
<landmark>_reliable    bool    per-landmark per-frame reliability mask
preprocessing_valid    bool    frame-level overall reliability
preprocessing_note     str     reason if unreliable
swap_corrected         bool    whether L/R label swap was applied
```

Task B report/metadata outputs (do not replace coordinates unless explicitly
stabilized by policy):

```text
<landmark>_camera_side       near_side | far_side | unknown
<landmark>_jitter_score      normalized landmark jitter score
<landmark>_confidence_note   landmark-level observation confidence note
preprocessing_confidence     frame-level confidence note for downstream stages
feature_availability_summary report-level feature scoring eligibility context
```

## 5. Reliability Detection

A landmark in a given frame is marked `unreliable` if any of the following holds:

### 5-1. Visibility Gating

```text
landmark.visibility < visibility_threshold (default: 0.5)
```

Low-visibility landmarks are marked, not deleted.

### 5-2. Segment Length Consistency

Per-frame segment length is compared to the sequence median.

```text
deviation = |segment_length(t) - median_segment_length| / median_segment_length

if deviation > segment_length_tolerance (default: 0.25):
    mark both endpoint landmarks as unreliable at frame t
```

**Exception**: hip-to-knee (thigh) segments are excluded from this check.
In monocular data, the thigh appears to shorten/lengthen by >40% during squats due to
depth perspective, triggering false positives on normal movement.

### 5-3. Joint Angle Physiological Bounds

Included angle computed from (proximal, vertex, distal) landmark triplets,
compared against conservative anatomical limits:

```text
Joint          Allowed included angle (degrees)
─────────────────────────────────────────────
knee           10 – 180
elbow          10 – 180
hip            20 – 180
```

Checked joints: `left_knee`, `right_knee`, `left_elbow`, `right_elbow`,
`left_hip`, `right_hip`.

This check flags anatomically impossible configurations only (conservative threshold).
Exercise-specific ROM checks are the responsibility of ⑧ feature extraction.

### 5-4. Velocity Outliers

```text
v(t) = |p(t) - p(t-1)| / Δt

if v(t) > velocity_threshold:
    mark landmark as unreliable at frame t
```

Threshold defined in torso-length-per-second units (body-size invariant).
Configured in `configs/pipeline_default.yaml`:
```yaml
preprocessing:
  reliability:
    velocity_threshold_torso_per_sec: 5.0
```

## 6. L/R Swap Detection

Pose estimators occasionally flip left/right landmark labels (especially during occlusion,
rotation, or prone postures). Activation depends on `classification.laterality`:

```text
bilateral_symmetric  → skip swap detection
alternating          → per-frame swap detection enabled
unilateral_*         → enabled, unilateral priority
generic fallback     → skip (safe default)
```

### Detection Heuristics (both used together)

Temporal consistency:
```text
flag swap at frame t if:
    |p_L(t) - p_R(t-1)| < |p_L(t) - p_L(t-1)|
    AND
    |p_R(t) - p_L(t-1)| < |p_R(t) - p_R(t-1)|
```

Exercise orientation prior (where applicable):
```text
For frontal-facing exercises:
    expected sign of (left_hip.x - right_hip.x) is fixed by camera convention.
    If the observed sign disagrees for > orientation_disagree_ratio of rep frames,
    flag the rep as a sequence-level swap candidate.
```

### Correction Policy

High-confidence swap → exchange paired landmark labels for that frame.
Labels are swapped; coordinate values are unchanged.
`swap_corrected = True`, reason recorded in `preprocessing_note`.

Low-confidence → flag only; no modification.
Rep-level consistency is checked by ⑦ motion attribution.

## 7. Short-Gap Interpolation

Applied only to reliability-masked gaps (not raw missing values).

```text
max_interpolation_gap_frames  : read from quality_rules (default: 3)
method                        : linear
```

```text
Short masked gap  → linear interpolation
Long masked gap   → remains unreliable; recorded in report as unresolved
```

## 8. Smoothing (optional)

Reduces small frame-level jitter in reliable landmarks.

```text
Methods: rolling_median (recommended), moving_average, none
Default: smoothing.enabled = false
```

`rolling_median` is preferred over `moving_average` for robustness to residual outliers.
Window size should be small enough to preserve meaningful movement dynamics
(compensation movements, etc.).

Configuration:
```yaml
preprocessing:
  smoothing:
    enabled: false
    method: rolling_median
    window_size: 3
```

## 9. Task B Extension: Visibility-Aware Far-Side Stabilization

This optional implementation addresses the case where the recording view is side
or near-side, and the side farther from the camera has lower visibility, higher
jitter, or higher L/R swap risk. It is not canonicalization and does not try to
make the skeleton symmetric.

### 9-1. Near-Side / Far-Side Inference

The preprocessing layer estimates camera-side context per landmark or side:

```text
near_side    landmark/body side closer to the camera in the observed pose
far_side     landmark/body side farther from the camera in the observed pose
unknown      insufficient evidence; do not apply side-specific stabilization
```

Inference may use:

```text
camera_zone from annotation or recording metadata
left/right depth coordinate relative to hip_center or body center
visibility difference between paired landmarks
temporal continuity of the side assignment
exercise laterality and active/support role when available
```

If camera-side inference is unstable, the result remains `unknown`. Unknown is a
confidence state, not a movement-quality penalty.

### 9-2. Far-Side Jitter Score

The jitter score is a reliability metric, not a biomechanical score. It
summarizes whether a landmark is likely to be an unstable monocular estimate:

```text
velocity_spike_ratio
acceleration_spike_ratio
visibility_drop_ratio
segment_length_inconsistency
left_right_swap_risk
```

The score should be normalized to body scale where possible. It is reported per
landmark or per paired side and consumed later by feature-availability gates.

### 9-3. Stabilization Policy

Far-side stabilization is conservative:

```text
Allowed:
    stronger smoothing only for low-visibility + high-jitter landmarks
    interpolation of short low-confidence gaps
    confidence/report metadata for unresolved long gaps

Not allowed:
    forcing far-side landmarks to match near-side landmarks
    removing true knee valgus, pelvic shift, trunk lean, or asymmetry
    converting far-side unreliability directly into a poor movement-quality score
```

Segment-length plausibility may be used as a guardrail, but it must not force a
fixed template. Long gaps or unstable side assignments remain `low_confidence` or
`not_assessed`.

### 9-4. Feature-Availability Hooks

④ Preprocessing should provide downstream stages with the context needed to decide
whether a feature can enter scoring:

```text
bilateral_landmark_coverage
near_far_side_context
far_side_jitter_score
left_right_swap_risk
segment_length_plausibility
view_reliability from exercise definition
```

For `spatial.symmetry.*`, availability is `assessed` only when both sides have
sufficient coverage, plausible segment lengths, low swap risk, acceptable far-side
jitter, and a camera view that supports left-right interpretation. Otherwise the
feature may be `low_confidence` or `not_assessed`.

Configuration block:

```yaml
preprocessing:
  far_side_stabilization:
    enabled: false
    camera_side_inference: true
    visibility_threshold: 0.6
    jitter_threshold_torso_per_sec: null
    acceleration_threshold_torso_per_sec2: null
    max_gap_frames: 3
    smoothing_method: rolling_median
    smoothing_window_size: 3
    mark_long_gaps_low_confidence: true
    depth_axis: z
    near_depth_sign: negative
    min_depth_offset_torso: 0.05
```

Report fields:

```python
{
    "far_side_stabilization_summary": {
        "enabled": bool,
        "camera_side_inference": dict,
        "num_near_side_landmark_frames": int,
        "num_far_side_landmark_frames": int,
        "num_unknown_side_landmark_frames": int,
        "num_high_jitter_far_side_landmark_frames": int,
        "num_far_side_gaps_interpolated": int,
        "num_far_side_gaps_unresolved": int,
        "num_far_side_values_smoothed": int,
    },
    "feature_availability_summary": {
        "symmetry_gate_ready": bool,
        "low_confidence_feature_families": list,
        "not_assessed_feature_families": list,
        "reasons": dict,
    },
}
```

## 10. Kalman Filter (future)

Kalman filtering is available as a YAML option but disabled by default.
Enable only after the baseline (visibility gating + anatomical checks + interpolation +
rolling median) is sufficiently characterized.

```yaml
preprocessing:
  kalman_filter:
    enabled: false
    process_noise: 0.01
    measurement_noise: 0.1
```

## 11. Laterality Branch Summary

```text
laterality               visibility  segment  ROM  velocity  L/R swap  far-side  smoothing
──────────────────────   ──────────  ───────  ───  ────────  ────────  ────────  ─────────
bilateral_symmetric      enabled     enabled  on   enabled   skip      view-gated optional
alternating              enabled     enabled  on   enabled   enabled   role-aware optional
unilateral_*             enabled     enabled  on   enabled   enabled   role-aware optional
generic fallback         enabled     enabled  on   enabled   skip      skip      optional
```

## 12. Invalid Frame Marking

Frames are never silently deleted. Quality metadata columns are added:

```text
preprocessing_valid = True    usable frame after this step
preprocessing_valid = False   unresolved quality issues remain
swap_corrected = True         L/R labels were exchanged
```

Exact frame exclusion at feature extraction time is determined by annotation rules
and feature step logic.

## 13. Preprocessing Report

```python
{
    "method": str,
    "exercise_type": str,
    "pattern": str,
    "laterality": str,
    "num_frames": int,
    "num_coordinate_columns": int,
    "reliability_summary": {
        "visibility_threshold": float,
        "num_low_visibility_frames_per_landmark": dict,
        "num_segment_length_violations": int,
        "num_joint_angle_violations": int,
        "num_velocity_outliers": int,
        "num_unreliable_landmark_frames": int,
    },
    "swap_detection_summary": {
        "enabled": bool,
        "num_temporal_swap_corrected": int,
        "num_orientation_disagree_reps": int,
    },
    "interpolation_summary": {
        "enabled": bool,
        "max_interpolation_gap": int,
        "num_short_gaps_interpolated": int,
        "num_long_gaps_unresolved": int,
    },
    "smoothing_summary": {
        "enabled": bool,
        "method": str,
        "window_size": int,
        "applied_columns": list,
    },
    "far_side_stabilization_summary": dict | None,
    "feature_availability_summary": dict | None,
    "num_invalid_frames": int,
    "applied_columns": list,
}
```

## 14. Planned Extensions

- Visibility-weighted interpolation
- Reliability-weighted smoothing
- Hampel filter (outlier-robust smoothing)
- One-Euro filter (low-latency jitter-aware smoothing)
- Per-exercise velocity threshold tuning
- Per-landmark reliability rules beyond the Task B far-side policy
- Before/after correction visualization
