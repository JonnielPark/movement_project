# Per-Exercise Feature x Clinical Meaning Mapping

**Document Version:** 1.1.1
**Last Updated:** 2026-06-29
**Korean Sync:** `docs/clinical/per_exercise_mapping.md` is the same-version Korean source.

This document summarizes implemented feature families and interpretation
boundaries for the four validation exercises. Detailed tooltip text is maintained
in [`data/definitions/clinical/feature_meanings.yaml`](../../data/definitions/clinical/feature_meanings.yaml).

The mapping is descriptive. It does not define diagnosis, treatment effect,
patient classification, or protected scoring text.

---

## 1. Record Levels

```text
rep            one record per repetition
rep / phase    one record per repetition and phase
set            one record spanning all reps in the set
```

Per-rep feature ids are metric ids, not repetition ids. Repetition identity is
stored in the `rep_id` field, so a metric such as
`temporal.tempo.rep_duration` can be compared against the same baseline entry
for rep 1, rep 10, or any other confirmed repetition.

Phase-level variants may be emitted for `spatial.range_of_motion`, `spatial.movement_path`,
`temporal.tempo`, and `control.stability`. Compensation features are rep-level
because their rules use the full rep trajectory.

`spatial.role_alignment.*` is interpreted only after the feature-availability gate in
[07_feature_extraction.md](../pipeline/07_feature_extraction.md). A side-view
monocular rendering is not direct frontal evidence; unsupported symmetry features
must be reported as `low_confidence` or `not_assessed`.

## 2. Feature Families By Exercise

| Exercise | ROM | Symmetry | Shape | Temporal | Stability | Implemented compensation |
|---|---|---|---|---|---|---|
| Squat | hip/knee/ankle | hip/knee/ankle | hip/knee/ankle arc length; descent/ascent ratio | rep tempo, tempo CV | hip_center x/z | knee valgus/varus, trunk flexion, pelvic shift, heel lift, pelvic rotation |
| Lunge | hip/knee/ankle | hip/knee/ankle | hip/knee/ankle arc length; descent/ascent ratio | rep tempo, tempo CV | hip_center x/z | knee valgus, trunk flexion, pelvic shift, heel lift |
| Pike push-up | shoulder/elbow/hip | shoulder/elbow/hip | shoulder/elbow/wrist arc length; descent/ascent ratio | rep tempo, tempo CV | hip_center x/z | none implemented yet |
| Plank shoulder tap | shoulder/elbow/hip | shoulder/elbow/hip | wrist/shoulder arc length | rep tempo, tempo CV | hip_center x/z | pelvic rotation, lateral pelvic shift |

Common units:

```text
degree                  joint-angle ROM and trunk-angle features
torso_length_ratio      normalized distance/trajectory features
torso_length_ratio_per_rep load-shift trend in ⑧
second                  rep duration
dimensionless_cv        coefficient of variation / symmetry index
dimensionless           ratios
```

## 3. Implemented Compensation Features

| Exercise | Feature ids | Interpretation boundary |
|---|---|---|
| Squat | `control.compensation.knee_valgus.xy.left/right` | Recording-view knee deviation proxy; requires view support and foot/hip/ankle landmark reliability. |
| Squat | `control.compensation.knee_varus.xy.left/right` | Recording-view lateral knee deviation proxy; sensitive to stance width and view. |
| Squat | `control.compensation.excessive_trunk_flexion.xy` | Recording-view trunk-lean proxy; relative load-strategy interpretation, not a spinal diagnosis. |
| Squat | `control.compensation.excessive_trunk_flexion.xyz` | Depth-mixed trunk-lean proxy; low-weight comparative evidence. |
| Squat | `control.compensation.lateral_pelvic_shift.xy` | Weight-shift proxy from pelvis displacement; diagnostic when hip-centered normalization removes the measured motion. |
| Squat | `control.compensation.heel_lift.xy.left/right` | Recording-view heel-elevation proxy; contact and landmark confidence can limit confidence. |
| Squat | `control.compensation.pelvis_rotation.xyz` | Hip-depth asymmetry proxy; depth-sensitive in monocular data. |
| Lunge | `control.compensation.knee_valgus.xy.left/right` | Forward-leg or side-specific knee deviation; must preserve active/forward-leg context. |
| Lunge | `control.compensation.excessive_trunk_flexion.xy` | Forward trunk-lean proxy in split stance. |
| Lunge | `control.compensation.lateral_pelvic_shift.xy` | Pelvic-control proxy; view and hip confidence dependent. |
| Lunge | `control.compensation.heel_lift.xy.left/right` | Must be interpreted with forward/trailing-leg role. |
| Plank shoulder tap | `control.compensation.pelvis_rotation.xyz` | Anti-rotation proxy from hip-depth asymmetry. |
| Plank shoulder tap | `control.compensation.lateral_pelvic_shift.xy` | Lateral weight-shift proxy during one-hand support. |

Pike push-up compensation patterns are currently YAML patterns only. They are
not listed as implemented until corresponding rules are added to
`COMPENSATION_RULES`.

## 4. Pending Pattern Handling

Exercise YAML may contain patterns without implemented rules. Runtime behavior:

```text
matching rule in COMPENSATION_RULES        feature may be emitted
no matching rule                           UserWarning; omitted from this mapping
```

Pending patterns remain research notes, not hidden score components.

## 5. Code And Data Mapping

```text
src/movement/features/
data/definitions/clinical/feature_meanings.yaml
docs_eng/pipeline/07_feature_extraction.md
docs_eng/pipeline/09_biomarker_scoring.md
```

When a feature family, unit, or interpretation boundary changes, update
`docs_eng/` first, then synchronize `docs/`, then update YAML/code.
