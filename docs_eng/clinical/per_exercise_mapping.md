# Per-Exercise Feature × Clinical Meaning Mapping

**Document Version:** 1.0.2
**Last Updated:** 2026-05-12
**Korean Sync:** `docs/clinical/per_exercise_mapping.md` is the same-version Korean source.

**Dissertation §5.5 / §5.6.** Active features for all four validation exercises, with unit and
biomechanical interpretation.

- Terminology: [`docs/terminology.md`](../terminology.md)
- Feature extraction code: [`src/movement/features/`](../../src/movement/features/)
- YAML mirror (dashboard tooltips): [`data/definitions/clinical/feature_meanings.yaml`](../../data/definitions/clinical/feature_meanings.yaml)
- Forbidden-vocabulary rules: clinical language-use principles in [`docs/terminology.md`](../terminology.md)

---

## Notes

| Term | Definition |
|---|---|
| **rep** | One record emitted per repetition (phase = None) |
| **rep / phase** | Also emitted per (rep × phase) with a lowercased phase suffix, e.g. `spatial.rom.left_knee_angle.descent` |
| **set** | One record spanning all reps in the set |
| **rep \*** | Template: one record per rep; N = rep number (e.g. `temporal.tempo.rep_1`) |

Phase-level variants are only emitted for features in `PHASE_AWARE_FEATURE_FAMILIES`
(`spatial.rom`, `spatial.shape`, `control.stability`).
Compensation features are rep-level only because candidate rules operate on the full rep trajectory.

Only **implemented** compensation rules are listed. Exercise-YAML candidates without a
matching entry in `COMPENSATION_RULES` produce a `UserWarning` at runtime and are omitted here.

All `spatial.symmetry.*` meanings assume that the symmetry feature has passed the
feature-availability gate described in `08_feature_extraction.md`. In side-view
or near-side-view monocular recordings, a rotated frontal rendering is not direct
frontal evidence. If bilateral landmark reliability, view compatibility, or
depth-sensitive stability is insufficient, the symmetry feature should be reported
as `low_confidence` or `not_assessed` rather than interpreted as poor movement
quality.

---

## Squat

