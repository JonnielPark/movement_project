# 10. Biomarker Scoring

**Document Version:** 1.6.2
**Last Updated:** 2026-07-07
**Korean Sync:** `docs/pipeline/10_biomarker_scoring.md` is the same-version Korean source.

Pipeline step ⑩ wraps ⑧ `FeatureRecord` and ⑨ `BiomechRecord` outputs into
interpretable biomarker records and, when a baseline exists, derives a per-rep
movement-quality score. Observation reliability, feature availability, and
coordinate-correction magnitude remain separate confidence/provenance signals.

Scores are engineering summaries, not clinical thresholds or diagnostic outputs.

---

## 1. Pipeline Position

```text
⑧ Feature Extraction   FeatureRecord list
⑨ Biomech Proxy        BiomechRecord list
→ ⑩ Biomarker Scoring  ← this step
```

Required inputs:

```text
feat_records           FeatureRecord list, including availability metadata
biomech_records        BiomechRecord list
exercise_definition    feature_domains, biomechanical_focus, quality rules
definition_version     exercise YAML version
baseline JSON          data/reference/baseline_zscore.json when scoring is enabled
```

Baseline matching is performed by metric id. Per-rep metrics must therefore use
rep-invariant ids such as `temporal.tempo.rep_duration`; the repetition number
belongs in `rep_id`, not in `feature_id`. If a feature id embeds the repetition
number, later reps can miss the baseline entry and receive no deduction.

---

## 2. Output Contract

Two record types are emitted.

```text
BiomarkerRecord
    Pass-through individual metric with value, unit, rep_id, source_fields,
    availability, view/depth reliability, focus tier, common record context
    metadata, landmark references, and note metadata.

BiomarkerScoreRecord
    Per-rep composite score with domain scores, final score, floor flags,
    deduction audit, withheld-feature audit, score bounds, and domain weights.

BiomarkerScoreItem
    Flattened per-feature score audit derived from BiomarkerScoreRecord.deductions.
    This is a reporting view, not a separate scoring algorithm.
```

`BiomarkerRecord.source_fields` is required. Records without provenance should not
be produced.

Saved follow-along outputs keep pass-through biomarker records separate from
composite score records.

```text
data/processed/biomarker/<recording_id>_biomarkers.csv
    One row per BiomarkerRecord. Keeps availability, source_fields,
    view/depth reliability, focus tier, record context metadata, landmark
    references, and unit metadata.

data/processed/biomarker/<recording_id>_biomarker_scores.csv
    One row per BiomarkerScoreRecord when baseline data exists. JSON-serializes
    domain_scores, floor_applied, deductions, withheld_features, domain_weights,
    domain-feature-family weights, low-confidence/depth/focus/feature gravity
    policies, and score_bounds for CSV compatibility.

data/processed/biomarker/<recording_id>_biomarker_score_items.csv
    One row per scored feature item. Expands each score record's deduction audit
    into rep_id, domain, feature_id, item_score, deduction, value, baseline,
    confidence gravity, depth/focus gravity, feature-family weight, and record
    context fields. item_score is computed as score_max - effective deduction,
    clipped to the configured score bounds, so it should be read as the feature's
    effective contribution audit rather than an independent clinical grade.

data/processed/biomarker/<recording_id>_biomarker_qc.json
    Compact row counts, score availability, final-score range, withheld-feature
    count, and output file provenance.
```

If no baseline exists for the selected exercise, the biomarker CSV and QC JSON
are still saved, while the score and score-item CSVs are saved with the current
schemas and zero rows. This is expected for newly authored exercises until a
baseline is generated.

---

## 3. Scoring Contract

Composite scoring uses Z-score deductions against a synthetic-normal baseline.
Default score bounds are 0-100 and default domain weights are equal relative
weights.

```text
spatial   range of motion, movement path, support consistency, and role alignment
temporal  pacing and timing consistency
control   stability and compensation features
biomech   relative load-distribution proxy features
```

The default configuration lives in `configs/pipeline_default.yaml`.

```yaml
biomarker:
  score_bounds:
    min: 0.0
    max: 100.0
  domain_weights:
    spatial: 1.0
    temporal: 1.0
    control: 1.0
    biomech: 1.0
  domain_feature_family_weights:
    spatial:
      range_of_motion: 0.60
      movement_path: 0.15
      support_consistency: 0.05
      role_alignment: 0.15
      phase_profile: 0.05
    temporal:
      tempo: 0.25
      variability: 0.50
      phase_profile: 0.25
  scoring_focus_weights:
    primary: 1.0
    secondary: 0.45
    context_constraint: 0.6
    compensation: 0.5
    diagnostic: 0.0
  low_confidence_score_weights:
    spatial: 0.0
    temporal: 0.0
    control: 0.0
    biomech: 0.1
  depth_dependency_score_weights:
    none: 1.0
    low: 1.0
    moderate: 0.5
    high: 0.1
    unknown: 0.3
  feature_score_weight_overrides:
    spatial.movement_path.arc_length_xy.left_ankle.*: 0.0
    spatial.movement_path.arc_length_xy.right_ankle.*: 0.0
    spatial.movement_path.arc_length_xyz.left_ankle.*: 0.0
    spatial.movement_path.arc_length_xyz.right_ankle.*: 0.0
    spatial.movement_path.arc_length_xyz.left_knee.*: 0.0
    spatial.movement_path.arc_length_xyz.right_knee.*: 0.0
    spatial.range_of_motion.xyz.*: 0.25
    control.compensation.knee_valgus.xy.*: 0.25
    control.compensation.knee_varus.xy.*: 0.25
    control.compensation.excessive_trunk_flexion.xy: 0.5
    control.compensation.excessive_trunk_flexion.xyz: 0.25
    spatial.range_of_motion.xy.left_hip_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xy.right_hip_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xy.left_knee_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xy.right_knee_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xy.left_ankle_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xy.right_ankle_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.left_hip_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.right_hip_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.left_knee_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.right_knee_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.left_ankle_angle.turnaround_hold: 0.0
    spatial.range_of_motion.xyz.right_ankle_angle.turnaround_hold: 0.0
  feature_score_direction_overrides:
    spatial.support_consistency.*: upper_bound_only
    spatial.role_alignment.left_right.support_consistency_xy_drift.*: upper_bound_only
    spatial.movement_path.arc_length_xy.left_hip.turnaround_hold: upper_bound_only
    spatial.movement_path.arc_length_xy.right_hip.turnaround_hold: upper_bound_only
    spatial.movement_path.arc_length_xy.left_knee.turnaround_hold: upper_bound_only
    spatial.movement_path.arc_length_xy.right_knee.turnaround_hold: upper_bound_only
  baseline_generation:
    enabled: true
    generate_when_missing: true
    source_mode: current_run
    baseline_status: provisional
    source_type: current_recording
    pose_backend: mediapipe
    coordinate_mode: norm
    output_dir: data/reference/baselines
    active_metrics_path: data/reference/baseline_zscore.json
    qc_output_dir: data/reference/baseline_qc
    mirror_active_metrics: false
    use_generated_for_current_scoring: true
```

