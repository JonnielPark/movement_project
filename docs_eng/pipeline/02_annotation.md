# 02. Annotation

**Document Version:** 1.1.4
**Last Updated:** 2026-05-10
**Korean Sync:** `docs/pipeline/02_annotation.md` is the same-version Korean source.

Pipeline step ②. Merges segment metadata from a user-prepared annotation CSV into
the pose dataframe. This step merges and propagates manual metadata and filming
provenance; it does not estimate rep/phase boundaries automatically or
semi-automatically. Rep/phase boundary estimation and failure-point recording are
handled by [06_segmentation.md](06_segmentation.md).

This step does not delete frames or modify coordinates.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation             ← this step
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Segmentation
→ ⑦ Motion Attribution
→ downstream steps
```

② runs before ③ because `exercise_type` declared here identifies which exercise YAML to load.

## 2. Output Columns

```text
use_for_analysis    bool      whether to include in analysis
segment_type        str       full_sequence | baseline | idle | rep | rest | transition | excluded
set_id              Int64     nullable
rep_id              Int64     nullable
phase               object    nullable; preserved if manually provided
note                str       nullable; free-text segment note
exercise_type       str       exercise definition YAML identifier
pattern             str       bilateral | alternating
starting_side       str       left | right (alternating exercises only)
session_id          str       nullable; identifier that groups multiple recordings into one session
recording_id        str       nullable; one-take filming-file identifier
set_index           Int64     nullable; set order within the session
camera_zone         str       nullable; Z1 | Z2 | Z3 | Z4 | Z5 | Z6 | Z7 | Z8 | unknown
camera_height_level str       nullable; H1 | H2 | H3 | unknown
reference_mat_used  bool      nullable; whether the reference-mat anchor was used
filming_protocol_status str   recommended | out_of_zone | no_anchor | unknown
performance_protocol_status str nullable; completed | partial | stopped_at_failure_point | unknown
actual_rep_count    Int64     nullable; protocol count actually completed
failure_point_frame Int64     nullable; frame where the performance failure point or stop point occurs
failure_rep_id      Int64     nullable; rep_id where performance failure is first observed
failure_reason      str       nullable; posture_breakdown | inconsistent_rom | side_order_error | pain_or_risk | participant_stop | unknown
performance_note    str       nullable; free-text note about performance quality or stop reason
rep_side_sequence   str       nullable; observed side order, e.g., right,left,right,left or same_side_block_then_switch
side_block_size     Int64     nullable; observed same-side block size when applicable
rep_unit            str       nullable; observed segmented unit, e.g., repetition | tap
protocol_cycle_id   Int64     nullable; participant-facing protocol-cycle id for grouped atomic reps
```

`exercise_type` drives ③ exercise definition loading.
`pattern` and `starting_side` drive ④ preprocessing L/R swap detection and ⑦ motion attribution.
When a manual `phase` value is provided, ② preserves it, but ⑥ Segmentation decides whether
the label is confirmed and how any failure is handled.
Filming provenance columns are not used to correct coordinates or exclude data.
Whether the recording matches the recommended protocol is shown as warning information
in reports or visualization.
Performance provenance columns record what actually happened during acquisition:
target-count completion, performance failure point, and stop reason. They do not
diagnose strength or fatigue and are not automatic exclusion rules.
Observed count/side-sequence columns (`rep_side_sequence`, `side_block_size`,
`rep_unit`, `protocol_cycle_id`) are compared with ③ `performance_protocol` in
later reporting and ⑦ Motion Attribution. A mismatch is warning/provenance, not
automatic frame exclusion.

A5 formalizes how performance/failure provenance is consumed by runner/reporting
outputs. The frame-level columns above remain the detailed record, and the
annotation report additionally exposes a set-level summary that downstream
visualization or interpretation layers can read without scanning the full pose
dataframe.

```text
performance_provenance.available                 bool
performance_provenance.policy                    warning_provenance_only
performance_provenance.forced_exclusion          false
performance_provenance.score_penalty_applied     false
performance_provenance.records                   list[dict]
performance_provenance.summary                   dict
performance_provenance.interpretation_confidence_notes list[str]
```

Each record contains:

```text
segment_type, set_id, rep_id, start_frame, end_frame
performance_protocol_status
actual_rep_count
failure_point_frame
failure_rep_id
failure_reason
performance_note
source_fields
```

Rules:

```text
- Missing or partial performance metadata does not fail annotation.
- A low actual repetition count is not a direct movement-quality penalty.
- A failure point is not a segmentation failure point. It marks where the
  participant stopped maintaining the protocol task.
