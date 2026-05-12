# 05. Normalization

**Document Version:** 1.2.8
**Last Updated:** 2026-05-12
**Korean Sync:** `docs/pipeline/05_normalization.md` is the same-version Korean source.

Pipeline step ⑤. Converts raw pose coordinates to a body-relative coordinate system
and, when needed, re-expresses the pose in a canonical analysis space that reduces
consistent monocular-observation bias.

Does not estimate absolute forces or absolute body dimensions.
Provides a stable coordinate base for ⑧ feature extraction and ⑨ biomechanical proxy modeling.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization          ← this step
   ├─ base normalization: hip-center translation + torso-length scale
   └─ optional canonicalization: analysis-space alignment
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

Runs after ④ preprocessing because the scale reference (median torso length) is more
stable once hip/shoulder landmarks have passed reliability checks.

The base hip-torso normalization does not branch per exercise type. Static
support-contact exercises or exercises with a clear primary movement plane may
optionally use `canonicalization` inside ⑤ Normalization. The currently implemented
sub-priors are `support_plane_alignment`, which wraps the existing
`floor_relative_correction` implementation, and a prototype
`movement_plane_alignment`. A protocol-gated `protocol_height_lateral_width_alignment`
prior is being added for height-aware lateral-width review. All priors emit
separate `canon` coordinates plus a `canonicalization_report`.

## 2. Method: hip_torso

```text
Translation reference : frame-wise hip center
Scale reference       : sequence-wise median torso length
```

Using the sequence-wise median (rather than per-frame scale) avoids artificial skeleton
jitter caused by per-frame torso length noise in monocular depth estimation.

## 3. Step 1 — Translation

Hip center as the body-reference origin:

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
```

Each landmark is translated:

```text
p_translated_i(t) = p_i(t) - hip_center(t)
```

After this step, all landmarks are expressed relative to the pelvis origin.

## 4. Step 2 — Scale

Torso length as the body scale unit:

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
```

Sequence-wise median is used as the representative scale:

```text
s = median(torso_length over all valid frames)
```

Each translated landmark is divided by `s`:

```text
p_norm_i(t) = (p_i(t) - hip_center(t)) / s
```

The resulting unit is `torso_length_ratio` (dimensionless).

## 5. Output Columns

Raw coordinates are preserved. Normalized coordinates are added as new columns:

```text
left_knee_x      → original x      left_knee_norm_x → normalized x
left_knee_y      → original y      left_knee_norm_y → normalized y
left_knee_z      → original z      left_knee_norm_z → normalized z
```

Reference columns (when `keep_reference_columns: true` in YAML):

```text
hip_center_x, hip_center_y, hip_center_z
shoulder_center_x, shoulder_center_y, shoulder_center_z
torso_length
```

When canonicalization is enabled, it does not overwrite base normalized coordinates.
It adds a separate `canon` coordinate family:

```text
left_knee_norm_x   → base normalized x
left_knee_canon_x  → analysis-space x after canonicalization
left_knee_canon_y  → analysis-space y after canonicalization
left_knee_canon_z  → analysis-space z after canonicalization
```

Coordinate-family meanings are fixed.

```text
raw      original pose coordinates
norm     base hip-torso normalized coordinates
canon    optional canonicalized analysis coordinates
```

## 6. Configuration