Domain assignment is by record ID prefix.

```text
spatial.*   → spatial
temporal.*  → temporal
control.*   → control
biomech.*   → biomech
other       → pass-through only
```

---

## 4. Feature Eligibility

⑧ may emit numeric features that are not reliable enough for scoring. ⑩ uses
`availability` as the composite-score gate and evidence gravity as the scoring
strength.

```text
assessed
    Eligible for Z-score deduction if baseline statistics exist.

low_confidence
    Eligible only when the scoring configuration gives the record's domain a
    non-zero low-confidence score weight. The default keeps spatial/temporal/
    control low-confidence records withheld, while biomech low-confidence
    records may contribute with small gravity.

not_assessed
    Excluded from composite score. Report as provenance/unavailable.

missing availability
    Backward-compatible: treated as assessed only for legacy records.
```

### Current scoring item catalog

The current score is an itemized scoring prototype, not a finalized normative
movement-quality judgment. Each item remains in the biomarker audit even when
its score gravity is low or zero.

```text
spatial.range_of_motion.xy.*
    Status: primary scoring candidate.
    Meaning: recording-view joint range of motion.
    Current caution: uses exercise-defined acceptable bands where available;
    do not interpret larger-but-controlled squat depth as automatically worse.

spatial.range_of_motion.xyz.*
    Status: depth-mixed comparative evidence.
    Meaning: same joint-angle family with model/candidate depth included.
    Current caution: low gravity by default until corrected-3D or multi-view
    validation supports stronger use.

spatial.movement_path.arc_length_xy.*
    Status: score-tunable recording-view path evidence.
    Meaning: camera-plane landmark path length.
    Current caution: fixed-support ankle paths are withheld by default for
    squat because apparent support motion is often pose noise, not true foot
    travel.

spatial.support_consistency.*
    Status: support-context scoring candidate with one-sided scoring.
    Meaning: recording-view consistency of fixed support anchors.
    Current caution: this is not a CoP/CoM stability claim; biomechanical
    center proxies stay in ⑨.

spatial.role_alignment.*
    Status: secondary/context scoring candidate.
    Meaning: bilateral or role-based agreement of exercise-relevant landmarks.
    Current caution: view-sensitive symmetry should be interpreted with camera
    compatibility and landmark quality.

temporal.tempo.* / temporal.variability.* / temporal.phase_profile.*
    Status: scoring candidate with broad tolerance bands.
    Meaning: rep duration, rhythm/repeatability, and exercise-defined phase
    timing balance.
    Current caution: the research does not treat absolute speed as a primary
    quality target; stable rhythm is more important than matching one narrow
    synthetic duration.

control.compensation.knee_valgus.xy.* / control.compensation.knee_varus.xy.*
    Status: attenuated control scoring candidate.
    Meaning: recording-view hip-knee-ankle tracking proxy.
    Current caution: meaningful for lower-body stance tasks, but view- and
    visibility-sensitive; low-confidence control records are withheld by default.

control.compensation.excessive_trunk_flexion.xy
    Status: provisional control scoring candidate.
    Meaning: recording-view trunk-line angle from image vertical.
    Current caution: normal trunk strategy depends on exercise context. A hinge,
    squat, plank, or push-up should not share one narrow trunk-flexion baseline.
    Default gravity: 0.5 while the trunk-orientation tolerance band remains
    provisional.

control.compensation.excessive_trunk_flexion.xyz
    Status: low-gravity comparative evidence.
    Meaning: trunk-line angle with model/candidate depth included.
    Current caution: depth-mixed monocular evidence; keep visible but weak until
    corrected-3D validation improves.

control.compensation.heel_lift.xy.*
    Status: recording-view support-contact proxy.
    Meaning: apparent heel elevation above the rep support baseline.
    Current caution: requires strong landmark visibility; depth-based heel lift
    is not promoted in the current prototype.

control.compensation.pelvis_rotation.xyz
    Status: low-confidence/report-heavy evidence.
    Meaning: left-right hip model-depth asymmetry as pelvic rotation proxy.
    Current caution: highly depth-sensitive under monocular pose.

biomech.*
    Status: biomechanical proxy evidence with low-confidence gravity.
    Meaning: relative CoM/moment-arm/load-shift tendencies, not absolute force or
    torque.
    Current caution: useful for interpretation and future comparison, but not a
    clinical or kinetic ground-truth measurement.
```

For the current p01 squat run, a low control subscore mainly indicates that
control-family baselines and tolerance rules still need multi-recording review.
The score audit should therefore be read item-by-item: control candidates and
their evidence paths are available, while final score calibration remains future
work.

### Control scoring grammar across exercises

Control features are not a fixed universal checklist. The exercise definition
decides which control families are applicable, and scoring then applies the same
evidence/availability grammar used by the other domains.

```text
exercise context
    posture, support, laterality, primary/secondary joints, movement phase, and
    camera-view family from the exercise definition.

control family
    stability | compensation | support_contact | alignment_control |
    phase_control | diagnostic

evidence path
    xy for recording-view candidate evidence, xyz/z for depth-sensitive
    comparative evidence, timing when the control question is phase-timing
    based, proxy when it comes from ⑨ biomechanical proxy records.

confidence gate
    landmark visibility/coverage, view compatibility, support-context
    compatibility, depth dependency, and correction/canonicalization provenance.

scoring status
    scoring_candidate | attenuated_candidate | low_gravity_compare |
    report_only | not_applicable
```