| feature_id | domain | unit | level | clinical_meaning |
|---|---|---|---|---|
| `spatial.rom.left_hip_angle` | spatial | degree | rep / phase | Left hip sagittal ROM (max − min included angle). Restricted ROM may reflect limited hip-flexor extensibility or pain-avoidance guarding. |
| `spatial.rom.right_hip_angle` | spatial | degree | rep / phase | Right hip sagittal ROM; compared with the left side to detect unilateral hip-mobility restriction. |
| `spatial.rom.left_knee_angle` | spatial | degree | rep / phase | Left knee sagittal ROM. Reduced ROM is a common indicator of quadriceps or hamstring stiffness limiting descent depth. |
| `spatial.rom.right_knee_angle` | spatial | degree | rep / phase | Right knee sagittal ROM; bilateral comparison reveals load-avoidance asymmetry. |
| `spatial.rom.left_ankle_angle` | spatial | degree | rep / phase | Left ankle dorsiflexion ROM. Ankle dorsiflexion is a primary structural constraint on squat depth and heel-ground contact. |
| `spatial.rom.right_ankle_angle` | spatial | degree | rep / phase | Right ankle dorsiflexion ROM; asymmetry with the left often drives compensatory trunk lean or heel lift. |
| `spatial.symmetry.hip` | spatial | dimensionless_cv | rep | L/R hip ROM symmetry index (0 = perfect symmetry; larger = more asymmetric). Persistent asymmetry indicates compensatory loading toward the more mobile side. |
| `spatial.symmetry.knee` | spatial | dimensionless_cv | rep | L/R knee ROM symmetry index. Bilateral knee-mobility imbalance is a recognized pattern in altered squat mechanics. |
| `spatial.symmetry.ankle` | spatial | dimensionless_cv | rep | L/R ankle ROM symmetry index. Ankle-mobility asymmetry often underlies compensatory heel lift or lateral pelvic shift. |
| `spatial.shape.arc_length.left_hip` | spatial | torso_length_ratio | rep / phase | Arc length of the left hip joint trajectory. Longer arcs indicate lateral or anterior sway, suggesting non-vertical CoM descent. |
| `spatial.shape.arc_length.right_hip` | spatial | torso_length_ratio | rep / phase | Arc length of the right hip trajectory; compared with the left to detect asymmetric hip sway. |
| `spatial.shape.arc_length.left_knee` | spatial | torso_length_ratio | rep / phase | Arc length of the left knee trajectory. Elevated values indicate compensatory anterior or lateral knee tracking deviation. |
| `spatial.shape.arc_length.right_knee` | spatial | torso_length_ratio | rep / phase | Arc length of the right knee trajectory; bilateral comparison detects unilateral tracking deviation. |
| `spatial.shape.arc_length.left_ankle` | spatial | torso_length_ratio | rep / phase | Arc length of the left ankle trajectory. Non-minimal values indicate foot roll or transient heel-lift episodes. |
| `spatial.shape.arc_length.right_ankle` | spatial | torso_length_ratio | rep / phase | Arc length of the right ankle trajectory; compared with the left to detect unilateral foot instability. |
| `spatial.phase_rom_ratio.descent_ascent` | spatial | dimensionless | rep | Ratio of mean Descent ROM to mean Ascent ROM. Values > 1 indicate greater range during load acceptance (descent) than during the return phase. |
| `temporal.tempo.rep_*` | temporal | second | rep | Duration of each individual rep. Abrupt changes across reps indicate pacing instability or fatigue-driven tempo drift. |
| `temporal.variability.tempo_cv` | temporal | dimensionless_cv | set | Coefficient of variation of rep durations within the set. Higher values indicate inconsistent movement tempo, reducing within-set comparability of other metrics. |
| `control.stability.hip_center_x_std` | control | torso_length_ratio | rep / phase | Standard deviation of hip-center lateral displacement. Elevated values indicate lateral CoM instability during a nominally vertical loading task. |
| `control.stability.hip_center_z_std` | control | torso_length_ratio | rep / phase | Standard deviation of hip-center vertical displacement. Reflects descent/ascent trajectory smoothness; high variability suggests motor-control inconsistency. |
| `control.compensation.knee_valgus.left` | control | torso_length_ratio | rep | Peak medial knee deviation (left) from the frontal-plane hip-ankle line. Valgus collapse indicates insufficient hip-abductor activation under load. |
| `control.compensation.knee_valgus.right` | control | torso_length_ratio | rep | Peak medial knee deviation (right). Asymmetric valgus between sides points to unilateral hip-abductor demand or structural difference. |
| `control.compensation.knee_varus.left` | control | torso_length_ratio | rep | Peak lateral knee deviation (left). Varus tendency may reflect IT-band stiffness, wide-stance mechanics, or compensatory bracing. |
| `control.compensation.knee_varus.right` | control | torso_length_ratio | rep | Peak lateral knee deviation (right); bilateral comparison distinguishes structural varus from unilateral compensation. |
| `control.compensation.excessive_trunk_flexion` | control | degree | rep | Peak trunk lean from the vertical axis. Excessive forward lean redistributes load from the knee-extensor mechanism toward the hip and lumbar spine. |
| `control.compensation.lateral_pelvic_shift` | control | torso_length_ratio | rep | Peak lateral pelvis displacement from the rep-mean baseline. Indicates weight-shifting compensation, often secondary to unilateral hip or ankle mobility restriction. |
| `control.compensation.heel_lift.left` | control | torso_length_ratio | rep | Peak left heel elevation above the rep-minimum heel height. Compensates for restricted ankle dorsiflexion and increases forefoot loading, altering knee-tracking mechanics. |
| `control.compensation.heel_lift.right` | control | torso_length_ratio | rep | Peak right heel elevation; compared with the left to detect unilateral ankle dorsiflexion restriction. |
| `control.compensation.pelvic_rotation` | control | torso_length_ratio | rep | Peak left-right hip depth asymmetry (transverse-plane proxy). Non-zero values indicate pelvis rotation, which may reflect core-stability limitation or unilateral limb compensation. |

---

## Lunge

