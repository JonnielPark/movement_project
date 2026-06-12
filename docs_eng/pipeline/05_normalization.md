# 05. Normalization

**Document Version:** 1.15.0
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
   └─ optional canonicalization: candidate-evidence coordinates
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
    emit_sensitivity_report: true
    support_pair: [left_ankle, right_ankle]
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

⑤ Normalization does not assign score gravity. Corrected-depth and
canonicalization candidates expose evidence only: availability, confidence,
visibility, residuals, correction burden, and norm-vs-candidate sensitivity.
Scoring gravity belongs to the later biomarker/scoring policy. The current
development policy keeps corrected-depth contribution at zero there, but that
policy is intentionally not encoded as a normalization output field.

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
        "emit_sensitivity_report": bool,
        "support_pair": list[str],
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
    "candidate_available": bool,
    "candidate_confidence": "not_available" | "high" | "moderate" | "low",
    "burden_level": "none" | "low" | "moderate" | "high",
    "coordinate_mode": "norm",
    "output_prefix": "canon",
    "report_only": bool,
    "downstream_coordinate_mode": "norm" | "canon",
    "status": "disabled" | "skipped" | "applied" | "partial" | "rejected",
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

The public canonicalization summary should prefer `candidate_available`,
`candidate_confidence`, and `burden_level`. The legacy `status` and prior-level
statuses remain as debugging/provenance fields so earlier reports can still be
interpreted, but they are not the primary readiness surface after prototype
review. Score gravity and final-score contribution flags are intentionally absent
from ⑤ Normalization reports.

Routine notebook review should show a prior evidence table rather than prior
counts. The table is derived from `canonicalization_report.prior_reports` and the
active `CanonicalizationConfig`:

```text
prior_id
configured_on
candidate_available
confidence
burden_level
reason
key_metric
```

`configured_on` comes from each prior config's `enabled` flag.
`candidate_available` is true when the prior report status is `applied` or
`warning`. `reason` should be a short human-readable status or confidence-note
summary. `key_metric` should expose the most relevant prior-specific diagnostic,
such as support anchor frames, movement rotation/residual, or protocol camera
height match. Prior counts may remain derivable from full provenance, but they
are not the primary review surface.

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
| `protocol_height_lateral_width_alignment` | prototype, disabled by default | Uses camera-height metadata as a gate before conservative lateral-width attenuation around H1/H2/H3 body anchors. | Zero-gravity scoring candidate; not lens correction, reprojection, or far-side coordinate invention. |
| `anthropometric_skeleton_prior` | planned, disabled by default | Uses loose body-segment length plausibility ranges as an engineering envelope for monocular-depth review. | Not empirical P5/P95 until raw row-level data are available; not skeleton template fitting. |

Current prior order:

```text
1. support_plane_alignment
2. movement_plane_alignment
3. protocol_height_lateral_width_alignment
4. anthropometric_skeleton_prior
```

### 5.1 Promoted Corrected-3D-Hypothesis Candidate Policy

The p01 squat correction review established the first promoted
corrected-3D-hypothesis candidate policy for ⑤ Normalization. Promotion means the
candidate family, burden ledger, residuals, and readiness gates are formal
normalization artifact requirements. It does not mean the corrected coordinates
are calibrated 3D, ground truth, a good-movement template, or scoring input.

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

The last reviewed p01 candidate family was
`rv_skeleton_fit_bounded_xy_endpoint_blend_support_memory`. The public evaluation
notebooks do not run this solver yet; they keep downstream coordinate mode on
`norm` until the solver is moved into `src/movement/` with a tested contract.
The reviewed parameter values are preserved as a historical snapshot in
`docs_eng/pipeline/05_normalization_p01_squat_review_snapshot.md`.

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

### 5.2 Corrected-3D-Hypothesis Solver Promotion Contract

Before the former p01 correction solver is moved into `src/movement/`, it must be
implemented as a report-first candidate generator with the following minimal
contract. This is a solver contract, not a scoring contract.

Required input:

```text
norm_pose_df
  DataFrame with one row per frame and existing <landmark>_norm_x/y/z columns.
  Raw and base norm columns are read-only.

landmarks
  Ordered landmark names used by the pipeline run.

common_subject_skeleton_profile
  Selected profile id, source matrix path, sex/bin provenance, and segment target
  ratios. Height may be used for readable nominal lengths only; coordinates are
  not rescaled to cm or m.

exercise_support_context
  Exercise id, kinetic chain, base of support, support surface, support-contact
  landmarks, primary support pair, and any rep/phase/ready-window labels.

solver_config
  Source family, output family, correction caps, strengths, visibility gates,
  support-width no-worsen guard, bend-side guard, and report settings. The p01
  review values are preserved in
  `05_normalization_p01_squat_review_snapshot.md`.
```

Required output:

```text
corrected_candidate_df
  Same frame index and row order as norm_pose_df.
  Candidate columns must be additive only. A family-specific convention such as
  <landmark>_<output_family>_<axis> is allowed only when the result report also
  exposes the exact coordinate-column map.

burden_ledger
  Frame/stage/landmark or segment-level correction burden table.

residual_report
  Segment-length, support-width, support-surface, bend-side, and visibility
  residuals before and after candidate generation.

norm_vs_corrected_sensitivity_report
  Feature-level comparison table for any feature considered for
  corrected-3D-hypothesis use.

readiness_provenance
  Candidate availability, confidence, status, and rejection reasons.
```