The current cross-exercise control matrix is:

```text
knee_tracking
    Feature ids:
        control.compensation.knee_valgus.xy.<side>
        control.compensation.knee_varus.xy.<side>
    Exercise context:
        lower-body stance tasks where hip-knee-ankle tracking is meaningful
        (squat, lunge, step-up-style patterns). Not applicable to upper-body or
        supine/core tasks unless the exercise definition explicitly promotes a
        lower-limb control question.
    Evidence path:
        recording-view xy only in the current pipeline. Do not emit a knee
        valgus/varus xyz variant until a body-frontal/corrected reference plane
        exists.
    Confidence gate:
        hip, knee, and ankle landmark quality; camera-view compatibility;
        laterality/role context for unilateral or alternating tasks.
    Scoring status:
        attenuated candidate. Low-confidence rows are withheld by default.

trunk_orientation_control
    Feature ids:
        control.compensation.excessive_trunk_flexion.xy
        control.compensation.excessive_trunk_flexion.xyz
    Exercise context:
        exercise-specific. Trunk lean may be a compensation in a squat, expected
        strategy in a hinge, and a different control problem in plank or push-up
        patterns. The exercise definition must provide the acceptable direction
        or target band before strong scoring use.
    Evidence path:
        xy is the recording-view public candidate; xyz is depth-mixed
        comparative evidence.
    Confidence gate:
        shoulder/hip landmark quality, view family, and whether the exercise
        posture makes image-vertical trunk angle meaningful.
    Scoring status:
        provisional candidate for xy, low-gravity comparison for xyz.

support_contact_control
    Feature ids:
        control.compensation.heel_lift.xy.<side>
        future hand/wrist support-contact proxies for plank or push-up style
        exercises when defined.
    Exercise context:
        closed-chain support tasks. For foot-supported lower-body exercises,
        heel lift can be meaningful; for hand-supported exercises, an analogous
        wrist/hand support-contact proxy must be defined separately.
    Evidence path:
        recording-view support-axis evidence by default. Depth-based contact
        inference remains low-confidence/report-only until validated.
    Confidence gate:
        support landmark visibility, declared support anchors, and support
        surface assumptions from the exercise definition.
    Scoring status:
        candidate only when support context and visibility are sufficient.

pelvis_control
    Feature ids:
        control.stability.hip_center_support_center_xy_drift
        control.compensation.lateral_pelvic_shift.xy
        control.compensation.pelvis_rotation.xyz
    Exercise context:
        support-relative pelvis control can matter in lower-body stance and
        plank/shoulder-tap style anti-rotation tasks. Hip-centered self-
        measurements are diagnostic/not_assessed until redefined against an
        independent support-relative reference.
    Evidence path:
        support-relative xy is preferred for scoring. Pelvis rotation via z/xyz
        is depth-sensitive comparative evidence.
    Confidence gate:
        support anchor availability, hip landmark quality, laterality/role
        context, and depth reliability for rotation.
    Scoring status:
        support-relative xy can become a candidate; depth-heavy rotation remains
        low-gravity or report-only.

phase_control
    Feature ids:
        control.phase_profile.* (future)
    Exercise context:
        only when the exercise definition has phase labels that make a control
        question meaningful, such as bottom-position hold stability or
        ascent-specific compensation.
    Evidence path:
        domain-local summary derived from phase-aware features, not a hidden
        coordinate correction.
    Confidence gate:
        phase segmentation quality plus the source feature's own confidence.
    Scoring status:
        planned extension, report-only until tested.
```

This grammar keeps control extensible without hard-coding squat-specific rules.
New exercises should add control scoring by declaring the relevant context and
letting the same availability, depth-dependency, focus-tier, feature-family, and
feature-id gravity gates decide score contribution.

`view_reliability` is not a separate score multiplier. It should already be
reflected in `availability`, which avoids false precision from camera artifacts.

Coordinate-reference self-measurements must not enter composite scoring. If a
feature measures the same derived reference point that ⑤ Normalization used as
the coordinate origin, the numeric value may collapse toward zero even when the
body segment did move in the original recording view. Such records should be
`not_assessed` or `diagnostic` until ⑧ redefines them against an independent
reference.

For hip-centered `norm` coordinates, this guard applies to hip/pelvis-center
stability proxies such as:

```text
control.stability.hip_center_x_std
control.stability.hip_center_z_std
control.compensation.lateral_pelvic_shift.xy
```

Closed-chain squat-style pelvis control should instead use support-relative
recording-view evidence, such as hip-center drift relative to the exercise
support center, and then rely on ordinary availability, depth-dependency,
focus-tier, and feature-family gravity.

Closed-chain heel-lift scoring is also a recording-view support-contact proxy in
the current pipeline. `control.compensation.heel_lift.xy.<side>` may be scored only
when it is computed from recording-view vertical evidence. A model-depth `z`
heel-lift diagnostic must remain low-confidence or report-only unless a later
corrected-3D validation promotes it.

Common record context metadata from ⑧ and ⑨ is preserved but does not create
additional score gravity by itself. In particular, `landmark_ids`,
`support_role`, `coordinate_reference`, `evaluation_domain`, `evidence_axes`,
and `feature_family` explain which landmarks were measured and which
coordinate/evidence path supported the value. Stable anatomical labels such as
body region, side, and default joint action are joined from the
joint/landmark metadata registry when a report needs them; they are not
duplicated in every score record. The active score strength still comes from
availability, depth dependency, focus tier, feature-family budget, and
feature-specific overrides.

`low_confidence_score_weights` is a scoring-stage gravity, not a normalization
or canonicalization output. It allows depth-sensitive biomech proxy evidence to
remain visible in the composite while preventing monocular depth from acting as
full-strength evidence. Records with effective score weight 0 are reported in
`withheld_features`; records with non-zero low-confidence weight appear in
`deductions` with their availability and confidence weight.

`depth_dependency_score_weights` is a second scoring-stage gravity. It does not
remove a feature and does not change its biomarker value. It only controls how
strongly a baseline-matched deduction contributes to the composite score.

