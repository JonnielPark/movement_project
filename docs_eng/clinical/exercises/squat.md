# Squat Clinical Rationale

**Document Version:** 1.0.0  
**Last Updated:** 2026-05-09  
**Korean Sync:** `docs/clinical/exercises/squat.md` is the same-version Korean source.

This document describes the biomechanical meaning of squat in this study, the
movement patterns to observe, and which patterns may become scoring candidates or
control factors. It is not a diagnostic standard or a code specification.

Related documents:

- Performance protocol: [exercise_performance_protocol.md §2-1](../../practical_protocols/exercise_performance_protocol.md#2-1-squat)
- Exercise YAML: `data/definitions/exercises/squat.yaml`
- Feature meaning map: [per_exercise_mapping.md §Squat](../per_exercise_mapping.md#squat)

---

## 1. Role In This Study

Squat is a bilateral lower-body closed-chain movement in which both legs support
body weight simultaneously. In this study, squat is used to observe hip-knee-ankle
coordination, descent depth, trunk alignment, hip-center stability, and left-right
symmetry.

Because squat has a clear repetition structure and bilateral movement, it is a
useful reference exercise for validating spatial, temporal, and control features
from monocular pose data. It also exposes common compensation candidates such as
knee valgus/varus, heel lift, excessive trunk flexion, and lateral pelvic shift.

---

## 2. Expected Movement

- Both feet remain in stable floor contact.
- Hip, knee, and ankle flex together while the hip center descends.
- The knees do not drift markedly away from the foot direction during descent or ascent.
- The trunk may lean slightly forward, but trunk folding should not obscure hip flexion.
- Left and right hip/knee ROM remain broadly similar.
- Depth and tempo remain reasonably consistent across repetitions.

These expectations are acquisition and interpretation references, not clinical
normality criteria.

---

## 3. Main Observation Structure

| Observation | Joints/Segments | Interpretation Direction |
|---|---|---|
| Descent depth | hip_center, hip/knee/ankle angles | ROM, depth proxy, inter-rep consistency |
| Knee tracking | hip-knee-ankle line | knee valgus/varus, frontal-plane tracking |
| Heel contact | heel, ankle, foot index | ankle-dorsiflexion restriction or forefoot-loading compensation |
| Trunk lean | shoulder-hip line | hip strategy, trunk compensation |
| Lateral pelvic shift | hip_center x trajectory | weight-shift compensation |
| Bilateral symmetry | left/right hip, knee, ankle ROM | unilateral mobility or load-avoidance tendency |

---

## 4. Compensation And Analysis-Disrupting Patterns

| Pattern | Biomechanical Meaning | Pose Detectability | Scoring/Control Direction | Related Candidate |
|---|---|---|---|---|
| knee valgus | Medial knee displacement relative to the hip-ankle line; may reflect hip-abductor control demand or foot/hip strategy changes under load. | High, especially in frontal or front-oblique views. | Scoring candidate | `knee_valgus` |
| knee varus | Lateral knee displacement; may overlap with wide stance, structural alignment, or bracing strategy. | Medium; sensitive to view and foot-direction estimation. | Scoring candidate with interpretation limitation | `knee_varus` |
| asymmetric depth | Side-to-side or inter-rep depth differences; may reflect unilateral mobility limit, pain avoidance, or balance strategy. | Medium; requires stable rep segmentation and hip-center tracking. | Scoring candidate | `asymmetric_depth` |
| excessive trunk flexion | Excessive forward trunk folding; may shift demand away from the knee-extensor mechanism toward hip/lumbar strategy. | High in side or front-oblique views. | Scoring candidate | `excessive_trunk_flexion` |
| lateral pelvic shift | Lateral hip-center displacement; may reflect unilateral lower-limb limitation or weight-shift compensation. | Medium; best in frontal/front-oblique views. | Scoring candidate | `lateral_pelvic_shift` |
| heel lift | Heel rising during descent; may reflect limited ankle dorsiflexion or forefoot-loading strategy. | Medium; depends on heel visibility and camera height. | Scoring candidate or interpretation limitation | `heel_lift` |
| arm swing | Arm momentum assisting ascent and contaminating lower-body/trunk trajectories. | Medium; arm motion is visible, but assistance intent is hard to prove from pose alone. | Mainly control factor | `analysis_disrupting_patterns.arm_swing` |
| unstable foot contact | Foot position or support changes across reps, making joint trajectories less comparable. | Low-medium; real contact and landmark jitter can be difficult to separate. | Control or interpretation-limitation factor | `unstable_foot_contact` |

---

## 5. Data Quality And Interpretation Limits

Front-oblique views help observe knee tracking and descent depth together, but foot
direction and true foot contact are still difficult to infer from pose alone. Knee
valgus/varus depends on foot-direction assumptions, and heel lift depends on heel
landmark visibility.

Loose clothing can hide knee or hip landmarks and weaken alignment and pelvis-shift
interpretation. A camera that is too close to side view can reduce frontal-plane
knee deviation, while a camera that is too close to frontal view weakens sagittal
ROM interpretation.

---

## 6. Development Reference

This document is not a development requirement. If a pattern is promoted to a
scoring candidate, use this sequence:

1. Record the candidate and detectability basis in `docs_eng/code_revision_plan.md`.
2. Link it to `compensation_candidates` or `analysis_disrupting_patterns` in YAML.
3. Document feature definitions and provenance rules in `docs_eng/pipeline/` and `docs/pipeline/`.
4. Test reproducible detectability with synthetic input or a minimal annotation fixture.

