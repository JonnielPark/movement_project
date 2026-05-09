# Plank Shoulder Tap Clinical Rationale

**Document Version:** 1.0.1
**Last Updated:** 2026-05-09  
**Korean Sync:** `docs/clinical/exercises/plank_shoulder_tap.md` is the same-version Korean source.

This document describes the biomechanical meaning of plank shoulder tap in this
study, how the anti-rotation task is interpreted, and which patterns may become
scoring candidates or control factors. It is not a diagnostic standard or a code
specification.

Related documents:

- Performance protocol: [exercise_performance_protocol.md §2-4](../../practical_protocols/exercise_performance_protocol.md#2-4-plank-shoulder-tap)
- Exercise YAML: `data/definitions/exercises/plank_shoulder_tap.yaml`
- Feature meaning map: [per_exercise_mapping.md §Plank Shoulder Tap](../per_exercise_mapping.md#plank-shoulder-tap)

---

## 1. Role In This Study

Plank shoulder tap is an anti-rotation task in which one hand leaves the ground
while the opposite upper limb and both feet support body weight. In this study, it
is used to observe pelvic rotation, lateral weight shift, base-of-support change,
trunk/pelvis stability, and left-right tap order.

For participant-facing counting, one left tap plus one right tap is one protocol
cycle. For segmentation, each tap may be an atomic movement. Protocol count and
segmented atomic reps therefore need to be stored separately.

---

## 2. Expected Movement

- The participant maintains a high-plank base of support.
- One hand taps the opposite shoulder and returns to the floor.
- Trunk and pelvis rotation remain controlled while the hand is lifted.
- Left-right tap order is maintained.
- The hips do not repeatedly sag or lift.
- Hand and foot positions do not shift substantially during the set.

---

## 3. Main Observation Structure

| Observation | Joints/Segments | Interpretation Direction |
|---|---|---|
| Pelvic rotation | left/right hip depth | anti-rotation control |
| Lateral weight shift | hip_center x, shoulder/hip trajectory | support-arm loading strategy |
| Hip-height change | hip_center z, hip angle | trunk stability, hip drop/lift |
| Active hand trajectory | wrist, shoulder | tap segmentation, missed tap |
| Base of support | support wrist/ankle/foot | base-of-support shift |
| Side order | active side per tap | protocol adherence, motion attribution |

---

## 4. Compensation And Analysis-Disrupting Patterns

| Pattern | Biomechanical Meaning | Pose Detectability | Scoring/Control Direction | Related Candidate |
|---|---|---|---|---|
| excessive pelvic rotation | Pelvis rotates while the hand is lifted; direct expression of anti-rotation control demand. | High-medium in front-oblique view. | Scoring candidate | `pelvis_rotation`, `trunk_rotation` |
| lateral pelvic shift | Body weight shifts toward the support arm, reflecting one-hand support strategy. | High-medium; depends on hip-center tracking and view. | Scoring candidate | `lateral_pelvic_shift`, `excessive_com_lateral_shift` |
| hip drop | Hips sag downward, possibly reflecting trunk/core stability demand or fatigue. | Medium; needs side component and hip visibility. | Scoring candidate | `hip_drop` |
| hip height drift | Hips progressively lift or drop across the set, suggesting task scaling or posture deterioration. | Medium; requires set-level trend interpretation. | Scoring candidate | `hip_height_drift` |
| shoulder collapse/asymmetry | Support shoulder drops or left/right shoulder trajectories differ, suggesting upper-limb support instability. | Medium; shoulder visibility and occlusion dependent. | Scoring candidate or interpretation limitation | `shoulder_collapse`, `shoulder_asymmetry` |
| side order error | Left-right tap order is missed or one side repeats, directly affecting protocol adherence and attribution. | High with active-hand detection. | Scoring candidate or protocol warning | `side_order_error` |
| missed shoulder tap | The hand lifts but does not actually tap the opposite shoulder. | Low-medium; true contact is difficult to prove from pose alone. | Mainly control or interpretation-limitation factor | `missed_shoulder_tap` |
| base-of-support shift | Hand or foot positions shift, changing the stability reference itself. | Low-medium; contact position and landmark stability are difficult to separate. | Control or interpretation-limitation factor | `base_of_support_shift` |

---

## 5. Data Quality And Interpretation Limits

Front-oblique low-angle views help capture pelvic rotation and lateral shift
together. However, active wrist trajectories can overlap the trunk or opposite
shoulder, making true tap contact difficult to confirm from pose alone. Missed tap
should therefore be treated conservatively as an annotation note or interpretation
limitation rather than a direct score unless validated.

Hand and foot shifts can reflect real base-of-support changes or landmark jitter.
They are better recorded as base-of-support warnings and interpretation-confidence
notes than used as automatic exclusion rules.

---

## 6. Recommended View Interpretation

The default recommended view for plank shoulder tap is low front-oblique view (`Z2`
or `Z8`, `H1`). This view is a compromise for observing pelvic rotation, lateral
weight shift, shoulder/pelvis-line sway, and active-hand trajectory while one hand
leaves the floor.

A pure frontal view can help lateral shift and tap order, but may make pelvic depth
rotation and true hand-shoulder contact harder to distinguish. A pure side view can
help hip-height drift or hip drop, but the active wrist can overlap the trunk and
weaken tap segmentation and side-order interpretation. For this reason, the study
uses low front-oblique view as the default and prioritizes combined lateral-shift
and rotation-control interpretation.

Patterns such as missed shoulder tap depend on true contact, which is difficult to
confirm from pose alone. They should be handled conservatively as annotation notes,
protocol warnings, or interpretation limitations rather than direct scoring factors.

---

## 7. Development Reference

The high-value development reference in plank shoulder tap is separating protocol
cycle from atomic tap. A left-right pair is one participant-facing protocol count,
but each active-hand trajectory may form an individual segment. Metadata such as
`protocol_cycle_id`, `rep_unit`, `tap_count`, and `rep_side_sequence` may be needed.

Scoring candidates should begin with patterns that are relatively reproducible in
pose data: pelvic rotation, lateral pelvic shift, hip drop, and side-order error.
