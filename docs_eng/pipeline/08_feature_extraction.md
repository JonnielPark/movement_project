# 08. Feature Extraction

**Document Version:** 1.0.0  
**Last Updated:** 2026-05-06  
**Korean Sync:** `docs/pipeline/08_feature_extraction.md` is the same-version Korean source.

Pipeline step ⑧. Computes movement-quality features from normalized pose data.
Each feature is returned as a `FeatureRecord` with `(value, unit, source_fields)`
so that downstream biomarker derivation (⑩) can trace provenance.

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
normalized coordinates    <landmark>_norm_x/y/z columns from ⑤
rep boundaries            segment_type == 'rep' + rep_id from ②
phase column (optional)   from ⑥; enables phase-level feature emission
exercise definition       angle_definitions, feature_domains, compensation_candidates
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

Not allowed:
    Branching on exercise_id in feature code  (drive everything from YAML)
    Producing a feature whose source_fields is empty (raises ValueError)
    Mixing kinetic and kinematic phase labels in feature_id suffixes
    Outputs in absolute units (N, kg, m)  — torso_length_ratio / degree only
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

- Kinematic phase labels (Descent / Ascent / Bottom_Hold / Lift / Tap / Return)
  must not be mixed with kinetic labels (eccentric / isometric / concentric)
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

`features_to_dataframe()` flattens `source_fields` into a pipe-joined string for
tabular interchange and preserves the `phase` column.

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

## 10. Relationship to Other Steps

- **⑥ Segmentation** — populates the `phase` column, enabling phase-level
  feature emission. When the column is absent or empty, only rep-level records
  are produced (graceful no-op).
- **⑦ Motion Attribution** — supplies per-rep `attribution_consistent` and
  `attribution_action`. Down-weighting / exclusion of inconsistent reps is
  handled at the biomarker layer rather than by mutating features here.
- **⑨ Biomech Proxy** — consumes the same normalized coordinates and YAML
  fields, but produces `BiomechRecord` (CoM, moment arm). It does **not**
  read FeatureRecord output.
- **⑩ Biomarker Derivation** — converts FeatureRecord into BiomarkerRecord
  pass-through and feeds them into the per-rep composite score.

## 11. Code Mapping

```text
src/movement/features/__init__.py        FeatureRecord, extract_rep_features,
                                         summarize_phase_to_rep,
                                         features_to_dataframe,
                                         PHASE_AWARE_FEATURE_FAMILIES
src/movement/features/spatial.py         compute_rom, compute_symmetry, compute_shape
src/movement/features/temporal.py        compute_tempo, compute_variability
src/movement/features/control.py         compute_stability, compute_compensation
src/movement/features/compensation.py    COMPENSATION_RULES registry, dispatch
```

## 12. Clinical Meaning Reference

Per-exercise feature × clinical meaning mapping:

```text
docs/clinical/per_exercise_mapping.md   markdown table (§5.5/§5.6)
data/definitions/clinical/feature_meanings.yaml     YAML mirror for dashboard tooltips
```

The YAML is keyed `exercise_id → feature_id → {domain, unit, level, phase_suffix, clinical_meaning}`.
Consumed by the planned CDSS dashboard (Task F) for hover-tooltip provenance disclosure.

## 13. Planned Extensions

- Visibility-weighted ROM / symmetry (drop low-visibility frames before max/min)
- Compensation rules: `asymmetric_depth`, `foot_external_rotation_proxy`,
  `tempo_instability` (currently in `_UNIMPLEMENTED`)
- Per-side tempora
