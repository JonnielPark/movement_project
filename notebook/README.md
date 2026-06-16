# Notebook Guide

This directory contains runnable notebooks for checking the movement analysis
pipeline after cloning the repository.

## Current Public Path

The code-backed evaluation path is the base ①-⑪ pipeline:

```text
Setup / data inspection
setup_00_environment_check.ipynb
setup_01_data_loading_test.ipynb
setup_02_raw_visualization_test.ipynb

Pipeline stage checks
01 validation
02 annotation mask
03 exercise definition
04 preprocessing
05 normalization
06 canonicalization
07 segmentation
08 motion attribution
09 feature extraction
10 biomechanical proxy
11 biomarker scoring
12 visualization
13 robustness simulation
14 user movement evaluation
```

For a new user, start with:

```text
setup_00_environment_check.ipynb
setup_01_data_loading_test.ipynb
01_validation_test.ipynb
14_user_movement_evaluation.ipynb
```

For the current local research review, open the individual stage notebooks in
order when you need to inspect each stage on the p01 squat recording.

## Important Boundary

The former closed-chain stance-corridor review notebook was a p01 squat research
surface for corrected-3D-hypothesis exploration. Its coordinate solver has not
yet been promoted to `src/movement/`, so it is not part of the public evaluation
notebook path.

Current public scoring uses `norm` coordinates. Corrected-depth candidates remain
⑥ canonicalization candidate evidence only; any nonzero score gravity is deferred to a later
scoring-policy task.

## User Inputs

The current local notebook defaults start from:

```text
data/pose/mediapipe/no_consent/20260517/p01_squat_set1_output_pose.csv
data/pose/mediapipe/no_consent/20260517/p01_squat_set1_annotation.csv
data/participants/no_consent/p01.yaml
```

If present, `p01_squat_set1_phase_split.csv` is loaded only as a
recording-specific visual/QC guideline in the phase-segmentation notebook. It is
not confirmed phase annotation and is not used for scoring.

The participant YAML is de-identified provenance/review metadata. It records
anthropometry and common-subject skeleton selection but is not used for scoring
or coordinate rescaling.

To evaluate another movement recording, edit the pose CSV path, optional
annotation CSV path, and `EXERCISE_ID` in the input cell of the relevant
notebook or in `14_user_movement_evaluation.ipynb`.

The p01 recording is real review data, not a clean synthetic baseline. Validation
or phase-segmentation failures in the stage notebooks should be read as
data-quality or readiness provenance unless a structural assertion fails.

## Outputs

Generated files should go under `data/processed/`. This directory is ignored by
git unless a future documented example artifact policy says otherwise.
