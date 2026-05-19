# 08. Feature Extraction

**Document Version:** 1.1.0
**Last Updated:** 2026-05-16
**Korean Sync:** `docs/pipeline/08_feature_extraction.md` is the same-version Korean source.

Pipeline step ⑧. Computes movement-quality features from normalized pose data.
Each feature is returned as a `FeatureRecord` with `(value, unit, source_fields)`
plus view-reliability and availability metadata so that downstream biomarker
derivation (⑩) can trace provenance without turning observation limits into
movement-quality penalties.

Beyond raw joint angles, the design enforces a strict three-domain decomposition
(**spatial / temporal / control**) so that every metric maps cleanly to a clinical
reasoning category. Corresponds to dissertation §5.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ ⑧ Feature Extraction         ← this step
→ ⑨ Biomech Proxy
→ ⑩ Biomarker Derivation
```

Required inputs:
```text
normalized coordinates        <landmark>_norm_x/y/z columns from ⑤
rep boundaries                segment_type == 'rep' + rep_id from ②
phase column (optional)       from ⑥; enables phase-level feature emission
exercise definition           angle_definitions, feature_domains,
                              compensation_candidates, view_metric_reliability
filming provenance            camera_zone, camera_height_level when available
preprocessing reliability      feature_availability_summary, far-side jitter,
                              swap-risk, and visibility context when available
```

Does not modify coordinates. Adds `FeatureRecord` rows only; the pose dataframe
is untouched.

## 2. Design Principle

```text
Allowed:
    Per-joint included angles from angle_definitions triplets
    Per-rep aggregation (min, max, range, std, arc length)
    Per-(rep × phase) aggregation when ⑥ phase column is populated
    Compensation candidate computation from COMPENSATION_RULES registry
    Provenance recording in source_fields
    Reporting computed values separately from scoring eligibility

Not allowed:
    Branching on exercise_id in feature code  (drive everything from YAML)
    Producing a feature whose source_fields is empty (raises ValueError)
    Mixing kinetic and kinematic phase labels in feature_id suffixes
    Outputs in absolute units (N, kg, m)  — torso_length_ratio / degree only
    Penalizing a feature only because the camera view cannot support that metric
```

## 3. Three Feature Domains

Three fixed domains are activated per exercise via `feature_domains` in the
exercise YAML. Domain membership is encoded in the `feature_id` prefix
(`spatial.*`, `temporal.*`, `control.*`).

### 3-1. Spatial Features

Reflect mobility limitation and musculoskeletal asymmetry.

```text
spatial.rom.<joint>             max − min included angle per rep        (degree)
spatial.symmetry.<joint>        | ROM_left − ROM_right | / mean         (dimensionless_cv)
spatial.shape.arc_length.<lm>   primary-joint trajectory length         (torso_length_ratio)
```

#### View-Dependent Symmetry Availability

`spatial.symmetry.*` is not interpreted as a valid movement-quality penalty every
time a left/right ROM difference can be computed. For monocular recordings, a
bilateral symmetry feature must first pass an availability gate. This is especially
important for side-view squat recordings, where rotating the monocular 3D skeleton
into a frontal view can expose depth-estimation artifacts that were not directly
observed by the camera.

The intended availability states are:

```text
assessed
    Both sides have sufficient landmark visibility/coverage, plausible segment
    lengths, low left/right swap risk, and a filming view that supports the
    requested left-right interpretation.

low_confidence
    The feature can be computed, but visibility, far-side jitter, depth-dependent
    canonicalization correction, or viewpoint mismatch makes the result suitable
    only as an interpretation note.

not_assessed
    The computed value would mainly reflect observation artifact rather than
    interpretable movement asymmetry. It should not enter the movement-quality
    score.
