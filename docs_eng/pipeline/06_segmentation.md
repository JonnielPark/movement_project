# 06. Segmentation

**Document Version:** 1.2.6
**Last Updated:** 2026-05-20
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
phase                          object    Descent | Ascent | Turnaround_Hold | Lift | Tap | Return | NA
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
optional phase    optional sub-phase such as Turnaround_Hold
```

Representative phase labels:

```text
resistance exercises   Descent | Turnaround_Hold | Ascent
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

## 6. Success / Failure / Skipped Policy

Rep-boundary segmentation is considered successful only after candidate boundaries
are converted into accepted intervals and the accepted interval count satisfies
`rep_segmentation.minimum_reps`.

```text
success
    - At least `minimum_reps` accepted intervals remain after filtering.
    - Each accepted interval has at least `minimum_rep_length_frames`.
    - Accepted frames receive segment_type='rep', rep_id, status='success',
      and source='semi_auto' unless annotation/manual override already supplied labels.

failed
    - Required reference landmarks or axes cannot be resolved.
    - Fewer than two boundary candidates are available.
    - All candidate intervals are too short.
    - The accepted interval count is lower than `minimum_reps`.
    - A flat or near-flat trace must not be promoted to success merely because
      endpoint insertion produced two boundary frames.

skipped
    - The exercise definition has no `rep_segmentation` block.
    - The pipeline runner keeps the dataframe unchanged and writes a skipped
      reason into the segmentation report.
```

When detected intervals are fewer than `minimum_reps`, the report uses:

```text
status          failed
reason          insufficient_reps
pipeline_action wait_for_manual_override
rep_id          remains unset for the affected analysis frames
```

## 7. Segmentation Failure Point Record

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

## 8. Pipeline Handling by Failure Level

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
    - Only an optional phase such as Turnaround_Hold is unclear.
    - The optional phase is skipped, and the pipeline continues with coarse phases.
    - The report records why the optional phase was skipped.
```

## 9. Manual Intervention Policy

Manual intervention confirms boundary/label metadata for a failure point. It does not
change coordinate values.

```text
rep_segmentation_status or phase_segmentation_status = manual_override
rep_segmentation_source or phase_segmentation_source = manual_override
```

Manual corrections become the only confirmed labels used by downstream steps. The
difference from the automatic candidate, correction reason, and reviewer note are
retained in the report to preserve provenance.

## 10. Recording-Plane Phase Split Artifact

For real one-take MediaPipe recordings, the generic pipeline `phase_segmentation`
may not be the safest first pass because MediaPipe `z` is a depth proxy rather
than vertical height. In this case, a recording-plane phase split can be generated
as an annotation-adjacent QC artifact before pipeline promotion.

```text
source file        <recording_id>_annotation.csv
candidate output   <recording_id>_phase_split.csv
confirmed output   <recording_id>_phase_annotation.csv
reference signal   hip_center_y in raw image/recording coordinates
phase order        Descent → Turnaround_Hold → Ascent
```

The candidate file is generated semi-automatically from confirmed rep ranges. It
is not treated as a researcher-confirmed annotation until visual QC passes and the
candidate is promoted to `<recording_id>_phase_annotation.csv`. Promotion requires:

Notebook 15 calls the stable helpers in
`src/movement/stages/recording_phase_split.py`:
`generate_recording_plane_phase_split`,
`validate_phase_split_for_promotion`, and
`promote_phase_split_to_annotation`. These helpers generate and validate the
artifact; they do not decide whether visual QC has passed.

```text
- every annotated rep is covered exactly
- phase ranges stay inside the corresponding rep range
- phase ranges have no gaps or overlaps
- phase order matches the exercise definition
- bottom_frame_estimate falls inside Turnaround_Hold
- filming provenance such as camera_zone and reference_signal is preserved
```

This artifact preserves the exercise-defined phase semantics while using a
recording-plane signal better suited to the observed MediaPipe sample. It is not
calibrated 3D reconstruction and does not reinterpret MediaPipe depth as height.

### 10-1. Pipeline Promotion Decision

Current decision: do not promote the recording-plane phase split to the generic
pipeline `phase_segmentation` source yet. It remains an annotation-adjacent
real-data QC and confirmed-annotation workflow.

Promotion to a formal pipeline source requires all of the following:

```text
- at least one additional real recording confirms the same phase-boundary behavior
- the rule is exercised beyond p01 or documented as a squat-only special source
- phase-level feature extraction reads the confirmed <recording_id>_phase_annotation.csv
  without changing the generic normalized-coordinate segmentation contract
- robustness tests show that the recording-plane split is stable under frame gaps,
  landmark jitter, and reasonable camera-zone variation
- notebook 15 and the module tests agree on candidate generation, visual-QC gating,
  and promotion semantics
```

Until those gates are met, downstream analysis may use the researcher-confirmed
`<recording_id>_phase_annotation.csv`, but the automatic pipeline default remains
the existing normalized-coordinate phase segmentation or no phase segmentation
when that is disabled for a real-data review.

## 11. Downstream Effects

```text
⑦ Motion Attribution   uses confirmed rep_id for active-side consistency
⑧ Feature Extraction   rep-level features use confirmed reps; phase-level features use only successful/manual phases
⑨ Biomech Proxy        excludes reps removed by segmentation failure
⑩ Biomarker Derivation keeps failure/exclusion state in provenance
⑪ Visualization        shows failure points and manual correction boundaries
```

## 12. Current Scope

Supported:

```text
- New rep_segmentation-based repetition-boundary splitting
- Existing phase_segmentation-based intra-rep phase splitting
- Recording conflicts between manual phase labels and automatic candidates
- Segmentation failure-point recording
- Failure-level pipeline handling policy
- Confirmed labels after manual intervention
- Annotation-adjacent recording-plane phase split artifacts for real-data QC
```

Not in scope:

```text
- Fully unattended segmentation without failure-point review
- Coordinate edits
- Treating a segmentation failure as success through arbitrary interpolation
```

## 13. Verification Targets

A2 verification locks the following behavior with focused unit tests:

```text
nominal phase split
    A confirmed rep with one clear kinematic inflection is split into the
    configured phase_sequence, and PhaseSegmentationReport records the
    inflection frame and phase frame ranges.

too-short rep
    A rep shorter than `phase_segmentation.minimum_rep_length_frames` is not
    assigned phase labels. The report keeps the rep_id and records a rejected
    reason.

multi-inflection policy
    When multiple inflection candidates are present, `multi_inflection_policy`
    deterministically selects the intended candidate or rejects the rep.

annotation override
    Existing non-null phase labels from ② Annotation are preserved and are not
    overwritten by semi-automatic phase splitting.

phase provenance handoff
    ⑥ phase-level FeatureRecords emitted from phase-labelled reps must include
    `phase_segmentation.*` entries in `source_fields`.
```

Test mapping:

```text
tests/test_phase_segmentation.py         phase splitting reports and override behavior
tests/test_features_phase_grouping.py    phase-level FeatureRecord provenance
tests/test_recording_phase_split.py      recording-plane phase split artifact and promotion validation
```
