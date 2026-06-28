# 08. Feature Extraction

**Document Version:** 1.2.4
**Last Updated:** 2026-06-27
**Korean Sync:** `docs/pipeline/08_feature_extraction.md` is the same-version Korean source.

Pipeline step ⑧ computes movement-quality features from normalized pose data. It
does not modify pose coordinates. Every output is a `FeatureRecord` with numeric
value, unit, `source_fields`, and availability/reliability metadata for ⑩
Biomarker Derivation.

---

## 1. Pipeline Position

```text
⑤ Normalization → ⑥ Canonicalization → ⑦ Segmentation
→ ⑧ Feature Extraction     ← this step
→ ⑨ Biomech Proxy → ⑩ Biomarker Derivation
```

Required inputs:

```text
<landmark>_norm_x/y/z       normalized coordinates
rep_id                      confirmed repetition labels
phase                       optional phase labels from ⑦
exercise_definition         feature_domains, angle_definitions,
                            compensation_candidates, view_metric_reliability
recording provenance        camera_zone, camera_height_level when available
preprocessing context       visibility, swap risk, far-side jitter, availability hooks
role context settings       laterality, execution pattern, side sequence
```

---

## 2. Design Contract

Allowed:

```text
Per-joint included angles from YAML angle_definitions
Per-rep and per-phase aggregation
Compensation candidates dispatched from a registry
Feature availability/reliability metadata
Provenance through source_fields
Units limited to degree, second, dimensionless, dimensionless_cv, torso_length_ratio
```

Not allowed:

```text
Branching on exercise_id in feature code
FeatureRecord without source_fields
Absolute force/torque/length output
Turning camera-view limitations directly into movement-quality penalties
Mixing kinematic phase labels with kinetic phase names in feature IDs
Using active-side role context for bilateral symmetric exercises
```

---

## 3. Feature Context Resolution

Feature Extraction owns side-role context resolution. This is not a score by
itself and no longer exists as a standalone pipeline stage. It only tells feature
families how to interpret side roles, confidence, and provenance.

The first context substep of ⑧ is:

```text
resolve_feature_context(df, exercise_definition, role_context_report=None)
apply_feature_context(records, feature_context)
```

Conceptual output:

```text
feature_context:
  laterality
  role_mode                 bilateral_symmetry | active_side | unavailable
  role_context              active_side, support_side, forward_leg, trailing_leg, etc.
  role_confidence           assessed | low_confidence | not_assessed
  context_reasons           provenance strings
```

Policy:

```text
bilateral_symmetric
    Do not run active-side role detection. Provide bilateral symmetry / side-bias
    context for feature families that compare left and right movement quality.

alternating / unilateral_left / unilateral_right
    Resolve side-role context inside ⑧ from the segmented dataframe,
    performance_protocol.side_sequence, and annotation context.

unilateral_unspecified / bilateral_asymmetric / unsupported
    Do not create strong side roles. Emit conditional or not-yet-supported
    provenance and let feature availability decide whether values are assessed.
```

This context-resolution substep must not modify coordinates, relabel reps or
phases, create scores, or branch on `exercise_id`.

Integration policy:

```text
⑧ owns feature-facing interpretation
    Resolve side-role context inside Feature Extraction, attach role_context only
    where a feature family declares it useful, and keep confidence/provenance
    separate from numeric feature values.

public notebook review
    Verify side-role context and feature records together in
    `27_feature_extraction_test.ipynb`.
```

Context application is intentionally narrow:

```text
spatial.symmetry.*
    Attach bilateral symmetry context when role_mode == bilateral_symmetry.
    This makes left/right comparison provenance explicit but does not change
    the numeric symmetry value or its low-confidence depth gate.

alternating / unilateral active-side records
    Attach active-side context only when side-role evidence is available.
    Ambiguous or missing context remains provenance, not a strong side role.

all other records
    Preserve the original role_context unless a future feature family declares
    a context requirement.
```

---

## 4. Feature Families

Domain membership is encoded in the `feature_id` prefix.

```text
spatial.*
    ROM, left/right symmetry, trajectory shape, alignment/depth proxies.

temporal.*
    Rep duration, phase duration, tempo variability, rhythm/smoothness proxies.

control.*
    Hip-center stability and compensation candidates such as knee_valgus,
    knee_varus, lateral_pelvic_shift, excessive_trunk_flexion, heel_lift,
    pelvis_rotation.
```

`feature_domains.biomechanical_proxy` is routed to ⑨ Biomech Proxy, not consumed
as a missing ⑧ extractor.

---

## 5. Availability And View Reliability

Feature extraction may compute a numeric value even when the camera view or pose
model does not support scoring that value. Therefore `FeatureRecord.availability`
is the scoring gate for ⑩.

```text
assessed
    Eligible for composite scoring if a baseline exists.

low_confidence
    Numeric value can be reported, but is withheld from composite scoring by
    default.

not_assessed
    Do not use for scoring; report only as unavailable/provenance.
```

