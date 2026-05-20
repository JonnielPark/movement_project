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
③ Exercise Definition → ④ Preprocessing ← this step → ⑤ Normalization
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
exercise_type, pattern
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
<landmark>_reliable          per-landmark reliability mask
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

Unreliable data are marked, not silently deleted.

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
and left for ⑦ Motion Attribution or manual review.

### Short-Gap Interpolation

Interpolation applies only to reliability-masked short gaps.

```text
short gap   linear interpolation
long gap    remains unreliable and is reported
```

`quality_rules.max_interpolation_gap_frames` controls the limit.

### Optional Smoothing

Smoothing is disabled by default and should use small windows. It is intended for
minor observation jitter, not for reshaping true movement patterns.

---

## 5. Far-Side Stabilization

Optional far-side stabilization addresses side-view or near-side-view recordings
where the side farther from the camera has lower visibility, higher jitter, or
higher swap risk. It is not canonicalization and does not make the skeleton
symmetric.

Allowed:

```text
infer near/far/unknown side context
apply stronger smoothing only to low-visibility + high-jitter landmarks
interpolate short low-confidence gaps
report unresolved long gaps as low confidence
emit feature-availability hooks for ⑧ and ⑩
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
    "exercise_type": str,
    "pattern": str,
    "laterality": str,
    "num_frames": int,
    "reliability_summary": dict,
    "swap_detection_summary": dict,
    "interpolation_summary": dict,
    "smoothing_summary": dict,
    "far_side_stabilization_summary": dict | None,
    "feature_availability_summary": dict | None,
    "num_invalid_frames": int,
    "applied_columns": list,
}
```

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
  smoothing: ...
  far_side_stabilization: ...
```

Kalman filtering is not active in the current preprocessing scope.

---

## 8. Planned Extensions

- Per-feature landmark coverage summaries for availability resolution.
- Reliability-weighted interpolation/smoothing after real-sample review.
- Per-exercise velocity thresholds when justified by tests.
- Before/after quality visualization in ⑪.