```text
none       recording-view or timing evidence; full default gravity
low        weak depth sensitivity; full default gravity for now
moderate   mixed recording-view/depth evidence; attenuated by default
high       monocular-depth or corrected-3D-hypothesis evidence; small gravity
unknown    reported but attenuated until the evidence path is classified
```

The effective deduction gravity is:

```text
g_effective =
    availability_gravity
  * depth_dependency_gravity
  * focus_gravity
  * feature_gravity
```

This keeps recording-view and depth-sensitive evidence in the same audit trail
while allowing the scorer to tune how much each evidence family affects the
final score. A future scoring study may change these defaults, but any change
must remain visible in the score record.

### Movement-path evidence variant gravity

Movement-path scoring must not make a single global choice between `xy` and `xyz`.
Stage 8 should emit both variants for coordinate-derived movement-path targets, and
Stage 10 should tune their contribution by feature id, focus tier, depth
dependency, and view compatibility.

```text
xy
    Recording-view evidence. Prefer it when the movement-quality question can be
    answered from camera-plane x/y and the baseline view is compatible.

xyz
    Depth-sensitive evidence. Keep it visible for review and corrected-3D
    comparison, but assign lower gravity under monocular MediaPipe depth unless
    later validation promotes the specific feature.

z
    Single-axis diagnostic/provenance. Do not score by default.
```

The calibration target is therefore not a project-wide `xy:xyz` ratio. It is a
feature-specific gravity policy learned from multiple recordings, camera views,
and exercises. For example, squat knee movement path may remain `xy`-dominant,
fixed ankle support movement path may be withheld in favor of `support_consistency`,
and future corrected-3D hip/trunk features may raise their `xyz` gravity only
when correction burden and residual evidence are acceptable.

### Range-of-motion evidence variant gravity

Range of motion follows the same explicit-evidence policy. ⑧ emits both
`spatial.range_of_motion.xy.<joint_angle>` and `spatial.range_of_motion.xyz.<joint_angle>` from the same
`angle_definitions` triplet. ⑩ should treat the `xy` variant as the preferred
recording-view scoring candidate when the camera view is compatible, and treat
the `xyz` variant as depth-sensitive comparative evidence with reduced default
gravity.

This is not a claim that 2D projected angles are universally correct. It is a
monocular research compromise: x/y evidence is more stable in the recording view,
while xyz evidence remains useful for review and future corrected-3D comparison.
The score must expose both variants and their gravity rather than hiding the
choice inside a single implicit range-of-motion value.

### Exercise-definition focus policy

The exercise definition is also a scoring-intent document. The authoring choices
for primary and secondary joint actions should therefore influence score gravity,
without turning the exercise definition into a hard whitelist. ⑧ assigns each
feature or proxy record a `focus_tier`, and ⑩ multiplies the corresponding
`scoring_focus_weights` value into the deduction gravity.

```text
primary
    Main task signal backed by primary joint actions, primary body regions,
    primary joints, or main load regions in the exercise definition.

secondary
    Supportive task signal backed by secondary joint actions or secondary
    movement planes. It remains score-visible with lower default gravity.

context_constraint
    Exercise-context signal such as closed-chain support consistency, base-of-
    support consistency, or role alignment that is required by the movement setup but
    is not simply a primary joint action.

compensation
    Candidate compensation or safety-related pattern. It can affect scoring,
    but should not dominate over the intended primary/secondary task signals.

diagnostic
    Report-only or weakly interpretable evidence such as axis diagnostics,
    support-consistency axis path diagnostics, or retired/deferred feature candidates.
```

Default focus weights keep primary features at full strength, attenuate
secondary and context signals, and withhold diagnostics from composite scoring.
The focus weight is only one factor. A primary feature can still contribute very
little when it is low-confidence, highly depth-dependent, missing from the
baseline, or explicitly overridden by feature id. Conversely, support-consistency
and compensation evidence can remain score-visible when the exercise definition
requires them.

Within a domain, the default public scoring policy uses feature-family weights
when a domain has `domain_feature_family_weights`. This avoids making remaining
features stronger just because another feature family was withheld. The
configured family budget is not redistributed to other families when a family is
missing, unavailable, or explicitly set to zero.

```text
spatial.range_of_motion.xy.*                  → range_of_motion
spatial.range_of_motion.xyz.*                 → range_of_motion
spatial.movement_path.arc_length_*.*      → movement_path
spatial.role_alignment.*                    → role_alignment
spatial.support_consistency.*               → support_consistency
temporal.tempo.*                            → tempo
temporal.variability.*                      → variability
<domain>.phase_profile.*                    → phase_profile
other spatial records                    → other
```

`spatial.phase_profile.*` and `temporal.phase_profile.*` may now be emitted as
domain-local phase-summary families. `control.phase_profile.*` and
`biomech.phase_profile.*` remain reserved and require separate scoring review
before activation.

Temporal family budgets intentionally differ from spatial budgets. Absolute
duration (`tempo`) is low-strength because the thesis does not score one fixed
exercise speed as inherently better. Rhythm/repeatability (`variability`) gets
the largest temporal budget, and exercise-defined phase ratios (`phase_profile`)
are kept visible without overpowering the temporal domain.

The current spatial policy gives `support_consistency` only a narrow
constraint/QC-style budget for recording-view fixed-support consistency. It should
not act like a primary movement-quality score, because fixed support can be
partly enforced by normalization/canonicalization and can also reflect pose
jitter. The spatial budget therefore favors range of motion and assessed role
alignment, while support-consistency rows remain visible as low-strength
fixed-support compliance evidence. The first scoring-ready support-consistency
role-alignment record is
`spatial.role_alignment.left_right.support_consistency_xy_drift.*`, because it is derived from
fixed-support x/y drift rather than monocular depth. Depth-sensitive range-of-motion role alignment
can still be emitted, but it remains governed by the view/depth availability
gates and is withheld when those gates mark it low-confidence. Axis-path
`support_consistency` diagnostics remain diagnostic; recording-view point, width,
and center stability rows may receive only the narrow support-consistency family
budget.