```

For a side-view or near-side-view squat, primary scoring should rely on sagittal
and centerline features such as descent depth, hip/knee/ankle ROM, trunk lean,
heel lift, hip-center trajectory stability, tempo, and smoothness. Left/right
symmetry should be emitted only when both sides pass the availability gate. If
the side-view animation appears stable but the rotated frontal rendering shows
large left/right imbalance, treat that pattern as a depth-inference limitation
unless an actual frontal or front-oblique view confirms the asymmetry.

The same rule generalizes to `view_metric_reliability` in the exercise definition.
Feature extraction may compute a feature while reporting view reliability separately:

```text
computed_value      numeric FeatureRecord value, when source fields exist
view_reliability   high | moderate | low | not_assessed
availability       assessed | low_confidence | not_assessed
```

For bilateral symmetric exercises, the reliability map is mainly organized by
frontal-plane versus sagittal-plane visibility. For unilateral or alternating
exercises, it is organized by role: `forward_leg`, `trailing_leg`, `active_side`,
and `support_side`. A lunge filmed from the side can therefore be high-confidence
for forward-leg sagittal ROM and rear-limb extension while low-confidence for
knee valgus or pelvis drop. A frontal lunge can show step width and pelvis drop
well while making anterior knee travel and rear-hip extension low-confidence.

#### Feature Availability Resolver Contract

Task A introduces a small resolver between raw feature computation and ⑩ scoring.
The resolver does not change numeric feature values. It annotates each
`FeatureRecord` with the best available observation context:

```text
view_reliability
    Reliability prior read from exercise_definition.view_metric_reliability for
    the active camera_zone and metric family. Allowed values are
    high | moderate | low | not_assessed | unknown.

availability
    Final scoring eligibility after combining view_reliability with landmark
    visibility, preprocessing feature_availability_summary, segment-length
    plausibility, and left/right swap risk.

availability_reasons
    Short machine-readable reasons such as
    view_metric_low, view_metric_not_assessed, far_side_jitter_high,
    bilateral_landmark_coverage_low, swap_risk_high, or camera_zone_unknown.

camera_zone
    Recording-level camera zone used for the decision. If missing, use unknown.

role_context
    Optional role metadata for unilateral/alternating exercises, for example
    {"active_side": "left", "support_side": "right", "near_side": "left"}.
```

The resolver uses feature-family mapping rather than hard-coded exercise IDs.
The initial required mapping is:

```text
spatial.symmetry.*                    → bilateral_symmetry
spatial.rom.*                         → sagittal_rom when the exercise primary plane is sagittal
control.compensation.knee_valgus      → frontal_alignment
control.compensation.knee_varus       → frontal_alignment
control.compensation.lateral_pelvic_shift → frontal_alignment | lateral_shift
control.compensation.heel_lift        → heel_lift | sagittal_rom
control.compensation.pelvis_rotation  → transverse_rotation | pelvis_rotation
temporal.tempo.*                      → tempo
temporal.variability.*                → tempo | smoothness
control.stability.*                   → centerline_stability | hip_center_stability
```

When several aliases exist, the resolver should select the first key present in
the active exercise's `view_metric_reliability.zones.<camera_zone>` map and record
the selected key in `source_fields` or `availability_reasons`.

Default availability resolution:

```text
view_reliability high/moderate + sufficient landmark/preprocessing gates
    → availability = assessed

view_reliability low
    → availability = low_confidence by default; report numeric value but do not
      send it to composite scoring unless a later policy explicitly overrides it.

view_reliability not_assessed
    → availability = not_assessed; report only as an omitted metric/provenance note.

camera_zone unknown or missing view_metric_reliability entry
    → availability = low_confidence unless all non-view gates are also missing,
      in which case use not_assessed.

preprocessing gate failure for bilateral interpretation
    → downgrade assessed to low_confidence or not_assessed according to the
      reported reason.
