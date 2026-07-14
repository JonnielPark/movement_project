# Korean National Gymnastics Rationale

**Document Version:** 0.1.4
**Last Updated:** 2026-07-14
**Korean Sync:** `docs/clinical/exercises/korean_national_gymnastics.md` is the same-version Korean source.

This document summarizes the conventional Korean National Gymnastics sequence
and how it is represented as a draft multi-block exercise-session example. It is
not a diagnostic standard, not a health-effect claim, and not a code
specification.

Related:

- Exercise session YAML: [korean_national_gymnastics.yaml](../../../data/definitions/exercise_sessions/korean_national_gymnastics.yaml)
- Section exercise YAMLs: `data/definitions/exercises/korean_national_gymnastics_*.yaml`
- Indexed section analysis profiles: `data/definitions/analysis_profiles/korean_national_gymnastics.yaml`
- Shared camera protocol: `data/protocols/camera/korean_national_gymnastics.yaml`
- Reference source: [Korean Wikipedia, 국민체조](https://ko.wikipedia.org/wiki/%EA%B5%AD%EB%AF%BC%EC%B2%B4%EC%A1%B0), accessed 2026-07-14

---

## 1. Study Role

Korean National Gymnastics is used as an illustrative multi-block sequence
example. Its role is methodological: it tests whether the framework can compose
multiple reviewed exercise definitions into one ordered session without creating
a separate "mixed exercise" category or hardcoded pipeline branch.

The exercise choice does not define the framework's scope. The same analysis
architecture should remain driven by exercise definitions, analysis profiles,
camera protocols, performance protocols, feature-availability policy, and scoring
policy.

## 2. Conventional Sequence Context

The commonly described Korean National Gymnastics routine was disseminated in
South Korea from 1977 and is conventionally treated as a 12-movement calisthenic
sequence performed with music and verbal counting. The public sequence also
includes a preparation cue, usually represented as marching in place, before the
12 main movement sections.

In the current project, preparation is treated as setup/reference context rather
than an analyzable session block. Data acquisition and analysis both start from
the repeated pass, and the initial pass through breathing-to-jumping is not part
of this project session. The executable draft session follows the 12-block order
listed in the current-analysis column below.

| Conventional order | Section ID | Korean section name | Conventional movement cue | Current analysis status |
|---|---|---|---|---|
| 0 | setup_reference | 준비 | marching in place | setup only; not acquired/analyzed as a session block |
| 1 | breathing_start | 숨쉬기 | raise arms forward and lower outward with breathing | analysis block 01 |
| 2 | leg | 다리운동 | bend and extend the knees | analysis block 02 |
| 3 | arm | 팔운동 | raise, swing, and circle the arms | analysis block 03 |
| 4 | neck | 목운동 | rotate the neck | analysis block 04 |
| 5 | chest | 가슴운동 | open/extend the chest | analysis block 05 |
| 6 | side | 옆구리운동 | bend the trunk left and right | analysis block 06 |
| 7 | back_abdomen | 등배운동 | bend forward and extend backward | analysis block 07 |
| 8 | trunk | 몸통운동 | twist the trunk side to side | analysis block 08 |
| 9 | whole_body | 온몸운동 | whole-body rowing or pulling-like motion | analysis block 09 |
| 10 | jumping | 뜀뛰기 | jumping section | analysis block 10 |
| 11 | limbs | 팔다리운동 | swing arms, bend knees, and lift one foot | analysis block 11 |
| 12 | breathing_cooldown | 숨고르기 | raise arms and regulate breathing | analysis block 12 |

The table above records conventional section labels and broad movement cues only.
It does not define final segmentation, thresholds, or score eligibility.

## 3. Execution Context

| Item | Current setting | Interpretation intent |
|---|---|---|
| Session type | ordered composition of 12 acquired/analyzed section definitions | validate repeat-pass sequencing and section provenance |
| Classification | standing, mostly bilateral, multi-plane calisthenic sequence | preserve section-specific movement identity |
| Segmentation | section/event model pending | avoid forcing every section into squat-like repetition logic |
| Performance | repeat-pass acquisition/analysis session, `repeat_count: 1` per section | show composition rather than volume prescription |
| Rest | `rest_between_blocks_s: 0` in the draft session | continuous routine by default |
| Camera | Z1, H2 | frontal waist-height whole-body coverage |
| Biomech focus | relative joint/segment motion, timing, symmetry, stability | no absolute force/torque or clinical outcome inference |

Execution source of truth remains YAML. This rationale document explains why the
draft exists and what should be reviewed next.

The section exercise YAMLs intentionally share one camera protocol and one
indexed analysis-profile file. Camera settings do not change across the
continuous recording, while the profile file begins with an `index` and keeps
section-level analysis entries separate under `profiles`.

## 4. Observation Targets

```text
section order                 fixed progression across 12 acquired/analyzed blocks
section boundary timing        start/end consistency per section
tempo and smoothness           rhythm continuity within and across sections
bilateral upper-limb symmetry  arm path and range consistency
trunk centerline control       lateral bend, rotation, forward/back extension
lower-limb support pattern     knee bend/extension, one-foot lift, jumping rhythm
whole-body coordination        synchronized upper/lower body movement
```

These are candidate observation targets. They become computational features only
after the pipeline docs, section analysis profiles, and tests define units,
confidence handling, and availability rules.

## 5. Candidate Movement-Quality Patterns

| Pattern | Interpretation direction | Detectability | Status |
|---|---|---|---|
| section order error | expected sequence does not match the fixed routine | high with section annotation | review candidate |
| incomplete section transition | section boundary or movement cue is skipped | medium; annotation or event model needed | review candidate |
| asymmetric arm path | left/right upper-limb range or path mismatch | medium-high in frontal view | review candidate |
| excessive trunk bias | persistent lateral, rotational, or forward/back deviation | medium; section-dependent | review candidate |
| unstable support | foot repositioning or poor support consistency outside the intended cue | medium | review candidate |
| jump rhythm inconsistency | irregular jump timing or landing pattern | medium; event model needed | review candidate |
| camera-facing direction change | body turns away from the expected frontal view | high with metadata/video review | control/limitation factor |
| low landmark confidence in neck or arms | pose uncertainty limits section interpretation | medium | interpretation-limitation factor |

The terms above describe movement-quality proxies and data-quality limitations,
not diagnoses.

## 6. View And Quality Limits

The current draft recommends frontal view (`Z1`) at waist height (`H2`). This is
appropriate for whole-body coverage, left/right comparison, arm-path review, and
gross frontal trunk movement.

Frontal view is weaker for depth-sensitive sagittal interpretation, especially
forward/back trunk motion and some jumping or landing details. These features
should remain low-confidence or report-only until section-specific
feature-availability policy is reviewed.

Neck movement is also constrained by the available pose landmarks. Head and
shoulder landmarks can support coarse movement review, but detailed cervical
range-of-motion claims should not be made from this pipeline without additional
validation.

## 7. Development Boundary

Before Korean National Gymnastics becomes a canonical runtime example:

```text
1. Review one section at a time and replace placeholder phase/event models.
2. Define section-level count units or event labels where needed.
3. Add performance protocol files only after section execution expectations are reviewed.
4. Expand camera view-metric reliability beyond the current Z1/H2 draft.
5. Define feature availability and scoring eligibility before enabling scores.
6. Add tests for each promoted section model.
```

Until those steps are complete, Korean National Gymnastics remains a useful
composition example and a structured authoring target, not a finalized scoring
exercise.
