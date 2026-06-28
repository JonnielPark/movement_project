# 02. Annotation

**Document Version:** 1.2.0
**Last Updated:** 2026-05-21
**Korean Sync:** `docs/pipeline/02_annotation.md` is the same-version Korean source.

Pipeline step ② merges user-prepared segment metadata into the pose dataframe.
It preserves manual labels, filming provenance, and performance provenance.
It does not estimate rep/phase boundaries, delete frames, or modify coordinates.
Rep/phase boundary estimation and segmentation failure handling belong to
[07_segmentation.md](07_segmentation.md).

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation             ← this step
→ ③ Exercise Definition
→ ④ Preprocessing
→ downstream steps
```

② runs before ③ because `exercise_id` selects the exercise-definition YAML.

## 2. Output Contract

Frame-level columns added or filled by this step:

```text
use_for_analysis    bool      include this frame in analysis
segment_type        str       full_sequence | baseline | idle | rep | rest | transition | excluded
set_id              Int64     nullable set identifier
rep_id              Int64     nullable repetition identifier
phase               object    optional manual phase label; confirmed later by ⑦
note                str       optional segment note
exercise_id         str       exercise definition identifier
execution_pattern   str       bilateral | alternating; observed side/sequence pattern
starting_side       str       left | right; alternating/unilateral context
session_id          str       optional acquisition-session identifier
recording_id        str       optional filming-file identifier
set_index           Int64     optional set order in the session
camera_zone         str       Z1-Z8 | unknown
camera_height_level str       H1-H3 | unknown
reference_mat_used  bool      nullable reference-anchor flag
filming_protocol_status str   recommended | out_of_zone | no_anchor | unknown
performance_protocol_status str completed | partial | stopped_at_failure_point | unknown
actual_rep_count    Int64     observed count actually completed
failure_point_frame Int64     observed protocol stop/failure frame
failure_rep_id      Int64     rep where protocol failure first appears
failure_reason      str       posture_breakdown | inconsistent_rom | side_order_error | pain_or_risk | participant_stop | unknown
performance_note    str       free-text performance note
rep_side_sequence   str       observed side order, e.g. right,left,right,left
side_block_size     Int64     observed same-side block size when applicable
rep_unit            str       repetition | tap | other exercise-defined unit
protocol_cycle_id   Int64     user-facing protocol cycle id for grouped atomic reps
```

Downstream use:

```text
exercise_id                   → ③ exercise definition loading
execution_pattern / starting_side
                               → ④ L/R checks and ⑧ Feature Extraction role context
phase                          → preserved here, accepted/rejected by ⑦
filming provenance             → warning/report context only
performance provenance         → warning/report context only
rep_side_sequence fields       → compared with ③ performance_protocol
```

## 3. Annotation CSV

Required columns:

```text
segment_type, set_id, rep_id, start_frame, end_frame, use_for_analysis
```

Optional columns are the remaining output-context fields listed in Section 2.

Minimal example:

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_id,execution_pattern,starting_side
baseline,,,20,60,false,squat,bilateral,
rep,1,1,85,160,true,squat,bilateral,
rep,1,2,170,245,true,squat,bilateral,
rest,1,,246,320,false,squat,bilateral,
rep,2,1,340,415,true,squat,bilateral,
idle,,,416,460,false,squat,bilateral,
```

For alternating exercises, `starting_side` defines the expected first active side.
For example, `plank_shoulder_tap` with `execution_pattern=alternating` and
`starting_side=right` means rep 1 is right, rep 2 is left, and so on.

## 4. Behavior

When an annotation CSV is provided:

```text
1. Validate required columns, segment_type values, frame ranges, and overlaps.
2. Initialize all frames as use_for_analysis = False.
3. Apply segment metadata to the declared inclusive frame ranges.
4. Leave frames outside every declared segment excluded.
5. Preserve original frame numbers.
```

When no annotation CSV is provided:

```text
use_for_analysis = True
segment_type     = full_sequence
set_id / rep_id  = None
phase            = None
exercise_id      = None   → ③ loads generic fallback
execution_pattern = bilateral
starting_side    = None
camera_zone      = unknown
camera_height_level = unknown
filming_protocol_status = unknown
```

The report records `annotation_provided = False` and
`performance_provenance.available = False`.

## 5. Provenance Policy

Filming and performance metadata are provenance, not automatic correction rules.

```text
Missing metadata                     → annotation still succeeds
Out-of-zone filming status           → warning/report only
Low actual_rep_count                 → not a direct movement-quality penalty
failure_point_frame                  → observed protocol stop point, not a segmentation failure
side-sequence mismatch               → warning/provenance unless ⑦ flags it from motion evidence
```

The annotation report exposes a compact performance summary:

```text
performance_provenance.available
performance_provenance.policy = warning_provenance_only
performance_provenance.forced_exclusion = false
performance_provenance.score_penalty_applied = false
performance_provenance.records
performance_provenance.summary
performance_provenance.interpretation_confidence_notes
```

## 6. Scope

Supported:

```text
- Full-sequence fallback
- Set-level and rep-level annotation
- baseline / idle / rep / rest / transition / excluded segments
- Exercise context propagation
- Manual phase-label preservation
- Filming and performance provenance preservation
- Performance/failure provenance summary for runner reports
```

Not in scope:

```text
- Automatic or semi-automatic rep/phase boundary estimation
- Segmentation failure-point detection
- Camera-angle correction or coordinate reprojection
- Forced rejection based only on filming-condition mismatch
- Scoring penalty based only on count or failure metadata
- Coordinate edits
```

## 7. Code Mapping

```text
src/movement/stages/annotation.py
    ANNOTATION_REQUIRED_COLUMNS / ANNOTATION_OPTIONAL_COLUMNS
    VALID_SEGMENT_TYPES / ANNOTATION_OUTPUT_COLUMNS
    load_annotation_csv()
    validate_annotation()
    apply_annotation()
    summarize_performance_provenance()

tests/test_annotation_metadata.py
```