Support-consistency scoring uses `upper_bound_only` direction by default. A smaller
support drift than the provisional baseline is not a fault; only larger-than
baseline drift should create a deduction. When corrected coordinates are used,
support-consistency scores must be interpreted with correction burden/residual so
that the score does not merely reward a hidden fixed-support correction.

### Range-of-motion target-band policy

Range-of-motion scoring should not always mean "closer to the synthetic baseline mean is
better." For exercise-defined `spatial.range_of_motion.xy.*` targets, ⑩ uses a functional
acceptable-band penalty instead of the generic absolute z-score penalty.

```yaml
quality_rules:
  range_of_motion_targets:
    spatial.range_of_motion.xy.left_knee_angle:
      scoring_mode: minimum_sufficient_band
      minimum_sufficient_deg: 90.0
      excessive_threshold_deg: 160.0
      soft_tolerance_deg: 10.0
      excessive_penalty_scale: 0.5
      apply_to_phase_suffixes: [full_rep, descent, ascent]
```

Current rule semantics:

- Below `minimum_sufficient_deg`: penalize the shortfall scaled by
  `soft_tolerance_deg`.
- Between `minimum_sufficient_deg` and `excessive_threshold_deg`: no range-of-motion
  deduction, because the movement achieved sufficient task range.
- Above `excessive_threshold_deg`: apply a softer excess penalty only when the
  exercise defines an upper bound.
- `turnaround_hold` range of motion is not matched by default for squat, because low motion
  during a hold is not a range-of-motion failure. The current default squat policy withholds
  lower-body `spatial.range_of_motion.xy.*.turnaround_hold` and
  `spatial.range_of_motion.xyz.*.turnaround_hold` from composite scoring via
  `feature_score_weight_overrides`.

This keeps range of motion as a movement-quality signal while avoiding the incorrect
interpretation that deeper or larger-but-controlled squat range of motion is worse merely
because it differs from the provisional baseline mean.

### Temporal tolerance-band policy

The current research does not treat absolute exercise speed as a primary movement-quality
target. Temporal scoring should mainly preserve rhythm and repeatability: a repetition can
be slower or faster than the provisional synthetic baseline and still be acceptable if it
stays inside an exercise-defined timing band.

For exercise-defined `temporal.tempo.rep_duration*` targets, ⑩ therefore uses an
acceptable-duration band before falling back to generic baseline z-score behavior.

```yaml
quality_rules:
  temporal_tolerance_bands:
    temporal.tempo.rep_duration:
      scoring_mode: acceptable_duration_band
      minimum_duration_s: 1.2
      maximum_duration_s: 3.5
      soft_tolerance_s: 0.3
    temporal.tempo.rep_duration.descent:
      scoring_mode: acceptable_duration_band
      minimum_duration_s: 0.4
      maximum_duration_s: 1.5
      soft_tolerance_s: 0.15
    temporal.tempo.rep_duration.turnaround_hold:
      scoring_mode: acceptable_duration_band
      minimum_duration_s: 0.0
      maximum_duration_s: 0.5
      soft_tolerance_s: 0.1
    temporal.tempo.rep_duration.ascent:
      scoring_mode: acceptable_duration_band
      minimum_duration_s: 0.4
      maximum_duration_s: 1.5
      soft_tolerance_s: 0.15
```

Current rule semantics:

- Inside `[minimum_duration_s, maximum_duration_s]`: no absolute-duration deduction.
- Below `minimum_duration_s`: penalize only the shortfall scaled by
  `soft_tolerance_s`.
- Above `maximum_duration_s`: penalize only the excess scaled by
  `soft_tolerance_s`.
- Timing consistency remains visible through `temporal.variability.tempo_cv` and
  `temporal.phase_profile.*` features; those are better suited to rhythm and
  repeatability than forcing every subject to match a narrow absolute speed.

This policy keeps temporal scoring compatible with the thesis scope: it can flag
obvious timing outliers, but it does not claim that one fixed squat speed is
clinically or biomechanically optimal.

`temporal.variability.tempo_cv` is sequence-level evidence. When per-rep score
records are present, the same sequence-level variability record may be included
in each rep's temporal audit so that rhythm consistency contributes to the
composite score without pretending that each rep has a separate CV.

For feature ids matched by `quality_rules.temporal_variability_bands`, ⑩ uses a
maximum-variability ceiling:

```yaml
quality_rules:
  temporal_variability_bands:
    temporal.variability.tempo_cv:
      scoring_mode: maximum_sufficient_ceiling
      maximum_cv: 0.05
      soft_tolerance_cv: 0.05
```

Values at or below `maximum_cv` create no rhythm deduction. Values above the
ceiling are penalized by the excess divided by `soft_tolerance_cv`.

For feature ids matched by `quality_rules.temporal_phase_profile_bands`, ⑩ uses
an acceptable phase-ratio band:

```yaml
quality_rules:
  temporal_phase_profile_bands:
    temporal.phase_profile.duration_ratio.descent_ascent:
      scoring_mode: acceptable_ratio_band
      minimum_ratio: 0.5
      maximum_ratio: 2.0
      soft_tolerance_ratio: 0.25
```

Values inside the ratio band create no deduction. Values outside the band are
penalized only by the distance from the nearest bound divided by
`soft_tolerance_ratio`. This keeps phase-profile scoring visible for squat
rhythm review while avoiding a narrow claim that one exact descent/ascent timing
ratio is biomechanically optimal.

`feature_score_weight_overrides` is an optional third gravity layer for exact
feature ids or `prefix.*` feature families. It is intended for evidence variants
whose numeric value is useful for review but is known to be a weak direct
movement-quality penalty under the current monocular pipeline. Feature
extraction should emit explicit movement-path and range-of-motion evidence variants:
`spatial.movement_path.arc_length_xy.<landmark>` for recording-view path evidence and
`spatial.movement_path.arc_length_xyz.<landmark>` for mixed recording-view/depth
evidence; `spatial.range_of_motion.xy.<joint_angle>` for recording-view included-angle
range of motion and `spatial.range_of_motion.xyz.<joint_angle>` for mixed recording-view/depth
range of motion. Scoring
owns the gravity decision.

For fixed bilateral-foot squat, support-consistency axis `xyz` movement-path evidence remains
visible and baseline-matchable, but its feature gravity is `0.0` by default so
it is withheld from composite scoring. A separate recording-view support-consistency
feature family should carry any future `maintain_foot_contact` scoring
contribution.

