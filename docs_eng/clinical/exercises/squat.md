# Squat Clinical Rationale

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/clinical/exercises/squat.md` is the same-version Korean source.

This document summarizes why squat is included and how its movement patterns are
interpreted in this study. It is not a diagnostic standard and not a code
specification.

Related:

- Performance protocol: [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md)
- Exercise YAML: [squat.yaml](../../../data/definitions/exercises/squat.yaml)
- Analysis profile: [squat.yaml](../../../data/definitions/analysis_profiles/squat.yaml)
- Feature meaning map: [per_exercise_mapping.md](../per_exercise_mapping.md)

---

## 1. Study Role

Squat is the bilateral lower-body reference task. It is used to observe
hip-knee-ankle coordination, descent depth, trunk alignment, hip-center stability,
and left/right symmetry from monocular pose data.

Its value in this project is methodological: it provides a clear repeated movement
with common observable compensation candidates. It does not define clinical
normality.

## 2. Execution Context

| Item | Current setting | Interpretation intent |
|---|---|---|
| Classification | bilateral symmetric, standing closed-chain | reference task for bilateral lower-body coordination |
| Primary joints | hip, knee, ankle | triple flexion/extension and lower-limb alignment |
| Segmentation | hip-center vertical trajectory, descent/ascent | simple repeated-cycle validation |
| Camera | Z2/Z8, H2 | compromise view for knee tracking and depth |
| Main feature families | ROM, symmetry, arc length, tempo, stability, compensation | broad spatial/temporal/control validation |
| Biomech focus | vertical CoM, hip/knee/ankle load regions | relative load-distribution proxy only |

Execution source of truth remains YAML, not this rationale text.

## 3. Observation Targets

```text
descent depth              hip_center and hip/knee/ankle ROM
knee tracking              hip-knee-ankle line
heel contact               heel/ankle/foot landmarks
trunk lean                 shoulder-hip line
lateral pelvic shift       hip_center x trajectory
bilateral symmetry         left/right hip, knee, ankle features
```

Expected performance is a data-acquisition reference: stable foot contact,
coordinated hip/knee/ankle flexion, consistent depth/tempo, and limited excessive
trunk folding.

## 4. Candidate Patterns

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| knee valgus | medial knee-deviation proxy under load | high in frontal/front-oblique view | implemented candidate |
| knee varus | lateral knee-deviation proxy; stance/view sensitive | medium | implemented candidate with limitation |
| excessive trunk flexion | forward trunk-lean strategy | high in side/front-oblique view | implemented candidate |
| lateral pelvic shift | weight-shift proxy | medium; view dependent | implemented candidate |
| heel lift | ankle/forefoot-loading proxy | medium; heel visibility dependent | implemented candidate |
| pelvic rotation | hip-depth asymmetry proxy | low-medium; depth sensitive | implemented candidate with caution |
| arm swing | upper-limb momentum contaminating lower-body trajectory | medium | control factor |
| unstable foot contact | support changes reducing comparability | low-medium | control/limitation factor |

The terms above describe movement-quality proxies, not diagnoses.

## 5. View And Quality Limits

Front-oblique view is the default compromise. A more frontal view improves frontal
knee/pelvis alignment; a more side view improves depth, sagittal ROM, trunk lean,
and heel-lift review.

In side-view or near-side-view recordings, bilateral symmetry is view-dependent.
A rotated monocular 3D rendering does not create direct frontal evidence. If
far-side visibility, depth plausibility, or swap risk is insufficient, symmetry
features should be `low_confidence` or `not_assessed`.

When view support is weak, prioritize sagittal and centerline features:

```text
descent depth
hip/knee/ankle ROM
trunk lean
heel lift
hip-center trajectory stability
tempo and smoothness
```

## 6. Development Boundary

If a rationale item becomes a scoring feature:

```text
1. Define feature/unit/provenance in pipeline docs.
2. Link YAML candidate or interpretation rule.
3. Add minimal tests for reproducible detectability.
4. Update per-exercise mapping only after implementation.
```
