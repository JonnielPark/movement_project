# 05. Normalization

**Document Version:** 1.12.0
**Last Updated:** 2026-06-10
**Korean Sync:** `docs/pipeline/05_normalization.md` is the same-version Korean source.

Pipeline step ⑤ converts raw pose coordinates to a body-relative coordinate
system. When explicitly enabled, it may also create corrected-3D-hypothesis
candidate coordinates and burden reports that reduce consistent
monocular-observation bias.

This step does not estimate absolute forces, absolute torque, calibrated 3D, or
absolute body dimensions. It provides the coordinate base for ⑧ Feature
Extraction and ⑨ Biomechanical Proxy.

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
   └─ optional canonicalization: review-only candidate coordinates
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction
```

Runs after ④ Preprocessing so unreliable hip/shoulder landmarks are corrected,
interpolated, or marked before they affect the scale reference.

---

## 2. Base Normalization Contract

The implemented method is `hip_torso`.

```text
Translation reference : frame-wise hip center
Scale reference       : sequence-wise median torso length
Model-depth gain      : model_depth_scale, default 1.0
Output unit           : torso_length_ratio (dimensionless)
```

The hip center is the body-relative origin.

```text
hip_center(t) = (left_hip(t) + right_hip(t)) / 2
p_translated_i(t) = p_i(t) - hip_center(t)
```

The sequence-level median torso length is the body scale. Using a sequence median
instead of per-frame scale avoids artificial skeleton jitter from monocular
torso-length noise.

```text
shoulder_center(t) = (left_shoulder(t) + right_shoulder(t)) / 2
torso_length(t)    = distance(hip_center(t), shoulder_center(t))
s                  = median(valid torso_length)
p_translated_i(t)  = p_i(t) - hip_center(t)
p_norm_x_i(t)      = p_translated_x_i(t) / s
p_norm_y_i(t)      = p_translated_y_i(t) / s
p_norm_z_i(t)      = p_translated_z_i(t) * model_depth_scale / s
```

`model_depth_scale` is a coordinate-gain parameter for monocular model depth,
not camera calibration. The default is `1.0`; review runs may attenuate model
depth, but this must be reported and remains low-confidence evidence.

Raw coordinates are never overwritten.

```text
left_knee_x       original x
left_knee_norm_x  base normalized x
left_knee_canon_x optional canonicalized candidate x
```

Coordinate families have fixed meanings.

```text
raw      original pose coordinates
norm     base hip-torso normalized coordinates
canon    optional review/candidate coordinates after canonicalization
```

---

## 3. Configuration Contract

Detailed defaults live in `configs/pipeline_default.yaml`. The stable contract is:

```yaml
normalization:
  enabled: true
  method: hip_torso
  keep_reference_columns: true
  model_depth_scale: 1.0
  corrected_3d_hypothesis:
    enabled: false
    output_family: corrected_3d_hypothesis
    downstream_coordinate_mode: norm
    feature_depth_gravity: 0.0
    report_burden_before_feature_use: true
    require_feature_domain_declaration: true
  canonicalization:
    enabled: false
    coordinate_mode: norm
    output_prefix: canon
    report_only: true
    downstream_coordinate_mode: norm
    data_confidence: ...
    support_plane_alignment: ...
    movement_plane_alignment: ...
    protocol_height_lateral_width_alignment: ...
    anthropometric_skeleton_prior: ...