| feature_id | domain | unit | level | clinical_meaning |
|---|---|---|---|---|
| `spatial.rom.left_hip_angle` | spatial | degree | rep / phase | Left hip sagittal ROM in the split-stance position. Reduced ROM in the forward leg may limit descent depth; in the rear leg it reflects hip-flexor extensibility. |
| `spatial.rom.right_hip_angle` | spatial | degree | rep / phase | Right hip sagittal ROM; the loaded leg and trailing leg alternate per rep, so side × rep interaction is important. |
| `spatial.rom.left_knee_angle` | spatial | degree | rep / phase | Left knee sagittal ROM. In lunge, reduced forward-leg knee ROM often co-occurs with excessive trunk lean or heel lift. |
| `spatial.rom.right_knee_angle` | spatial | degree | rep / phase | Right knee sagittal ROM; asymmetry between the forward and trailing legs reflects inter-limb loading strategy. |
| `spatial.rom.left_ankle_angle` | spatial | degree | rep / phase | Left ankle dorsiflexion ROM. In lunge, forward-leg ankle restriction is a primary driver of compensatory trunk lean. |
| `spatial.rom.right_ankle_angle` | spatial | degree | rep / phase | Right ankle dorsiflexion ROM; trailing-leg ankle ROM governs rear-foot positioning and hip-extension capacity. |
| `spatial.symmetry.hip` | spatial | dimensionless_cv | rep | L/R hip ROM symmetry index across all reps of the set. Persistent asymmetry indicates unilateral loading preference between the dominant and non-dominant limb. |
| `spatial.symmetry.knee` | spatial | dimensionless_cv | rep | L/R knee ROM symmetry index. Bilateral knee-mobility imbalance in lunge is amplified by the alternating loading pattern. |
| `spatial.symmetry.ankle` | spatial | dimensionless_cv | rep | L/R ankle ROM symmetry index. Ankle asymmetry in split-stance exercises tends to produce visible pelvic compensations. |
| `spatial.shape.arc_length.left_hip` | spatial | torso_length_ratio | rep / phase | Arc length of the left hip trajectory. In lunge, elevated values indicate excessive anterior-posterior sway or lateral trunk lean. |
| `spatial.shape.arc_length.right_hip` | spatial | torso_length_ratio | rep / phase | Arc length of the right hip trajectory; asymmetry with the left reflects loading imbalance across alternating reps. |
| `spatial.shape.arc_length.left_knee` | spatial | torso_length_ratio | rep / phase | Arc length of the left knee trajectory. Elevated arcs indicate medial-lateral knee instability during the split-stance loading phase. |
| `spatial.shape.arc_length.right_knee` | spatial | torso_length_ratio | rep / phase | Arc length of the right knee trajectory; compared with the left to detect unilateral knee tracking deviation. |
| `spatial.shape.arc_length.left_ankle` | spatial | torso_length_ratio | rep / phase | Arc length of the left ankle trajectory. Non-minimal values indicate foot roll or contact instability during the descent. |
| `spatial.shape.arc_length.right_ankle` | spatial | torso_length_ratio | rep / phase | Arc length of the right ankle trajectory; bilateral comparison detects unilateral foot positioning instability. |
| `spatial.phase_rom_ratio.descent_ascent` | spatial | dimensionless | rep | Ratio of mean Descent ROM to mean Ascent ROM. Values > 1 indicate load-acceptance ROM is larger than recovery ROM, suggesting braking-dominant mechanics. |
| `temporal.tempo.rep_*` | temporal | second | rep | Duration of each individual rep. Inter-rep variability is particularly relevant in alternating exercises where left and right rep durations should be compared. |
| `temporal.variability.tempo_cv` | temporal | dimensionless_cv | set | Coefficient of variation of rep durations within the set. High values may indicate alternating-limb timing asymmetry or fatigue effects. |
| `control.stability.hip_center_x_std` | control | torso_length_ratio | rep / phase | Standard deviation of hip-center lateral displacement. In lunge, elevated values reflect poor medial-lateral CoM control during the split-stance transition. |
| `control.stability.hip_center_z_std` | control | torso_length_ratio | rep / phase | Standard deviation of hip-center vertical displacement. Reflects smoothness of the descent/ascent trajectory in the sagittal plane. |
| `control.compensation.knee_valgus.left` | control | torso_length_ratio | rep | Peak medial knee deviation (left) from the frontal-plane hip-ankle line. In lunge, valgus is more likely during the high-load descent phase of the forward leg. |
| `control.compensation.knee_valgus.right` | control | torso_length_ratio | rep | Peak medial knee deviation (right). Comparing left and right across alternating reps quantifies inter-limb valgus asymmetry. |
| `control.compensation.excessive_trunk_flexion` | control | degree | rep | Peak trunk lean from the vertical axis. Excessive lean in lunge is frequently a secondary compensation for restricted forward-leg ankle dorsiflexion. |
| `control.compensation.lateral_pelvic_shift` | control | torso_length_ratio | rep | Peak lateral pelvis displacement from the rep-mean baseline. In split-stance, lateral shift indicates difficulty maintaining pelvic alignment over the base of support. |
| `control.compensation.heel_lift.left` | control | torso_length_ratio | rep | Peak left heel elevation above rep-minimum. In lunge, forward-leg heel lift indicates ankle dorsiflexion restriction; trailing-leg heel lift is typically expected during descent. |
| `control.compensation.heel_lift.right` | control | torso_length_ratio | rep | Peak right heel elevation; context (forward vs. trailing leg) must be inferred from the alternating annotation. |

