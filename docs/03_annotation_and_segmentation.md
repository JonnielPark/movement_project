# Annotation and Segmentation

## Purpose

In the current framework, segmentation is treated as an annotation-based frame selection step rather than a fully automatic movement detection algorithm.

The goal is to mark which frames, sets, and repetitions should be used for analysis while preserving the original pose sequence.

This step does not remove frames from the dataframe.

Instead, it adds metadata columns such as:

```text
use_for_analysis
segment_type
set_id
rep_id
phase
```

Annotation also declares exercise-level context that downstream modules use for exercise-aware processing. See [Exercise Context Columns](#exercise-context-columns).

## Terminology

The annotation structure follows this hierarchy:

```text
recording
└─ set
   └─ rep
      └─ phase
```

## Recording

A recording is one full captured sequence from a video or pose CSV.

A single recording may contain:

```text
idle frames
preparation frames
one or more sets
rest periods
ending frames
```

A recording may contain only one set, or multiple sets.

## Set

A set is a group of repeated exercise movements performed continuously.

Example:

```text
squat set 1: 10 reps
squat set 2: 10 reps
squat set 3: 10 reps
```

The framework should allow one recording to contain one or more sets.

## Rep

A repetition, or rep, is one complete movement cycle within a set.

For example, in a squat:

```text
one rep = standing position
        → descent
        → bottom
        → ascent
        → standing position
```

In the initial implementation, rep-level annotation is the main target.

## Phase

A phase is a sub-section within a repetition.

Examples:

```text
descent
bottom
ascent
transition
```

Phase-level annotation is reserved for future development.

The initial implementation may allow a `phase` column, but it does not require phase-level annotation or phase-level logic.

## Current Implementation Scope

The first implementation should support:

```text
- full-sequence fallback when no annotation is provided
- set-level annotation
- rep-level annotation
- idle / baseline / rest / excluded segment marking
- use_for_analysis mask
- exercise context declaration (exercise_type, pattern, starting_side)
```

The following are not part of the initial implementation:

```text
- automatic segmentation
- automatic rep detection
- automatic phase detection
- phase-level analysis
```

## Design Principle

Annotation should not delete or physically crop frames.

Instead, annotation should preserve the full sequence and add metadata columns.

Recommended output columns:

```text
use_for_analysis
segment_type
set_id
rep_id
phase
exercise_type
```

This allows:

```text
- original frame numbers to be preserved
- full-sequence visualization
- repeated annotation updates
- exclusion of idle or invalid frames from later analysis
- exercise-aware logic in preprocessing, motion attribution, and feature extraction
```

## Minimal Annotation Columns

The minimal required annotation file should contain:

```text
segment_type
set_id
rep_id
start_frame
end_frame
use_for_analysis
```

Optional columns:

```text
exercise_type
phase
note
```

## Exercise Context Columns

The annotation file may declare exercise-level context that downstream modules use for exercise-aware processing.

```text
exercise_type   identifier of the exercise
                examples: squat | lunge | pike_pushup | plank_shoulder_tap

pattern         expected left-right movement pattern
                values: bilateral | alternating

starting_side   first active side for alternating exercises
                values: left | right
                ignored when pattern is bilateral
```

The recommended convention is to declare these values once per recording (or once per set if a recording contains multiple exercises) using rows whose `segment_type` is `full_sequence`, `baseline`, or any per-set marker.

Example annotation row that only declares exercise context:

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern,starting_side
full_sequence,,,0,800,false,plank_shoulder_tap,alternating,right
```

These columns are consumed by:

```text
preprocessing      -> enable or skip frame-level left-right swap detection
motion_attribution -> compare detected active limb against the expected pattern
features           -> apply exercise-specific feature definitions
```

If `pattern` is missing, downstream modules treat the exercise as bilateral by default.

## Segment Types

Recommended `segment_type` values:

```text
full_sequence
baseline
idle
rep
rest
transition
excluded
```

Suggested meaning:

```text
full_sequence  → default when no annotation is provided
baseline       → stable posture before movement
idle           → waiting or non-exercise period
rep            → one complete repetition
rest           → rest period between sets
transition     → movement transition not assigned to a rep
excluded       → known invalid or unusable frames
```

## Example: Single Set

Example annotation for one squat set with three repetitions:

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern
baseline,,,20,60,false,squat,bilateral
rep,1,1,85,160,true,squat,bilateral
rep,1,2,170,245,true,squat,bilateral
rep,1,3,255,330,true,squat,bilateral
idle,,,331,370,false,squat,bilateral
```

## Example: Multiple Sets

Example annotation for one recording containing two squat sets:

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

## Example: Alternating Exercise

Example annotation for plank shoulder tap, where each rep alternates the active hand:

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis,exercise_type,pattern,starting_side
baseline,,,0,40,false,plank_shoulder_tap,alternating,right
rep,1,1,50,100,true,plank_shoulder_tap,alternating,right
rep,1,2,110,160,true,plank_shoulder_tap,alternating,right
rep,1,3,170,220,true,plank_shoulder_tap,alternating,right
rep,1,4,230,280,true,plank_shoulder_tap,alternating,right
idle,,,281,320,false,plank_shoulder_tap,alternating,right
```

`starting_side = right` means the right hand performs the tap on the first rep, the left hand on the second, and so on.

## Optional Phase Column

The `phase` column may be included for future compatibility.

Example:

```csv
segment_type,set_id,rep_id,phase,start_frame,end_frame,use_for_analysis
rep,1,1,,85,160,true
```

For the initial implementation, `phase` can remain empty.

Phase-level annotation should not be required.

## Missing Annotation Policy

If no annotation file is provided, the pipeline should not fail.

Default behavior:

```text
use_for_analysis = True for all frames
segment_type = full_sequence
set_id = None
rep_id = None
phase = None
exercise_type = None
pattern = bilateral
starting_side = None
```

The annotation report should record:

```text
annotation_provided = False
policy = use_full_sequence
num_total_frames
num_analysis_frames
```

This allows the pipeline to run even when no manual annotation exists.

When `exercise_type` is not declared, downstream exercise-aware logic falls back to a generic, exercise-agnostic mode.

## Annotation Provided Policy

If an annotation file is provided:

```text
1. all frames are initially set to use_for_analysis = False
2. frames inside annotated segments are updated according to the annotation file
3. frames outside annotated ranges remain excluded from analysis
4. exercise context columns are propagated to all frames inside their declared range
```

This prevents unmarked idle or invalid frames from being included accidentally.

## Overlap Policy

Overlapping annotation ranges should be treated as an error.

Example of invalid annotation:

```csv
segment_type,set_id,rep_id,start_frame,end_frame,use_for_analysis
rep,1,1,50,120,true
rep,1,2,100,180,true
```

The initial implementation should not silently overwrite overlapping segments.

It should raise an error or return a failed annotation validation report.

## Frame Index Policy

Manual annotations should be defined using the original frame indices from the pose CSV.

The annotation step should preserve the original `frame` column.

If needed later, a separate segment-level frame index can be added, but the original frame number should not be overwritten.

## Pipeline Role

The annotation file is prepared before running the pipeline.

Inside the pipeline, annotation is applied as a metadata layer immediately after validation, so that exercise context and rep boundaries are available to all subsequent modules.

```text
load pose CSV
→ validation
→ annotation mask application
→ preprocessing
→ normalization
→ motion attribution
→ later analysis modules
```

This order is intentional. Preprocessing reads `exercise_type` and `pattern` to decide whether to enable exercise-specific checks such as frame-level left-right swap detection. Motion attribution reads rep boundaries and exercise context to verify that each rep's active limb matches the expected pattern.

The key output of this step is an annotated dataframe.

```text
input:
pose dataframe
optional annotation file

output:
pose dataframe with annotation metadata columns
annotation report
```

## Initial Completion Criteria

The first annotation implementation is complete when:

```text
1. annotation CSV can be loaded
2. required annotation columns are checked
3. missing annotation falls back to full-sequence mode
4. provided annotation adds use_for_analysis, segment_type, set_id, rep_id, and phase columns
5. exercise context columns (exercise_type, pattern, starting_side) are populated when present
6. overlapping segments are detected
7. original frame numbers are preserved
8. annotation report is returned
```