```

`report_only: true` means `canon` coordinates and reports may be created, but
downstream stages continue to consume `norm` coordinates. Changing
`downstream_coordinate_mode` to `canon` requires notebook review, robustness
evidence, and an explicit docs update before code promotion.

`floor_relative_correction` may still appear in local or legacy config files. It
is treated as a backward-compatible alias for `support_plane_alignment`; new work
should prefer the canonicalization key.

`corrected_3d_hypothesis.feature_depth_gravity` is the explicit scoring gate for
depth-derived candidate evidence. The default value is `0.0`, meaning corrected
depth is excluded from feature scoring even when a candidate coordinate family is
produced for review. Future work may raise this value only after multi-recording
and multi-exercise sensitivity review defines feature-specific burden thresholds.

---

## 4. Report Contract

`normalize_pose_by_hip_torso(df, landmarks)` returns a normalized DataFrame and a
report.

```python
{
    "method": str,
    "num_frames": int,
    "scale_method": str,
    "scale_value": float,
    "min_torso_length": float,
    "max_torso_length": float,
    "median_torso_length": float,
    "num_invalid_torso_frames": int,
    "num_normalized_landmarks": int,
    "model_depth_scale": float,
    "corrected_3d_hypothesis": {
        "enabled": bool,
        "output_family": str,
        "downstream_coordinate_mode": "norm" | "corrected_3d_hypothesis",
        "feature_depth_gravity": float,
        "used_for_features_or_scores": bool,
        "require_feature_domain_declaration": bool,
        "report_burden_before_feature_use": bool,
        "depth_evidence_policy": str,
    },
}
```

When canonicalization is enabled, `canonicalization_report` is added inside the
normalization report.

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
        "anthropometric_skeleton_prior": dict | None,
    },
}
```

`data_confidence.level` is not a movement-quality score. Low confidence should
surface as caution, withholding, or provenance rather than automatic score
deduction.

---

## 5. Canonicalization Contract

Canonicalization is optional and disabled by default. It is not calibrated 3D
reconstruction and does not fit the pose to a good-movement template. Its role is
to attenuate consistent observation bias while preserving raw/norm coordinates
and true compensation patterns such as knee valgus, heel lift, trunk lean, or
pelvis rotation.

Current active or planned priors:

| Prior | Status | Purpose | Guardrail |
|---|---|---|---|
| `support_plane_alignment` | implemented, disabled by default | Pose-internal pseudo-floor/support-plane review from support-contact landmarks. Wraps the older `floor_relative_correction` logic. | Does not lock feet to the floor; not camera calibration. |
| `movement_plane_alignment` | prototype, disabled by default | Capped rigid rotation around the vertical axis using the dominant hip-knee-ankle movement direction. | Preserves out-of-plane residuals for compensation review. |
| `protocol_height_lateral_width_alignment` | prototype, disabled by default | Uses camera-height metadata as a gate before conservative lateral-width attenuation around H1/H2/H3 body anchors. | Not lens correction, reprojection, or far-side coordinate invention. |
| `anthropometric_skeleton_prior` | planned, disabled by default | Uses loose body-segment length plausibility ranges as an engineering envelope for monocular-depth review. | Not empirical P5/P95 until raw row-level data are available; not skeleton template fitting. |

Current prior order:

```text
1. support_plane_alignment
2. movement_plane_alignment
3. protocol_height_lateral_width_alignment
4. anthropometric_skeleton_prior
```

### 5.1 Promoted Corrected-3D-Hypothesis Candidate

The stable notebook-16 squat stack is the first promoted corrected-3D-hypothesis
candidate surface for ⑤ Normalization. Promotion means the candidate family,
burden ledger, residuals, and readiness gates are part of the normalization
review artifact. It does not mean the corrected coordinates are calibrated 3D,
ground truth, a good-movement template, or scoring input.

Current promoted stack:

```text
1. common-subject skeleton envelope from aggregate anthropometry
2. within-session stable segment-memory table from reference-worthy frames
3. squat closed-chain support context
4. recording-view-constrained skeleton placement: rv_skeleton_fit
5. bounded recording-view residual variant: rv_skeleton_fit_bounded_xy
6. visible-support mirrored anchor prior
7. bounded pre/post standing support-anchor blend
8. whole-video planted support temporal memory
9. scoring-readiness and bend-flip provenance gates
```

The current p01 review profile emits
`rv_skeleton_fit_bounded_xy_endpoint_blend_support_memory` as a named candidate
family and keeps downstream coordinate mode on `norm`.

Retired review-only candidates are no longer active code/config branches:

```text
paired target unification
strong segment projection
support-body corridor pull
support-locked or knee-led support projection
support-width projection variants
lower-body knee-heading and knee-lane priors
foot-heading / toe-fixed adjustment templates
standalone support-height leveling
visual or ideal symmetry templates
knee-over-foot and knee-bend templates
phase-specific norm blend
far-side decompression
post-correction smoothing
```

They may be reintroduced only through the docs-first path: define the research
need in `docs_eng/`, sync `docs/`, add config/report fields, and compare ON/OFF
behavior across multiple recordings or exercises.