```

For side-view squat specifically, sagittal and centerline families are the first
scoring candidates: descent depth, hip/knee/ankle ROM, trunk lean, heel lift,
hip-center stability, tempo, and smoothness. Depth-derived bilateral symmetry
from a rotated monocular frontal rendering must be `low_confidence` or
`not_assessed` unless an actual frontal or front-oblique view supports the same
finding.

### 3-2. Temporal Features

Capture pain-avoidance hesitation and timing-control deficits.

```text
temporal.tempo.rep_<n>          rep duration                            (second)
temporal.variability.tempo_cv   inter-rep tempo CV                      (dimensionless_cv)
```

### 3-3. Control Features

Quantify postural stability and substitution by adjacent joints.

```text
control.stability.hip_center_x_std   pelvis lateral sway                 (torso_length_ratio)
control.stability.hip_center_z_std   pelvis vertical sway                (torso_length_ratio)
control.compensation.<candidate>     rule-registry compensation metric  (torso_length_ratio | degree)
```

The `control` domain is intentionally not abbreviated to "stability"
(see [`terminology.md`](../terminology.md) §3).

## 4. Compensation Rule Registry

`compensation_candidates` from the exercise YAML are dispatched to the
`COMPENSATION_RULES` registry in `features/compensation.py`. Unregistered
candidates emit a `UserWarning` and are skipped so that the YAML can list
aspirational candidates without crashing the pipeline.

Registered rules:

| Candidate | Plane / Axis | Output |
|---|---|---|
| `knee_valgus`            | frontal (x-z), per side  | peak medial knee deviation from hip-ankle line |
| `knee_varus`             | frontal (x-z), per side  | peak lateral knee deviation |
| `lateral_pelvic_shift`   | x-axis                   | peak pelvis-center lateral displacement from rep mean |
| `excessive_trunk_flexion`| z-axis                   | peak trunk lean from vertical (degree) |
| `heel_lift`              | z-axis, per side         | peak heel elevation above rep minimum |
| `pelvis_rotation`        | y-axis (depth)           | peak left-right hip depth asymmetry (transverse proxy) |

Each rule returns one or more `FeatureRecord` with `feature_id` pattern
`control.compensation.<candidate>[.<side>]`.

## 5. Phase-Aware Feature Families

When ⑥ Segmentation populates the `phase` column, features in
`PHASE_AWARE_FEATURE_FAMILIES` are emitted at both rep-level (`phase=None`)
and phase-level (`phase='Descent'`, etc.).

```text
PHASE_AWARE_FEATURE_FAMILIES = {
    "spatial.rom",
    "spatial.shape",
    "temporal.tempo",
    "control.stability",
}
```

Rules:
```text
- Phase-level feature_id appends a lowercased phase suffix
  e.g. spatial.rom.left_knee  →  spatial.rom.left_knee.descent

- Phase-level FeatureRecord.source_fields includes 'segmentation.*' entries
  (reference_landmark, reference_axis, split_logic)

- control.compensation is rep-level only — candidates span phase boundaries
  and would lose meaning if split

- Kinematic phase labels (Descent / Ascent / Turnaround_Hold / Lift / Tap / Return)
  must not be mixed with kinetic labels (eccentric / isometric / concentric)
```

A2 verification requirement:

```text
Every phase-level FeatureRecord emitted from a phase-labelled rep must include:
    phase                         non-null kinematic phase label
    feature_id suffix             lowercased phase label
    source_fields                 original feature provenance +
                                  phase_segmentation.reference_landmark,
                                  phase_segmentation.reference_axis,
                                  phase_segmentation.split_logic
```

## 6. Hierarchical Summary

`summarize_phase_to_rep()` derives rep-level summary metrics from the
phase-level records (dissertation §5.5).

```text
spatial.phase_rom_ratio.descent_ascent
    Ratio of mean Descent ROM to mean Ascent ROM per rep.
    Values > 1 → descent excursion exceeds ascent (e.g. uncontrolled lowering).
```

The summarizer is purely additive: input records are not modified, and the
returned list contains only the new summary `FeatureRecord` entries.

## 7. Output: FeatureRecord

```python
@dataclass
class FeatureRecord:
    feature_id:    str            # e.g. 'spatial.rom.left_knee.descent'
    exercise_id:   str
    rep_id:        int | None     # None = sequence-level
    value:         float
    unit:          str            # 'degree' | 'torso_length_ratio'
                                  # | 'second' | 'dimensionless_cv' | 'dimensionless'
    source_fields: list[str]      # required; raises ValueError if empty
    note:          str | None
    phase:         str | None     # None = rep-level; 'Descent' etc. = phase-level
    view_reliability: str = "unknown"      # high | moderate | low | not_assessed | unknown
    availability: str = "assessed"         # assessed | low_confidence | not_assessed
    availability_reasons: list[str] = []
    camera_zone: str | None = None
    role_context: dict[str, str] | None = None
```

Per-exercise mapping of which features are produced:

```text
feature_domains.spatial   = [rom, symmetry, shape, ...]   → spatial.* features
feature_domains.temporal  = [tempo, variability, ...]     → temporal.* features
feature_domains.control   = [stability, compensation, ...] → control.* features
compensation_candidates   = [knee_valgus, ...]            → control.compensation.* features
```

## 8. Entry Point

```python
from movement.features import (
    extract_rep_features,
    summarize_phase_to_rep,
    features_to_dataframe,
)