```yaml
normalization:
  enabled: true
  method: hip_torso
  keep_reference_columns: true
  canonicalization:
    enabled: false
    coordinate_mode: norm
    output_prefix: canon
    report_only: true
    downstream_coordinate_mode: norm
    data_confidence:
      emit: true
      correction_magnitude_warn_torso: 0.15
      correction_magnitude_fail_torso: 0.30
      residual_warn_torso: 0.08
    support_plane_alignment:
      enabled: false
      method: support_contact_plane
      vertical_axis: y
      support_landmarks: [left_heel, right_heel, left_foot_index, right_foot_index]
      diagnostic_landmarks: [left_heel, right_heel, left_foot_index, right_foot_index]
      visibility_threshold: 0.7
      stability_window_frames: 5
      max_anchor_residual_torso: 0.08
      correction_transform: rigid_rotation
      camera_pitch_deg: 0.0
      camera_roll_deg: 0.0
      correction_strength: 1.0
      max_correction_torso: 0.25
    movement_plane_alignment:
      enabled: false
      method: principal_motion_plane
      fit_landmarks: [left_hip, left_knee, left_ankle, right_hip, right_knee, right_ankle]
      minimum_visible_landmark_ratio: 0.7
      correction_strength: 0.5
      max_rotation_deg: 20.0
      preserve_out_of_plane_residual: true
    protocol_height_lateral_width_alignment:
      enabled: false
      method: height_anchor_lateral_width
      observed_height_level: null
      observed_height_column: camera_height_level
      recommended_height_level: null
      require_height_match: true
      height_anchor_map:
        H1: [left_ankle, right_ankle]
        H2: [left_hip, right_hip]
        H3: [left_shoulder, right_shoulder]
      near_depth_sign: negative
      correction_mode: near_side_attenuation
      correction_strength: 0.3
      max_scale_change: 0.20
      max_correction_torso: 0.15
      min_depth_offset_torso: 0.05
      visibility_threshold: 0.6
      apply_to_landmarks: []
      preserve_anchor_landmarks: true
    body_axis_alignment:
      enabled: false
      method: pelvis_shoulder_axis
      correction_strength: 0.5
      max_rotation_deg: 15.0

  # Current implementation key. During the transition, this is treated as a
  # backward-compatible alias for canonicalization.support_plane_alignment.
  floor_relative_correction:
    enabled: false
    method: support_contact_plane
    coordinate_mode: norm
    vertical_axis: y
    support_landmarks: [left_heel, right_heel, left_foot_index, right_foot_index]
    diagnostic_landmarks: [left_heel, right_heel, left_foot_index, right_foot_index]
    visibility_threshold: 0.7
    stability_window_frames: 5
    max_anchor_residual_torso: 0.08
    correction_transform: rigid_rotation
    camera_pitch_deg: 0.0
    camera_roll_deg: 0.0
    correction_strength: 1.0
    max_correction_torso: 0.25
```

When `report_only: true`, the pipeline may create `canon` coordinates and a report,
but downstream stages after ⑤ continue to use `norm` coordinates by default.
`downstream_coordinate_mode: canon` is allowed only after notebook review and
robustness evaluation.

Current decision for this implementation pass: `canon` coordinates remain
visualization/review-only. The pipeline should keep `report_only: true` and
`downstream_coordinate_mode: norm`, so ⑥ Segmentation, ⑧ Feature Extraction,
⑨ Biomechanical Proxy, and ⑩ Biomarker Scoring continue to consume the base
`norm` coordinate family.

## 7. Normalization Report

```python
norm_df, norm_report = normalize_pose_by_hip_torso(df, landmarks)
```

Report fields:

```python
{
    "method": str,
    "num_frames": int,
    "scale_method": str,
    "scale_value": float,          # median torso length (raw units)
    "min_torso_length": float,
    "max_torso_length": float,
    "median_torso_length": float,
    "num_invalid_torso_frames": int,
    "num_normalized_landmarks": int,
}
```

When canonicalization is enabled, `canonicalization_report` is added inside
`norm_report`.

```python
{
    "enabled": bool,
    "status": "skipped" | "applied" | "partial" | "rejected",
    "coordinate_mode": "norm",
    "output_prefix": "canon",
    "report_only": bool,
    "downstream_coordinate_mode": "norm" | "canon",
    "active_priors": list[str],
    "applied_priors": list[str],
    "skipped_priors": dict[str, str],
    "max_correction_torso": float,
    "median_correction_torso": float,
    "residual_after_fit_torso": float | None,
    "data_confidence": {
        "level": "high" | "moderate" | "low",
        "reasons": list[str],
    },
    "prior_reports": {
        "support_plane_alignment": dict | None,
        "movement_plane_alignment": dict | None,
        "protocol_height_lateral_width_alignment": dict | None,
        "body_axis_alignment": dict | None,
    },
}
```

