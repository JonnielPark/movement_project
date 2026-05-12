# Notebooks

These notebooks are ordered as step-by-step checks for a new user after cloning and installing the package.

They are not ordered by development history. They are ordered by expected user verification flow.

## Order

```text
00_environment_check.ipynb
01_data_loading_test.ipynb
02_validation_test.ipynb
03_raw_visualization_test.ipynb
04_normalization_test.ipynb
05_annotation_mask_test.ipynb
06_exercise_definition_test.ipynb
07_preprocessing_test.ipynb
08_phase_segmentation_test.ipynb
09_motion_attribution_test.ipynb
10_feature_extraction_test.ipynb
11_biomechanical_proxy_test.ipynb
12_biomarker_scoring_test.ipynb
13_pipeline_end_to_end_test.ipynb
14_simulation_robustness_test.ipynb
15_real_squat_import_visualization_test.ipynb
```

## Implementation Status

| Notebook | Module | Status |
|----------|--------|--------|
| 00 | environment | implemented |
| 01 | io | implemented |
| 02 | validation | implemented |
| 03 | visualization | implemented |
| 04 | normalization + floor-relative filter | implemented; optional floor-relative synthetic check included and disabled by default |
| 05 | annotation | implemented |
| 06 | exercise_definition | implemented |
| 07 | preprocessing | implemented |
| 08 | phase segmentation | implemented |
| 09 | motion_attribution | implemented |
| 10 | features | implemented |
| 11 | biomech | implemented |
| 12 | biomarker scoring | implemented |
| 13 | pipeline end-to-end | partial (implemented stages only) |
| 14 | simulation robustness | not yet implemented |
| 15 | real squat import + raw/normalized/floor visualization + normalization | implemented; current floor-relative review gate |

Notebook `04` contains the reusable synthetic-sample check for the optional floor-relative normalization filter.
Notebook `15` is the current real-sample entry point and floor-relative review gate.
