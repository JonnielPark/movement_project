# Lunge Clinical Rationale

**Document Version:** 1.0.2
**Last Updated:** 2026-05-10  
**Korean Sync:** `docs/clinical/exercises/lunge.md` is the same-version Korean source.

This document describes the biomechanical meaning of lunge in this study, how
unilateral/alternating execution should be interpreted, and which patterns may
become scoring candidates or control factors. It is not a diagnostic standard or
a code specification.

Related documents:

- Performance protocol: [exercise_performance_protocol.md §2-2](../../practical_protocols/exercise_performance_protocol.md#2-2-lunge)
- Exercise YAML: [lunge.yaml](../../../data/definitions/exercises/lunge.yaml)
- Feature meaning map: [per_exercise_mapping.md §Lunge](../per_exercise_mapping.md#lunge)

---

## Analysis Parameter Summary

This summary explains the key exercise-YAML settings from an interpretation
perspective. The execution source of truth is
[lunge.yaml](../../../data/definitions/exercises/lunge.yaml).

| YAML Block | Current Setting | Setting Intent |
|---|---|---|
| `classification` | `alternating`, split-stance closed-chain, primary plane `sagittal` | Define lunge as a unilateral lower-body task with different forward- and rear-limb roles. |
| `landmarks` / `angle_definitions` | Bilateral hip/knee/ankle centered; shoulder/pelvis lines as support | Compare forward leg, trailing leg, trunk alignment, and pelvic stability within each repetition. |
| `rep_segmentation` / `phase_segmentation` | `hip_center` vertical trajectory; top boundary, bottom split; `Descent` / `Ascent` | Use hip-center descent/ascent in split stance to split repetitions and phases. |
| `performance_protocol` | 10 repetitions; default `same_side_block_then_switch`, block size 5; also allows `alternating_each_rep` | Support the current 5-and-5 acquisition protocol while keeping a future alternating-each-rep variant compatible. |
| `camera_protocol` | `Z3` / `Z7`, `H2`, 200-250 cm | Prioritize side-view observation of anterior knee travel, rear-limb ROM, and trunk alignment. |
| `feature_domains` | ROM, symmetry, alignment, support width, left/right timing variability, balance control | Preserve side order and forward/rear limb role differences at the feature level. |
| `biomechanical_focus` | Vertical + anterior-posterior CoM motion, hip/knee/ankle load regions | Interpret forward-limb load acceptance and rear-limb support strategy from relative motion. |
| `compensation_candidates` | knee valgus, asymmetric knee/hip flexion, rear hip extension, trunk lean, pelvis drop/shift, etc. | Review compensation candidates that can emerge during unilateral loading and balance control. |
| `quality_rules` | visible ratio `0.8`, critical ratio `0.9`, max interpolation gap 3 frames | Interpret side-to-side comparison only when lower-limb landmarks and active-side provenance are sufficient. |

---

## 1. Role In This Study

Lunge is a split-stance lower-body movement in which one limb takes the primary
load while the other assists support and balance. In this study, lunge is used to
observe active-side attribution, forward/rear limb role differences, step-length
consistency, trunk alignment, anterior knee travel, and pelvic stability.

The current acquisition protocol uses five repetitions with one forward leg and
then five repetitions with the opposite forward leg. Lunge can also be performed
by alternating sides every repetition. Therefore, left-right order is a
protocol-specific choice rather than an intrinsic property of the exercise.

---

## 2. Expected Movement

- The feet maintain a split stance.
- During descent, the forward hip, knee, and ankle accept load and flex.
- The rear limb assists balance with hip extension and knee flexion.
- The trunk does not fold excessively forward or extend backward to assist ascent.
- Step length remains reasonably consistent across repetitions.
- During side switching, the body does not turn toward a different camera-facing direction.

---

## 3. Main Observation Structure

| Observation | Joints/Segments | Interpretation Direction |
|---|---|---|
| Forward-leg ROM | forward hip/knee/ankle | load acceptance, descent depth, side difference |
| Rear-leg extension | rear hip/knee | hip-flexor extensibility, trailing-leg control |
| Step consistency | ankle/foot trajectory | inter-rep comparability, segmentation stability |
| Trunk alignment | shoulder-hip line | anterior trunk lean, ascent compensation |
| Pelvic stability | hip_center, pelvis line | lateral shift, pelvis drop/rotation |
| Side order | active side per rep | protocol adherence, motion attribution |

---

## 4. Compensation And Analysis-Disrupting Patterns

| Pattern | Biomechanical Meaning | Pose Detectability | Scoring/Control Direction | Related Candidate |
|---|---|---|---|---|
| knee valgus | Medial collapse of the forward knee, especially during load acceptance. | Medium; sagittal views can hide frontal-plane deviation. | Scoring candidate with view warning | `knee_valgus` |
| asymmetric knee/hip flexion | Side or forward/rear limb ROM differences reflecting inter-limb loading strategy. | High when active-side annotation is available. | Scoring candidate | `asymmetric_knee_flexion`, `asymmetric_hip_flexion` |
| insufficient rear hip extension | Limited rear-hip extension, possibly reflecting hip-flexor extensibility limits or short step length. | Medium; requires side view and rear-limb visibility. | Scoring candidate | `insufficient_rear_hip_extension` |
| excessive trunk flexion | Excessive forward lean, possibly compensating for forward-leg ankle restriction or balance demand. | High in side view. | Scoring candidate | `excessive_trunk_flexion` |
| lateral trunk lean | Side bending, possibly reflecting pelvic-control demand or load avoidance. | Medium; better in frontal/front-oblique views. | Scoring candidate or interpretation limitation | `lateral_trunk_lean` |
| pelvis drop/shift | Pelvic drop or lateral displacement linked to hip-abductor control or balance strategy. | Medium; view and hip landmark visibility dependent. | Scoring candidate | `pelvis_drop`, `lateral_pelvic_shift` |
| unstable step width | Step width or foot position changes across reps, weakening comparability and active-side interpretation. | Low-medium; real foot contact and landmark stability are difficult to separate. | Mainly control factor | `unstable_step_width`, `inconsistent_step_length` |
| camera side change | Body or camera-facing direction changes during side switch, weakening left-right comparison. | High with recording metadata or video review. | Control or interpretation-limitation factor | `camera_side_change` |
| arm swing/trunk extension assist | Momentum used to assist ascent, contaminating lower-limb loading interpretation. | Medium; motion is visible but assistance intent is not certain from pose alone. | Control factor | `arm_swing` |

---

## 5. Data Quality And Interpretation Limits

Because forward and rear limbs have different roles, simple left/right joint
comparison can be misleading. Each repetition should identify whether the left or
right limb is the forward leg using annotation or motion attribution.

Side views help anterior knee travel and trunk alignment, but can weaken
frontal-plane knee valgus or pelvis-drop observation. Frontal or front-oblique
views help left-right alignment but weaken sagittal ROM and rear-limb interpretation.

---

## 6. Recommended View Interpretation

The default recommended view for lunge is side view (`Z3` or `Z7`). Lunge depends on
the different roles of the forward and rear limbs, and the key observations include
anterior knee travel, sagittal ROM of the forward/rear limbs, forward trunk lean,
and step-length consistency. Side view is the most direct view for these features.

This does not mean frontal-plane compensation is ignored. Knee valgus, pelvis drop,
and lateral trunk lean may be more visible in frontal or front-oblique views. However,
requiring two views in the basic single-camera protocol would increase acquisition
burden and make identical-repetition comparison harder. Therefore, the default
protocol uses side view; frontal-plane patterns are treated as scoring candidates
when observable, and as confidence or interpretation limitations when the view is
unfavorable.

If far-side joints are extracted reliably in real filming, bilateral or trailing-leg
features may be used. If occlusion repeatedly appears, those features should be
reported as unavailable or low-confidence rather than scored as poor movement. This
defensive logic is an optional extension to consider after pilot filming, not a
default requirement.

---

## 7. Development Reference

The key development reference for lunge is side-sequence and active-side provenance.
The current protocol uses a same-side block followed by a switch, but an
alternate-each-rep variant may be added later. In that case, exercise name alone is
not enough; a protocol profile or separate YAML variant may be needed.

Scoring candidates should preserve forward leg, trailing leg, expected side
sequence, and observed side sequence together.
