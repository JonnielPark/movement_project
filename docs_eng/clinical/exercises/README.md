# Per-Exercise Clinical Rationale

**Document Version:** 1.1.3
**Last Updated:** 2026-07-14
**Korean Sync:** `docs/clinical/exercises/README.md` is the same-version Korean source.

This folder stores biomechanical interpretation rationale for the current squat
example and retained prior exercise-definition examples. Here,
"clinical" means expert movement-observation context, not disease diagnosis,
treatment-effect evidence, or patient classification.

Squat is an illustrative single-block repeated-exercise example. Korean National
Gymnastics is an illustrative draft multi-block sequence example represented by
an exercise-session definition and section-level draft exercise definitions.
These examples do not define the framework's exercise limits.

These documents are not execution specifications. The execution source is YAML
and code. Rationale text may inform future `compensation_patterns`,
`analysis_disrupting_patterns`, feature registries, or scoring rules only after
the pipeline docs are updated first.

---

## 1. Document List

| Exercise | Status | Rationale | Exercise YAML | Performance protocol |
|---|---|---|---|---|
| Squat | Illustrative single-block repeated-exercise example | [squat.md](squat.md) | [squat.yaml](../../../data/definitions/exercises/squat.yaml) | [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md) |
| Korean National Gymnastics | Illustrative draft multi-block sequence example | [korean_national_gymnastics.md](korean_national_gymnastics.md) | [korean_national_gymnastics.yaml](../../../data/definitions/exercise_sessions/korean_national_gymnastics.yaml) | pending section protocol |
| Lunge | Retained prior example artifact | [lunge.md](lunge.md) | [lunge.yaml](../../../data/definitions/exercises/lunge.yaml) | [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md) |
| Pike Push-up | Retained prior example artifact | [pike_pushup.md](pike_pushup.md) | [pike_pushup.yaml](../../../data/definitions/exercises/pike_pushup.yaml) | [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md) |
| Plank Shoulder Tap | Retained prior example artifact | [plank_shoulder_tap.md](plank_shoulder_tap.md) | [plank_shoulder_tap.yaml](../../../data/definitions/exercises/plank_shoulder_tap.yaml) | [exercise_performance_protocol.md](../../practical_protocols/exercise_performance_protocol.md) |

## 2. Promotion Rule

When a rationale item becomes a computational rule:

```text
1. Define the feature, unit, confidence/provenance policy in docs_eng/pipeline/ and docs/pipeline/.
2. Add or update YAML: analysis profile, performance protocol, camera protocol, or interpretation rule.
3. Implement the code with tests.
4. Update per-exercise mapping only for implemented behavior.
```

Do not let a rationale paragraph become a hidden scoring rule.

## 3. Shared Labels

| Label | Meaning |
|---|---|
| Score-eligible feature | Pattern likely identifiable from joint-point time series and eligible for future feature/biomarker linkage |
| Control factor | Pattern that is hard to separate from acquisition behavior or pose uncertainty |
| Interpretation-limitation factor | Pattern that should be displayed as a confidence limitation, not a direct penalty |
| High detectability | Relatively clear under current landmarks and recommended view |
| Medium detectability | Requires suitable view, confidence, or annotation support |
| Low detectability | Difficult from pose time series alone or needs external information |

## 4. Side-View Rule

In unilateral tasks and side-view recordings, far-side joints may be reliable or
may degrade because of occlusion and left/right overlap. If far-side confidence
or jitter is poor, treat the affected feature as unavailable or low-confidence
rather than poor movement quality.

Bilateral symmetry features are interpreted only when both sides have sufficient
coverage and view support. Otherwise, prioritize centerline or visible-side
features such as `hip_center`, `shoulder_center`, trunk angle, vertical motion,
and visible-side sagittal ROM.

## 5. Asset Policy

Representative performance photos stay in:

```text
docs/practical_protocols/assets/
docs_eng/practical_protocols/assets/
```

Exercise-interpretation figures go under:

```text
docs/clinical/exercises/assets/<exercise_id>/
docs_eng/clinical/exercises/assets/<exercise_id>/
```

Use the same filename in both languages when a figure has no embedded text. Use
`*_ko.png` and `*_eng.png` when labels are language-specific.