The current validation policy promotes recording-view knee movement path
length and withholds the knee `xyz` path from composite scoring. Knee motion is
a legitimate moving-joint signal during squat, but p01 review showed that the
`xyz` path can be strongly z-dominated under monocular MediaPipe depth.
Therefore `spatial.movement_path.arc_length_xy.*_knee*` becomes the active movement-path
scoring evidence, while `spatial.movement_path.arc_length_xyz.*_knee*` remains visible
with feature gravity `0.0` to avoid double-counting the same movement with
depth-dominated evidence.

For lower-body movement path during `turnaround_hold`, lower-than-baseline path
length is not treated as a fault. A quiet transition can represent stable
bottom-position control rather than failed motion. The default policy therefore
applies `upper_bound_only` scoring to promoted hip and knee recording-view
movement path: excessive path is penalized, while smaller path length is not.

Recording-view movement-path features remain camera-view dependent. They are less
exposed to monocular depth noise than `z` or `xyz` path length, but they are not
view invariant. A future multi-camera-zone baseline should compare these
features only within compatible camera-zone families, or reduce scoring gravity
when the active recording view is not compatible with the baseline view.

Frontal knee-tracking compensation (`control.compensation.knee_valgus.xy.*` and
`control.compensation.knee_varus.xy.*`) is also attenuated in the default
development policy. The feature remains a scoring candidate because knee
tracking is biomechanically meaningful in squat, but the current monocular
proxy is view-sensitive and the provisional baseline can make small
hip-knee-ankle line deviations produce very large z-scores. Until camera-view
gating and multi-recording baselines are available, the default feature gravity
is `0.25`: enough to keep repeated frontal knee deviation visible, but not
enough to dominate the control domain by itself. Depth-mixed control variants
such as `control.compensation.excessive_trunk_flexion.xyz` remain visible but
low-gravity until corrected-3D or multi-view validation supports stronger use.
Recording-view trunk orientation
(`control.compensation.excessive_trunk_flexion.xy`) uses a temporary feature
gravity of `0.5`, because the current synthetic baseline is too narrow to act as
a final trunk-control rule across squat, hinge, plank, and push-up style
contexts. This keeps trunk compensation visible while preventing the provisional
baseline from dominating the entire control subscore.

Single-axis movement-path diagnostics remain report-only by default except for a
specific future validation study. `spatial.movement_path.axis_path_z.<landmark>` is not
scored by default; it is depth-noise/corrected-3D-hypothesis provenance unless a
validated depth-sensitive score path promotes it. `xy` and `xyz` records are the
score-tunable movement-path variants; their contribution is controlled by
availability, focus tier, depth-dependency gravity, and feature-specific
gravity.

Large canonicalization correction magnitude also does not directly reduce the
movement-quality score. It belongs in data-confidence/provenance unless a later
validated scoring policy says otherwise.

---

## 5. Z-Score Deduction And Dynamic Floor

For each assessed feature in a domain:

```text
σ_eff  = max(σ_baseline, STD_FLOOR_RATIO * |μ_baseline|, STD_ABS_FLOOR)
Z      = (value - μ_baseline) / σ_eff
w_i    = feature_family_weight / number_of_scoring_candidate_features_in_family
g_a    = 1.0 for assessed, domain low-confidence score weight for low_confidence
g_d    = depth_dependency_score_weights[record.depth_dependency]
g_f    = feature_score_weight_overrides.get(feature_id, 1.0)
g_i    = g_a * g_d * g_f
Z_eff  = score_direction_transform(Z, feature_score_direction_overrides)
deduct = scaled_abs_z_deduction(Z_eff, w_i, score_bounds) * g_i
```

`feature_score_direction_overrides` controls whether a matched feature uses the
default two-sided baseline deviation or a one-sided interpretation.

```text
two_sided         penalize |Z|; default for most baseline-matched features
upper_bound_only  penalize max(Z, 0); lower-than-baseline values are not faults
lower_bound_only  penalize min(Z, 0); higher-than-baseline values are not faults
```

For feature ids matched by `quality_rules.range_of_motion_targets`, `Z` is replaced by the
signed target-band deviation:

```text
Z_band = 0                                           if value is inside band
Z_band = (value - minimum_sufficient) / tolerance    if range of motion is insufficient
Z_band = excess_scale * (value - excessive) / tolerance
                                                    if range of motion is excessive
```

The deduction audit marks these rows with `scoring_mode:
minimum_sufficient_band` and records the target bounds.

For feature ids matched by `quality_rules.temporal_tolerance_bands`, `Z` is replaced by
the signed acceptable-duration-band deviation:

```text
Z_band = 0                                           if duration is inside band
Z_band = (duration - minimum_duration_s) / tolerance if duration is too short
Z_band = (duration - maximum_duration_s) / tolerance if duration is too long
```

The deduction audit marks these rows with `scoring_mode:
acceptable_duration_band` and records the target timing bounds.

For feature ids matched by `quality_rules.temporal_variability_bands`, `Z` is
replaced by the signed maximum-variability deviation:

```text
Z_band = 0                              if CV <= maximum_cv
Z_band = (CV - maximum_cv) / tolerance  if CV is too high
```

The deduction audit marks these rows with `scoring_mode:
maximum_sufficient_ceiling` and records the target CV bound.

For feature ids matched by `quality_rules.temporal_phase_profile_bands`, `Z` is
replaced by the signed acceptable-ratio-band deviation:

```text
Z_band = 0                                if ratio is inside band
Z_band = (ratio - minimum_ratio) / tol    if ratio is too low
Z_band = (ratio - maximum_ratio) / tol    if ratio is too high
```

The deduction audit marks these rows with `scoring_mode:
acceptable_ratio_band` and records the target ratio bounds.

If a domain has no configured feature-family weights, the scorer falls back to
the legacy equal-within-domain weight. If a domain has configured family weights
and a record belongs to a zero-weight or unlisted family, that record is reported
in `withheld_features` with `feature_family_weight_zero`; the budget is not
transferred to another family.

The σ floor prevents near-zero baseline variance from producing unstable
deductions.

