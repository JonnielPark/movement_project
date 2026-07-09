# Pike Push-up Clinical Rationale

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/clinical/exercises/pike_pushup.md` is the same-version Korean source.

This document summarizes why pike push-up is included and how its inverted
upper-body support mechanics are interpreted. It is not a diagnostic standard and
not a code specification.

Related:

- Performance protocol: [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md)
- Exercise YAML: [pike_pushup.yaml](../../../data/definitions/exercises/pike_pushup.yaml)
- Analysis profile: [pike_pushup.yaml](../../../data/definitions/analysis_profiles/pike_pushup.yaml)
- Feature meaning map: [per_exercise_mapping.md](../per_exercise_mapping.md)

---

## 1. Study Role

Pike push-up is an inverted upper-body closed-chain task. It is used to observe
shoulder/elbow ROM and symmetry, head descent, inverted-V maintenance, hip-height
change, and support consistency under a difficult bodyweight task.

It is also useful for testing confidence limits and performance failure-point
recording because self-occlusion and partial completion are common.

## 2. Execution Context

| Item | Current setting | Interpretation intent |
|---|---|---|
| Classification | bilateral symmetric, inverted closed-chain | upper-body support task |
| Primary joints | shoulder, elbow, wrist, trunk | push mechanics and support consistency |
| Segmentation | nose/head vertical trajectory, descent/ascent | head descent as depth proxy |
| Performance | 10 reps or clean maximum with failure provenance | difficult task with partial completion expected |
| Camera | Z3/Z7, H1 | low side view for head descent and hip position |
| Biomech focus | shoulder/elbow/wrist/trunk load regions | relative support tendency only |

Execution source of truth remains YAML.

## 3. Observation Targets

```text
head descent              nose or head proxy
shoulder ROM              shoulder angle and side symmetry
elbow ROM                 push-phase control and flare tendency
hip height                hip_center and hip angle
support consistency         wrist/ankle/foot contact trajectories
upper-limb symmetry       left/right shoulder and elbow features
```

Expected performance is a data-acquisition reference: hips remain high in an
inverted V, head descends between the hands, and support points do not shift
substantially.

## 4. Compensation Patterns

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| insufficient head descent | partial depth proxy | high-medium; head proxy needed if nose unstable | pending pattern |
| head forward shift | load-avoidance trajectory proxy | medium; side view best | pending pattern |
| elbow flare | altered support strategy | medium; view/elbow confidence dependent | pending pattern |
| shoulder asymmetry | unequal upper-limb support proxy | medium; self-occlusion sensitive | pending pattern |
| hip drop | task changes toward regular push-up | high in side view | pending pattern |
| hip pike variation | changing hip-height strategy | medium | pending pattern |
| hand/foot repositioning | support-reference change | low-medium | control/limitation factor |
| tempo instability | timing drift under task difficulty | high with stable segmentation | review pattern |

No pike push-up compensation feature is currently implemented in
`COMPENSATION_RULES`; patterns remain research notes until rules and tests exist.

## 5. View And Quality Limits

The default view is low side (`Z3`/`Z7`, `H1`). It supports head descent,
hip pike/drop, and vertical upper-body motion. Frontal/oblique views may help
elbow flare and shoulder asymmetry, but they are less direct for head depth.

Far-side elbow or wrist occlusion is common. If far-side landmarks are unstable,
do not penalize upper-limb symmetry directly. Prioritize visible-side sagittal
ROM, head descent, hip position, and trunk/hip alignment.

Low repetition count is not a score by itself. Interpret it with actual count,
failure point, and failure reason.

## 6. Development Boundary

High-value first rules are likely:

```text
insufficient_head_descent
hip_drop
head_forward_shift
```

Shoulder asymmetry and elbow flare should wait for detectability checks because
they are view and self-occlusion dependent.
