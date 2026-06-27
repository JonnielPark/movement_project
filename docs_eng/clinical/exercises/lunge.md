# Lunge Clinical Rationale

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/clinical/exercises/lunge.md` is the same-version Korean source.

This document summarizes why lunge is included and how its alternating
split-stance mechanics are interpreted. It is not a diagnostic standard and not a
code specification.

Related:

- Performance protocol: [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md)
- Exercise YAML: [lunge.yaml](../../../data/definitions/exercises/lunge.yaml)
- Analysis profile: [lunge.yaml](../../../data/definitions/analysis_profiles/lunge.yaml)
- Feature meaning map: [per_exercise_mapping.md](../per_exercise_mapping.md)

---

## 1. Study Role

Lunge is the main lower-body task for active-side and role-based interpretation.
One limb acts as the forward/load-accepting limb while the other supports balance
as the trailing limb. The study uses it to test side-sequence provenance,
side-role context, anterior knee travel, trunk alignment, pelvic stability, and
step consistency.

Left/right order is protocol-specific, not an intrinsic property of the exercise.

## 2. Execution Context

| Item | Current setting | Interpretation intent |
|---|---|---|
| Classification | alternating split-stance closed-chain | preserve forward/trailing limb roles |
| Primary joints | hip, knee, ankle | lower-limb ROM and alignment |
| Segmentation | hip-center vertical trajectory, descent/ascent | split repeated lunge cycles |
| Performance | 5 reps one front foot, then 5 reps the other | same-side block now; alternating-each-rep possible later |
| Camera | Z3/Z7, H2 | side-view read of knee travel, rear-limb ROM, trunk lean |
| Biomech focus | vertical + anterior-posterior CoM, hip/knee/ankle load regions | relative load-acceptance tendency |

Execution source of truth remains YAML.

## 3. Observation Targets

```text
forward-leg ROM          forward hip/knee/ankle load acceptance
rear-leg motion          rear hip extension and support strategy
step consistency         ankle/foot trajectory and base of support
trunk alignment          shoulder-hip line
pelvic stability         hip_center and pelvis line
side order               active side per rep
```

Expected performance is a data-acquisition reference: stable split stance,
consistent step length, controlled trunk, and no camera-facing direction change
during side switching.

## 4. Candidate Patterns

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| knee valgus | forward-knee medial deviation during load acceptance | medium; frontal info limited in side view | implemented candidate with view warning |
| asymmetric knee/hip flexion | role-specific ROM difference | high when active-side metadata exists | candidate / role-based feature |
| insufficient rear hip extension | rear-limb extension constraint or short step strategy | medium; side view needed | candidate |
| excessive trunk flexion | forward trunk-lean strategy | high in side view | implemented candidate |
| lateral trunk lean | side-bending strategy | medium; frontal/oblique better | candidate or limitation |
| pelvis drop/shift | pelvic-control proxy | medium; view/visibility dependent | candidate |
| heel lift | ankle/contact proxy requiring forward/trailing role context | medium | implemented candidate |
| camera side change | body turns during side switch | high with metadata/video review | control/limitation factor |

## 5. Role And View Limits

Simple anatomical left/right comparison is not enough. Each rep should preserve:

```text
forward_leg / trailing_leg
active_side / support_side
near_side / far_side
expected side sequence / observed side sequence
```

Side view supports anterior knee travel, sagittal ROM, rear-hip extension, trunk
flexion, and step length. Frontal or oblique views support step width, pelvis
drop/shift, lateral trunk lean, and frontal knee alignment. These are confidence
states, not direct penalties.

If one limb is consistently far-side or low-visibility, side-to-side comparison
should be unavailable or low-confidence rather than interpreted as unilateral
movement deficit.

## 6. Development Boundary

High-value development work for lunge should preserve side-sequence provenance.
If an alternating-each-rep variant is added later, a protocol profile or separate
YAML variant may be needed; exercise name alone is not enough.