records = extract_rep_features(df, exercise_definition)
records += summarize_phase_to_rep(records)
feat_df = features_to_dataframe(records)
```

`features_to_dataframe()` flattens `source_fields` and `availability_reasons` into
pipe-joined strings for tabular interchange, preserves the `phase` column, and
serializes `role_context` as a JSON-compatible object or string depending on the
output format.

## 9. Configuration

Activation is YAML-driven only; no Python code branching per exercise:

```yaml
feature_domains:
  spatial: [rom, symmetry, shape, depth_proxy, alignment]
  temporal: [tempo, rep_duration, eccentric_duration, isometric_duration, concentric_duration, timing_ratio]
  control: [stability, compensation, com_stability, pelvis_stability, lateral_shift]
  biomechanical_proxy: [com_displacement, moment_arm_proxy, relative_joint_load_proxy]

compensation_candidates:
  - knee_valgus
  - excessive_trunk_flexion
  - lateral_pelvic_shift
```

`biomechanical_proxy` items are consumed by ⑨ Biomech Proxy, not ⑧.

## 10. Feature Registry Coverage Audit

A3 adds an explicit coverage report so YAML can safely contain aspirational
feature vocabulary without silently implying that every item is already scored.

```python
@dataclass
class FeatureRegistryCoverageReport:
    exercise_id: str
    connected_feature_domain_entries: dict[str, list[str]]
    unsupported_feature_domain_entries: list[dict]
    external_step_feature_domain_entries: list[dict]
    implemented_compensation_candidates: list[str]
    unimplemented_compensation_candidates: list[dict]
    compensation_candidate_availability: list[dict]
```

Coverage rules:

```text
feature_domains.spatial / temporal / control
    Report each YAML entry as connected when it maps to an implemented extractor
    or documented alias. Report it as unsupported when no extractor exists.

feature_domains.biomechanical_proxy
    Do not treat as missing ⑧ extractors. These entries are routed to ⑨
    Biomech Proxy and appear in external_step_feature_domain_entries.

compensation_candidates
    Report candidates found in COMPENSATION_RULES as implemented. Report all
    declared-but-unregistered candidates as unimplemented, with reason
    declared_unimplemented or no_rule_registered.
```

This report is diagnostic/provenance output. Unsupported entries do not crash
feature extraction and are not automatically promoted to scoring factors.

The per-exercise compensation-candidate availability matrix is the canonical
current-state view for candidate implementation status; it does not create new
metrics by itself.

```text
candidate                    YAML candidate name
availability_status          implemented_rule |
                             declared_unimplemented |
                             deferred_feature_design |
                             no_rule_registered
emits_feature                true when COMPENSATION_RULES has a dispatch rule
report_reason                implemented_rule | declared_unimplemented |
                             deferred_feature_design | no_rule_registered
source_fields                provenance fields such as
                             compensation_candidates.<candidate>
                             feature_domains.control.compensation
next_action                  concise implementation or documentation action
```

Status meanings:

```text
implemented_rule
    A rule exists in COMPENSATION_RULES and can emit control.compensation.* records
    when the required landmarks are present.

declared_unimplemented
    The candidate is accepted as YAML vocabulary and intentionally tracked in
    `_UNIMPLEMENTED`, but no feature rule is active yet.

deferred_feature_design
    The candidate is meaningful for the exercise but requires a separate feature
    definition, visibility policy, role-based side logic, or validation fixture
    before it should become a score factor.

no_rule_registered
    The candidate is declared in YAML but has not yet been assigned to one of the
    explicit statuses above. It must stay visible in reports.
```

This matrix keeps candidates visible in reports even when squat or pike push-up
candidates have not yet been promoted into scoring rules.

## 11. Analysis-Disrupting Pattern Detectability Audit

This step adds a second diagnostic report for
`performance_protocol.analysis_disrupting_patterns`. This audit separates
pose-detectable scoring candidates from protocol-control or interpretation-limit
factors, so analysis-disrupting patterns are not silently promoted to automatic
data exclusion or automatic scoring.

```python
@dataclass
class AnalysisDisruptingPatternDetectabilityReport:
    exercise_id: str
    pose_detectable_scoring_candidates: list[dict]
    acquisition_control_factors: list[dict]
    interpretation_limitation_factors: list[dict]
    unknown_patterns: list[dict]
    all_patterns: list[dict]
