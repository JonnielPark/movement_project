# Notebook Guide

This directory is organized by workflow role so a new user can start from a
pose CSV without guessing which notebook to open.

## Folder Map

```text
00_setup/
    setup_00_environment_check.ipynb
    setup_01_data_loading_test.ipynb
    setup_02_raw_visualization_test.ipynb

10_manual_preparation/
    16_exercise_authoring_test.ipynb
    annotation authoring/review notebooks will live here when promoted

20_stage_checks/
    01_validation_test.ipynb
    02_annotation_mask_test.ipynb
    03_exercise_definition_test.ipynb
    04_preprocessing_test.ipynb
    05_normalization_test.ipynb
    06_canonicalization_test.ipynb
    07_segmentation_test.ipynb
    08_motion_attribution_test.ipynb
    09_feature_extraction_test.ipynb
    10_biomechanical_proxy_test.ipynb
    11_biomarker_scoring_test.ipynb
    12_visualization_test.ipynb
    13_simulation_robustness_test.ipynb

30_user_evaluation/
    14_user_movement_evaluation.ipynb

90_local_research_review/
    15_real_squat_import_visualization_test.ipynb
```

## Modes

```text
setup_check
    Environment, file path, and raw data checks. These are safe first steps.

auto_check
    Runs a pipeline stage against already prepared inputs. These notebooks
    should be executable in order once pose/annotation/exercise inputs exist.

manual_preparation
    Creates or reviews artifacts that require user judgment, such as annotation
    ranges or exercise-definition YAML drafts. Run these before downstream
    automated checks when the required artifact does not already exist.

manual_review
    Visual/QC review gate. The notebook can run automatically, but the result
    needs human inspection before it is trusted downstream.

local_research_review
    Researcher-local surfaces for p01 or temporary investigations. These are not
    part of the public evaluation path.
```

## New User Path

1. Put a MediaPipe-style pose CSV under `data/pose/...`.
2. If available, put a matching annotation CSV beside the pose CSV.
3. Start with setup:

```text
00_setup/setup_00_environment_check.ipynb
00_setup/setup_01_data_loading_test.ipynb
00_setup/setup_02_raw_visualization_test.ipynb
```

4. If manual artifacts are missing, prepare them first:

```text
10_manual_preparation/16_exercise_authoring_test.ipynb
```

Annotation authoring/review should also live under `10_manual_preparation/`
once promoted. For now, `20_stage_checks/02_annotation_mask_test.ipynb` validates
and applies an existing annotation CSV; it is not an annotation authoring UI.

5. Run stage checks as needed:

```text
20_stage_checks/01_validation_test.ipynb
20_stage_checks/02_annotation_mask_test.ipynb
20_stage_checks/03_exercise_definition_test.ipynb
...
20_stage_checks/13_simulation_robustness_test.ipynb
```

6. For the public end-to-end route, open:

```text
30_user_evaluation/14_user_movement_evaluation.ipynb
```

Edit the pose CSV path, optional annotation CSV path, participant YAML path, and
`EXERCISE_ID` in that notebook's input cell.

## Manual UI Direction

Notebook-based dropdown or checkbox selection is feasible for authoring
exercise definitions. The UI should generate a small authoring spec first, then
use `src/movement/definitions/exercise_authoring.py` to preview and export draft
YAML under `data/processed/authoring_drafts/<exercise_id>/`.

The widget UI must remain a preparation surface. Draft YAML requires researcher
review before it is promoted to canonical files under `data/definitions/` or
`data/protocols/`.

## Current Defaults

The local default notebooks use:

```text
data/pose/mediapipe/no_consent/20260517/p01_squat_set1_output_pose.csv
data/pose/mediapipe/no_consent/20260517/p01_squat_set1_annotation.csv
data/participants/no_consent/p01.yaml
```

If present, `p01_squat_set1_phase_split.csv` is loaded only as a
recording-specific visual/QC guideline in the segmentation notebook. It is not
confirmed phase annotation and is not used for scoring.

The participant YAML is de-identified provenance/review metadata. It records
anthropometry and common-subject skeleton selection but is not used for scoring
or coordinate rescaling.

The p01 recording is real review data, not a clean synthetic baseline. Validation
or phase-segmentation failures in stage notebooks should be read as data-quality
or readiness provenance unless a structural assertion fails.

## Outputs

Generated files should go under `data/processed/`. This directory is ignored by
git unless a future documented example artifact policy says otherwise.
