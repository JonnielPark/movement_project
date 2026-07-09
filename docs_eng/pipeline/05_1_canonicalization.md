# 05-1. Canonicalization

**Document Version:** 2.3.1
**Last Updated:** 2026-07-09
**Korean Sync:** `docs/pipeline/05_1_canonicalization.md` is the same-version Korean source.

Canonicalization is no longer a required standalone pipeline step. It is the
optional ⑤-1 substage of [05_normalization.md](05_normalization.md): it consumes
`norm` coordinates from ⑤ Normalization and may add analysis-space
coordinate families such as `canon` or `corrected_3d_hypothesis`. This file is
kept as the detailed reference for the optional filters and their provenance
contract.

This step does not estimate absolute forces, absolute torque, calibrated 3D, or
absolute body dimensions. It does not fit the pose to a good-movement template.
The default downstream coordinate mode remains `norm` unless a later
feature/scoring policy explicitly declares otherwise.

**Current status:** merged under ⑤ Normalization as optional ⑤-1
canonicalization filters. The root-level YAML key `canonicalization` is retained
only as a backward-compatible alias; new configs should use
`normalization.canonicalization`.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
   └─ ⑤-1 Optional Canonicalization filters       ← this reference
→ ⑥ Segmentation
→ ⑦ Feature Extraction
→ ⑧ Biomechanical Proxy
→ ⑨ Biomarker Scoring
```

Runs after ⑤ Normalization because all priors operate on an existing
body-relative coordinate family. It should preserve `raw` and `norm` columns and
add analysis-space columns only.

---

## 2. Input And Coordinate-Family Contract

Required input is normalized pose data: preprocessed pose data plus the ⑤
body-relative `norm` coordinate family and depth-evidence metadata. After ①
schema harmonization and ⑤ Normalization, `norm` should have an xyz column
shape. The important distinction is whether `norm_z` contains finite depth
evidence or only `NaN` placeholders.

Raw coordinates are never overwritten.

```text
left_knee_x       original x
left_knee_norm_x  base normalized x from ⑤
left_knee_canon_x optional canonicalized x from ⑤-1
left_knee_canon_z optional canonical depth hypothesis z from ⑤-1
```

Coordinate families have fixed meanings.

```text
raw      original pose coordinates
norm     hip-torso normalized coordinates from ⑤
canon    optional analysis-space coordinates from ⑤-1
```

The canonicalization output should be described as canonicalized pose data:

```text
Canonicalized pose data = normalized pose data + analysis-space coordinates + analysis-evidence report
```

When `norm_z` is a placeholder, ⑤-1 may fill a `canon_z` analysis evidence only when a
prior such as `xy_depth_lift` is explicitly enabled. In that case `canon_z` is
a canonical depth hypothesis, not observed depth. Future corrected-3D-hypothesis
families must follow the same additive rule, for example
`<landmark>_<output_family>_<axis>`. Analysis-space columns must not replace `norm`.

---

## 3. Configuration Contract

Detailed defaults live in `configs/pipeline_default.yaml`. The stable ⑤-1
configuration contract is nested under `normalization`:

```yaml
normalization:
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
    xy_depth_lift:
      enabled: false
      method: recording_view_depth_hypothesis
    anthropometric_skeleton_prior: ...
    corrected_3d_hypothesis:
      enabled: false
      output_family: corrected_3d_hypothesis
      downstream_coordinate_mode: norm
      emit_sensitivity_report: true
      support_pair: [left_ankle, right_ankle]
      report_burden_before_feature_use: true
      require_feature_domain_declaration: true
