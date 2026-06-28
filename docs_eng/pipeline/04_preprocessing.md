# 04. Preprocessing

**Document Version:** 1.2.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/04_preprocessing.md` is the same-version Korean source.

Pipeline step ④ corrects or marks data-quality issues in monocular pose data
before normalization. It returns a corrected copy of the DataFrame and does not
modify the input object.

This step handles observation reliability only. It must not alter movement-quality
patterns such as depth, knee valgus, trunk lean, or compensatory asymmetry.

---

## 1. Pipeline Position

```text
③ Exercise Definition → ④ Preprocessing ← this step → ⑤ Normalization → ⑥ Canonicalization
```

Runs after ③ so laterality, landmarks, camera protocol, and quality rules are
available. Runs before ⑤ so unreliable hip/shoulder landmarks do not contaminate
the torso-length scale.

---

## 2. Inputs And Outputs

Required input columns:

```text
<landmark>_x / _y / _z
```

Optional inputs:

```text
<landmark>_visibility
exercise_id, execution_pattern
camera_zone, camera_height_level
```

Exercise-definition fields consumed:

```text
classification.laterality
landmarks.primary_joints
landmarks.critical_landmarks
quality_rules.*
camera_protocol
view_metric_reliability
```

Added columns include:

```text
<landmark>_observed_reliable raw observation reliability before repair
<landmark>_usable            per-landmark usability after short-gap repair
<landmark>_preprocessing_source
                              observed | short_gap_interpolated | unusable
preprocessing_valid          frame-level validity
preprocessing_note           machine-readable reason text
swap_corrected               L/R labels exchanged for this frame
<landmark>_camera_side       near_side | far_side | unknown
<landmark>_jitter_score      optional observation-jitter score
<landmark>_confidence_note   optional landmark confidence note
preprocessing_confidence     frame-level confidence note
```

---

## 3. Reliability Checks

Landmarks may be marked unreliable by:

```text
visibility gating
    visibility below threshold.

segment-length consistency
    segment length deviates from sequence median beyond tolerance.
    Thigh segments may be excluded because monocular depth can make them vary
    substantially during valid squats.

conservative joint-angle bounds
    flags anatomically impossible configurations only.
    Exercise-specific ROM assessment belongs to ⑧ Feature Extraction.

velocity outliers
    body-scale-normalized frame-to-frame jumps above threshold.
