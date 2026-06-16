# 09. Feature Extraction

**Document Version:** 1.2.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/09_feature_extraction.md` is the same-version Korean source.

Pipeline step ⑨ computes movement-quality features from normalized pose data. It
does not modify pose coordinates. Every output is a `FeatureRecord` with numeric
value, unit, `source_fields`, and availability/reliability metadata for ⑪
Biomarker Derivation.

---

## 1. Pipeline Position

```text
⑤ Normalization → ⑥ Canonicalization → ⑦ Segmentation → ⑧ Motion Attribution
→ ⑨ Feature Extraction     ← this step
→ ⑩ Biomech Proxy → ⑪ Biomarker Derivation
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
```

---

## 3. Feature Families

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

`feature_domains.biomechanical_proxy` is routed to ⑩ Biomech Proxy, not consumed
as a missing ⑨ extractor.

---

## 4. Availability And View Reliability

Feature extraction may compute a numeric value even when the camera view or pose
model does not support scoring that value. Therefore `FeatureRecord.availability`
is the scoring gate for ⑪.

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
swap or far-side risk         from ④ Preprocessing and ⑧ Motion Attribution
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

## 5. Phase-Aware Features

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

## 6. Output Contract

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

## 7. Audits

⑨ may emit diagnostic audits beside the feature records.

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

## 8. Entry Point

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

## 9. Relationship To Other Steps

- ⑦ Segmentation provides `rep_id` and optional `phase`; missing phase labels
  produce rep-level features only.
- ⑧ Motion Attribution provides side/consistency context for role-aware features.
- ⑩ Biomech Proxy consumes the same normalized coordinates but emits
  `BiomechRecord`, not `FeatureRecord`.
- ⑪ Biomarker Derivation wraps all features as pass-through biomarkers and uses
  only `availability == assessed` features for composite scoring.
- ⑬ Simulation may later use pose-detectable audit entries as perturbation
  candidates.

---

## 11. Code Mapping

```text
src/movement/features/__init__.py        FeatureRecord, extract_rep_features,
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
```

---

## 12. Planned Extensions

- More compensation rules after source fields, visibility policy, and tests exist.
- Per-feature landmark coverage instead of coarse preprocessing summaries.
- Role-aware feature families for lunge and plank shoulder tap.
- Reporting views that show computed-but-withheld features beside scored features.