```

`report_only: true` means `canon` coordinates and reports may be created, but
downstream stages continue to consume `norm` coordinates. Changing
`downstream_coordinate_mode` to `canon` requires notebook review, robustness
evidence, and an explicit docs update before code promotion.

`floor_relative_correction` may still appear in local or legacy config files. It
is treated as a backward-compatible alias for `support_plane_alignment`; new work
should prefer the canonicalization key.

⑤-1 Canonicalization does not assign score-policy weights or final-score
contribution. Corrected-depth and canonicalization analysis evidence expose evidence
summaries only: availability, confidence, `quality_gravity`, and
norm-vs-analysis sensitivity. Raw residuals and correction burden remain
report-local diagnostics. The current development policy keeps corrected-depth
score contribution at zero in ⑨, but that policy is intentionally not encoded as
a ⑤-1 output field.

---

## 4. Report Contract

`apply_canonicalization(df, landmarks, config)` returns a DataFrame with additive
analysis-space columns and a `canonicalization_report`.

```python
{
    "enabled": bool,
    "evidence_available": bool,
    "evidence_confidence": "not_available" | "high" | "moderate" | "low",
    "quality_gravity": float,
    "burden_level": "none" | "low" | "moderate" | "high",
    "input_pose_data_state": "normalized_pose_data" | str,
    "output_pose_data_state": "canonicalized_pose_data" | str,
    "input_coordinate_families": list[str],
    "output_coordinate_families": list[str],
    "input_coordinate_axes": dict[str, list[str]],
    "output_coordinate_axes": dict[str, list[str]],
    "added_coordinate_family": "canon" | str | None,
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
        "xy_depth_lift": dict | None,
        "anthropometric_skeleton_prior": dict | None,
    },
}
```

The public canonicalization summary should prefer `evidence_available`,
`evidence_confidence`, and `quality_gravity`. `burden_level` remains a
report-local diagnostic summary for review, not a required downstream payload
field. The legacy `status` and prior-level statuses remain as
debugging/provenance fields so earlier reports can still be interpreted, but
they are not the primary readiness surface after prototype review. Score-policy
weights and final-score contribution flags are intentionally absent from ⑤-1
Canonicalization reports.

Routine notebook review should show a prior evidence table rather than prior
counts. The table is derived from `canonicalization_report.prior_reports` and the
active `CanonicalizationConfig`:

```text
prior_id
configured_on
evidence_available
reason
key_metric
```

`evidence_confidence`, `quality_gravity`, and `burden_level` belong to the
whole canonicalization evidence summary, not to each prior row. Keeping them
out of the prior evidence table avoids implying that a prior-specific confidence
or burden score was computed.

`configured_on` comes from each prior config's `enabled` flag.
`evidence_available` is true when the prior report status is `applied` or
`warning`. `reason` should be a short human-readable status or confidence-note
summary. `key_metric` should expose the most relevant prior-specific diagnostic,
such as support anchor frames, movement rotation/residual, or protocol camera
height match. Prior counts may remain derivable from full provenance, but they
are not the primary review surface.

`data_confidence.level` is not a movement-quality score. Low confidence should
surface as caution, withholding, or provenance rather than automatic score
deduction.

The stage-check notebook should follow the established notebook style used by
the earlier stage checks: `Data Setup`, `Direct Canonicalization Test`, numbered
checks, `Pipeline Integration`, and `Check Summary`. Its setup must prepare the
same previous-stage input chain used by ⑤ Normalization: validation,
annotation, exercise definition loading, preprocessing, and normalization.
Canonicalization should be tested on normalized preprocessed pose data, not
on a raw-pose dataframe that was normalized in isolation, so preprocessing
validity/usability provenance is available when analysis evidence is reviewed.

Visualization in the stage-check notebook should stay compact: one normalized
vs canonical comparison is enough for pose inspection, with a separate
diagnostic plot only when it directly exposes residuals, correction magnitude,
or prior-specific evidence.

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
| `xy_depth_lift` | planned, disabled by default | Recording-view-constrained depth hypothesis that fills `canon_z` planned patterns from `norm_x/y` when `norm_z` is only a placeholder, as expected for YOLO-style 2D pose backends. | Not 3D reconstruction, measured depth, or subject-specific skeleton fitting; does not create score-policy weight. |
| `support_plane_alignment` | implemented, disabled by default | Pose-internal pseudo-floor/support-plane review from exercise-defined support landmarks. Wraps the older `floor_relative_correction` logic. | Does not lock feet to the floor; not camera calibration. |
| `movement_plane_alignment` | prototype, disabled by default | Capped rigid rotation around the vertical axis using the dominant hip-knee-ankle movement direction. | Preserves out-of-plane residuals for compensation review. |
| `protocol_height_lateral_width_alignment` | prototype, disabled by default | Uses camera-height metadata as a gate before conservative lateral-width attenuation around H1/H2/H3 body anchors. | Analysis evidence with zero default score contribution; not lens correction, reprojection, or far-side coordinate invention. |
| `anthropometric_skeleton_prior` | planned, disabled by default | Uses loose body-segment length plausibility ranges as an engineering envelope for monocular-depth review. | Not empirical P5/P95 until raw row-level data are available; not skeleton template fitting. |

Current prior order:

```text
1. xy_depth_lift
2. support_plane_alignment
3. movement_plane_alignment
4. protocol_height_lateral_width_alignment
5. anthropometric_skeleton_prior
```

`xy_depth_lift` can be a required analysis prior only when finite `norm_z`
evidence is unavailable. For MediaPipe-style inputs with finite model-depth
`norm_z`, it remains disabled by default or may be used only for sensitivity
comparison.

### 5.1 XY Depth Lift Evidence Contract

The default `xy_depth_lift` method is `recording_view_depth_hypothesis`. Its
purpose is not to recover calibrated 3D from 2D recording-view coordinates. It
creates an analysis z estimate and provenance so later depth-sensitive features
can explain why they are withheld or low confidence.

Required input:

```text
norm_pose_df
  DataFrame with <landmark>_norm_x/y/z columns. <landmark>_norm_z may be a
  NaN placeholder when the backend did not provide z.