`data_confidence.level` is an interpretation confidence signal, not a score
deduction. Even with large correction magnitude, movement quality may remain high
when joint-change patterns are stable; the confidence note carries the interpretive
caution.

## 8. Relationship to Other Steps

- **④ Preprocessing**: unreliable landmarks (low visibility, swap-corrected) should be
  resolved or marked before normalization to prevent scale contamination.
- **⑦ Motion Attribution**: uses normalized coordinates; body-size and camera-distance
  effects are already removed, making per-rep motion energy comparison more consistent.
- **⑨ Biomech Proxy**: uses normalized coordinates as input for CoM and moment arm estimation.
  This step provides the coordinate system; ⑨ adds the biomechanical computation.
- **⑩ Scoring**: data confidence is separated from the movement quality score, regardless
  of whether `canon` coordinates are used. Low confidence triggers caution or withholding,
  not an automatic score penalty.

## 9. Optional Normalization Layer: canonicalization

This study does not aim to reconstruct monocular pose into perfect physical 3D.
Even when a raw skeleton looks distorted in 3D visualization, joint-relative
trajectories and temporal change may remain evaluable if the same landmarks track
the same body parts and the observation bias is reasonably consistent within the
sequence.

`canonicalization` follows this premise. It is not a procedure that fits the pose
to a good-movement template. It is an optional layer that attenuates consistent
observation bias caused by camera position and monocular depth artifacts so the
pose can be evaluated in a canonical analysis space. True compensations such as
knee valgus, heel lift, and trunk lean must remain visible.

In the current non-calibrated monocular workflow, canonicalization is placed after
base `norm` coordinates. This is intentional: hip-center translation and
torso-length scaling first remove subject position, camera distance, and body-size
effects, then the optional priors operate in dimensionless torso-length units.
That makes correction magnitude, residual thresholds, and confidence reports
comparable across subjects and videos. Raw coordinates remain preserved for audit,
but they are not the default space for these priors.

The recommended output structure preserves three coordinate families.

```text
raw coordinates
    Original pose coordinates. Never overwritten.

norm coordinates
    Base normalized coordinates after hip-center translation and torso-length scale.

canon coordinates
    Analysis coordinates after canonicalization. These may become candidate inputs
    for final features and biomechanical proxies, but must be interpreted with
    correction magnitude and confidence reports.
```

Canonicalization can use separate priors.

```text
support_plane_alignment
    Pseudo-floor / support-plane alignment from support-contact landmarks.

movement_plane_alignment
    Stabilizes the common movement plane of key joint trajectories such as
    hip-knee-ankle in squats and lunges.

protocol_height_lateral_width_alignment
    Uses filming height metadata as a gate before applying a conservative
    depth-dependent lateral-width prior around a height-specific body anchor.
    H1 maps to a support/ankle-level anchor, H2 to the pelvis / hip center, and
    H3 to the shoulder line. This is review-only and not lens correction.

body_axis_alignment
    Stabilizes body-relative orientation from pelvis/shoulder axes and the body centerline.

camera_prior
    Uses camera zone, height level, pitch/roll, and related recording metadata for
    correction interpretation and confidence/provenance. It does not perform
    calibrated reprojection.
```

### 9.1 Canonicalization Prior Order

Initial implementation is intentionally limited to the following order.

```text
1. support_plane_alignment
   Attenuates pseudo-floor artifacts in static support-contact exercises.

2. movement_plane_alignment
   Applies only to exercises with a clear primary movement plane, such as squat/lunge.
   It preserves out-of-plane residuals and reports them so true frontal-plane
   compensation or heel lift is not erased.

3. protocol_height_lateral_width_alignment
   Applies only when observed camera height matches the exercise protocol, unless
   the researcher explicitly overrides the review metadata. It attenuates excessive
   near-side lateral spread around the H1/H2/H3 anchor and records far-side depth
   compression as confidence context rather than inventing a physical location.

4. body_axis_alignment
   Applies only when pelvis/shoulder axes are stable enough for optional use.
```