- The default behavior is warning/provenance only. Downstream scoring or figure
  captions may display the note, but ② does not exclude frames and ⑩ does not
  penalize scores solely from these metadata fields.
```

## 3. Annotation Hierarchy

```text
recording
└─ set          group of consecutive reps of the same exercise
   └─ rep       one complete movement cycle
      └─ phase  sub-phase within a rep (optional; confirmed by ⑥)
```

## 4. segment_type Values

```text
full_sequence   default when no annotation file is provided
baseline        stable standing posture before movement starts
idle            waiting or non-exercise segment
rep             one complete rep
rest            inter-set rest
transition      segment not attributed to a specific rep
excluded        explicitly invalid segment
```

## 5. Annotation File Format

Minimum required columns:

```text
segment_type, set_id, rep_id, start_frame, end_frame, use_for_analysis
```

Optional columns:

```text
exercise_type, pattern, starting_side, phase, note,
session_id, recording_id, set_index,
camera_zone, camera_height_level, reference_mat_used, filming_protocol_status,
performance_protocol_status, actual_rep_count, failure_point_frame,
failure_rep_id, failure_reason, performance_note,
rep_side_sequence, side_block_size, rep_unit, protocol_cycle_id
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

## 6. No-Annotation Fallback

If no annotation file is provided, this step does not fail. Defaults applied:

```text
use_for_analysis = True  (all frames)
segment_type     = full_sequence
set_id           = None
rep_id           = None
phase            = None
exercise_type    = None   → ③ loads generic fallback definition
pattern          = bilateral
starting_side    = None
session_id       = None
recording_id     = None
set_index        = None
camera_zone      = unknown
camera_height_level = unknown
reference_mat_used = None
filming_protocol_status = unknown
```

Report records `annotation_provided = False`.
It also records `performance_provenance.available = False`; no performance
failure is inferred from the absence of annotation metadata.

## 7. When Annotation is Provided

```text
1. Initialize all frames to use_for_analysis = False.
2. Apply use_for_analysis values from the annotation file for declared segments.
3. Frames not covered by any annotation segment are excluded from analysis.
4. Exercise context columns (exercise_type, pattern, starting_side) are propagated
   to all frames within the declared segment.
5. Filming provenance columns (session_id, camera_zone, and related fields) are
   propagated to every frame in the recording or declared range.
```

## 8. Overlap Policy

Overlapping annotation segments are treated as an error. The step either raises an error
or records a failure in the annotation report; it does not silently overwrite.

## 9. Frame Index Convention

Original `frame` column values are preserved. This step does not renumber frames.

## 10. Current Scope

Supported:

```text
- Full-sequence fallback (no annotation file)
- Set-level and rep-level annotation
- idle / baseline / rest / excluded segment marking
- use_for_analysis mask
- Exercise context columns (exercise_type, pattern, starting_side)
- Preserving manually provided phase labels
- Preserving filming provenance columns (session_id, recording_id, set_index, camera_zone, camera_height_level)
- Preserving observed protocol metadata (rep_side_sequence, side_block_size, rep_unit, protocol_cycle_id)
- Summarizing performance/failure provenance into the annotation report
```

Not in scope:

```text
- Automatic or semi-automatic rep/phase boundary estimation
- Segmentation failure-point recording
- Camera-angle correction or coordinate reprojection
- Forced rejection of data with mismatched filming conditions
- Automatic scoring penalty from low actual repetition count or failure metadata
- Coordinate edits
```