landmarks
  Ordered landmark names used by the pipeline run.

exercise_context
  Exercise id, kinetic chain, support landmarks, support pair, movement plane,
  and camera protocol.

depth_prior_config
  Segment prior source, correction caps, temporal smoothness, confidence gates,
  near/far-side sign policy, and rejection rules.
```

Base generation rules:

```text
1. Copy norm_x/y into canon_x/y.
2. Compute each segment's recording-view length d_xy.
3. If a loose segment target or envelope exists and d_xy is inside the envelope,
   analysis dz_abs may be computed as sqrt(max(target_length^2 - d_xy^2, 0)).
4. Do not assign z sign arbitrarily. Sign may be assigned only when a documented
   sign prior exists, such as near/far-side evidence, support contact, or
   stable-frame memory.
5. If d_xy already exceeds the target/envelope, reject the analysis evidence with
   `projected_length_exceeds_prior` instead of inventing z to fit it.
6. Frames or segments that fail temporal continuity or correction caps remain
   evidence unavailable.
```

Required output:

```text
<landmark>_canon_x/y/z
canonical_depth_hypothesis_available
canonical_depth_hypothesis_confidence
canonical_depth_hypothesis_quality_gravity
canonical_depth_hypothesis_rejection_reason
```

The report-local burden/residual diagnostics must contain at least:

```text
frame
landmark_or_segment
source_axes = xy
target_axes = xyz
d_xy_torso_ratio
target_length_torso_ratio
analysis_dz_torso_ratio
cap_torso_ratio
cap_fraction
residual_before_torso
residual_after_torso
accepted
rejection_reason
confidence
used_for_features_or_scores = false
```

`xy_depth_lift` output is analysis evidence. A post-⑥ feature may use this z
analysis evidence only after declaring `evaluation_domain = canonical_depth_hypothesis`
or `dual_domain_compare`; it must not contribute to the default composite score
until ⑨ Scoring explicitly promotes nonzero score-policy weight.

### 5.2 Promoted Corrected-3D-Hypothesis Review Policy

The p01 squat correction review established the first promoted
corrected-3D-hypothesis review policy for ⑤-1 Canonicalization. Promotion means
the coordinate family, quality summary, burden ledger, residual diagnostics, and
readiness gates are formal canonicalization artifact requirements. It does not
mean the corrected coordinates are calibrated 3D, ground truth, a good-movement
template, or scoring input.

Current promoted stack:

```text
1. common-subject skeleton envelope from aggregate anthropometry
2. within-session stable segment-memory table from reference-worthy frames
3. squat closed-chain support context
4. recording-view-constrained skeleton placement: rv_skeleton_fit
5. bounded recording-view residual variant: rv_skeleton_fit_bounded_xy
6. visible-support mirrored anchor prior
7. bounded pre/post standing support-landmark blend
8. whole-video planted support temporal memory
9. scoring-readiness and bend-flip provenance gates
```

The last reviewed p01 coordinate family was
`rv_skeleton_fit_bounded_xy_endpoint_blend_support_memory`. The public evaluation
notebooks do not run this solver yet; they keep downstream coordinate mode on
`norm` until the solver is moved into `src/movement/` with a tested contract.
The reviewed parameter values are preserved as a historical snapshot in
`docs_eng/pipeline/05_1_canonicalization_p01_squat_review_snapshot.md`.

Retired tuning branches are no longer active code/config branches:

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

### 5.3 Corrected-3D-Hypothesis Solver Promotion Contract

Before the former p01 correction solver is moved into `src/movement/`, it must be
implemented as a report-first analysis-evidence generator with the following minimal
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
  Exercise id, kinetic chain, base of support, support surface, support landmark
  landmarks, primary support pair, and any rep/phase/ready-window labels.

solver_config
  Source family, output family, correction caps, strengths, confidence gates,
  support-width no-worsen guard, bend-side guard, and report settings. The p01
  review values are preserved in
  `05_1_canonicalization_p01_squat_review_snapshot.md`.
```

