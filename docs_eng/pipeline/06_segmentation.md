# 06. Segmentation

**Document Version:** 1.3.1
**Last Updated:** 2026-06-10
**Korean Sync:** `docs/pipeline/06_segmentation.md` is the same-version Korean source.

Pipeline step ⑥ confirms repetition boundaries and intra-rep phase labels. It is
named `Segmentation` because it covers both reps and phases. The existing
`phase_segmentation` YAML/code key remains dedicated to phase splitting, while
`rep_segmentation` handles repetition boundaries.

This step does not modify coordinates or delete frames.

---

## 1. Pipeline Position

```text
⑤ Normalization → ⑥ Segmentation ← this step → ⑦ Motion Attribution
```

Inputs:

```text
normalized dataframe       from ⑤
annotation metadata        set_id, rep_id, phase, use_for_analysis when available
exercise definition        rep_segmentation and phase_segmentation settings
```

Outputs:

```text
rep_id
rep_segmentation_status        not_run | success | failed | manual_override | skipped
rep_segmentation_source        annotation | semi_auto | manual_override | fallback
rep_segmentation_failure_id
phase
phase_segmentation_status      not_run | success | failed | manual_override | skipped
phase_segmentation_source      annotation | semi_auto | manual_override | fallback
phase_segmentation_failure_id
```

Manual labels from ② Annotation are treated as candidate or confirmed labels and
are never silently overwritten.

---

## 2. Strategy

```text
rep_segmentation
    Estimates repetition start/end boundaries and confirms rep_id.

phase_segmentation
    Estimates phase boundaries inside confirmed reps and fills phase labels.
```

Both blocks use exercise-defined reference landmarks, axes, expected phase order,
and minimum-length settings. Automatic segmentation is rejected when visibility,
ROM, candidate boundary count, boundary order, or manual-label consistency is
unclear.

---

## 3. Status And Failure Policy

```text
success
    Accepted intervals satisfy minimum_reps and minimum_rep_length_frames.

failed
    Required landmarks/axes are unavailable, candidate boundaries are missing,
    intervals are too short, candidate order is invalid, or accepted intervals
    are fewer than minimum_reps.

skipped
    Required segmentation config is absent or the stage is disabled.

manual_override
    A researcher-confirmed label resolves a failure or overrides an automatic
    candidate.
```

Failure levels:

```text
rep_boundary
    Rep cannot be confirmed. Affected range is excluded from rep-level and
    phase-level outputs until manually resolved.

phase_boundary
    Rep is confirmed, but phase boundaries are unclear. Rep-level metrics remain;
    phase-level records are withheld for that rep.

optional_phase
    Optional phase such as Turnaround_Hold is unclear. Continue with coarse
    phases and record the skipped optional phase.
```

---

## 4. Failure Point Contract

```text
failure_id
failure_level          rep_boundary | phase_boundary | optional_phase
set_id, rep_id
start_frame, end_frame
candidate_frame
reason                 low_visibility | insufficient_rom | missing_candidate |
                       multiple_candidates | order_mismatch | manual_required
confidence
pipeline_action        exclude_range | rep_level_only | coarse_phase_continue |
                       wait_for_manual_override
resolved
resolution_note
```

Failure points are provenance. They are not interpolated into success.

---

## 5. Manual Intervention

Manual intervention confirms labels for a failure point without changing
coordinate values.

```text
rep_segmentation_status / phase_segmentation_status = manual_override
rep_segmentation_source / phase_segmentation_source = manual_override
```

Downstream stages use the confirmed labels and retain the correction reason and
reviewer note.

---

## 6. Recording-Plane Phase Split Artifact

For real one-take MediaPipe recordings, a recording-plane phase split may be
created beside the annotation file before being promoted to confirmed annotation.
This is useful when MediaPipe `z` is a depth proxy and raw image/recording-plane
signals are safer for visual QC.

Before promotion, `<recording_id>_phase_split.csv` is a recording-specific guide
for inspection only. It must not be treated as ground-truth phase annotation or
used for scoring.

```text
source annotation    <recording_id>_annotation.csv
candidate output     <recording_id>_phase_split.csv
confirmed output     <recording_id>_phase_annotation.csv
reference signal     hip_center_y in raw image/recording coordinates
```

Stable helpers:

```text
generate_recording_plane_phase_split
validate_phase_split_for_promotion
promote_phase_split_to_annotation
```

Promotion requires exact rep coverage, no phase gaps/overlaps, correct phase
order, preserved filming provenance, and visual QC. Until additional real samples
and robustness evidence support promotion, this remains an annotation-adjacent QC
workflow rather than the generic pipeline default.

---

## 7. Downstream Rules

```text
⑦ Motion Attribution   uses confirmed rep_id.
⑧ Feature Extraction   emits rep-level features for confirmed reps and phase-level
                       features only for successful/manual phases.
⑨ Biomech Proxy        excludes unresolved rep-boundary failures.
⑩ Biomarker Scoring    keeps failure/exclusion provenance.
⑪ Visualization        shows failure points and manual boundaries.
```

---

## 8. Verification Targets

```text
tests/test_phase_segmentation.py
    nominal phase split, rejected short reps, multi-inflection policy, annotation
    override behavior.

tests/test_features_phase_grouping.py
    phase-level FeatureRecord provenance.

tests/test_recording_phase_split.py
    recording-plane artifact generation and promotion validation.
```
