# 03. Annotation & Segmentation

**Document Version:** 1.1.0
**Last Updated:** 2026-05-07
**Versioning Rule:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)
**Korean Sync:** `docs/pipeline/03_annotation_and_segmentation.md` is the same-version Korean source.

This document defines the boundary and failure-handling policy for pipeline step
② Annotation and ⑥ Phase Segmentation. ② Annotation merges a user-prepared manual
annotation CSV into the pose dataframe. ⑥ Phase Segmentation tracks joint motion
to split rep/phase boundaries semi-automatically, records unclear automatic results
as failure points, and confirms them through manual intervention.

Neither step deletes frames or modifies coordinates.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation             ← manual annotation merge
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Phase Segmentation     ← semi-automatic rep/phase split + failure-point recording
→ ⑦ Motion Attribution
→ downstream steps
```

② runs before ③ because `exercise_type` declared here identifies which exercise YAML to load.

## 2. ② Annotation Output Columns

```text
use_for_analysis    bool      whether to include in analysis
segment_type        str       full_sequence | baseline | idle | rep | rest | transition | excluded
set_id              Int64     nullable
rep_id              Int64     nullable
phase               object    nullable (usually unfilled by ②)
exercise_type       str       exercise definition YAML identifier
pattern             str       bilateral | alternating
starting_side       str       left | right (alternating exercises only)
```

`exercise_type` drives ③ exercise definition loading.
`pattern` and `starting_side` drive ④ preprocessing L/R swap detection and ⑦ motion attribution.

## 3. ⑥ Phase Segmentation Output Columns

⑥ fills the `phase` column reserved by ② and adds metadata to track failures or manual corrections.

```text
phase                    object    Descent | Ascent | Bottom_Hold | Lift | Tap | Return | NA
segmentation_status      str       not_run | success | failed | manual_override | skipped
segmentation_source      str       annotation | semi_auto | manual_override | fallback
segmentation_failure_id  str       nullable; links frames to the failure-point report
```

## 4. Annotation Hierarchy

```text
recording
└─ set          group of consecutive reps of the same exercise
   └─ rep       one complete movement cycle
      └─ phase  sub-phase within a rep
```

## 5. segment_type Values

```text
full_sequence   default when no annotation file is provided
baseline        stable standing posture before movement starts
idle            waiting or non-exercise segment
rep             one complete rep
rest            inter-set rest
transition      segment not attributed to a specific rep
excluded        explicitly invalid segment
```

## 6. Annotation File Format

Minimum required columns:

```text
segment_type, set_id, rep_id, start_frame, end_frame, use_for_analysis
```

Optional columns:

```text
exercise_type, pattern, starting_side, phase, note
```

### Example: single set, 3 reps

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern
baseline,,,20,60,false,squat,bilateral
rep,1,1,85,160,true,squat,bilateral
rep,1,2,170,245,true,squat,bilateral
rep,1,3,255,330,true,squat,bilateral
idle,,,331,370,false,squat,bilateral
```

### Example: two sets

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern
baseline,,,20,60,false,squat,bilateral
rep,1,1,85,160,true,squat,bilateral
rep,1,2,170,245,true,squat,bilateral
rep,1,3,255,330,true,squat,bilateral
rest,1,,331,430,false,squat,bilateral
rep,2,1,450,525,true,squat,bilateral
rep,2,2,535,610,true,squat,bilateral
rep,2,3,620,700,true,squat,bilateral
idle,,,701,760,false,squat,bilateral
```

### Example: alternating exercise (plank shoulder tap)

`starting_side = right` means rep 1 → right active, rep 2 → left active, alternating.

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern,starting_side
baseline,,,0,40,false,plank_shoulder_tap,alternating,right
rep,1,1,50,100,true,plank_shoulder_tap,alternating,right
rep,1,2,110,160,true,plank_shoulder_tap,alternating,right
rep,1,3,170,220,true,plank_shoulder_tap,alternating,right
rep,1,4,230,280,true,plank_shoulder_tap,alternating,right
idle,,,281,320,false,plank_shoulder_tap,alternating,right
```

## 7. No-Annotation Fallback

If no annotation file is provided, ② does not fail. Defaults applied:

```text
use_for_analysis = True  (all frames)
segment_type     = full_sequence
set_id           = None
rep_id           = None
phase            = None
exercise_type    = None   → ③ loads generic fallback definition
pattern          = bilateral
starting_side    = None
```

Report records `annotation_provided = False`.

## 8. When Annotation is Provided

```text
1. Initialize all frames to use_for_analysis = False.
2. Apply use_for_analysis values from the annotation file for declared segments.
3. Frames not covered by any annotation segment are excluded from analysis.
4. Exercise context columns (exercise_type, pattern, starting_side) are propagated
   to all frames within the declared segment.
```

## 9. ⑥ Phase Segmentation Strategy

⑥ uses the exercise YAML reference landmarks, reference axis, and expected phase order
to estimate rep/phase boundaries semi-automatically. Automatic estimation is not treated
as successful when any of the following are unclear.

```text
- reference-landmark visibility is insufficient
- ROM along the reference axis is too small
- no candidate boundary exists, or multiple candidates cannot be collapsed to one
- boundary order does not match the phase order declared in the exercise YAML
- a manual boundary and automatic candidate conflict outside the allowed tolerance
```

In these cases, ⑥ records the affected frame or frame range as a
`SegmentationFailurePoint`. Failure points are not interpolated or treated as success.

## 10. Segmentation Failure Point Record

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

## 11. Pipeline Handling by Failure Level

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

When manual intervention resolves a failure point, the output records
`segmentation_status = manual_override` and `segmentation_source = manual_override`.
Manual correction confirms boundary/label metadata only; it does not modify coordinates.

## 12. Overlap Policy

Overlapping annotation segments or conflicting manual correction ranges are treated as
errors. The step either raises an error or records a failure in the report; it does not
silently overwrite.

## 13. Frame Index Convention

Original `frame` column values are preserved. Neither step in this document renumbers frames.

## 14. Current Scope

Supported:

```text
- Full-sequence fallback (no annotation file)
- Set-level and rep-level annotation
- idle / baseline / rest / excluded segment marking
- use_for_analysis mask
- Exercise context columns (exercise_type, pattern, starting_side)
- Design for semi-automatic ⑥ Phase Segmentation rep/phase splitting
- Segmentation failure-point recording and failure-level pipeline handling policy
```

Not in scope:

```text
- Fully unattended segmentation without failure-point review
- Coordinate edits
- Treating a segmentation failure as success through arbitrary interpolation
```