The dynamic floor is anchored to mandatory range-of-motion achievement:

```text
mandatory_range_of_motion_ratio = mean(min(range_of_motion_i / range_of_motion_baseline_i, 1.0))
floor_dynamic       = score_min + 0.50 * score_span * clamp(mandatory_range_of_motion_ratio)
domain_score        = max(floor_dynamic, raw_domain_score)
```

This keeps a completed movement from collapsing to the minimum score solely
because several compensation or control deductions are present. `floor_applied`
records where the floor affected the domain.

---

## 6. Baseline

```text
File       data/reference/baseline_zscore.json
Generator  scripts/generate_baseline.py
Schema     { exercise_id: { metric_id: {"mean": float, "std": float} } }
```

The baseline is a synthetic engineering reference, not a population norm. A
missing baseline file or missing exercise entry should skip composite score
records with a warning while still returning pass-through biomarker records.

Baseline statistics are tied to the exact exercise definition and feature schema
that generated them. If an authored exercise is promoted or the feature set
changes, the previous baseline entry is invalid until regenerated or explicitly
version-guarded.

Baseline generation is a ⑩ scoring sub-policy, not a separate numbered pipeline
stage. Baseline generation and baseline adoption are separate actions. When
`biomarker.baseline_generation.enabled` and `generate_when_missing` are true, ⑩
may generate a provisional baseline if the selected exercise has no active
baseline entry. This opens the scoring path for smoke testing, but it must not
silently promote the generated baseline into the active research baseline.
Generated baselines should be reviewed through their QC/provenance metadata
before they are used as an active baseline.

Baseline-view compatibility is also a metadata contract, not a pose-derived
inference. For view-sensitive recording-view features, especially movement path and
frontal-plane compensation features, the baseline and target recording should be
matched by declared recording/protocol metadata first:

```text
exercise_id
definition_version
pose_backend
coordinate_mode
feature_schema_version
camera_view_family
camera_height_level
framing_scope
scoring_policy_version
```

Pose-derived body direction is not a primary view-match key. It can be noisy,
exercise-dependent, and hard to separate from subject rotation. Instead it is a
secondary QC signal:

```text
metadata compatible + pose QC plausible       → normal scoring eligibility
metadata compatible + pose QC contradictory   → warning / possible low_confidence
metadata missing                              → view-sensitive features are provisional
metadata incompatible                         → view-sensitive feature families should be withheld or rescored against a compatible baseline
```

This keeps the research scope explicit: the framework does not claim camera
invariance. It produces protocol-conditioned movement-quality proxies under a
declared recording-view contract. Small within-protocol view variation should be
absorbed by reviewed baselines, tolerance rules, feature-family budgets, and
directional scoring rules rather than by a universal view-sensitivity
multiplier.

---

## 7. Exercise Priors And Baseline Tiers

An exercise definition can seed scoring policy, but it cannot by itself produce a
trusted score baseline.

Exercise definitions provide priors:

```text
feature selection         which spatial/temporal/control/biomech metrics matter
eligibility policy        which evidence can be assessed vs withheld
expected movement pattern phase model, support context, primary plane
QC and warning defaults   impossible/implausible ranges, camera-view reliability
```

Exercise definitions do not provide stable score statistics:

```text
baseline mean/std         observed from reference executions
natural variability       estimated across reviewed reps/recordings/subjects
model error distribution  observed under the actual pose backend and pipeline
```

Reference construction is therefore a research task. Users must build or choose
the reference material that defines "expected" movement for the target exercise:

```text
synthetic reference       controlled synthetic or demonstration sequence
reviewed-good examples   researcher-reviewed executions judged suitable for
                         provisional/reviewed engineering reference
custom expected values    exercise-specific values or tolerance bands chosen
                         from pilot experiments, advisor review, or study design
```

The exercise YAML and default scoring config can seed feature selection,
eligibility, and default gravity. They cannot discover normative mean/std values
by themselves. If a user wants exercise-specific or participant-specific scoring,
the required reference recordings, reviewed-good examples, or custom tolerance
values must be collected and documented by the user before the resulting scores
are interpreted beyond smoke-test behavior.

Baseline generation therefore uses tiers.

```text
exercise_prior
    Definition-, literature-, or expert-informed expected ranges. Used for
    feature selection, warnings, availability, and QC. Not a composite-score
    baseline.

provisional_baseline
    Synthetic data or a small reviewed sample set. Used to open the scoring
    pipeline, inspect deductions/withheld evidence, and study sensitivity.
    Scores from this tier must be labeled provisional.

reviewed_baseline
    Multiple reviewed good-quality recordings/reps generated through the same
    exercise definition, pose backend, feature schema, and pipeline policy. This
    is the first tier suitable for study scoring.

locked_baseline
    A reviewed baseline frozen with explicit provenance for a thesis/result
    snapshot. Any exercise-definition, feature-schema, preprocessing, or
    scoring-policy change requires a new baseline version.
```

The current `baseline_zscore.json` schema stores only metric statistics and is
kept as the backward-compatible active metrics store. New generation should write
a generated baseline bundle first, with human-readable metadata separated from
numeric metric statistics:

```text
data/reference/baselines/<baseline_id>/
    baseline.yaml      reviewable metadata, status, and paths
    metrics.json       { metric_id: {"mean": float, "std": float} }
    qc.json            included/withheld metric audit and source provenance
```

`baseline.yaml` should record:

```text
exercise_id
definition_version
baseline_status          provisional | reviewed | locked
source_type              synthetic | reviewed_recordings | mixed
source_mode              current_run | single_file | manifest
pose_backend             mediapipe | yolo | other
coordinate_mode          norm by default
camera_view_family       front | front_oblique | side | rear_oblique | unknown
camera_height_level      H1 | H2 | H3 | unknown
framing_scope            full_body | lower_body | upper_body | unknown
view_match_source        protocol_metadata, not body-direction inference
recording_count
rep_count
included_metric_count
withheld_metric_count
created_from_manifest
created_at
pipeline_version_or_commit
metrics_path
qc_path
active_for_scoring       false for generated baselines until promoted
used_for_current_scoring true only for current-run provisional bootstrap
```

For newly authored user exercises, the recommended path is:

