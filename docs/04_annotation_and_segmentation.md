# Annotation and Segmentation

## Purpose

In the current framework, segmentation is treated as an annotation-based frame selection step rather than a fully automatic movement detection algorithm.

The goal is to identify which frames should be used for movement analysis while preserving the original pose sequence.

## Design Principle

Segmentation should not remove frames from the dataframe.

Instead, it should add annotation columns such as:

```text
use_for_analysis
segment_type
rep_id
phase
```

This allows the full sequence to be preserved for visualization, debugging, baseline estimation, and later re-analysis.

## Manual Annotation

For early-stage development, analysis segments are manually annotated.

Example annotation file:

```csv
segment_type,rep_id,start_frame,end_frame,use_for_analysis
baseline,,20,60,false
rep,1,85,160,true
rep,2,170,245,true
rep,3,255,330,true
idle,,331,370,false
```

The pipeline applies this annotation to the pose dataframe.

Frames inside a segment with `use_for_analysis=true` are included in feature extraction.

Frames outside analysis segments are preserved but excluded from analysis statistics.

## Missing Annotation Policy

If no annotation file is provided, the pipeline should not fail.

Default behavior:

```text
use_for_analysis = True for all frames
segment_type = full_sequence
rep_id = None
phase = None
```

The report should record:

```text
annotation_provided = False
policy = use_full_sequence
```

This ensures that the pipeline can always run, even without manual segmentation.

## Processing Range vs Analysis Range

Two ranges should be conceptually separated.

```text
processing range:
- frames used for preprocessing, filtering, normalization, and visualization
- may include idle or preparation frames

analysis range:
- frames used for feature extraction and movement statistics
- defined by use_for_analysis=True
```

This is important because filtering and smoothing may require additional frames before and after the main movement to reduce boundary effects.

## Repetition-Level Analysis

For repeated exercises such as squats, each repetition can be annotated separately.

Example:

```csv
segment_type,rep_id,start_frame,bottom_frame,end_frame,use_for_analysis
rep,1,85,120,160,true
rep,2,170,205,245,true
rep,3,255,292,330,true
```

This enables both rep-level and session-level analysis.

Rep-level features may include:

```text
ROM
tempo
symmetry
stability
compensation
```

Session-level summaries may include:

```text
mean
standard deviation
worst repetition
fatigue trend
```

## Relationship to Automatic Segmentation

Automatic segmentation is not the primary focus of the current research stage.

The initial implementation focuses on reliable annotation application.

Automatic or semi-automatic segmentation may be added later using exercise-specific signals such as:

```text
hip height
knee angle
trunk angle
COM trajectory
```

## Pipeline Role

The annotation step is expected to run after validation, preprocessing, and normalization.

Recommended order:

```text
load pose CSV
-> validation
-> preprocessing
-> normalization
-> annotation mask application
-> feature extraction
```

Feature extraction should use only frames where:

```text
use_for_analysis == True
```
