# 06. Segmentation

**Document Version:** 1.3.4
**Last Updated:** 2026-07-04
**Korean Sync:** `docs/pipeline/06_segmentation.md` is the same-version Korean source.

Pipeline step ⑥ confirms repetition boundaries and intra-rep phase labels. It is
named `Segmentation` because it covers both reps and phases. The existing
`phase_segmentation` YAML/code key remains dedicated to phase splitting, while
`rep_segmentation` handles repetition boundaries.

This step does not modify coordinates or delete frames.

---

## 1. Pipeline Position

```text
⑤ Normalization → optional ⑤-1 Canonicalization → ⑥ Segmentation ← this step → ⑦ Feature Extraction
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

Manual labels from ② Annotation are treated as analysis evidence or confirmed labels and
are never silently overwritten.

Stage-check notebook 26 follows the shared stage-check pattern:

```text
Data Setup
    Uses prepare_previous_stage_inputs(prepare_until="normalization") to prepare
    validation, annotation, exercise definition, preprocessing, and normalization
    outputs.

Direct Segmentation Test
    Runs a compact rep-label handoff check, then calls phase segmentation on the
    prepared normalized dataframe.

Pipeline Integration
    Runs the same stage through run_pipeline and compares report presence and
    frame-level labels.
```

The stage-check notebook does not re-audit annotation rep ranges in detail and
does not promote recording-specific phase-split guides to ground truth. It only
confirms that annotation rep labels are preserved as handoff evidence and that
the current exercise definition can produce usable phase labels and provenance.

Canonicalization remains the preceding pipeline stage, but current segmentation
boundary detection does not require canonical analysis-space coordinates; it consumes
the normalized/preprocessed dataframe and the exercise-defined reference signal.

---

## 2. Strategy

```text
rep_segmentation
    Estimates repetition start/end boundaries and confirms rep_id.

phase_segmentation
    Estimates phase boundaries inside confirmed reps and fills phase labels.
```

Both blocks use exercise-defined reference landmarks, coordinate families, axes,
expected phase order, and minimum-length settings. Automatic segmentation is
rejected when confidence, ROM, proposal boundary count, boundary order, or
manual-label consistency is unclear.

`reference_coordinate_family` separates the signal used for boundary detection
from the coordinates used for feature/scoring computation:

```text
norm
    Default. Reads <landmark>_norm_x/y/z from ⑤ Normalization.

recording_view_raw
    Reads raw recording-plane columns such as <landmark>_x/y/z. This is useful
    when the reference landmark is the normalization anchor and its normalized
    trajectory has been removed.
```

For example, squat phase splitting may use `hip_center` in
`recording_view_raw` with `image_y` so the descent/ascent split follows the
visible recording-plane hip trajectory. This does not change normalized
coordinates or promote raw coordinates to scoring features.

### 2.1 Phase Label Vocabulary

Phase labels are exercise-defined kinematic or task labels. They are not
hardcoded to `Descent` and `Ascent`. The exercise definition selects a
`phase_sequence` from a registry template or an authoring bundle, and
segmentation fills that sequence when the reference signal supports it.

Common label groups include:

```text
vertical/resistance cycle
    Start_Hold, Descent, Turnaround_Hold, Ascent, Top_Hold, Reset

flexion-extension cycle
    Flexion, Flexion_Hold, Extension, Extension_Hold, Return

push/pull cycle
    Lowering, Bottom_Hold, Press, Pull, Top_Hold, Lockout, Return

reach/return cycle
    Reach, Reach_Hold, Return, Recenter

support/alternating cycle
    Support, Weight_Shift, Unweight, Lift, Tap, Replant, Return

directional reach/step cycle
    Step_Out, Step_In, Forward_Reach, Backward_Return, Lateral_Reach,
    Medial_Return

rotation/control cycle
    Rotate_Left, Rotate_Right, Rotate, Rotation_Hold, AntiRotation_Hold, Return

static/control cycle
    Hold, Drift, Correction, Failure_Point
```

Human-readable phase labels are preserved in the `phase` column. Feature IDs use
the same labels converted to lower snake case when a phase-specific suffix is
needed, for example `Turnaround_Hold` → `turnaround_hold`.

Kinetic terms such as `eccentric`, `isometric`, and `concentric` may appear in a
`phase_model` expectation or interpretation note, but they are not used as
primary phase labels unless the exercise definition explicitly promotes them as
task labels. This prevents the pipeline from implying force or muscle-action
ground truth from monocular pose alone.

Optional labels such as `Turnaround_Hold`, `Top_Hold`, or `Reach_Hold` are only
emitted when the corresponding option is enabled and accepted. If an optional
phase is unclear, segmentation continues with the coarser phase sequence and
records an `optional_phase` failure point.

Current implementation status:

```text
implemented
    Segmentation can consume an exercise-defined phase_sequence for implemented
    templates, and phase-level feature records preserve the observed phase label.

limited
    The current rep-level spatial.phase_profile aggregate is still specific to
    Descent/Ascent ROM ratio. Generic phase-profile aggregates must be designed
    explicitly before they are used for scoring.
```

---

## 3. Status And Failure Policy

```text
success
    Accepted intervals satisfy minimum_reps and minimum_rep_length_frames.

failed
    Required landmarks/axes are unavailable, proposal boundaries are missing,
    intervals are too short, proposal order is invalid, or accepted intervals
    are fewer than minimum_reps.

skipped
    Required segmentation config is absent or the stage is disabled.

manual_override
    A researcher-confirmed label resolves a failure or overrides an automatic
    analysis evidence.
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
boundary_proposal_frame
reason                 low_confidence | insufficient_rom | missing_boundary_proposal |
                       multiple_planned patterns | order_mismatch | manual_required
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
analysis-space output     <recording_id>_phase_split.csv
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
⑦ Feature Extraction   uses confirmed rep_id, resolves side-role context, and emits
                       rep-level features for confirmed reps and phase-level features
                       only for successful/manual phases.
⑧ Biomech Proxy        excludes unresolved rep-boundary failures.
⑨ Biomarker Scoring    keeps failure/exclusion provenance.
⑩ Visualization        shows failure points and manual boundaries.
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