---

## Pike Push-up

| feature_id | domain | unit | level | clinical_meaning |
|---|---|---|---|---|
| `spatial.rom.left_shoulder_angle` | spatial | degree | rep / phase | Left shoulder sagittal ROM (hip–shoulder–elbow angle, vertex at shoulder). Restricted ROM reflects limited shoulder-flexion range under load. |
| `spatial.rom.right_shoulder_angle` | spatial | degree | rep / phase | Right shoulder sagittal ROM; compared with the left to detect bilateral shoulder-mobility asymmetry. |
| `spatial.rom.left_elbow_angle` | spatial | degree | rep / phase | Left elbow sagittal ROM. Restricted elbow ROM limits head descent and may indicate elbow-flexor strength or mobility limitation. |
| `spatial.rom.right_elbow_angle` | spatial | degree | rep / phase | Right elbow sagittal ROM; bilateral comparison reveals lateral loading asymmetry at the elbow. |
| `spatial.rom.left_hip_angle` | spatial | degree | rep / phase | Left hip angle in the piked position. Variation reflects pelvic-tilt strategy and trunk stiffness during the push movement. |
| `spatial.rom.right_hip_angle` | spatial | degree | rep / phase | Right hip angle; bilateral comparison detects pelvic asymmetry during the inverted support. |
| `spatial.symmetry.shoulder` | spatial | dimensionless_cv | rep | L/R shoulder ROM symmetry index. Asymmetry indicates unequal load distribution between the two arms, a risk factor for shoulder overuse. |
| `spatial.symmetry.elbow` | spatial | dimensionless_cv | rep | L/R elbow ROM symmetry index. Elbow asymmetry often co-occurs with shoulder asymmetry and reflects hand-position compensation. |
| `spatial.symmetry.hip` | spatial | dimensionless_cv | rep | L/R hip angle symmetry index in the piked position. Non-zero values indicate pelvic lateral tilt during the inverted support phase. |
| `spatial.shape.arc_length.left_shoulder` | spatial | torso_length_ratio | rep / phase | Arc length of the left shoulder trajectory. Elevated arcs suggest scapular winging or shoulder collapse rather than pure sagittal descent. |
| `spatial.shape.arc_length.right_shoulder` | spatial | torso_length_ratio | rep / phase | Arc length of the right shoulder trajectory; asymmetry with the left reveals unilateral scapular instability. |
| `spatial.shape.arc_length.left_elbow` | spatial | torso_length_ratio | rep / phase | Arc length of the left elbow trajectory. Non-linear paths indicate elbow-flare or inward-drift compensation during the push phase. |
| `spatial.shape.arc_length.right_elbow` | spatial | torso_length_ratio | rep / phase | Arc length of the right elbow trajectory; bilateral comparison detects asymmetric elbow tracking. |
| `spatial.shape.arc_length.left_wrist` | spatial | torso_length_ratio | rep / phase | Arc length of the left wrist trajectory. Wrist arcs reflect hand-position stability; elevated values indicate contact-point drift. |
| `spatial.shape.arc_length.right_wrist` | spatial | torso_length_ratio | rep / phase | Arc length of the right wrist trajectory; compared with the left to detect asymmetric hand-contact instability. |
| `spatial.phase_rom_ratio.descent_ascent` | spatial | dimensionless | rep | Ratio of mean Descent ROM to mean Ascent ROM. Values > 1 suggest greater range during the eccentric (lowering) phase, reflecting a controlled descent strategy. |
| `temporal.tempo.rep_*` | temporal | second | rep | Duration of each individual rep. In pike push-up, slower reps increase time under tension; abrupt shortening may indicate fatigue-related form breakdown. |
| `temporal.variability.tempo_cv` | temporal | dimensionless_cv | set | Coefficient of variation of rep durations within the set. Temporal inconsistency in upper-body push tasks often precedes form deterioration. |
| `control.stability.hip_center_x_std` | control | torso_length_ratio | rep / phase | Standard deviation of hip-center lateral displacement. In the piked posture, lateral hip sway indicates trunk or core instability during the upper-body push. |
| `control.stability.hip_center_z_std` | control | torso_length_ratio | rep / phase | Standard deviation of hip-center vertical displacement in the piked posture. Reflects how well the hip position is maintained during the push cycle. |

