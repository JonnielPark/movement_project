# Per-Exercise Feature x Clinical Meaning Mapping

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
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
rep_*          template id expanded per rep, e.g. temporal.tempo.rep_1
```

Phase-level variants are emitted only for `spatial.rom`, `spatial.shape`, and
`control.stability`. Compensation features are rep-level because their rules use
the full rep trajectory.

`spatial.symmetry.*` is interpreted only after the feature-availability gate in
[08_feature_extraction.md](../pipeline/08_feature_extraction.md). A side-view
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
torso_length_ratio_per_rep load-shift trend in ⑨
second                  rep duration
dimensionless_cv        coefficient of variation / symmetry index
dimensionless           ratios
```

## 3. Implemented Compensation Features

| Exercise | Feature ids | Interpretation boundary |
|---|---|---|
| Squat | `control.compensation.knee_valgus.left/right` | Frontal-plane knee deviation proxy; requires view support and foot/hip/ankle landmark reliability. |
| Squat | `control.compensation.knee_varus.left/right` | Lateral knee deviation proxy; sensitive to stance width and view. |
| Squat | `control.compensation.excessive_trunk_flexion` | Trunk-lean proxy; relative load-strategy interpretation, not a spinal diagnosis. |
| Squat | `control.compensation.lateral_pelvic_shift` | Weight-shift proxy from pelvis displacement. |
| Squat | `control.compensation.heel_lift.left/right` | Heel-elevation proxy; contact and landmark visibility can limit confidence. |
| Squat | `control.compensation.pelvic_rotation` | Hip-depth asymmetry proxy; depth-sensitive in monocular data. |
| Lunge | `control.compensation.knee_valgus.left/right` | Forward-leg or side-specific knee deviation; must preserve active/forward-leg context. |
| Lunge | `control.compensation.excessive_trunk_flexion` | Forward trunk-lean proxy in split stance. |
| Lunge | `control.compensation.lateral_pelvic_shift` | Pelvic-control proxy; view and hip visibility dependent. |
| Lunge | `control.compensation.heel_lift.left/right` | Must be interpreted with forward/trailing-leg role. |
| Plank shoulder tap | `control.compensation.pelvic_rotation` | Anti-rotation proxy from hip-depth asymmetry. |
| Plank shoulder tap | `control.compensation.lateral_pelvic_shift` | Lateral weight-shift proxy during one-hand support. |

Pike push-up compensation candidates are currently YAML candidates only. They are
not listed as implemented until corresponding rules are added to
`COMPENSATION_RULES`.

## 4. Pending Candidate Handling

Exercise YAML may contain candidates without implemented rules. Runtime behavior:

```text
matching rule in COMPENSATION_RULES        feature may be emitted
no matching rule                           UserWarning; omitted from this mapping
```

Pending candidates remain research notes, not hidden score components.

## 5. Code And Data Mapping

```text
src/movement/features/
data/definitions/clinical/feature_meanings.yaml
docs_eng/pipeline/08_feature_extraction.md
docs_eng/pipeline/10_biomarker_scoring.md
```

When a feature family, unit, or interpretation boundary changes, update
`docs_eng/` first, then synchronize `docs/`, then update YAML/code.