Required output:

```text
analysis_coordinate_df
  Same frame index and row order as norm_pose_df.
  Analysis-space columns must be additive only. A family-specific convention such as
  <landmark>_<output_family>_<axis> is allowed only when the result report also
  exposes the exact coordinate-column map.

burden_ledger
  Frame/stage/landmark or segment-level correction burden table.

residual_report
  Segment-length, support-width, support-surface, bend-side, and confidence
  residuals before and after analysis-evidence generation.

norm_vs_corrected_sensitivity_report
  Feature-level comparison table for any feature considered for
  corrected-3D-hypothesis use.

readiness_provenance
  Evidence availability, confidence, status, and rejection reasons.
```

The burden ledger must contain at least:

```text
frame
rep_id or phase label when available
coordinate_family
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
confidence_min
confidence
used_for_features_or_scores = false
```

The sensitivity report must contain at least:

```text
feature_id
evaluation_domain
source_evidence
norm_value
corrected_value
delta
delta_abs
correction_burden
residual
availability
confidence
quality_gravity
```

Promotion gates:

```text
1. raw, norm, and existing canon columns are never overwritten.
2. No analysis evidence is emitted without burden and residual reports.
3. No feature may consume a analysis evidence unless its evaluation_domain is declared as
   corrected_3d_hypothesis or dual_domain_compare.
4. Canonicalization must not decide score-policy weight or final-score contribution.
   It emits only analysis evidence for the later scoring policy.
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
primary function build_corrected_3d_hypothesis_evidence(...)
return object    Corrected3DHypothesisResult
default mode     analysis evidence only, downstream_coordinate_mode = norm
first feature    analysis.support_width_stability sensitivity only
```

### 5.4 First Sensitivity Target: `analysis.support_width_stability`

The first code-backed sensitivity target is a analysis-evidence comparison of
support width stability. It does not create corrected coordinates.
It only compares an existing analysis-space coordinate family with the base `norm`
family.

Definition:

```text
support_pair          left_ankle, right_ankle by default
norm_width(t)         distance between support_pair in norm axes [x, y]
analysis_width(t)    distance between support_pair in coordinate axes [x, y, z]
stability_value       P95(width) - P05(width), in torso-length ratio
delta                 analysis_stability_value - norm_stability_value
```

The `norm` value intentionally uses recording-plane axes only. The analysis-space value
value may include model-depth or corrected-depth axes, but remains
low-confidence corrected-3D-hypothesis evidence. When analysis-space coordinate
columns are absent, the feature is `not_assessed`; the function must not create a
analysis evidence by itself.

Required output row:

```text
feature_id = analysis.support_width_stability
evaluation_domain = corrected_3d_hypothesis
source_evidence = norm support-pair width versus existing coordinate family
norm_value
corrected_value
delta
delta_abs
correction_burden
residual
availability
confidence
quality_gravity
```

`quality_gravity` is the downstream trust summary for the row. `correction_burden`
and residual details are report-local diagnostics taken from the supplied burden
ledger and comparison residual when available. A missing ledger makes the row
`low_confidence` even if analysis-space columns are present. High burden or non-finite
values keep the row as low-confidence analysis evidence and can lower
availability to `low_confidence` or `not_assessed`.