Each enabled prior emits its own report. If one prior is `rejected`, the remaining
priors may still run, and the final `canonicalization_report.status` becomes
`partial`.

### 9.2 Current Implemented Prior: floor_relative_correction

The currently implemented `floor_relative_correction` is the initial
`support_plane_alignment` prior inside the broader canonicalization concept. In
some real monocular recordings, camera angle and learned-depth artifacts can make
a flat floor appear tilted in the coordinate system or make the foot farther from
the camera appear artificially elevated. To mitigate this, it may run after base
hip-torso normalization and before ⑥ Segmentation.

This prior does not force the feet to the floor. It estimates a pseudo-floor
reference inside the pose coordinate system from support-contact candidate landmarks
and applies the floor-tilt component partially to the full pose. Raw and normalized
coordinates are preserved; corrected coordinates, correction magnitude, and
floor-relative diagnostic residuals are added only as new columns and report fields.

The correction is not limited to foot or leg landmarks. For example, even when the
camera is approximately level, monocular depth artifacts may make both the far-side
foot and the far-side arm appear elevated. The filter evaluates the pseudo-floor
tilt at each requested landmark position and applies the same principle to arms,
trunk, head, and legs. In other words, it does not "pull the foot to the floor";
it reduces the shared floor-tilt component while preserving each landmark's
relative height above the local pseudo-floor.

Two transform modes are supported:

```text
rigid_rotation
    Default review mode. Rotates the full 3D pose as one rigid body so the
    observed pseudo-floor normal approaches the target pseudo-floor normal.
    This better preserves segment geometry and left-right parallel structure.

vertical_shear
    Legacy comparison mode. Adjusts only the vertical coordinate by the local
    difference between the observed pseudo-floor and the target plane. It can
    stabilize support-contact height but may visually warp the skeleton.
```

Current implementation status:

```text
module              src/movement/stages/floor_reference.py
default state       disabled
default method      support_contact_plane
default transform   rigid_rotation
current fit space   normalized pose coordinates (`<landmark>_norm_x/y/z`)
output mode         `<landmark>_floor_x/y/z`
diagnostics         `<landmark>_floor_height`, correction magnitude, report notes
```

The default camera-angle prior is level-camera:

```text
camera_pitch_deg = 0.0
camera_roll_deg  = 0.0
```

These values are not calibrated camera extrinsics. They define the target
pseudo-floor slope to preserve inside the pose coordinate system. With the
default level-camera prior, the fitted support-contact plane is compared against
a flat target plane. If a recording setup should preserve a known pose-coordinate
slope, `camera_pitch_deg` and `camera_roll_deg` may be changed; only the observed
excess tilt beyond that target is attenuated. With the default `vertical_axis: y`,
`camera_roll_deg` maps to the x-direction target slope and `camera_pitch_deg`
maps to the z-direction target slope.

Camera height is not currently a floor-relative correction parameter. Exercise
definitions and recording metadata may carry `camera_height_level` as provenance
for filming-condition review; for the current squat protocol, the recommended
height is H2 (80-110 cm above the floor). Because the pipeline does not estimate
camera intrinsics/extrinsics or the true camera-to-floor distance, camera height
is not used to compute the pseudo-floor transform. Its effect should be handled
as a confidence/provenance factor or later robustness condition rather than as a
direct geometric correction.

Design constraints:

```text
preserve originals
    Raw and normalized coordinates are never overwritten.

no foot locking
    Individual foot landmarks are not forcibly snapped to a floor line.

full-pose correction
    The estimated floor-tilt component is applied to all requested landmarks,
    not only to the support-contact landmarks used for fitting. Far-side arm
    and trunk landmarks therefore receive floor-relative coordinates under the
    same pseudo-floor reference.

rigid geometry first
    `rigid_rotation` is preferred for real-sample review because it rotates the
    full pose together. `vertical_shear` remains available for debugging and
    comparison but should not be assumed to preserve segment geometry.

diagnostic preservation
    Heel lift, toe loading, and other true support-contact changes remain visible
    through floor-height residuals and confidence notes.

not calibration
    The pseudo-floor is a pose-internal reference, not a physical floor plane.
    `camera_pitch_deg` and `camera_roll_deg` parameterize a target pose-coordinate
    prior; they do not estimate camera intrinsics, extrinsics, or perspective
    reprojection.
```

