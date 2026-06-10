# Squat Clinical Rationale

**Document Version:** 1.2.0
**Last Updated:** 2026-06-10
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

## 6. p01 Squat Feature-Domain Table

This table is the current p01 squat gate before any corrected coordinate can be
used by feature extraction, biomechanical proxies, or scoring. `corrected_3d_hypothesis`
rows are review candidates only while `feature_depth_gravity = 0.0`.

| feature_id | evaluation_domain | source_evidence | active_constraints | cap_strength | expected_output | confidence/burden rule |
|---|---|---|---|---|---|---|
| `spatial.rom.left_hip_angle`, `spatial.rom.right_hip_angle` | `recording_view_only` | `norm` camera-plane hip/shoulder/knee trajectory; phase labels when available | visible hip/knee/shoulder, valid rep/phase segmentation, view supports sagittal motion | none | degree ROM per rep/phase | Use as scoring candidate only when source landmarks are visible and no swap/far-side warning dominates. |
| `spatial.rom.left_knee_angle`, `spatial.rom.right_knee_angle` | `recording_view_only` | `norm` camera-plane hip-knee-ankle trajectory | visible hip/knee/ankle, valid rep/phase segmentation, no bend-flip provenance flag | none | degree ROM per rep/phase | If knee bend-side or far-side evidence is unstable, keep value as provenance or `low_confidence`. |
| `spatial.rom.left_ankle_angle`, `spatial.rom.right_ankle_angle` | `recording_view_only` | `norm` camera-plane knee-ankle-foot trajectory | visible knee/ankle/foot, heel/foot visibility, valid rep/phase segmentation | none | degree ROM per rep/phase | Withhold or lower confidence when foot landmarks are unstable or support-contact evidence is weak. |
| `spatial.symmetry.hip`, `spatial.symmetry.knee`, `spatial.symmetry.ankle` | `dual_domain_compare` | left/right recording-view ROM; optional corrected candidate comparison later | bilateral squat context, both sides sufficiently visible, no high correction burden | report-only delta for corrected comparison | dimensionless symmetry index | Score recording-view symmetry only when both sides are view-supported; report norm-vs-corrected delta before any corrected use. |
| `spatial.shape.arc_length.left_hip`, `spatial.shape.arc_length.right_hip` | `recording_view_only` | `norm` camera-plane hip trajectory | valid rep/phase segmentation, hip visibility | none | trajectory arc length in torso-length ratio | Lower confidence when pelvis visibility or segmentation is unstable. |
| `spatial.shape.arc_length.left_knee`, `spatial.shape.arc_length.right_knee` | `recording_view_only` | `norm` camera-plane knee trajectory | visible knee, valid rep/phase segmentation, view supports knee tracking | none | trajectory arc length in torso-length ratio | Treat far-side knee arc as `low_confidence` when occlusion/swap risk is high. |
| `spatial.shape.arc_length.left_ankle`, `spatial.shape.arc_length.right_ankle` | `dual_domain_compare` | recording-view ankle trajectory; optional support-memory candidate comparison | closed-chain support context, ankle/foot visibility, planted-support provenance | report-only corrected delta | trajectory arc length in torso-length ratio | Use recording-view score only when support landmarks are stable; corrected support-memory comparison is burden provenance only. |
| `spatial.phase_rom_ratio.descent_ascent` | `recording_view_only` | phase-level ROM records from confirmed descent/ascent labels | valid phase segmentation and sufficient ROM records in both phases | none | descent/ascent ratio | Withhold when phase segmentation is failed, manually uncertain, or too short. |
| `temporal.tempo.rep_*`, `temporal.variability.tempo_cv` | `recording_view_only` | timestamps and rep boundaries | valid annotation or accepted rep segmentation | none | seconds; dimensionless CV | Depth is irrelevant; availability depends on rep boundary reliability. |
| `control.stability.hip_center_x_std` | `recording_view_only` | `norm` camera-plane hip-center lateral trajectory | visible bilateral hips, valid rep/phase segmentation | none | torso-length ratio | Scoring candidate when pelvis x trajectory is visible and not dominated by swap/interpolation. |
| `control.stability.hip_center_z_std` | `dual_domain_compare` | current model-depth axis plus future corrected candidate comparison | depth evidence is low-confidence; require norm-vs-corrected sensitivity before scoring | score-excluded corrected depth | torso-length ratio | Do not use corrected depth for score while `feature_depth_gravity = 0.0`; report sensitivity and availability. |
| `control.compensation.knee_valgus.left`, `control.compensation.knee_valgus.right` | `recording_view_only` | camera-plane knee deviation from hip-ankle line | frontal/front-oblique view support, visible hip/knee/ankle | none | peak medial deviation in torso-length ratio | Score only when view supports frontal knee tracking; side-view results are provenance or `not_assessed`. |
| `control.compensation.knee_varus.left`, `control.compensation.knee_varus.right` | `recording_view_only` | camera-plane knee deviation from hip-ankle line | same as knee valgus; stance width reviewed as context | none | peak lateral deviation in torso-length ratio | Lower confidence when support stance is view-sensitive or far-side landmarks are unreliable. |
| `control.compensation.excessive_trunk_flexion` | `recording_view_only` | camera-plane shoulder-hip trunk line | visible shoulders/hips, view supports sagittal trunk lean | none | peak trunk angle in degrees | Score as sagittal/centerline feature when shoulder/hip landmarks are stable. |
| `control.compensation.lateral_pelvic_shift` | `recording_view_only` | `norm` camera-plane hip-center lateral displacement | bilateral hip visibility, valid rep segmentation | none | peak lateral displacement in torso-length ratio | Lower confidence when pelvis center is unstable due to landmark quality. |
| `control.compensation.heel_lift.left`, `control.compensation.heel_lift.right` | `dual_domain_compare` | recording-view heel/ankle/foot height; optional support-surface candidate comparison | closed-chain support context, heel visibility, foot support provenance | soft support-contact cap for review only | peak heel elevation in torso-length ratio | Recording-view value may score if heel is visible; corrected support-surface comparison is burden provenance only. |
| `control.compensation.pelvic_rotation` | `corrected_3d_hypothesis` | left/right hip model-depth asymmetry and future corrected candidate | depth-sensitive; require correction burden, residual, and sensitivity report | score-excluded while depth gravity is zero | hip-depth asymmetry in torso-length ratio | Do not score in the current public path; use as low-confidence corrected-3D review only. |
| `biomech.com.range_x`, `biomech.com.path_length` | `recording_view_only` | normalized camera-plane CoM proxy from segment ratios | visibility weighting, valid rep segmentation | none | torso-length ratio | Score as relative proxy only; no absolute force/torque interpretation. |
| `biomech.com.range_z` | `dual_domain_compare` | model-depth CoM proxy and future corrected candidate comparison | depth-sensitive; visibility weighting; burden report required before corrected use | score-excluded corrected depth | torso-length ratio | Keep as provenance or low-confidence until multi-video sensitivity supports use. |
| `biomech.moment_arm.knee.<side>.median`, `biomech.moment_arm.hip.<side>.median` | `recording_view_only` | 2D recording-view CoM-to-joint proxy | view-supported joint/CoM projection, visibility weighting | none | torso-length ratio | Relative load-distribution proxy only; do not infer absolute torque. |
| `candidate.support_width_stability` | `corrected_3d_hypothesis` | corrected support anchors compared with recording-view ankle width | closed-chain support context, support-width residual, planted-support memory | soft cap plus hard not-assessed on high burden | review metric, not score | First depth-sensitive review candidate; report norm/corrected delta and burden before any feature promotion. |
| `candidate.segment_length_stability.shank`, `candidate.segment_length_stability.thigh` | `corrected_3d_hypothesis` | corrected candidate segment lengths versus skeleton envelope/session memory | anthropometric skeleton envelope, segment memory, visibility, residual | soft envelope; hard invalid/not-assessed boundary | review metric, not score | Use to decide availability/confidence of corrected candidates, not movement quality. |

## 7. Development Boundary

If a rationale item becomes a scoring feature:

```text
1. Define feature/unit/provenance in pipeline docs.
2. Link YAML candidate or interpretation rule.
3. Add minimal tests for reproducible detectability.
4. Update per-exercise mapping only after implementation.
```