### 5.5 Pipeline Review Surface

When `canonicalization.corrected_3d_hypothesis.enabled = true` and
`emit_sensitivity_report = true`, `run_pipeline` emits a top-level report block:

```python
{
    "corrected_3d_hypothesis_review": {
        "num_analysis_rows": int,
        "num_burden_rows": int,
        "residual_report": dict,
        "norm_vs_corrected_sensitivity_report": list[dict],
        "num_sensitivity_rows": int,
        "readiness_provenance": {
            "status": "analysis_evidence",
            "used_for_features_or_scores": False,
            "downstream_coordinate_mode": "norm",
        },
    }
}
```

This block is a analysis-evidence surface. It must not alter `df`, downstream
coordinate mode, feature extraction, biomechanical proxies, biomarker records,
or final scores. If the configured coordinate family columns are absent, the
sensitivity row is still emitted as `not_assessed` so the reason is visible in
the report. Score-policy weight is intentionally deferred to the later scoring
policy.

### 5.6 Multi-Recording / Multi-Exercise Sensitivity Surface

Multi-recording review starts by aggregating already generated pipeline reports.
The aggregation helper reads `corrected_3d_hypothesis_review` blocks and returns
grouped analysis-evidence rows. Required grouping fields:

```text
feature_id
exercise_id
n_recordings
n_rows
n_assessed
n_low_confidence
n_not_assessed
median_norm_value
median_corrected_value
median_delta_abs
max_correction_burden
median_quality_gravity
```

The summary does not decide whether a feature should affect the final score. It
only shows whether enough recordings exist to review stability, availability,
`quality_gravity`, report-local burden diagnostics, and norm-vs-analysis
sensitivity. Assigning nonzero score-policy weight remains deferred to a later
scoring-policy task after this summary is reviewed across multiple recordings
and exercises.

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
- create analysis depth residual evidence when bounded and small
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
| Stage A | file design + aggregate statistics | conservative engineering range around aggregate ratios | plausibility flag, low-confidence marking, analysis residual evidence |
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

The prior may create `canon` analysis-space coordinates only when all conditions hold:

```text
1. the segment is available in the prior
2. x/y evidence does not already violate the plausible range
3. a bounded depth residual can bring the segment inside the loose range
4. correction magnitude is below configured cap
5. landmark confidence and swap-risk gates allow review
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
analysis_corrections
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

- ⑥ Segmentation, ⑦ Feature Extraction, ⑧ Biomechanical Proxy, and ⑨ Biomarker
  Scoring consume `norm` coordinates by default.
- Downstream features must declare `recording_view_only`,
  `corrected_3d_hypothesis`, or `dual_domain_compare` before using corrected
  coordinates.
- Corrected-3D-hypothesis coordinates remain analysis evidence in ⑥. The later
  scoring policy decides any score-policy weight; the current development plan
  keeps corrected-depth contribution at zero there.
- Corrected-coordinate magnitude and residuals are data-confidence/provenance
  signals, not movement-quality penalties.
- ④ Preprocessing may mark reliability violations before scale computation,
  ⑤ Normalization owns body-relative scaling, and ⑤-1 Canonicalization owns
  canonical analysis-space coordinates.
- ⑧ Biomechanical Proxy uses normalized coordinates to compute relative CoM,
  moment-arm, and load-shift proxies. It must not infer absolute force, torque,
  or calibrated physical distances from this step.
- Corrected analysis-space outputs are not used downstream until feature-specific
  `quality_gravity`, report-local burden/residual diagnostics, and
  norm-vs-corrected sensitivity gates are documented.

---

## 8. Planned Extensions

- Build Stage A aggregate-only engineering prior from the documented Size Korea
  8th 3D full-body automatic measurement source.
- Add row-level empirical prior only if de-identified raw 3D full-body automatic
  measurements become available.
- confidence-weighted scale estimation and torso-length outlier handling.
- Per-exercise canonicalization prior selection from exercise definition fields.
- Robustness evaluation before any corrected coordinate receives nonzero
  score-policy weight in a later scoring policy.
- Gradual de-emphasis of the legacy `floor_relative_correction` key once local
  configs no longer depend on it.

