# Per-Exercise Clinical Rationale

**Document Version:** 1.0.3
**Last Updated:** 2026-05-11
**Korean Sync:** `docs/clinical/exercises/README.md` is the same-version Korean source.

This folder provides detailed biomechanical and clinical-interpretation rationale
for the four target exercises. Here, "clinical" does not mean disease diagnosis
or treatment-effect evidence. It means observation perspectives and biomechanical
interpretation points that clinicians or movement experts may use when reviewing
movement quality.

These documents are not development specifications. They may inform future
`compensation_candidates`, `analysis_disrupting_patterns`, feature registry, or
scoring rules. When an item is promoted to a computational rule, first document the
feature definition and provenance policy in `docs_eng/pipeline/` and `docs/pipeline/`,
then update YAML and code in that order.

The `Analysis Parameter Summary` section in each exercise document explains the key
exercise-YAML settings from an interpretation perspective. The execution source of
truth is always the linked `data/definitions/exercises/<exercise_id>.yaml` file.

---

## Document List

| Exercise | Detailed Document | Exercise YAML | Current Performance Protocol |
|---|---|---|---|
| Squat | [squat.md](squat.md) | [squat.yaml](../../../data/definitions/exercises/squat.yaml) | [exercise_performance_protocol.md §2-1](../../practical_protocols/exercise_performance_protocol.md#2-1-squat) |
| Lunge | [lunge.md](lunge.md) | [lunge.yaml](../../../data/definitions/exercises/lunge.yaml) | [exercise_performance_protocol.md §2-2](../../practical_protocols/exercise_performance_protocol.md#2-2-lunge) |
| Pike Push-up | [pike_pushup.md](pike_pushup.md) | [pike_pushup.yaml](../../../data/definitions/exercises/pike_pushup.yaml) | [exercise_performance_protocol.md §2-3](../../practical_protocols/exercise_performance_protocol.md#2-3-pike-push-up) |
| Plank Shoulder Tap | [plank_shoulder_tap.md](plank_shoulder_tap.md) | [plank_shoulder_tap.yaml](../../../data/definitions/exercises/plank_shoulder_tap.yaml) | [exercise_performance_protocol.md §2-4](../../practical_protocols/exercise_performance_protocol.md#2-4-plank-shoulder-tap) |

---

## Asset Management

Images in `docs/practical_protocols/assets/` are representative example photos
used to help participants understand the movement. Keep those images in place.

Figures added for detailed exercise interpretation should be stored under:

```text
docs/clinical/exercises/assets/<exercise_id>/
docs_eng/clinical/exercises/assets/<exercise_id>/
```

Recommended rules:

1. Keep representative performance photos in `docs/practical_protocols/assets/`.
2. Put interpretation figures, such as joint-angle diagrams, compensation examples,
   landmark-visibility comparisons, and camera-view comparisons, in
   `docs/clinical/exercises/assets/<exercise_id>/`.
3. If a figure contains no embedded language, use the same filename and visual
   composition in both Korean and English document trees.
4. If a figure contains Korean or English labels, split filenames with `*_ko.png`
   and `*_eng.png`.
5. For annotated source images, record filming condition, camera zone, height, and
   participant cue in the caption or surrounding text.
6. Final dissertation figures should be managed separately from these explanation
   figures, under `outputs/figures/` or a future dissertation-figure policy.

---

## Shared Labels

| Label | Meaning |
|---|---|
| Scoring candidate | Pattern likely identifiable from joint-point time series and therefore eligible for future feature or biomarker linkage |
| Control factor | Pattern that is hard to separate from pose data or strongly acquisition-dependent; better handled as acquisition control than scoring |
| Interpretation-limitation factor | Pattern that does not necessarily invalidate the data but should be displayed as a confidence or interpretation limitation |
| High detectability | Relatively clear under the current landmarks and recommended camera view |
| Medium detectability | Observable only with a suitable camera view, visibility, or annotation support |
| Low detectability | Difficult to separate from pose time series alone or requires external information |

---

## Shared Considerations For Single Side-View Filming

In unilateral exercises and side-view filming of bilateral symmetric exercises,
far-side joints may be estimated well by the pose model, but they may also become
unstable because of occlusion or left-right overlap. If joint points are extracted
reliably, the regular features can be used without additional defensive logic.

If real filming repeatedly shows low visibility or high jitter for far-side joints,
treat those joints as feature-availability or interpretation-confidence issues
rather than poor movement quality. For side-view bilateral symmetric exercises,
centerline or visible-side features may be prioritized, such as `hip_center`,
`shoulder_center`, trunk angle, head/hip vertical displacement, and visible-side
sagittal ROM.

Bilateral symmetry features should be interpreted only when both sides have sufficient
coverage. If one side is occluded, do not penalize symmetry; mark that feature as
not assessed or low-confidence instead.