Body-axis alignment is intentionally not active. It may be reconsidered only
after the anthropometric skeleton prior is specified, because pelvis/shoulder
axis alignment could suppress true pelvis rotation, trunk lean, or transverse
compensation if applied too early.

---

## 6. Anthropometric Skeleton Prior Policy

### 6.1 Purpose

The anthropometric skeleton prior is a **loose anatomical plausibility envelope**
for monocular pose depth. It is not a precise anthropometric statistical model.

Allowed uses:

```text
- flag segment lengths that are anatomically implausible after normalization
- create review-only candidate depth residual corrections when bounded and small
- downgrade data confidence for affected segment/frame/feature records
- document why a depth-sensitive feature is withheld or marked low confidence
```

Not allowed:

```text
- overwrite raw coordinates
- overwrite base norm coordinates
- force the pose into a normal skeleton template
- promote monocular depth confidence to high
- claim calibrated 3D reconstruction or subject-specific body reconstruction
- claim empirical P5/P95 ranges before row-level raw anthropometric data exist
- infer absolute physical length, force, torque, strength, diagnosis, or prognosis
```

### 6.2 Evidence Level

Current source scope:

```text
source                 Size Korea 8th Korean Anthropometric Survey
included data family   2020 3D full-body automatic measurements only
included item range    No.138-311
excluded families      direct measurement, 3D direct measurement,
                       3D foot/hand/head automatic measurements
current evidence       file design + aggregate statistics fallback
raw row-level data     not yet available
```

The current statistics table gives marginal aggregate values. It does **not**
provide individual paired ratios such as `(hip height - knee height) / stature`.
Therefore, the first implementation stage may use only an aggregate engineering
envelope. It must not call the range empirical percentile prior.

Two-stage evidence model:

| Stage | Data level | Allowed claim | Use |
|---|---|---|---|
| Stage A | file design + aggregate statistics | conservative engineering range around aggregate ratios | plausibility flag, low-confidence marking, review-only candidate residual |
| Stage B | de-identified row-level 3D full-body automatic raw data | empirical row-level ratio distribution, P1/P99, P5/P95, stratified checks | narrower prior, height-bin validation, model comparison |

### 6.3 Aggregate-Only Segment Map

The first prior uses dimensionless ratios derived from aggregate statistics. The
values below are **not** individual-level ratio percentiles.

| Segment | Pose endpoints | Measurement proxy | Aggregate mean/stature | Status |
|---|---|---|---:|---|
| `shoulder_width` | left_shoulder ↔ right_shoulder | `m299` shoulder-outside breadth | 0.2220 | proxy close |
| `hip_width` | left_hip ↔ right_hip | `m265` hip breadth | 0.2114 | surface-width proxy |
| `torso` | shoulder_center ↔ hip_center | `m145 - m155` | 0.3211 | vertical proxy, not Euclidean torso |
| `upper_arm` | shoulder ↔ elbow | `m189` | 0.1921 | proxy close |
| `forearm` | elbow ↔ wrist | `m191 - m189` | 0.1423 | derived proxy |
| `thigh` | hip ↔ knee | `m155 - m159` | 0.2287 | vertical proxy |
| `shank` | knee ↔ ankle | `m159 - m161` | 0.2186 | vertical proxy to lateral malleolus |
| `foot` | ankle ↔ foot_index | not available | null | unavailable in current source scope |

Additional reference proxies may be stored for review but are not primary skeleton
segments: `sitting_height`, `trunk_vertical`, `crotch_height`, and
`outside_leg_length`.

`m195` thigh straight length is not the primary hip-knee prior. Its aggregate
stature ratio is much smaller than `m155 - m159`; keep it only as a
definition-check or sensitivity note until the measurement definition is reviewed.

### 6.4 Range Policy

Stage A range policy:

```text
center value          aggregate mean(segment) / aggregate mean(stature)
range name            conservative_engineering_range
range source          researcher-defined loose tolerance around aggregate center
range purpose         detect impossible skeleton behavior, not estimate population percentile
configuration         stored in YAML/data artifact, never hardcoded in Python
```

Stage B upgrade policy:

```text
required input        de-identified row-level 3D full-body automatic raw table
ratio calculation     segment / stature, segment / torso proxy, relevant body-scale ratios
summary statistics    n, mean, SD, median, IQR, P1, P5, P95, P99
range names           recommended_plausible_range = P5-P95
                      conservative_range = P1-P99
stratification        sex, age_group, height_bin only after sample-size review
```

### 6.5 Height-Bin Policy

The survey may collect height by optional 5 cm bins:

```text
150cm or less
151-155cm
156-160cm
161-165cm
166-170cm
171-175cm
176-180cm
181cm or more
prefer not to answer
```

At Stage A, height bins are metadata/provenance only. They are not used to select
a stratified prior because aggregate tables do not prove that height-bin-specific
segment ratios improve the model.

At Stage B, row-level data may test whether bins help:

```text
Model 0  overall mean ratio
Model 1  sex mean ratio
Model 2  sex + height_bin mean ratio
Model 3  sex + age_group + height_bin mean ratio
```

If 5 cm bins are sparse or unstable, internal analysis may merge adjacent bins.
Questionnaire collection may still keep 5 cm bins for future flexibility.

### 6.6 Correction And Confidence Policy

The prior may create candidate `canon` coordinates only when all conditions hold:

```text
1. the segment is available in the prior
2. x/y evidence does not already violate the plausible range
3. a bounded depth residual can bring the segment inside the loose range
4. correction magnitude is below configured cap
5. landmark visibility and swap-risk gates allow review
```

If the x/y projection is already outside the envelope, the system must not invent
depth to make the segment fit. It should mark the segment/frame as low confidence
or not assessed.

Report fields should include:

```text
source_scope
evidence_level
range_type
segments_checked
segments_unavailable
candidate_corrections
correction_magnitude_torso
rejection_reasons
confidence_downgrade_reasons
model_depth_reliability_after_correction = low
```

### 6.7 Articulation Plausibility

Joint-angle and reverse-bending constraints are separate from Size Korea segment
length statistics. They should be documented and implemented as an
`articulation_plausibility` guard that downgrades data confidence for impossible
configurations. It must not directly penalize movement-quality scores.

### 6.8 Data Artifact Policy

Recommended repository locations:

```text
data/reference/anthropometry/
    size_korea8_3d_auto_skeleton_prior.yaml
    size_korea8_3d_auto_aggregate_ratio_preview.csv
    size_korea8_3d_auto_unavailable_segments.csv

data/processed/anthropometry/
    row-level-derived summaries and validation reports when raw data become available
```

Every derived table must include:

```text
source_scope = 3d_fullbody_auto_only
evidence_level = aggregate_engineering_preview | row_level_empirical
unit = dimensionless_ratio
```

---

## 7. Downstream Rules

- ⑥ Segmentation, ⑧ Feature Extraction, ⑨ Biomechanical Proxy, and ⑩ Biomarker
  Scoring consume `norm` coordinates by default.
- Downstream features must declare `recording_view_only`,
  `corrected_3d_hypothesis`, or `dual_domain_compare` before using corrected
  coordinates.
- Corrected-3D-hypothesis coordinates are score-excluded while
  `feature_depth_gravity = 0.0`.
- Corrected-coordinate magnitude and residuals are data-confidence/provenance
  signals, not movement-quality penalties.
- ④ Preprocessing may mark reliability violations before scale computation, but
  ⑤ Normalization owns body-relative scaling and canonical candidate coordinates.
- ⑨ Biomechanical Proxy uses normalized coordinates to compute relative CoM,
  moment-arm, and load-shift proxies. It must not infer absolute force, torque,
  or calibrated physical distances from this step.
- Corrected candidate outputs are not used downstream until feature-specific
  burden, residual, and norm-vs-corrected sensitivity gates are documented.

---

## 8. Planned Extensions

- Build Stage A aggregate-only engineering prior from the documented Size Korea
  8th 3D full-body automatic measurement source.
- Add row-level empirical prior only if de-identified raw 3D full-body automatic
  measurements become available.
- Visibility-weighted scale estimation and torso-length outlier handling.
- Per-exercise canonicalization prior selection from exercise definition fields.
- Robustness evaluation before any corrected coordinate is used for scoring or
  before `feature_depth_gravity` is raised above `0.0`.
- Gradual de-emphasis of the legacy `floor_relative_correction` key once local
  configs no longer depend on it.