> **Note — pending compensation features.** The following pike push-up candidates are registered
> in the exercise YAML but do not yet have an implemented rule in `COMPENSATION_RULES`:
> `elbow_flare`, `elbow_asymmetry`, `shoulder_asymmetry`, `shoulder_collapse`,
> `shoulder_elevation_compensation`, `scapular_instability_proxy`, `insufficient_head_descent`,
> `head_forward_shift`, `hip_drop`, `hip_pike`, `lateral_trunk_lean`.
> They will be added to this table once rules are implemented.

---

## Plank Shoulder Tap

| feature_id | domain | unit | level | clinical_meaning |
|---|---|---|---|---|
| `spatial.rom.left_shoulder_angle` | spatial | degree | rep / phase | Left shoulder angle in the plank position (hip–shoulder–elbow). Variation across reps indicates trunk-position drift during the anti-rotation task. |
| `spatial.rom.right_shoulder_angle` | spatial | degree | rep / phase | Right shoulder angle; bilateral comparison detects asymmetric scapular loading during the alternating tap. |
| `spatial.rom.left_elbow_angle` | spatial | degree | rep / phase | Left elbow angle in the plank-support position. Elbow-angle variation reflects support-arm stability during the contralateral tap phase. |
| `spatial.rom.right_elbow_angle` | spatial | degree | rep / phase | Right elbow angle; compared with the left to detect asymmetric support-arm mechanics. |
| `spatial.rom.left_hip_angle` | spatial | degree | rep / phase | Left hip angle in the plank position. Changes across phases indicate hip-flexion compensation when core stability is compromised. |
| `spatial.rom.right_hip_angle` | spatial | degree | rep / phase | Right hip angle; bilateral comparison detects pelvic lateral tilt during the one-hand-off support. |
| `spatial.symmetry.shoulder` | spatial | dimensionless_cv | rep | L/R shoulder angle symmetry index across all reps. Asymmetry indicates unequal scapular loading between the support arm and the tapping arm. |
| `spatial.symmetry.elbow` | spatial | dimensionless_cv | rep | L/R elbow angle symmetry index. Elbow asymmetry in plank often reflects compensatory elbow repositioning under lateral CoM shift. |
| `spatial.symmetry.hip` | spatial | dimensionless_cv | rep | L/R hip angle symmetry index. Non-zero values indicate persistent pelvic tilt, a common trunk-instability compensation in this exercise. |
| `spatial.shape.arc_length.left_wrist` | spatial | torso_length_ratio | rep / phase | Arc length of the left wrist trajectory. During a left-tap rep the active wrist should have the larger arc; elevated values on the support wrist indicate contact instability. |
| `spatial.shape.arc_length.right_wrist` | spatial | torso_length_ratio | rep / phase | Arc length of the right wrist trajectory; compared with the left to confirm which side is the tapping hand per rep. |
| `spatial.shape.arc_length.left_shoulder` | spatial | torso_length_ratio | rep / phase | Arc length of the left shoulder trajectory. Large arcs in the frontal plane indicate lateral trunk lean compensation during the tap. |
| `spatial.shape.arc_length.right_shoulder` | spatial | torso_length_ratio | rep / phase | Arc length of the right shoulder trajectory; bilateral comparison detects asymmetric trunk sway driven by alternating limb loading. |
| `temporal.tempo.rep_*` | temporal | second | rep | Duration of each individual tap cycle. Rhythm consistency is a key quality indicator for this anti-rotation stability task. |
| `temporal.variability.tempo_cv` | temporal | dimensionless_cv | set | Coefficient of variation of tap-cycle durations. High variability suggests difficulty maintaining a stable movement rhythm under the anti-rotation demand. |
| `control.stability.hip_center_x_std` | control | torso_length_ratio | rep / phase | Standard deviation of hip-center lateral displacement. This is the primary stability metric for plank shoulder tap; elevated values directly reflect failure to control medial-lateral CoM shift during the tap. |
| `control.stability.hip_center_z_std` | control | torso_length_ratio | rep / phase | Standard deviation of hip-center vertical displacement in the plank posture. Non-zero variation indicates vertical trunk oscillation, often secondary to hip-drop or hip-lift compensation. |
| `control.compensation.pelvic_rotation` | control | torso_length_ratio | rep | Peak left-right hip depth asymmetry (transverse-plane proxy). In plank shoulder tap, pelvic rotation is the most direct compensation for insufficient anti-rotation core control. |
| `control.compensation.lateral_pelvic_shift` | control | torso_length_ratio | rep | Peak lateral pelvis displacement from the rep-mean baseline. Reflects the degree to which body weight shifts laterally toward the support arm during the one-hand-off phase. |