```text
author exercise definition
→ run stage checks and feature/biomech extraction
→ generate a provisional baseline from synthetic or reviewed-good examples
→ inspect score sensitivity, deductions, and withheld evidence
→ promote to reviewed baseline only after enough representative executions exist
```

---

## 8. Baseline Generation Procedure

Baseline generation should be driven by the exercise definition and a reviewed
recording manifest, not by hidden exercise-specific branches.

For the current implementation, this procedure can be executed explicitly through
`scripts/generate_baseline.py` or automatically inside ⑩ when
`biomarker.baseline_generation.enabled` is true. Automatic generation currently
supports `source_mode = current_run`; this is a provisional bootstrap for opening
the scoring path, not a reviewed reference baseline. Reviewed baselines still
require user-supplied reference recordings or a manifest.

Required procedure:

```text
1. Load the canonical exercise definition and protocol files.
2. Read a manifest of baseline-source recordings/reps.
3. Run the same ①-⑨ pipeline used for evaluation.
4. Collect FeatureRecord and BiomechRecord rows.
5. Include records only when their effective scoring gravity is non-zero.
   This means `availability == assessed` records still pass through the
   depth-dependency gravity policy, and low-confidence records are included only
   when both low-confidence and depth-dependency gravity are non-zero.
6. Preserve all low_confidence/not_assessed rows as baseline QC; low-confidence
   rows included in provisional statistics must still be labeled as such.
7. Compute per-metric mean/std with the scoring σ floor.
8. Save a generated baseline bundle (`baseline.yaml`, `metrics.json`, `qc.json`).
9. Optionally mirror the generated metrics into the backward-compatible active
   `baseline_zscore.json` only after explicit promotion or a development-only
   compatibility step.
10. Re-run ⑩ on held-out examples to inspect score scale and deductions.
```

`source_mode = current_run` uses the current pipeline's already-computed
FeatureRecord and BiomechRecord rows as the temporary reference. This mode can
fill default metadata and produce a complete baseline bundle, but it is a
self-reference: it should be labeled `provisional`, used for inspection, and
replaced by synthetic/reference/reviewed-good material before study scoring.

`scripts/generate_baseline.py` is the baseline-generation entry point. The name
is used because it describes the research workflow more accurately than
"compute": the script generates a provisional or reviewed baseline bundle for
inspection instead of silently declaring active scoring statistics.

---

## 9. Audit Fields

`deductions` explains why scored features affected a domain score.
For notebook and UI review, the same entries are also expanded into
`_biomarker_score_items.csv` with one item row per scored feature.

```python
{
    "domain": "spatial",
    "feature_id": "spatial.range_of_motion.xy.left_knee_angle",
    "item_score": 99.73,
    "landmark_ids": ["left_hip", "left_knee", "left_ankle"],
    "evaluation_domain": "recording_view_only",
    "evidence_axes": "xy",
    "value": 85.4,
    "baseline_mean": 92.1,
    "baseline_std": 3.5,
    "z": -1.91,
    "weight": 0.143,
    "feature_family": "range_of_motion",
    "feature_family_weight": 0.65,
    "deduction": 0.273,
}
```

`withheld_features` explains why computed metrics did not affect the score. The
`reasons` field preserves feature availability reasons and may add scoring
policy reasons such as `feature_score_weight_zero` when a feature family is
withheld by explicit score gravity.

```python
{
    "feature_id": "spatial.role_alignment.left_right.range_of_motion_xy.knee",
    "value": 0.31,
    "availability": "low_confidence",
    "view_reliability": "low",
    "camera_zone": "Z3",
    "depth_dependency": "high",
    "model_depth_reliability": "low",
    "landmark_ids": ["left_knee", "right_knee"],
    "evaluation_domain": "dual_domain_compare",
    "evidence_axes": "xyz",
    "reasons": ["view_metric_low"],
}
```

Reporting and visualization should show both lists: one answers "why points were
deducted"; the other answers "why a computed metric was withheld."

---

## 10. Entry Point

```python
from movement.biomarker import derive_biomarkers

biomarker_records, score_records = derive_biomarkers(
    feat_records,
    biomech_records,
    exercise_definition,
    definition_version=exercise_definition.version,
    baseline_path=None,
    domain_weights=None,
    score_bounds=None,
)
```

Behavior:

```text
Always returns pass-through BiomarkerRecord entries.
Returns empty score_records if the baseline file or exercise entry is missing.
Scores each rep_id independently; falls back to sequence-level when needed.
```

---

## 11. Provenance And Clinical Boundary

```text
BiomarkerRecord.source_fields       inherited from FeatureRecord/BiomechRecord
BiomarkerScoreRecord.source_fields  feature_domains, biomechanical_focus,
                                    quality_rules, baseline file, score config
```

The composite score may mirror the structure of functional movement assessments,
but it is not directly comparable to FMS/OAB scores and must not be described as a
clinical diagnosis, patient classification, or clinical significance claim.

---

## 12. Code Mapping

```text
src/movement/biomarker/__init__.py        BiomarkerRecord, derive_biomarkers,
                                          save_biomarker_outputs
src/movement/biomarker/scoring.py         BiomarkerScoreRecord, baseline IO,
                                          scoring, score bounds, weights
src/movement/record_metadata.py           shared record context metadata fields
src/movement/biomarker/interpretation.py  YAML rule loader and InterpretationRecord
data/definitions/interpretation_rules/    per-exercise interpretation rules
scripts/generate_baseline.py              baseline generator
data/reference/baseline_zscore.json       current metric-statistics store
tests/test_biomarker_scoring_weights.py   weights and bounds
tests/test_biomarker_scoring_availability.py availability gravity and withheld audit
tests/test_interpretation.py              rule engine behavior
```

---

## 13. Planned Extensions

- Baseline manifest input and baseline QC metadata output.
- Baseline tier labels: `provisional`, `reviewed`, and `locked`.
- Baseline version guards keyed by exercise definition and feature schema.
- Phase-specific sub-scores after phase-aware feature evidence stabilizes.
- Exercise-specific domain-weight profiles after sensitivity analysis.
- Real cohort baseline support while preserving the synthetic fallback.
- Set-level trend records for within-set fatigue or consistency analysis.
