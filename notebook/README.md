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

Then open the individual 01-12 notebooks only when you need to inspect a
specific stage.

## Important Boundary

The former closed-chain stance-corridor review notebook was a p01 squat research
surface for corrected-3D-hypothesis exploration. Its coordinate solver has not
yet been promoted to `src/movement/`, so it is not part of the public evaluation
notebook path.

Current public scoring uses `norm` coordinates. Corrected depth remains excluded
from feature/scoring use through `feature_depth_gravity: 0.0`.

## User Inputs

The user-facing evaluation notebook starts from:

```text
data/pose/sample/mediapipe_squat_synthetic.csv
data/pose/sample/mediapipe_squat_synthetic_annotation.csv
```

To evaluate another movement recording, edit the pose CSV path, optional
annotation CSV path, and `EXERCISE_ID` in the input cell of
`13_user_movement_evaluation.ipynb`.

## Outputs

Generated files should go under `data/processed/`. This directory is ignored by
git unless a future documented example artifact policy says otherwise.
