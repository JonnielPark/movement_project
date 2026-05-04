# 05. Preprocessing

Pipeline step ④. Corrects data quality issues in monocular pose data before normalization.
Returns a corrected copy of the dataframe; does not modify the input.

Corrects data quality issues only — does not alter movement quality patterns
(compensation movements, squat depth, etc.).

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing          ← this step
→ ⑤ Normalization
→ ⑥ Phase Segmentation
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

## 9. Kalman Filter (future)

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

## 10. Laterality Branch Summary

```text
laterality               visibility  segment  ROM  velocity  L/R swap  smoothing
──────────────────────   ──────────  ───────  ───  ────────  ────────  ─────────
bilateral_symmetric      enabled     enabled  on   enabled   skip      optional
alternating              enabled     enabled  on   enabled   enabled   optional
unilateral_*             enabled     enabled  on   enabled   enabled   optional
generic fallback         enabled     enabled  on   enabled   skip      optional
```

## 11. Invalid Frame Marking

Frames are never silently deleted. Quality metadata columns are added:

```text
preprocessing_valid = True    usable frame after this step
preprocessing_valid = False   unresolved quality issues remain
swap_corrected = True         L/R labels were exchanged
```

Exact frame exclusion at feature extraction time is determined by annotation rules
and feature step logic.

## 12. Preprocessing Report

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
    "num_invalid_frames": int,
    "applied_columns": list,
}
```

## 13. Planned Extensions

- Visibility-weighted interpolation
- Reliability-weighted smoothing
- Hampel filter (outlier-robust smoothing)
- One-Euro filter (low-latency jitter-aware smoothing)
- Per-exercise velocity threshold tuning
- Per-landmark reliability rules (e.g., foot landmarks in occluded reps)
- Before/after correction visualization
