# Notebook Guide

This directory contains runnable notebooks for checking the movement analysis
pipeline after cloning the repository.

## Current Public Path

The code-backed evaluation path is the base ①-⑩ pipeline:

```text
00 environment check
01 data loading
02 validation
03 raw visualization
04 normalization
05 annotation mask
06 exercise definition
07 preprocessing
08 phase segmentation
09 motion attribution
10 feature extraction
11 biomechanical proxy
12 biomarker scoring
13 user movement evaluation
14 robustness simulation
```

For a new user, start with:

```text
00_environment_check.ipynb
13_user_movement_evaluation.ipynb
```

For the current local research review, open the individual 01-12 notebooks in
order when you need to inspect each stage on the p01 squat recording.

## Important Boundary

The former closed-chain stance-corridor review notebook was a p01 squat research
surface for corrected-3D-hypothesis exploration. Its coordinate solver has not
yet been promoted to `src/movement/`, so it is not part of the public evaluation
notebook path.

Current public scoring uses `norm` coordinates. Corrected depth remains excluded
from feature/scoring use through `feature_depth_gravity: 0.0`.

## User Inputs

The current local notebook defaults start from:

```text
data/pose/mediapipe/no_consent/20260517/p01_squat_set1_output_pose.csv
data/pose/mediapipe/no_consent/20260517/p01_squat_set1_annotation.csv
```

If present, `p01_squat_set1_phase_split.csv` is loaded only as a
recording-specific visual/QC guideline in the phase-segmentation notebook. It is
not confirmed phase annotation and is not used for scoring.

To evaluate another movement recording, edit the pose CSV path, optional
annotation CSV path, and `EXERCISE_ID` in the input cell of the relevant
notebook or in `13_user_movement_evaluation.ipynb`.

The p01 recording is real review data, not a clean synthetic baseline. Validation
or phase-segmentation failures in the stage notebooks should be read as
data-quality or readiness provenance unless a structural assertion fails.

## Outputs

Generated files should go under `data/processed/`. This directory is ignored by
git unless a future documented example artifact policy says otherwise.
