# Pike Push-up Clinical Rationale

**Document Version:** 1.0.1
**Last Updated:** 2026-05-09  
**Korean Sync:** `docs/clinical/exercises/pike_pushup.md` is the same-version Korean source.

This document describes the biomechanical meaning of pike push-up in this study,
how upper-body support and inverted-V posture are interpreted, and which patterns
may become scoring candidates or control factors. It is not a diagnostic standard
or a code specification.

Related documents:

- Performance protocol: [exercise_performance_protocol.md §2-3](../../practical_protocols/exercise_performance_protocol.md#2-3-pike-push-up)
- Exercise YAML: `data/definitions/exercises/pike_pushup.yaml`
- Feature meaning map: [per_exercise_mapping.md §Pike Push-up](../per_exercise_mapping.md#pike-push-up)

---

## 1. Role In This Study

Pike push-up is an upper-body closed-chain task performed in an inverted posture.
In this study, it is used to observe shoulder and elbow symmetry, head descent
trajectory, inverted-V maintenance, hip-height change, and upper-body support
stability.

Unlike lower-body exercises, pike push-up often produces upper-limb self-occlusion
and near-floor postures. It is therefore useful for testing visibility limits and
performance failure-point recording in an upper-body support task.

---

## 2. Expected Movement

- The hips remain high, creating an inverted-V shape.
- The head descends toward the space between the hands.
- Shoulders and elbows flex/extend relatively symmetrically.
- The hips do not drop into a regular push-up posture.
- Hand and foot positions do not shift substantially across reps.
- If 10 repetitions are not possible, actual repetition count and failure point are recorded.

---

## 3. Main Observation Structure

| Observation | Joints/Segments | Interpretation Direction |
|---|---|---|
| Head descent | nose or head proxy | depth proxy, partial completion |
| Shoulder ROM | shoulder angle | upper-body support, bilateral symmetry |
| Elbow ROM | elbow angle | push-phase control, elbow flare |
| Hip height | hip_center, hip angle | inverted-V maintenance, hip drop |
| Hand/foot position | wrist, ankle, foot | base-of-support stability |
| Upper-limb symmetry | left/right shoulder/elbow | unilateral loading or compensation |

---

## 4. Compensation And Analysis-Disrupting Patterns

| Pattern | Biomechanical Meaning | Pose Detectability | Scoring/Control Direction | Related Candidate |
|---|---|---|---|---|
| insufficient head descent | Head does not descend far enough; may reflect ROM limit, fatigue, task scaling, or partial completion. | High-medium; requires nose visibility or shoulder-center fallback. | Scoring candidate with failure provenance | `insufficient_head_descent` |
| head forward shift | Head moves forward beyond the hands instead of between them, potentially avoiding shoulder load. | Medium; best in side view. | Scoring candidate | `head_forward_shift` |
| elbow flare | Elbows drift outward, suggesting shoulder stability demand or altered support strategy. | Medium; view and elbow visibility dependent. | Scoring candidate | `elbow_flare` |
| shoulder asymmetry | Left/right shoulder ROM or trajectory differs, suggesting unilateral support avoidance or control difference. | Medium; strongly affected by self-occlusion. | Scoring candidate or interpretation limitation | `shoulder_asymmetry` |
| hip drop | Hips lower toward regular push-up posture, changing the task itself. | High in side view. | Scoring candidate, or control/interpretation limitation if severe | `hip_drop` |
| hip pike variation | Hip height is too high or varies strongly, changing shoulder demand and head-depth reference. | Medium; requires hip and shoulder visibility. | Scoring candidate | `hip_pike` |
| hand/foot repositioning | Support points move during the set, changing base of support and ROM reference. | Low-medium; true contact and landmark jitter can be hard to separate. | Control or interpretation-limitation factor | `hand_foot_repositioning` |
| tempo instability | Repetition timing changes abruptly, possibly reflecting difficulty, fatigue, or partial completion. | High with stable rep segmentation. | Scoring candidate | `tempo_instability` |

---

## 5. Data Quality And Interpretation Limits

Side low-angle views help observe head and hip-height changes, but elbows and
wrists can self-occlude near the bottom position. If the nose landmark is unstable,
head descent may need shoulder-center or another head proxy fallback.

Because pike push-up is difficult, failing to reach 10 repetitions is expected in
some participants. Low repetition count should be interpreted with actual count,
performance failure point, and failure reason rather than treated as a direct score
by itself.

---

## 6. Recommended View Interpretation

The default recommended view for pike push-up is low side view (`Z3` or `Z7`, `H1`).
This view supports observation of whether the head descends between the hands,
whether the hips maintain the inverted-V shape, whether hip drop turns the task
toward a regular push-up, and how the upper body moves vertically.

Frontal or front-oblique views may help elbow flare, shoulder asymmetry, or left-right
hand-support differences, but they are less direct for head descent and hip pike/drop.
Therefore, side view remains the default, and upper-limb symmetry is interpreted as
a secondary feature only when both shoulder and elbow landmarks have sufficient
visibility.

In side-view filming, the far-side elbow or wrist may be occluded. In that case,
far-side upper-limb ROM or symmetry should not be penalized directly. More stable
features such as visible-side sagittal ROM, head descent, hip position, and trunk/hip
alignment should be prioritized.

---

## 7. Development Reference

High-value development references in pike push-up are partial completion and
failure-point provenance. Insufficient head descent, hip drop, and head forward
shift are relatively observable from pose data. Shoulder asymmetry and elbow flare
require detectability evaluation first because they are view and self-occlusion
dependent.