The resolver combines:

```text
view_reliability             exercise_definition.view_metric_reliability
landmark_quality             visibility / coverage / preprocessing context
depth_dependency             none | low | moderate | high | unknown
model_depth_reliability      high | moderate | low | unknown
swap or far-side risk         from ④ Preprocessing and ⑧ side-role context
camera_zone                  from annotation or recording metadata
role_context                 active/support/near/far side when available
```

For side-view or near-side-view squat recordings, sagittal and centerline
features may remain assessed when their gates pass. Depth-sensitive bilateral
symmetry from a rotated monocular skeleton should be `low_confidence` or
`not_assessed` unless frontal/front-oblique evidence supports the interpretation.

For unilateral or alternating exercises, reliability should use role labels such
as `forward_leg`, `trailing_leg`, `active_side`, and `support_side` rather than
raw anatomical left/right alone.

---

## 6. Phase-Aware Features

When ⑦ provides a `phase` column, these families may emit both rep-level and
phase-level records:

```text
spatial.rom
spatial.shape
temporal.tempo
control.stability
```

Rules:

```text
Rep-level record      phase = None
Phase-level record    phase = "Descent" etc.; feature_id gets a lower-case suffix
source_fields         include phase_segmentation provenance
control.compensation  rep-level only unless a separate phase-specific rule is defined
```

`summarize_phase_to_rep()` may add derived rep-level summaries, such as
descent/ascent ROM ratios. It is additive and must not mutate input records.

---

## 7. Output Contract

```python
@dataclass
class FeatureRecord:
    feature_id: str
    exercise_id: str
    rep_id: int | None
    value: float
    unit: str
    source_fields: list[str]
    note: str | None = None
    phase: str | None = None
    view_reliability: str = "unknown"
    availability: str = "assessed"
    availability_reasons: list[str] = field(default_factory=list)
    camera_zone: str | None = None
    role_context: dict[str, str] | None = None
    depth_dependency: str = "unknown"
    model_depth_reliability: str = "unknown"
    landmark_quality: str = "unknown"
```

`features_to_dataframe()` flattens record lists for tabular output while
preserving phase, availability, camera-zone, and provenance fields.

---

## 8. Audits

⑧ may emit diagnostic audits beside the feature records.

```text
Feature registry coverage
    Reports which YAML feature_domain entries and compensation candidates are
    implemented, routed to another step, unsupported, or declared but deferred.

Analysis-disrupting pattern detectability
    Classifies performance_protocol.analysis_disrupting_patterns as
    pose_detectable_scoring_candidate, acquisition_control_factor,
    interpretation_limitation_factor, or unknown.
```

Audits are provenance/reporting outputs. They do not mutate coordinates, exclude
repetitions, or create scores by themselves.

---

## 9. Entry Point

```python
from movement.features import (
    extract_rep_features,
    features_to_dataframe,
    summarize_phase_to_rep,
)

records = extract_rep_features(df, exercise_definition)
records += summarize_phase_to_rep(records)
feat_df = features_to_dataframe(records)
```

---

## 10. Relationship To Other Steps

- ⑦ Segmentation provides `rep_id` and optional `phase`; missing phase labels
  produce rep-level features only.
- Side-role context is resolved inside ⑧, then attached only to role-aware
  feature records. The public stage-check path reviews this context in
  `27_feature_extraction_test.ipynb`.
- ⑨ Biomech Proxy consumes the same normalized coordinates but emits
  `BiomechRecord`, not `FeatureRecord`.
- ⑩ Biomarker Derivation wraps all features as pass-through biomarkers and uses
  only `availability == assessed` features for composite scoring.
- ⑫ Simulation may later use pose-detectable audit entries as perturbation
  candidates.

---

## 11. Code Mapping

```text
src/movement/features/__init__.py        FeatureRecord, extract_rep_features,
                                         FeatureContext, resolve_feature_context,
                                         apply_feature_context,
                                         audits, summarize_phase_to_rep,
                                         features_to_dataframe
src/movement/features/spatial.py         ROM, symmetry, shape
src/movement/features/temporal.py        tempo, variability
src/movement/features/control.py         stability, compensation
src/movement/features/compensation.py    COMPENSATION_RULES registry
tests/test_feature_view_reliability.py   availability metadata
tests/test_feature_registry_coverage.py  feature/compensation coverage audit
tests/test_analysis_disrupting_patterns.py detectability audit
tests/test_features_phase_grouping.py    phase-level feature behavior
tests/test_feature_context_resolution.py feature-context resolution/application
```

---

## 12. Planned Extensions

- Review alternating/unilateral samples before expanding side-role context from
  bilateral provenance to active/support-side feature families.
- More compensation rules after source fields, visibility policy, and tests exist.
- Per-feature landmark coverage instead of coarse preprocessing summaries.
- Role-aware feature families for lunge and plank shoulder tap.
- Reporting views that show computed-but-withheld features beside scored features.
