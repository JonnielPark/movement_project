# 06. Segmentation

**Document Version:** 1.1.0
**Last Updated:** 2026-05-07
**Korean Sync:** `docs/pipeline/06_segmentation.md` is the same-version Korean source.

Pipeline step ⑥. Tracks normalized joint motion to split rep boundaries and phase
boundaries semi-automatically. This step is named `Segmentation`, not `Phase Segmentation`,
because it confirms both repetitions and intra-rep phases.
However, the existing `phase_segmentation` code identifier and YAML key remain dedicated
to phase splitting; the new repetition-boundary detector is separated as `rep_segmentation`.

Unclear automatic recognition is recorded as a `SegmentationFailurePoint` and confirmed
through manual intervention. This step does not delete frames or modify coordinates.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Segmentation          ← this step
→ ⑦ Motion Attribution
→ downstream steps
```

## 2. Inputs

```text
normalized dataframe   coordinates after ⑤ Normalization
annotation metadata    set_id, rep_id, use_for_analysis, and optional phase from ② Annotation
exercise definition    rep_segmentation and phase_segmentation settings from ③ Exercise Definition
```

## 3. Output Columns

```text
rep_id                         Int64     automatically/manually confirmed rep ID
rep_segmentation_status        str       not_run | success | failed | manual_override | skipped
rep_segmentation_source        str       annotation | semi_auto | manual_override | fallback
rep_segmentation_failure_id    str       nullable; links frames to the rep-boundary failure report
phase                          object    Descent | Ascent | Bottom_Hold | Lift | Tap | Return | NA
phase_segmentation_status      str       not_run | success | failed | manual_override | skipped
phase_segmentation_source      str       annotation | semi_auto | manual_override | fallback
phase_segmentation_failure_id  str       nullable; links frames to the phase-boundary failure report
```

When ② Annotation already provides `rep_id` or `phase`, ⑥ treats it as a candidate label.
If the automatic candidate conflicts with the manual candidate, the step does not overwrite
silently; it records a failure point or manual-intervention requirement.

## 4. Segmentation Targets

```text
rep boundary      start/end frame of a repetition
phase boundary    kinematic transition frame inside a repetition
optional phase    optional sub-phase such as Bottom_Hold
```

Representative phase labels:

```text
resistance exercises   Descent | Bottom_Hold | Ascent
task exercises         Lift | Tap | Return
```

## 5. Semi-Automatic Segmentation Strategy

The step uses two exercise-YAML settings blocks in order.

```text
rep_segmentation      estimates repetition start/end boundaries and confirms rep_id
phase_segmentation    estimates phase boundaries inside confirmed reps and fills phase
```

`phase_segmentation` keeps the existing code identifier and YAML key. It still means
phase splitting; renaming the overall step to `Segmentation` does not rename this key
to `segmentation`.

The step uses reference landmarks, reference axes, and expected phase order declared
in the exercise YAML to estimate rep/phase boundaries. Automatic estimation is not
treated as successful when any of the following are unclear.

```text
- reference-landmark visibility is insufficient
- ROM along the reference axis is too small
- no candidate boundary exists, or multiple candidates cannot be collapsed to one
- boundary order does not match the phase order declared in the exercise YAML
- a manual boundary and automatic candidate conflict outside the allowed tolerance
```

In these cases, ⑥ records the affected frame or frame range as a
`SegmentationFailurePoint`. Failure points are not interpolated or treated as success.

## 6. Segmentation Failure Point Record

The failure-point report has at least the following fields.

```text
failure_id        str       unique identifier
failure_level     str       rep_boundary | phase_boundary | optional_phase
set_id            Int64     nullable
rep_id            Int64     nullable
start_frame       int       start frame of the failed range
end_frame         int       end frame of the failed range
candidate_frame   int       nullable; automatic candidate frame
reason            str       low_visibility | insufficient_rom | missing_candidate |
                            multiple_candidates | order_mismatch | manual_required
confidence        float     nullable; confidence of the automatic candidate
pipeline_action   str       exclude_range | rep_level_only | coarse_phase_continue |
                            wait_for_manual_override
resolved          bool      whether manual intervention resolved the failure
resolution_note   str       nullable
```

## 7. Pipeline Handling by Failure Level

```text
rep_boundary failure
    - The rep boundary cannot be confirmed.
    - Until manually corrected, the affected rep/range is excluded from rep-level
      and phase-level analysis.
    - Downstream Feature/Biomech/Biomarker outputs do not emit records for that rep.

phase_boundary failure
    - The rep boundary is confirmed, but phase boundaries such as descent/hold/ascent
      are unclear.
    - Rep-level metrics are retained.
    - Phase-level features and phase summaries are not emitted for that rep.

optional_phase failure
    - Only an optional phase such as Bottom_Hold is unclear.
    - The optional phase is skipped, and the pipeline continues with coarse phases.
    - The report records why the optional phase was skipped.
```

## 8. Manual Intervention Policy

Manual intervention confirms boundary/label metadata for a failure point. It does not
change coordinate values.

```text
rep_segmentation_status or phase_segmentation_status = manual_override
rep_segmentation_source or phase_segmentation_source = manual_override
```

Manual corrections become the only confirmed labels used by downstream steps. The
difference from the automatic candidate, correction reason, and reviewer note are
retained in the report to preserve provenance.

## 9. Downstream Effects

```text
⑦ Motion Attribution   uses confirmed rep_id for active-side consistency
⑧ Feature Extraction   rep-level features use confirmed reps; phase-level features use only successful/manual phases
⑨ Biomech Proxy        excludes reps removed by segmentation failure
⑩ Biomarker Derivation keeps failure/exclusion state in provenance
⑪ Visualization        shows failure points and manual correction boundaries
```

## 10. Current Scope

Supported:

```text
- New rep_segmentation-based repetition-boundary splitting
- Existing phase_segmentation-based intra-rep phase splitting
- Recording conflicts between manual phase labels and automatic candidates
- Segmentation failure-point recording
- Failure-level pipeline handling policy
- Confirmed labels after manual intervention
```

Not in scope:

```text
- Fully unattended segmentation without failure-point review
- Coordinate edits
- Treating a segmentation failure as success through arbitrary interpolation
```