```

Unreliable data are marked, not silently deleted. A repaired value can become
usable for the next calculation while still carrying lower observation
confidence through its preprocessing source.

---

## 4. Corrections

### L/R Swap Correction

Activation depends on `classification.laterality`.

```text
bilateral_symmetric  skip by default
alternating          enabled
unilateral_*         enabled
generic fallback     skip
```

High-confidence swap candidates exchange paired landmark labels for the affected
frame. Coordinate values are not modified. Low-confidence cases are flagged only
and left for ⑧ Feature Extraction role-context handling or manual review.

### Short-Gap Interpolation

Interpolation applies only to reliability-masked short gaps.

```text
short gap   linear interpolation
long gap    remains unreliable and is reported
```

`quality_rules.max_interpolation_gap_frames` controls the limit.

Interpolation updates `<landmark>_usable`, not
`<landmark>_observed_reliable`. This keeps two questions separate:

```text
observed_reliable  Was the original landmark observation trustworthy?
usable             Can the landmark be used by the next stage after repair?
```

When enabled, the post-interpolation velocity sanity check re-evaluates only the
landmark-frames recovered by interpolation. If the interpolated coordinate still
creates a frame-to-frame jump beyond the velocity threshold, it is marked
unusable with `post_interpolation_velocity_failed`.

Short-gap interpolated landmarks are usable but should be treated as lower
confidence evidence by later feature/scoring stages.

### Optional Smoothing

Smoothing is disabled by default and should use small windows. It is intended for
minor observation jitter, not for reshaping true movement patterns.

---

## 5. Far-Side Stabilization

Optional far-side stabilization addresses side-view or near-side-view recordings
where the side farther from the camera has lower visibility, higher jitter, or
higher swap risk. It is not canonicalization and does not make the skeleton
symmetric.

Because monocular pose coordinates are noisy, far-side jitter detection is
intentionally conservative. Minor coordinate wobble is not treated as jitter.
The jitter gate should require a large motion spike plus low-confidence context
such as low visibility or an existing reliability-mask failure.

The report separates the original observation from the post-preprocessing state:

```text
observed_*             raw observation before interpolation/far-side repair
post_preprocessing_*   remaining issue after preprocessing repair attempts
```

Observed-only issues are provenance. Post-preprocessing issues are the stronger
signal for later feature availability gates.

Far-side summaries should therefore expose separate counts such as
`num_observed_low_confidence_far_side_landmark_frames`,
`num_observed_high_jitter_far_side_landmark_frames`,
`num_post_preprocessing_low_confidence_far_side_landmark_frames`, and
`num_post_preprocessing_high_jitter_far_side_landmark_frames`.

Allowed:

```text
infer near/far/unknown side context
apply optional smoothing/interpolation only to far-side low-confidence landmarks
interpolate short low-confidence gaps
report unresolved long gaps as low confidence
emit feature-availability hooks for ⑧ and ⑨
```

Not allowed:

```text
force far-side landmarks to match near-side landmarks
remove true knee valgus, pelvic shift, trunk lean, or asymmetry
convert far-side unreliability directly into poor movement-quality score
```

Feature-availability hooks may include:

```text
bilateral_landmark_coverage
near_far_side_context
far_side_jitter_score
left_right_swap_risk
segment_length_plausibility
view_reliability
```

---

## 6. Report Contract

`preprocess_pose_dataframe(df, landmarks, exercise_definition)` returns a
DataFrame and a report.

```python
{
    "method": str,
    "exercise_id": str | None,
    "movement_template_id": str | None,
    "execution_pattern": str | None,
    "laterality": str,
    "num_frames": int,
    "reliability_summary": dict,
    "landmark_quality_summary": list[dict],
    "rule_contribution_summary": dict,
    "worst_landmarks_by_observed_unreliable": list[dict],
    "worst_landmarks_by_unusable": list[dict],
    "frames_with_many_unusable_landmarks": list[dict],
    "swap_detection_summary": dict,
    "interpolation_summary": dict,
    "smoothing_summary": dict,
    "far_side_stabilization_summary": dict | None,
    "feature_availability_summary": dict | None,
    "num_invalid_frames": int,
    "applied_columns": list,
}
```

`exercise_id` and `movement_template_id` come from the loaded exercise definition.
`execution_pattern` uses representative non-null dataframe values rather than
the first frame, because real recordings may include setup frames before the
annotated exercise starts.

The landmark/rule/frame summaries are QC provenance, not movement-quality
scores. They identify which landmarks, rules, and frames made preprocessing
confidence low so later feature stages can decide whether a feature should be
used, down-weighted, or skipped.

Stage-check notebooks may derive compact QC ratios and a readiness label from
this report, such as `ready_for_next_stage`, `ready_with_low_confidence_notes`,
or `review_recommended`. These labels are execution/QC interpretation aids only;
they are not biomarker scores and do not replace feature-level availability
decisions.

Stage-check notebooks may also display the active preprocessing configuration
next to those QC ratios: visibility threshold, segment-length tolerance, joint
angle check, velocity threshold, interpolation gap, post-interpolation velocity
check, smoothing setting, and far-side jitter gate. This configuration summary
is provenance for reproducibility, not a scoring input.

The stage-check notebook should follow the established notebook style used by
the earlier stage checks: `Data Setup`, `Direct Preprocessing Test`, numbered
checks, `Pipeline Integration`, and `Check Summary`. Synthetic diagnostics may
be kept as a separate numbered check near the end, clearly marked as diagnostic
evidence rather than target-recording movement quality.

Frames are never silently deleted. Exact feature-level exclusion is decided later
by ⑧ Feature Extraction and ⑩ Biomarker Scoring.

---

## 7. Configuration

Detailed defaults live in `configs/pipeline_default.yaml`.

```yaml
preprocessing:
  enabled: false
  reliability: ...
  swap_detection: ...
  interpolation: ...
    post_velocity_check: true
  smoothing: ...
  far_side_stabilization: ...
```

Kalman filtering is not active in the current preprocessing scope.

---

## 8. Planned Extensions

- Per-feature landmark coverage summaries for availability resolution.
- Reliability-weighted interpolation/smoothing after real-sample review.
- Per-exercise velocity thresholds when justified by tests.
- Before/after quality visualization in ⑩.