Report fields include method, enabled/status, correction transform, support and
diagnostic landmarks, anchor count, observed plane coefficients, target plane
coefficients, camera-angle prior, correction strength, effective correction
strength, max/median correction, anchor residual summary, excluded-anchor
reasons, and confidence notes.

### 9.3 Current Implemented Prior: movement_plane_alignment

`movement_plane_alignment` is a prototype prior for exercises with a clear
primary movement plane, currently intended for squat/lunge review rather than
default scoring. It estimates the dominant horizontal motion axis from
frame-to-frame hip-knee-ankle displacement vectors, then applies a capped rigid
rotation around the configured vertical axis so the common movement direction is
closer to the canonical sagittal analysis plane.

This prior does not flatten the body into a template plane. The full pose is
rotated as one rigid body, and any remaining out-of-plane motion remains in the
`canon` coordinates and in the prior report. This is how possible knee valgus,
trunk lean, heel lift, or asymmetric control remains available for later
feature/biomechanical interpretation.

Current implementation status:

```text
module              src/movement/stages/canonicalization.py
default state       disabled
default method      principal_motion_plane
fit landmarks       left/right hip, knee, ankle when available
transform           capped rigid rotation around the vertical axis
target plane        vertical axis + second horizontal axis (default y-z)
output mode         updates `<landmark>_canon_x/y/z`
diagnostics         rotation angle, motion-vector count, coverage, residual ratio,
                    correction magnitude, excluded-landmark reasons
```

The report stores the requested and applied rotation angle, the estimated primary
movement axis, landmark coverage, out-of-plane residual motion ratio before and
after alignment, and correction magnitude in torso-length-normalized units.
Large residuals are not automatically treated as poor movement quality; they are
data-confidence and interpretation context until notebook review and robustness
simulation decide whether `canon` coordinates should be promoted downstream.

### 9.4 Planned/Prototype Prior: protocol_height_lateral_width_alignment

The `protocol_height_lateral_width_alignment` prior addresses the review pattern
where a frontal or oblique view shows the near-side arm/leg laterally exaggerated
while the far-side limb appears compressed toward the body. The prior is gated by
filming protocol metadata instead of a lens model:

```text
1. Resolve observed camera height from `observed_height_level` or
   `camera_height_level`.
2. Compare it with the exercise's recommended height level.
3. If the height matches, choose the body anchor:
   H1 → support/ankle-level anchor
   H2 → pelvis / hip-center anchor
   H3 → shoulder-center / shoulder-line anchor
4. Apply only capped lateral-width attenuation in `canon` coordinates and keep
   the original `norm` coordinates unchanged.
```

For the current squat protocol, H2 is the recommended height and the pelvis /
hip-center anchor is used. The first implementation should be conservative:
near-side excessive lateral spread may be attenuated, but far-side expansion is
reported as a confidence issue unless later robustness tests justify applying it.
This avoids creating unsupported coordinates for low-visibility far-side joints.

This prior is not camera calibration, lens correction, or perspective reprojection.
It is a protocol-gated pose-internal prior for visual review and data-confidence
reporting.

The first review gates are `notebook/04_normalization_test.ipynb` for the synthetic
sample and `notebook/15_real_squat_import_visualization_test.ipynb` for the real
squat sample. Until pilot review and robustness testing are complete, floor or
canon coordinates are not the default downstream input for final scores.

## 10. Planned Extensions

- Visibility-weighted scale estimation
- Torso length outlier removal before median computation
- Per-exercise canonicalization prior selection driven by exercise definition fields
- Primary movement-plane `movement_plane_alignment` notebook and robustness evaluation
- Protocol-height lateral-width prior robustness evaluation
- Support-plane prior stability evaluation and gradual de-emphasis of the legacy `floor_relative_correction` name