```

Each item in `all_patterns` reports:

```text
pattern                       YAML pattern name
classification                pose_detectable_scoring_candidate |
                              acquisition_control_factor |
                              interpretation_limitation_factor |
                              unknown
required_landmarks            landmarks needed for a pose-based read
view_sensitivity              low | medium | high
visibility_dependency         low | medium | high
annotation_fallback           annotation or metadata fallback, if needed
linked_compensation_candidates compensation candidates this pattern may map to
linked_feature_domain_entries feature-domain entries this pattern may map to
source_fields                 provenance fields behind the classification
basis                         short rationale for the classification
```

Rules:

```text
pose_detectable_scoring_candidate
    May be connected to future FeatureRecord/BiomarkerRecord output when an
    implemented feature rule and provenance test exist. It is not scored by the
    audit itself.

acquisition_control_factor
    Remains a recording/protocol warning. It can appear in reports and captions
    but should not directly change the movement-quality score.

interpretation_limitation_factor
    Remains a confidence or interpretation note when pose data alone cannot prove
    the underlying event.

unknown
    Must stay warning/provenance only until explicitly classified.
```

The report may be emitted beside `feature_registry_coverage` when ⑧ runs. It is
safe for downstream reporting and ⑫ simulation planning, but it does not mutate
pose coordinates and does not exclude repetitions.

## 12. Relationship to Other Steps

- **⑥ Segmentation** — populates the `phase` column, enabling phase-level
  feature emission. When the column is absent or empty, only rep-level records
  are produced (graceful no-op).
- **⑦ Motion Attribution** — supplies per-rep `attribution_consistent` and
  `attribution_action`. Down-weighting / exclusion of inconsistent reps is
  handled at the biomarker layer rather than by mutating features here.
- **⑨ Biomech Proxy** — consumes the same normalized coordinates and
  `feature_domains.biomechanical_proxy` / `biomechanical_focus` fields, but
  produces `BiomechRecord` (CoM, moment arm). It does **not** read
  FeatureRecord output.
- **⑩ Biomarker Derivation** — converts FeatureRecord into BiomarkerRecord
  pass-through and feeds them into the per-rep composite score.
- **⑫ In-Silico Simulation** — may later use pose-detectable analysis-disrupting
  patterns as named perturbation candidates. Control and interpretation-limit
  factors remain reporting notes unless separate injectors are designed.

## 13. Code Mapping

```text
src/movement/features/__init__.py        FeatureRecord, extract_rep_features,
                                         FeatureRegistryCoverageReport,
                                         audit_feature_registry,
                                         AnalysisDisruptingPatternDetectabilityReport,
                                         audit_analysis_disrupting_patterns,
                                         summarize_phase_to_rep,
                                         features_to_dataframe,
                                         PHASE_AWARE_FEATURE_FAMILIES
src/movement/features/spatial.py         compute_rom, compute_symmetry, compute_shape
src/movement/features/temporal.py        compute_tempo, compute_variability
src/movement/features/control.py         compute_stability, compute_compensation
src/movement/features/compensation.py    COMPENSATION_RULES registry, dispatch
tests/test_features_phase_grouping.py    phase-level feature emission and provenance
tests/test_feature_registry_coverage.py  YAML feature-domain, compensation coverage,
                                         and candidate availability
tests/test_analysis_disrupting_patterns.py
                                         analysis-disrupting pattern detectability coverage
tests/test_feature_provenance.py          missing source_fields policy
tests/test_feature_view_reliability.py    camera-zone reliability and availability metadata
```

## 14. Clinical Meaning Reference

Per-exercise feature × clinical meaning mapping:

```text
docs/clinical/per_exercise_mapping.md   markdown table (§5.5/§5.6)
data/definitions/clinical/feature_meanings.yaml     YAML mirror for dashboard tooltips
```

The YAML is keyed `exercise_id → feature_id → {domain, unit, level, phase_suffix, clinical_meaning}`.
Consumed by the planned CDSS dashboard (Task F) for hover-tooltip provenance disclosure.

## 15. Planned Extensions

- Visibility-weighted ROM / symmetry (drop low-visibility frames before max/min)
- Compensation rules: `asymmetric_depth`, `foot_external_rotation_proxy`,
  `tempo_instability` (currently in `_UNIMPLEMENTED`)
- Per-side tempora
