# 03. Annotation & Segmentation

Pipeline step ②. Merges pre-labelled segment metadata into the pose dataframe.
Does not perform automatic rep detection. Does not delete frames or modify coordinates.

---

## 1. Pipeline Position

```text
Pose CSV
→ ① Validation
→ ② Annotation             ← this step
→ ③ Exercise Definition
→ ④ Preprocessing
→ ⑤ Normalization
→ ⑥ Motion Attribution
→ downstream steps
```

② runs before ③ because `exercise_type` declared here identifies which exercise YAML to load.

## 2. Output Columns Added

```text
use_for_analysis    bool      whether to include in analysis
segment_type        str       full_sequence | baseline | idle | rep | rest | transition | excluded
set_id              Int64     nullable
rep_id              Int64     nullable
phase               object    nullable (reserved for future phase-level analysis)
exercise_type       str       exercise definition YAML identifier
pattern             str       bilateral | alternating
starting_side       str       left | right (alternating exercises only)
```

`exercise_type` drives ③ exercise definition loading.
`pattern` and `starting_side` drive ④ preprocessing L/R swap detection and ⑥ motion attribution.

## 3. Annotation Hierarchy

```text
recording
└─ set          group of consecutive reps of the same exercise
   └─ rep       one complete movement cycle
      └─ phase  sub-phase within a rep (reserved; not yet used in analysis)
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

## 6. No-Annotation Fallback

If no annotation file is provided, the step does not fail. Defaults applied:

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

## 7. When Annotation is Provided

```text
1. Initialize all frames to use_for_analysis = False.
2. Apply use_for_analysis values from the annotation file for declared segments.
3. Frames not covered by any annotation segment are excluded from analysis.
4. Exercise context columns (exercise_type, pattern, starting_side) are propagated
   to all frames within the declared segment.
```

## 8. Overlap Policy

Overlapping annotation segments are treated as an error. The step either raises an error
or records a failure in the annotation report (does not silently overwrite).

## 9. Frame Index Convention

Original `frame` column values are preserved. This step does not renumber frames.

## 10. Initial Scope

Supported:
```text
- Full-sequence fallback (no annotation file)
- Set-level and rep-level annotation
- idle / baseline / rest / excluded segment marking
- use_for_analysis mask
- Exercise context columns (exercise_type, pattern, starting_side)
```

Not in scope:
```text
- Automatic segmentation
- Automatic rep detection
- Automatic phase detection
- Phase-level analysis
```
