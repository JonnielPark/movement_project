# Plank Shoulder Tap Clinical Rationale

**Document Version:** 1.1.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/clinical/exercises/plank_shoulder_tap.md` is the same-version Korean source.

This document summarizes why plank shoulder tap is included and how its
anti-rotation mechanics are interpreted. It is not a diagnostic standard and not
a code specification.

Related:

- Performance protocol: [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md)
- Exercise YAML: [plank_shoulder_tap.yaml](../../../data/definitions/exercises/plank_shoulder_tap.yaml)
- Analysis profile: [plank_shoulder_tap.yaml](../../../data/definitions/analysis_profiles/plank_shoulder_tap.yaml)
- Feature meaning map: [per_exercise_mapping.md](../per_exercise_mapping.md)

---

## 1. Study Role

Plank shoulder tap is the main stability-under-perturbation task. One hand leaves
the floor while the opposite arm and both feet support the body. The study uses it
to observe pelvic rotation, lateral weight shift, base-of-support changes,
trunk/pelvis stability, and left-right tap order.

Participant-facing count and segmentation unit differ: one left tap plus one
right tap is one protocol cycle, while each tap can be an atomic segmented rep.

## 2. Execution Context

| Item | Current setting | Interpretation intent |
|---|---|---|
| Classification | alternating plank closed-chain | anti-rotation during one-hand support |
| Primary joints | wrist, shoulder, hip, pelvis/trunk support | active hand, support arm, pelvis/trunk control |
| Segmentation | active-wrist trajectory, Lift/Tap/Return | atomic tap segmentation |
| Performance | 10 left-right protocol cycles; 2 atomic reps per count | separate user count from segmentation reps |
| Camera | Z2/Z8, H1 | low front-oblique view for rotation + lateral shift |
| Biomech focus | medial-lateral CoM, shoulder/trunk/core/pelvis regions | relative one-hand-support tendency |

Execution source of truth remains YAML.

## 3. Observation Targets

```text
pelvic rotation          left/right hip depth
lateral weight shift     hip_center x and shoulder/hip trajectory
hip-height change        hip_center z and hip angle
active hand trajectory   wrist and shoulder
base of support          support wrist/ankle/foot
side order               active side per tap
```

Expected performance is a data-acquisition reference: high plank, controlled
trunk/pelvis rotation, maintained side order, and minimal support repositioning.

## 4. Candidate Patterns

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| pelvic rotation | anti-rotation control proxy from hip-depth asymmetry | high-medium in front-oblique view | implemented candidate |
| lateral pelvic shift | weight shift toward support arm | high-medium; hip-center/view dependent | implemented candidate |
| hip drop / height drift | trunk/core stability or posture deterioration proxy | medium | pending candidate |
| shoulder collapse/asymmetry | support-arm stability proxy | medium; shoulder visibility dependent | pending candidate |
| side order error | protocol-adherence and attribution issue | high with active-hand detection | candidate/protocol warning |
| missed shoulder tap | true contact uncertainty | low-medium | control/limitation factor |
| base-of-support shift | support reference changes | low-medium | control/limitation factor |

Only pelvic rotation and lateral pelvic shift are currently implemented
compensation features.

## 5. View And Quality Limits

Low front-oblique view (`Z2`/`Z8`, `H1`) is the default compromise. It supports
pelvic rotation, lateral shift, shoulder/pelvis sway, and active-hand trajectory.

Pure frontal view can improve lateral shift and side order, but weakens depth
rotation. Pure side view can improve hip-height review, but active wrist overlap
can weaken tap segmentation and side-order interpretation.

Missed tap requires true contact, which pose alone cannot prove robustly. Treat it
as annotation note, protocol warning, or interpretation limitation unless validated.

## 6. Development Boundary

High-value early rules:

```text
pelvic_rotation
lateral_pelvic_shift
hip_drop
side_order_error
```

Keep `protocol_cycle_id`, `rep_unit`, `tap_count`, and `rep_side_sequence`
available so user-facing count and atomic tap segmentation do not collapse into
one ambiguous label.