The burden ledger must contain at least:

```text
frame
rep_id or phase label when available
candidate_family
stage
landmark_or_segment
axis
delta_torso_ratio
cap_torso_ratio
cap_fraction
residual_before_torso
residual_after_torso
accepted
rejection_reason
visibility_min
confidence
used_for_features_or_scores = false
```

The sensitivity report must contain at least:

```text
feature_id
evaluation_domain
source_evidence
norm_value
corrected_candidate_value
delta
delta_abs
correction_burden
residual
availability
confidence
```

Promotion gates:

```text
1. raw, norm, and existing canon columns are never overwritten.
2. No candidate is emitted without burden and residual reports.
3. No feature may consume a candidate unless its evaluation_domain is declared as
   corrected_3d_hypothesis or dual_domain_compare.
4. Normalization must not decide score gravity or final-score contribution.
   It emits only candidate evidence for the later scoring policy.
5. A correction step must be rejected or marked not_assessed when it worsens a
   configured hard residual gate such as support width, bend-side consistency, or
   support-surface plausibility.
6. Impossible caps are availability gates when trusted depth is absent; they are
   not hidden correction targets.
7. Readiness is per feature and per recording. A successful p01 review does not
   imply readiness for another exercise, camera view, or participant.
```

Minimum implementation target for the first module extraction:

```text
module path      src/movement/stages/corrected_3d_hypothesis.py
primary function build_corrected_3d_hypothesis_candidates(...)
return object    Corrected3DHypothesisResult
default mode     candidate evidence only, downstream_coordinate_mode = norm
first feature    candidate.support_width_stability sensitivity only
```

### 5.3 First Sensitivity Target: `candidate.support_width_stability`

The first code-backed sensitivity target is a candidate-evidence comparison of
support width stability. It does not create corrected coordinates.
It only compares an existing candidate coordinate family with the base `norm`
family.

Definition:

```text
support_pair          left_ankle, right_ankle by default
norm_width(t)         distance between support_pair in norm axes [x, y]
candidate_width(t)    distance between support_pair in candidate axes [x, y, z]
stability_value       P95(width) - P05(width), in torso-length ratio
delta                 candidate_stability_value - norm_stability_value
```

The `norm` value intentionally uses recording-plane axes only. The candidate
value may include model-depth or corrected-depth axes, but remains
low-confidence corrected-3D-hypothesis evidence. When candidate coordinate
columns are absent, the feature is `not_assessed`; the function must not create a
candidate by itself.

Required output row:

```text
feature_id = candidate.support_width_stability
evaluation_domain = corrected_3d_hypothesis
source_evidence = norm support-pair width versus existing candidate family
norm_value
corrected_candidate_value
delta
delta_abs
correction_burden
residual
availability
confidence
```

`correction_burden` is taken from the supplied burden ledger when available. A
missing ledger makes the row `low_confidence` even if candidate columns are
present. High burden or non-finite values keep the row as low-confidence
candidate evidence and can lower availability to `low_confidence` or
`not_assessed`.

### 5.4 Pipeline Review Surface

When `normalization.corrected_3d_hypothesis.enabled = true` and
`emit_sensitivity_report = true`, `run_pipeline` emits a top-level report block:

```python
{
    "corrected_3d_hypothesis_review": {
        "num_candidate_rows": int,
        "num_burden_rows": int,
        "residual_report": dict,
        "norm_vs_corrected_sensitivity_report": list[dict],
        "num_sensitivity_rows": int,
        "readiness_provenance": {
            "status": "candidate_evidence",
            "used_for_features_or_scores": False,
            "downstream_coordinate_mode": "norm",
        },
    }
}
```

This block is a candidate-evidence surface. It must not alter `df`, downstream
coordinate mode, feature extraction, biomechanical proxies, biomarker records,
or final scores. If the configured candidate family columns are absent, the
sensitivity row is still emitted as `not_assessed` so the reason is visible in
the report. Score gravity is intentionally deferred to the later scoring policy.

### 5.5 Multi-Recording / Multi-Exercise Sensitivity Surface

Multi-recording review starts by aggregating already generated pipeline reports.
The aggregation helper reads `corrected_3d_hypothesis_review` blocks and returns
grouped candidate-evidence rows. Required grouping fields:

```text
feature_id
exercise_id
n_recordings
n_rows
n_assessed
n_low_confidence
n_not_assessed
median_norm_value
median_corrected_candidate_value
median_delta_abs
max_correction_burden
```

The summary does not decide whether a feature should affect the final score. It
only shows whether enough recordings exist to review stability, availability,
burden, and norm-vs-candidate sensitivity. Assigning nonzero score gravity
remains deferred to a later scoring-policy task after this summary is reviewed
across multiple recordings and exercises.

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
- create candidate depth residual evidence when bounded and small
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
| Stage A | file design + aggregate statistics | conservative engineering range around aggregate ratios | plausibility flag, low-confidence marking, candidate residual evidence |
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
- Corrected-3D-hypothesis coordinates remain candidate evidence in ⑤. The later
  scoring policy decides any score gravity; the current development plan keeps
  corrected-depth contribution at zero there.
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
- Robustness evaluation before any corrected coordinate receives nonzero score
  gravity in a later scoring policy.
- Gradual de-emphasis of the legacy `floor_relative_correction` key once local
  configs no longer depend on it.