> **Note — pending compensation features.** The following plank shoulder tap candidates are
> registered in the exercise YAML but do not yet have an implemented rule in `COMPENSATION_RULES`:
> `trunk_rotation`, `lateral_trunk_lean`, `hip_drop`, `shoulder_collapse`, `shoulder_asymmetry`,
> `excessive_com_lateral_shift`, `excessive_com_variability`, `left_right_timing_variability`,
> `phase_timing_asymmetry`, `movement_discontinuity`.
> They will be added to this table once rules are implemented.

---

## Cross-Exercise Summary

| feature_id prefix | exercises active | domain | notes |
|---|---|---|---|
| `spatial.rom.*` | all 4 | spatial | Joints differ by exercise (lower-body for squat/lunge; upper-body + hip for pike_pushup / plank_shoulder_tap) |
| `spatial.symmetry.*` | all 4 | spatial | Pairs derived from `left_` / `right_` entries in `angle_definitions` |
| `spatial.shape.arc_length.*` | all 4 | spatial | Joints from `landmarks.primary_joints`; differ by exercise |
| `spatial.phase_rom_ratio.descent_ascent` | squat, lunge, pike_pushup | spatial | Not emitted for plank_shoulder_tap (phases: Lift / Tap / Return) |
| `temporal.tempo.rep_*` | all 4 | temporal | |
| `temporal.variability.tempo_cv` | all 4 | temporal | Requires ≥ 2 reps |
| `control.stability.hip_center_x_std` | all 4 | control | CoM lateral stability proxy |
| `control.stability.hip_center_z_std` | all 4 | control | CoM vertical stability proxy |
| `control.compensation.knee_valgus.*` | squat, lunge | control | Lower-body frontal-plane compensation |
| `control.compensation.knee_varus.*` | squat | control | Lower-body lateral knee deviation |
| `control.compensation.excessive_trunk_flexion` | squat, lunge | control | Trunk-lean compensation (standing exercises) |
| `control.compensation.lateral_pelvic_shift` | squat, lunge, plank_shoulder_tap | control | |
| `control.compensation.heel_lift.*` | squat, lunge | control | Ankle dorsiflexion restriction proxy |
| `control.compensation.pelvic_rotation` | squat, plank_shoulder_tap | control | Transverse-plane pelvic asymmetry proxy |
